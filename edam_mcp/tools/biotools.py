import asyncio

from fastmcp.server import Context

from ..models.biotools import BiotoolsQueryResponse, BiotoolsQueryTermsRequest, BiotoolsQueryTextRequest
from ..ontology import biotools_searcher


async def query_biotools_by_text(
    request: BiotoolsQueryTextRequest,
    context: Context,
) -> BiotoolsQueryResponse:
    """Search for tools in Biotools repository.

    This tool takes a textual description as seed and performs a query in the Biotools database. It returns matches
    with name, description, biotools database url, and list of concepts in the four EDAM ontology categories (topic, operation, format and data).

    Args:
        request: Biotools query request containing search seed and parameters.
        context: MCP context for logging and progress reporting.

    Returns:
        Biotools query response with matching tools and their associated EDAM terms.
    """
    try:
        context.info(f"Query keyword: {request.seed[:100]}...")
        matches = await asyncio.to_thread(biotools_searcher.query_by_text, request.seed, request.max_results)
        context.info(f"Found {len(matches)} tool matches")
        return BiotoolsQueryResponse(matches=matches, total_matches=len(matches))

    except Exception as e:
        context.error(f"Error in biotools query: {e}")
        raise


async def query_biotools_by_edam_terms(
    request: BiotoolsQueryTermsRequest,
    context: Context,
) -> BiotoolsQueryResponse:
    """Search for tools in Biotools repository.

    This tool takes EDAM concept URIs (at most one per category) and searches the Biotools database for tools annotated with all of them. It returns matches
    with name, description, biotools database url, and list of concepts in the four EDAM ontology categories (topic, operation, format and data).

    Args:
        request: Biotools query request containing EDAM term URIs and parameters.
        context: MCP context for logging and progress reporting.

    Returns:
        Biotools query response with matching tools and their associated EDAM terms.
    """
    try:
        context.info(f"Query EDAM terms: {request.edam_terms[:5]}...")
        matches = await asyncio.to_thread(
            biotools_searcher.query_by_edam_terms, request.edam_terms, request.max_results
        )
        context.info(f"Found {len(matches)} tool matches")
        return BiotoolsQueryResponse(matches=matches, total_matches=len(matches))

    except Exception as e:
        context.error(f"Error in biotools query: {e}")
        raise
