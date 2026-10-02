"""ChromaDB cache must follow ontology changes (issue #65)."""

from unittest.mock import Mock, patch

import numpy as np

from edam_mcp.ontology.matcher import ConceptMatcher


def _concept(label, definition):
    return {"label": label, "definition": definition, "synonyms": [], "type": "Format"}


def test_chromadb_cache_follows_ontology_changes(tmp_path):
    model = Mock()
    model.encode.side_effect = lambda texts, **_: np.random.rand(len(texts), 4)
    loader = Mock()
    loader.concepts = {"a": _concept("A", "old text"), "b": _concept("B", "kept"), "c": _concept("C", "removed")}

    with patch("chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction", return_value=None):
        matcher = ConceptMatcher(loader)
        matcher.use_chromadb = True
        matcher.chroma_db = str(tmp_path / "default.db")
        matcher.embedding_model = model
        matcher._build_embeddings()

        loader.concepts = {"a": _concept("A", "new text"), "b": _concept("B", "kept"), "d": _concept("D", "added")}
        matcher._build_embeddings()

    import chromadb

    stored = chromadb.PersistentClient(path=matcher.chroma_db).get_collection("concept_embeddings").get()
    assert sorted(stored["ids"]) == ["a", "b", "d"]
    assert "new text" in dict(zip(stored["ids"], stored["documents"]))["a"]
    # Second build only embeds the changed and the new concept
    assert len(model.encode.call_args_list[1].args[0]) == 2
