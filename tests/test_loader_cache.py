import pickle

import pytest

from edam_mcp.ontology.loader import OntologyLoader


@pytest.mark.parametrize(("record", "ok"), [({"label": "x"}, False), ({"label": "x", "obsolete": False}, True)])
def test_load_cache_requires_obsolete_field(tmp_path, record, ok):
    loader = OntologyLoader()
    loader.cache_dir = str(tmp_path)
    concepts_path, types_path, _ = loader._cache_paths()
    for path, data in [(concepts_path, {"http://edamontology.org/topic_1": record}), (types_path, set())]:
        with open(path, "wb") as f:
            pickle.dump(data, f)

    if ok:
        loader._load_cache()
        assert "http://edamontology.org/topic_1" in loader.concepts
    else:
        with pytest.raises(ValueError, match="obsolete"):
            loader._load_cache()
