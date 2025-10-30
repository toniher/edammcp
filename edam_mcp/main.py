"""Main entry point for the EDAM MCP server."""

import logging
import sys

from fastmcp import FastMCP
from fastmcp.server import Context

from .config import settings
from .models.requests import MappingRequest, SuggestionRequest
from .models.responses import MappingResponse, SuggestionResponse
from .tools import map_to_edam_concept, suggest_new_concept

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def create_server() -> FastMCP:
    """Create and configure the FastMCP server.

    Returns:
        Configured FastMCP server instance.
    """
    # Create server
    mcp = FastMCP("edam-mcp")

    # Register tools using decorators
    # TODO: Check whether context is actually needed
    @mcp.tool
    async def map_to_edam_concept_tool(
        description: str,
        context: str | None = None,
        max_results: str | None = "5",
        min_confidence: str | None = "0.5",
        tool_context: Context = None,
    ) -> MappingResponse:
        request = MappingRequest(
            description=description,
            context=context,
            max_results=int(max_results),
            min_confidence=float(min_confidence),
        )
        return await map_to_edam_concept(request, tool_context)

    @mcp.tool
    async def suggest_new_concept_tool(
        description: str,
        concept_type: str | None = None,
        parent_concept: str | None = None,
        rationale: str | None = None,
        tool_context: Context = None,
    ) -> SuggestionResponse:
        request = SuggestionRequest(
            description=description,
            concept_type=concept_type,
            parent_concept=parent_concept,
            rationale=rationale,
        )
        return await suggest_new_concept(request, tool_context)

    return mcp


def main() -> None:
    """Main entry point for running the server."""
    try:
        # Create server
        mcp = create_server()

        # Run server
        mcp.run()

    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
