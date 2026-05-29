from drummer.api.mock import wikidata


def test_entity_returns_real_scalar_fields() -> None:
    result = wikidata.execute('{ entity(id: "Q42") { id label instanceOf { label } } }')
    assert "errors" not in result
    entity = result["data"]["entity"]
    assert entity["id"] == "Q42"
    assert entity["label"] == "Douglas Adams"
    assert {t["label"] for t in entity["instanceOf"]} == {"human"}


def test_nested_relation_resolves_end_to_end() -> None:
    query = (
        "query($id: ID!) { entity(id: $id) { label "
        "author { label placeOfBirth { label country { label } } } } }"
    )
    result = wikidata.execute(query, {"id": "Q3107329"})
    assert "errors" not in result
    entity = result["data"]["entity"]
    assert entity["author"]["label"] == "Douglas Adams"
    assert entity["author"]["placeOfBirth"]["label"] == "Cambridge"
    assert entity["author"]["placeOfBirth"]["country"]["label"] == "United Kingdom"


def test_search_matches_label_substring() -> None:
    result = wikidata.execute('{ search(term: "adams") { id } }')
    ids = {e["id"] for e in result["data"]["search"]}
    assert "Q42" in ids


def test_unknown_entity_returns_null() -> None:
    result = wikidata.execute('{ entity(id: "Q0") { label } }')
    assert result["data"]["entity"] is None


def test_malformed_query_returns_errors() -> None:
    result = wikidata.execute("{ entity { label } }")  # missing required id arg
    assert "errors" in result
    assert result["data"] is None


def test_introspection_returns_schema() -> None:
    result = wikidata.execute("{ __schema { queryType { name } } }")
    assert result["data"]["__schema"]["queryType"]["name"] == "Query"


def test_snapshot_has_no_dangling_relation_refs() -> None:
    index = wikidata.INDEX
    list_fields = ("instanceOf", "notableWork")
    single_fields = ("author", "placeOfBirth", "country")
    for entity in index.values():
        for field in list_fields:
            for ref in entity.get(field, []):
                assert ref in index, f"{entity['id']}.{field} -> missing {ref}"
        for field in single_fields:
            ref = entity.get(field)
            assert ref is None or ref in index, f"{entity['id']}.{field} -> missing {ref}"
