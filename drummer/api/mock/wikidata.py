import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from graphql import GraphQLResolveInfo, build_schema, graphql_sync

_SNAPSHOT_PATH = Path(__file__).parent / "wikidata_snapshot.json"
_raw: Any = json.loads(_SNAPSHOT_PATH.read_text(encoding="utf-8"))
INDEX: dict[str, dict[str, Any]] = dict(_raw)

_SDL = """
type Query {
  "Look up a single entity by its Wikidata Q-id."
  entity(id: ID!): Entity
  "Case-insensitive substring search over label and description."
  search(term: String!): [Entity!]!
}

type Entity {
  "The Wikidata Q-id, e.g. \\"Q42\\"."
  id: ID!
  "English label (rdfs:label)."
  label: String!
  "English description (schema:description)."
  description: String
  "instance of (P31)"
  instanceOf: [Entity!]!
  "author (P50)"
  author: Entity
  "place of birth (P19)"
  placeOfBirth: Entity
  "country (P17)"
  country: Entity
  "publication date (P577)"
  publicationDate: String
  "notable work (P800)"
  notableWork: [Entity!]
}
"""

_schema = build_schema(_SDL)

_LIST_RELATIONS = ("instanceOf", "notableWork")
_SINGLE_RELATIONS = ("author", "placeOfBirth", "country")

_Entity = dict[str, Any]
_Resolver = Callable[[_Entity, GraphQLResolveInfo], _Entity | list[_Entity] | None]


def _resolve_entity(_root: object, _info: GraphQLResolveInfo, **kwargs: str) -> _Entity | None:
    return INDEX.get(kwargs["id"])


def _resolve_search(_root: object, _info: GraphQLResolveInfo, **kwargs: str) -> list[_Entity]:
    needle = kwargs["term"].lower()
    return [
        e
        for e in INDEX.values()
        if needle in e["label"].lower() or needle in (e.get("description") or "").lower()
    ]


def _make_list_resolver(field: str) -> _Resolver:
    def resolve(source: _Entity, _info: GraphQLResolveInfo) -> list[_Entity]:
        return [INDEX[ref] for ref in source.get(field, [])]

    return resolve


def _make_single_resolver(field: str) -> _Resolver:
    def resolve(source: _Entity, _info: GraphQLResolveInfo) -> _Entity | None:
        ref = source.get(field)
        return INDEX[ref] if ref is not None else None

    return resolve


_query_type = _schema.query_type
if _query_type is None:  # pragma: no cover - SDL always defines Query
    _msg = "schema missing Query type"
    raise RuntimeError(_msg)
_query_type.fields["entity"].resolve = _resolve_entity
_query_type.fields["search"].resolve = _resolve_search

_entity_type: Any = _schema.type_map["Entity"]
for _field in _LIST_RELATIONS:
    _entity_type.fields[_field].resolve = _make_list_resolver(_field)
for _field in _SINGLE_RELATIONS:
    _entity_type.fields[_field].resolve = _make_single_resolver(_field)


def execute(query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
    result = graphql_sync(_schema, query, variable_values=variables or {})
    out: dict[str, Any] = {"data": result.data}
    if result.errors:
        out["errors"] = [error.formatted for error in result.errors]
    return out
