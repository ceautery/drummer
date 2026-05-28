from drummer.api.routes.mock import get_departments, get_object, get_object_ids, search_objects

DEPT_COUNT = 5
TOTAL_OBJECTS = 25
DEPT_EUROPEAN_PAINTINGS = 11
DEPT_MODERN_CONTEMPORARY = 21
EUROPEAN_PAINTINGS_COUNT = 5
TWO_DEPT_COUNT = 10
VAN_GOGH_STRAW_HAT_ID = 45734
VAN_GOGH_SUNFLOWERS_ID = 45804
POLLOCK_ID = 60002


def test_get_departments_returns_five() -> None:
    depts = get_departments()
    assert len(depts) == DEPT_COUNT


def test_get_departments_has_required_keys() -> None:
    for d in get_departments():
        assert "departmentId" in d
        assert "displayName" in d


def test_get_object_ids_returns_25() -> None:
    assert len(get_object_ids()) == TOTAL_OBJECTS


def test_get_object_ids_filters_by_department() -> None:
    ids = get_object_ids(department_ids=[DEPT_EUROPEAN_PAINTINGS])
    assert len(ids) == EUROPEAN_PAINTINGS_COUNT
    assert VAN_GOGH_STRAW_HAT_ID in ids


def test_get_object_ids_multiple_departments() -> None:
    ids = get_object_ids(department_ids=[DEPT_EUROPEAN_PAINTINGS, DEPT_MODERN_CONTEMPORARY])
    assert len(ids) == TWO_DEPT_COUNT


def test_get_object_ids_unknown_department_returns_empty() -> None:
    ids = get_object_ids(department_ids=[999])
    assert ids == []


def test_get_object_returns_van_gogh() -> None:
    obj = get_object(VAN_GOGH_STRAW_HAT_ID)
    assert obj is not None
    assert obj["title"] == "Self-Portrait with a Straw Hat"
    assert obj["artistDisplayName"] == "Vincent van Gogh"


def test_get_object_returns_none_for_unknown() -> None:
    assert get_object(99999) is None


def test_search_finds_sunflowers_by_title() -> None:
    ids = search_objects("sunflowers")
    assert VAN_GOGH_SUNFLOWERS_ID in ids


def test_search_finds_van_gogh_by_artist() -> None:
    ids = search_objects("van gogh")
    assert VAN_GOGH_STRAW_HAT_ID in ids
    assert VAN_GOGH_SUNFLOWERS_ID in ids


def test_search_is_case_insensitive() -> None:
    assert set(search_objects("van gogh")) == set(search_objects("Van Gogh"))


def test_search_no_match_returns_empty() -> None:
    assert search_objects("xyzzy_no_match_qwerty") == []


def test_search_finds_by_medium() -> None:
    ids = search_objects("enamel on canvas")
    assert POLLOCK_ID in ids
