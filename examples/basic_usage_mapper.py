#!/usr/bin/env python3
"""Basic usage example for the EDAM MCP server."""

import asyncio
import logging
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from edam_mcp.models.mapping import EDAMConceptType
    from edam_mcp.tools.mapping import map_description_to_concepts
except ImportError as e:
    print(f"Error importing edam_mcp: {e}")
    print("Make sure you have installed the package in development mode:")
    print("  uv sync --dev")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def example_mapping():
    """Example of mapping descriptions to EDAM concepts."""
    print("=== EDAM Concept Mapping Example ===\n")

    # Bioconductor Spectra package, mapped to one EDAM branch at a time
    spectra = (
        "The Spectra package defines an efficient infrastructure for storing and handling mass spectrometry "
        "spectra and functionality to subset, process, visualize and compare spectra data."
    )

    # Example descriptions to map, optionally restricted to one EDAM branch
    descriptions = [
        ("sequence alignment tool", None),
        ("FASTQ file format", None),
        ("gene expression analysis", None),
        ("protein structure prediction", None),
        ("metabolomics data processing", None),
        (spectra, EDAMConceptType.OPERATION),
        (spectra, EDAMConceptType.FORMAT),
    ]

    for description, concept_type in descriptions:
        print(f"Mapping [{concept_type or 'all types'}]: {description}")

        try:
            response = await map_description_to_concepts(
                description=description,
                context="bioinformatics tool",
                max_results=3,
                min_confidence=0.5,
                concept_type=concept_type,
            )

            if response.matches:
                print(f"  Found {response.total_matches} matches:")
                for match in response.matches:
                    print(f"    - {match.concept_label} (confidence: {match.confidence:.2f})")
                    print(f"      URI: {match.concept_uri}")
                    print(f"      Type: {match.concept_type}")
            else:
                print("  No matches found")

        except Exception as e:
            print(f"  Error: {e}")


async def main():
    """Run the examples."""
    print("EDAM MCP Server - Basic Usage Examples - Mapping")
    print("=" * 50)

    # Run mapping example
    await example_mapping()

    print("Examples completed!")


if __name__ == "__main__":
    asyncio.run(main())
