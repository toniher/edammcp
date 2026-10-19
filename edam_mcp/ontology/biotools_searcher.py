import re
import threading
from time import sleep

import requests

from edam_mcp.ontology.loader import OntologyLoader

from ..models.biotools import BiotoolsMatch

EDAM_LOADER = OntologyLoader()
_load_lock = threading.Lock()
_loaded = False

API_URL = "https://bio.tools/api/t/"
EDAM_URI = re.compile(r"https?://edamontology\.org/((topic|operation|data|format)_\d+)")
FILTER_KEYS = {"topic": "topicID", "operation": "operationID", "data": "dataTypeID", "format": "dataFormatID"}

def _is_obsolete(uri: str) -> bool:
    """True if uri is obsolete or unknown to EDAM. Loads the ontology on first use, retrying after a failure."""
    global _loaded
    with _load_lock:  # tools run in worker threads; readers wait until the load is complete
        if not _loaded:
            if not EDAM_LOADER.load_ontology():
                raise RuntimeError("EDAM ontology could not be loaded")
            _loaded = True
    return (EDAM_LOADER.concepts.get(uri) or {}).get("obsolete", True)


def _terms(items) -> dict[str, dict]:
    """Map EDAM term URI to its label and obsolete flag, deduplicated."""
    return {x["uri"]: {"label": x.get("term"), "obsolete": _is_obsolete(x["uri"])} for x in items or []}


def _io_terms(functions: list[dict], key: str) -> tuple[dict[str, dict], dict[str, dict]]:
    """Data and format terms of the inputs or outputs (key) of all functions."""
    ios = [io for fn in functions for io in fn.get(key) or []]
    formats = [f for io in ios for f in io.get("format") or []]
    return _terms([io["data"] for io in ios if io.get("data")]), _terms(formats)


def _to_match(tool: dict) -> BiotoolsMatch:
    """Build a match from a bio.tools entry; term fields stay empty for unannotated tools."""
    functions = tool.get("function") or []
    terms = {
        "topic_terms": _terms(tool.get("topic")),
        "operation_terms": _terms([op for fn in functions for op in fn.get("operation") or []]),
    }
    terms["input_data_terms"], terms["input_format_terms"] = _io_terms(functions, "input")
    terms["output_data_terms"], terms["output_format_terms"] = _io_terms(functions, "output")

    return BiotoolsMatch(
        name=tool["name"],
        description=tool.get("description") or "",
        biotools_link=f"https://bio.tools/{tool['biotoolsID']}",
        **terms,
    )


def _search(params: dict, max_results: int, matches: list[BiotoolsMatch], seen: set[str]) -> int:
    """Page through bio.tools results for params, appending new matches to matches.

    Returns the total number of tools bio.tools reports for the query.
    """
    page = 1
    while True:
        r = requests.get(
            API_URL,
            params={**params, "format": "json", "per_page": 100, "page": page},
            timeout=(3.05, 30),
        )
        r.raise_for_status()
        data = r.json()

        for tool in data["list"]:
            if tool["biotoolsID"] in seen:
                continue
            seen.add(tool["biotoolsID"])
            matches.append(_to_match(tool))

        if len(matches) >= max_results or not data.get("next"):
            return data["count"]
        page += 1
        sleep(1)  # be polite to the bio.tools API between pages

def _search_by_id(biotools_id: str, matches: list[BiotoolsMatch]) -> int:
    r = requests.get(f"{API_URL}{biotools_id}", params={"format": "json"}, timeout=(3.05, 30))
    if r.status_code == 404:
        return 0
    r.raise_for_status()
    matches.append(_to_match(r.json()))
    return 1

def query_by_text(
    seed: str,
    max_results: int = 10,
) -> tuple[list[BiotoolsMatch], int]:
    """Search for tools in bio.tools matching the keywords in seed, ranked by bio.tools relevance.

    Tools without EDAM annotations are returned with empty term fields.

    Args:
        seed: Keywords or tool name to search in bio.tools.
        max_results: Maximum number of matches to return.

    Returns:
        Matched bio.tools tools, and the total number of tools bio.tools reports for the query
    """
    matches: list[BiotoolsMatch] = []
    total = _search({"q": seed, "sort": "score"}, max_results, matches, set())
    return matches[:max_results], total

def query_by_text_exact_match(name: str | None = None, biotools_id: str | None = None) -> tuple[list[BiotoolsMatch], int]:
    """Search for tools in bio.tools matching the name or the biotools_id identifier in the repository.

    Args:
        name: tool name to search in bio.tools.
        biotools_id: biotools tool identifier to search in bio.tools.

    Returns:
        Matched bio.tools tools, and the total number of tools bio.tools reports for the query
    """
    if name is None and biotools_id is None:
        raise ValueError("You must specify either the tool name or its database identifier")

    matches: list[BiotoolsMatch] = []
    if name is None:
        total = _search_by_id(re.sub(r"['\"]", "", biotools_id), matches)
    else:
        params = {"name": '"' + re.sub(r"['\"]", "", name) + '"'}
        if biotools_id is not None:
            params["biotoolsID"] = '"' + re.sub(r"['\"]", "", biotools_id) + '"'
        total = _search(params, 10, matches, set())
    return matches, total


def query_by_edam_terms(
    edam_terms: list[str],
    max_results: int = 10,
) -> tuple[list[BiotoolsMatch], int]:
    """Search for tools in bio.tools annotated with all of the given EDAM terms.

    bio.tools only combines filters of different categories, so at most one term per category is allowed.

    Args:
        edam_terms: EDAM concept URIs (topic, operation, data or format), at most one per category.
        max_results: Maximum number of matches to return.

    Returns:
        Matched bio.tools tools annotated with all of the terms, and the total number bio.tools reports

    Raises:
        ValueError: If a URI is not an EDAM topic, operation, data or format concept,
            or two terms share a category.
    """
    bad = [u for u in edam_terms if _is_obsolete(u)]
    if bad:
        raise ValueError(f"Unknown or obsolete EDAM terms: {', '.join(bad)}")

    params: dict[str, str] = {}
    for uri in edam_terms:
        m = EDAM_URI.fullmatch(uri)
        if not m:
            raise ValueError(f"Not an EDAM topic/operation/data/format URI: {uri}")
        term, category = m.groups()
        key = FILTER_KEYS[category]
        # Quoted for an exact match; unquoted, bio.tools does a loose text match on the ID
        if params.setdefault(key, f'"{term}"') != f'"{term}"':
            raise ValueError(
                f'bio.tools can only combine one {category} term per query, got {params[key]} and "{term}"'
            )

    matches: list[BiotoolsMatch] = []
    total = _search(params, max_results, matches, set())
    return matches[:max_results], total
