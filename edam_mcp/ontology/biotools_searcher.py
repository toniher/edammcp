import logging
from time import sleep

import requests

from ..models.biotools import BiotoolsMatch

logger = logging.getLogger(__name__)

API_URL = "https://bio.tools/api/t/"
FILTER_KEYS = {"topic": "topicID", "operation": "operationID", "data": "dataTypeID", "format": "dataFormatID"}


def _uris(items) -> list[str]:
    return [x["uri"] for x in items or []]


def _to_match(tool: dict) -> BiotoolsMatch | None:
    """Build a match from a bio.tools entry, or None if it has no EDAM annotations."""
    topics = _uris(tool.get("topic"))
    operations, data, formats = [], [], []
    for fn in tool.get("function") or []:
        operations += _uris(fn.get("operation"))
        for io in (fn.get("input") or []) + (fn.get("output") or []):
            if io.get("data"):
                data.append(io["data"]["uri"])
            formats += _uris(io.get("format"))

    if not (topics or operations or data or formats):
        return None

    return BiotoolsMatch(
        name=tool["name"],
        description=tool.get("description") or "",
        biotools_link=f"https://bio.tools/{tool['biotoolsID']}",
        topic_terms=sorted(set(topics)),
        operation_terms=sorted(set(operations)),
        data_terms=sorted(set(data)),
        format_terms=sorted(set(formats)),
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
) -> list[BiotoolsMatch]:
    """Search for tools in bio.tools whose name or description contains the exact phrase seed.

    Only tools annotated with at least one EDAM term are returned.

    Args:
        seed: Textual phrase to search in tool names and descriptions.
        max_results: Maximum number of matches to return.

    Returns:
        List of bio.tools tools that matched the phrase
    """
    matches: list[BiotoolsMatch] = []
    total = _search({"q": f'"{seed}"'}, max_results, matches, set())
    logger.info(f"There are {total} tools in bio.tools related to your keyword, displaying at most {max_results}")
    return matches[:max_results]


def query_by_edam_terms(
    edam_terms: list[str],
    max_results: int = 10,
) -> list[BiotoolsMatch]:
    """Search for tools in bio.tools annotated with all of the given EDAM terms.

    bio.tools only combines filters of different categories, so at most one term per category is allowed.

    Args:
        edam_terms: EDAM concept URIs (topic, operation, data or format), at most one per category.
        max_results: Maximum number of matches to return.

    Returns:
        List of bio.tools tools annotated with all of the terms

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
    logger.info(f"There are {total} tools in bio.tools for the given EDAM terms, displaying at most {max_results}")
    return matches[:max_results]
