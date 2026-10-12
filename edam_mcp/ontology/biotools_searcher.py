from time import sleep

import requests

from ..models.biotools import BiotoolsMatch

API_URL = "https://bio.tools/api/t/"
FILTER_KEYS = {"topic": "topicID", "operation": "operationID", "data": "dataTypeID", "format": "dataFormatID"}


def _terms(items) -> dict[str, str]:
    """Map EDAM term URI to label, deduplicated."""
    return {x["uri"]: x.get("term") or "" for x in items or []}


def _io_terms(functions: list[dict], key: str) -> tuple[dict[str, str], dict[str, str]]:
    """Data and format terms of the inputs or outputs (key) of all functions."""
    ios = [io for fn in functions for io in fn.get(key) or []]
    formats = [f for io in ios for f in io.get("format") or []]
    return _terms([io["data"] for io in ios if io.get("data")]), _terms(formats)


def _to_match(tool: dict) -> BiotoolsMatch | None:
    """Build a match from a bio.tools entry, or None if it has no EDAM annotations."""
    functions = tool.get("function") or []
    terms = {
        "topic_terms": _terms(tool.get("topic")),
        "operation_terms": _terms([op for fn in functions for op in fn.get("operation") or []]),
    }
    terms["input_data_terms"], terms["input_format_terms"] = _io_terms(functions, "input")
    terms["output_data_terms"], terms["output_format_terms"] = _io_terms(functions, "output")

    if not any(terms.values()):
        return None

    return BiotoolsMatch(
        name=tool["name"],
        description=tool.get("description") or "",
        biotools_link=f"https://bio.tools/{tool['biotoolsID']}",
        **terms,
    )


def _search(params: dict, max_results: int, matches: list[BiotoolsMatch], seen: set[str]) -> int:
    """Page through bio.tools results for params, appending new annotated matches to matches.

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
            match = _to_match(tool)
            if match:
                matches.append(match)

        if len(matches) >= max_results or not data.get("next"):
            return data["count"]
        page += 1
        sleep(1)  # be polite to the bio.tools API between pages


def query_by_text(
    seed: str,
    max_results: int = 10,
) -> tuple[list[BiotoolsMatch], int]:
    """Search for tools in bio.tools matching the keywords in seed, ranked by bio.tools relevance.

    Only tools annotated with at least one EDAM term are returned.

    Args:
        seed: Keywords or tool name to search in bio.tools.
        max_results: Maximum number of matches to return.

    Returns:
        Matched bio.tools tools, and the total number of tools bio.tools reports for the query
    """
    matches: list[BiotoolsMatch] = []
    total = _search({"q": seed, "sort": "score"}, max_results, matches, set())
    return matches[:max_results], total


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
    params: dict[str, str] = {}
    for uri in edam_terms:
        term = uri.rstrip("/").split("/")[-1]
        category = term.split("_")[0]
        if category not in FILTER_KEYS:
            raise ValueError(f"Not an EDAM topic/operation/data/format URI: {uri}")
        key = FILTER_KEYS[category]
        # Quoted for an exact match; unquoted, bio.tools does a loose text match on the ID
        if params.setdefault(key, f'"{term}"') != f'"{term}"':
            raise ValueError(f"bio.tools can only combine one {category} term per query, got {params[key]} and {term}")

    matches: list[BiotoolsMatch] = []
    total = _search(params, max_results, matches, set())
    return matches[:max_results], total
