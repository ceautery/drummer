import json
from pathlib import Path
from typing import Annotated, Any, cast

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

_SNAPSHOT_PATH = Path(__file__).parent.parent / "mock" / "met_snapshot.json"
_raw: Any = json.loads(_SNAPSHOT_PATH.read_text(encoding="utf-8"))
_departments: list[dict[str, Any]] = cast("list[dict[str, Any]]", _raw["departments"])
_objects: dict[str, dict[str, Any]] = cast("dict[str, dict[str, Any]]", _raw["objects"])
_dept_id_to_name: dict[int, str] = {d["departmentId"]: d["displayName"] for d in _departments}

router = APIRouter(prefix="/mock/met", tags=["mock"])


def get_departments() -> list[dict[str, Any]]:
    return list(_departments)


def get_object_ids(department_ids: list[int] | None = None) -> list[int]:
    ids = sorted(int(k) for k in _objects)
    if department_ids is None:
        return ids
    allowed = {_dept_id_to_name[did] for did in department_ids if did in _dept_id_to_name}
    return [i for i in ids if _objects[str(i)]["department"] in allowed]


def get_object(object_id: int) -> dict[str, Any] | None:
    obj = _objects.get(str(object_id))
    return dict(obj) if obj is not None else None


def search_objects(q: str) -> list[int]:
    q_lower = q.lower()
    return sorted(
        int(k)
        for k, obj in _objects.items()
        if any(
            q_lower in field.lower()
            for field in [
                obj.get("title", ""),
                obj.get("artistDisplayName", ""),
                obj.get("medium", ""),
            ]
        )
    )


@router.get("/departments")
def departments_route() -> JSONResponse:
    return JSONResponse({"departments": get_departments()})


@router.get("/objects")
def objects_list_route(
    department_ids: Annotated[str | None, Query(alias="departmentIds")] = None,
) -> JSONResponse:
    if department_ids:
        try:
            dept_ids: list[int] | None = [int(x) for x in department_ids.split(",")]
        except ValueError:
            raise HTTPException(
                status_code=422, detail="departmentIds must be comma-separated integers"
            ) from None
    else:
        dept_ids = None
    ids = get_object_ids(dept_ids)
    return JSONResponse({"total": len(ids), "objectIDs": ids})


@router.get("/objects/{object_id}")
def object_detail_route(object_id: int) -> JSONResponse:
    obj = get_object(object_id)
    if obj is None:
        raise HTTPException(status_code=404, detail=f"Object {object_id} not found in snapshot")
    return JSONResponse(obj)


@router.get("/search")
def search_route(q: str = "") -> JSONResponse:
    ids = search_objects(q) if q else get_object_ids()
    return JSONResponse({"total": len(ids), "objectIDs": ids})
