"""Deprecated EDAM classes are skipped unless EDAM_INCLUDE_DEPRECATED is set (issue #56)."""

from edam_mcp.config import settings
from edam_mcp.ontology.loader import OntologyLoader

OWL = """<?xml version="1.0"?>
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
         xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#"
         xmlns:owl="http://www.w3.org/2002/07/owl#">
  <owl:Class rdf:about="http://edamontology.org/format_1"><rdfs:label>Live</rdfs:label></owl:Class>
  <owl:Class rdf:about="http://edamontology.org/format_2">
    <rdfs:label>Old</rdfs:label>
    <owl:deprecated>1.8</owl:deprecated>
    <owl:deprecated rdf:datatype="http://www.w3.org/2001/XMLSchema#boolean">true</owl:deprecated>
  </owl:Class>
</rdf:RDF>
"""


def test_deprecated_concepts_are_opt_in(tmp_path, monkeypatch):
    owl = tmp_path / "edam.owl"
    owl.write_text(OWL)
    monkeypatch.setattr(settings, "cache_dir", str(tmp_path / "cache"))

    def load():
        loader = OntologyLoader(ontology_url=str(owl))
        assert loader.load_ontology()
        return sorted(c["label"] for c in loader.concepts.values())

    assert load() == ["Live"]
    monkeypatch.setattr(settings, "include_deprecated", True)
    owl.unlink()  # second load must come from the cache, which kept both
    assert load() == ["Live", "Old"]
