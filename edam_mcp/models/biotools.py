"""Models for Biotools Query functionality."""

from pydantic import BaseModel, Field


class BiotoolsQueryTextRequest(BaseModel):
    """Request model for biotools query by text."""

    seed: str = Field(
        ...,
        description="Search textual keyword to search in tool names and descriptions.",
        min_length=1,
        max_length=10000,
    )

    max_results: int = Field(10, ge=1, le=100, description="Maximum number of matches to return")


class BiotoolsQueryTermsRequest(BaseModel):
    """Request model for biotools query by EDAM terms."""

    edam_terms: list[str] = Field(
        ...,
        min_length=1,
        max_length=4,
        description="EDAM term URIs that every returned tool must be annotated with, at most one per category (topic, operation, data, format)",
    )

    max_results: int = Field(10, ge=1, le=100, description="Maximum number of matches to return")


class BiotoolsMatch(BaseModel):
    """Represents a query match item (tool) with the name, description and the edam terms found for the ontology categories."""

    name: str = Field(..., description="Tool name")

    description: str = Field(..., description="Tool description")

    biotools_link: str = Field(..., description="Tool link in biotools")

    topic_terms: list[str] = Field(
        default_factory=list, description="List of uris of the EDAM terms belonging to topic category"
    )

    operation_terms: list[str] = Field(
        default_factory=list, description="List of uris of the EDAM terms belonging to operation category"
    )

    data_terms: list[str] = Field(
        default_factory=list, description="List of uris of the EDAM terms belonging to data category"
    )

    format_terms: list[str] = Field(
        default_factory=list, description="List of uris of the EDAM terms belonging to format category"
    )


class BiotoolsQueryResponse(BaseModel):
    """Response model for biotools query results."""

    matches: list[BiotoolsMatch] = Field(..., description="List of matched tools in biotools database")

    total_matches: int = Field(..., description="Total number of matches found")
