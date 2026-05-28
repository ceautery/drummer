# Phase 7: Mock Server + Tutorial Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a bundled Met Museum dataset, FastAPI mock routes that serve it, and a 7-step guided TutorialView in the React frontend.

**Architecture:** The Met snapshot (`drummer/api/mock/met_snapshot.json`) is loaded at module import. A new FastAPI router (`/mock/met/...`) exposes four endpoints over it. A second router (`/api/tutorial/steps/{n}/send`) constructs `RequestFile` objects from embedded step specs and runs them through the existing `resolve()` + `engine.send()` pipeline — identical to the regular send route, but without DB history. The React `TutorialView` is a full-screen two-column component with its own nav bar; `App.tsx` renders it when a Zustand `viewStore` holds `"tutorial"`.

**Tech Stack:** FastAPI, Pydantic, stdlib `json`/`pathlib`, React 19, Zustand 5, Tailwind CSS. No new Python or JS dependencies.

---

### File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `drummer/api/mock/__init__.py` | Package marker |
| Create | `drummer/api/mock/met_snapshot.json` | 25 artwork objects + 5 departments |
| Create | `drummer/api/routes/mock.py` | Query functions + FastAPI router at `/mock/met` |
| Create | `drummer/api/routes/tutorial.py` | Step specs + `POST /api/tutorial/steps/{n}/send` |
| Modify | `drummer/api/app.py` | Mount mock and tutorial routers |
| Create | `frontend/src/store/viewStore.ts` | `view: "workspace" \| "tutorial"` Zustand store |
| Create | `frontend/src/views/TutorialView.tsx` | Full-screen 7-step guided walkthrough |
| Modify | `frontend/src/App.tsx` | Render TutorialView when view==="tutorial" |
| Modify | `frontend/src/views/WelcomeView.tsx` | Add "Try the tutorial" link |
| Create | `tests/unit/test_mock_routes.py` | Unit tests for query functions |
| Create | `tests/unit/test_tutorial.py` | Unit tests for step spec validity |
| Create | `tests/integration/test_mock_routes.py` | HTTP integration tests for mock endpoints |
| Create | `tests/integration/test_tutorial_route.py` | SSE integration tests for tutorial send |

---

### Task 1: Met snapshot + mock query functions

**Files:**
- Create: `drummer/api/mock/__init__.py`
- Create: `drummer/api/mock/met_snapshot.json`
- Create: `drummer/api/routes/mock.py` (query functions only — no router yet)
- Create: `tests/unit/test_mock_routes.py`

- [ ] **Step 1: Create the package marker**

```bash
touch drummer/api/mock/__init__.py
```

- [ ] **Step 2: Create the snapshot JSON**

Create `drummer/api/mock/met_snapshot.json`:

```json
{
  "departments": [
    {"departmentId": 1, "displayName": "American Decorative Arts"},
    {"departmentId": 6, "displayName": "Asian Art"},
    {"departmentId": 10, "displayName": "Egyptian Art"},
    {"departmentId": 11, "displayName": "European Paintings"},
    {"departmentId": 21, "displayName": "Modern and Contemporary Art"}
  ],
  "objects": {
    "10001": {
      "objectID": 10001, "isHighlight": false, "isPublicDomain": true,
      "department": "American Decorative Arts", "objectName": "Sugar Urn",
      "title": "Sugar Urn", "culture": "American", "artistRole": "Maker",
      "artistDisplayName": "Paul Revere Jr.", "artistDisplayBio": "American, Boston 1734–1818 Boston",
      "objectDate": "1792–1795", "objectBeginDate": 1792, "objectEndDate": 1795,
      "medium": "Silver", "dimensions": "7 1/2 × 4 in. (19.1 × 10.2 cm)",
      "creditLine": "Gift of Joseph France, 1943", "accessionNumber": "43.80.1",
      "country": "United States", "classification": "Metalwork",
      "objectURL": "https://www.metmuseum.org/art/collection/search/10001",
      "primaryImage": "", "primaryImageSmall": ""
    },
    "10002": {
      "objectID": 10002, "isHighlight": false, "isPublicDomain": true,
      "department": "American Decorative Arts", "objectName": "Chest of Drawers",
      "title": "Chest of Drawers", "culture": "American", "artistRole": "Maker",
      "artistDisplayName": "", "artistDisplayBio": "",
      "objectDate": "ca. 1750–1770", "objectBeginDate": 1750, "objectEndDate": 1770,
      "medium": "Mahogany", "dimensions": "33 × 38 × 20 in. (83.8 × 96.5 × 50.8 cm)",
      "creditLine": "Rogers Fund, 1925", "accessionNumber": "25.115.4",
      "country": "United States", "classification": "Furniture",
      "objectURL": "https://www.metmuseum.org/art/collection/search/10002",
      "primaryImage": "", "primaryImageSmall": ""
    },
    "10003": {
      "objectID": 10003, "isHighlight": true, "isPublicDomain": true,
      "department": "American Decorative Arts", "objectName": "Lamp",
      "title": "Wisteria Table Lamp", "culture": "American", "artistRole": "Maker",
      "artistDisplayName": "Tiffany Studios", "artistDisplayBio": "American, 1902–1933",
      "objectDate": "ca. 1902", "objectBeginDate": 1900, "objectEndDate": 1905,
      "medium": "Leaded glass and patinated bronze",
      "dimensions": "27 × 18 in. (68.6 × 45.7 cm)",
      "creditLine": "Gift of Mr. and Mrs. Douglas Williams, 1976", "accessionNumber": "1976.51",
      "country": "United States", "classification": "Glass",
      "objectURL": "https://www.metmuseum.org/art/collection/search/10003",
      "primaryImage": "", "primaryImageSmall": ""
    },
    "10004": {
      "objectID": 10004, "isHighlight": false, "isPublicDomain": true,
      "department": "American Decorative Arts", "objectName": "Highboy",
      "title": "High Chest of Drawers (Highboy)", "culture": "American", "artistRole": "Maker",
      "artistDisplayName": "", "artistDisplayBio": "",
      "objectDate": "ca. 1740–1760", "objectBeginDate": 1740, "objectEndDate": 1760,
      "medium": "Walnut", "dimensions": "72 × 42 × 22 in. (182.9 × 106.7 × 55.9 cm)",
      "creditLine": "Bequest of Mrs. J. Insley Blair, 1951", "accessionNumber": "52.77.4",
      "country": "United States", "classification": "Furniture",
      "objectURL": "https://www.metmuseum.org/art/collection/search/10004",
      "primaryImage": "", "primaryImageSmall": ""
    },
    "10005": {
      "objectID": 10005, "isHighlight": false, "isPublicDomain": true,
      "department": "American Decorative Arts", "objectName": "Side Chair",
      "title": "Side Chair", "culture": "American", "artistRole": "Maker",
      "artistDisplayName": "John Henry Belter", "artistDisplayBio": "American, Ulm 1804–1863 New York City",
      "objectDate": "ca. 1850–1860", "objectBeginDate": 1850, "objectEndDate": 1860,
      "medium": "Rosewood", "dimensions": "44 × 19 × 22 in. (111.8 × 48.3 × 55.9 cm)",
      "creditLine": "Gift of Mr. and Mrs. Lowell Ross Burch, 1951", "accessionNumber": "51.82.1",
      "country": "United States", "classification": "Furniture",
      "objectURL": "https://www.metmuseum.org/art/collection/search/10005",
      "primaryImage": "", "primaryImageSmall": ""
    },
    "20001": {
      "objectID": 20001, "isHighlight": true, "isPublicDomain": true,
      "department": "Asian Art", "objectName": "Sculpture",
      "title": "Bodhisattva Guanyin", "culture": "Chinese", "artistRole": "",
      "artistDisplayName": "", "artistDisplayBio": "",
      "objectDate": "11th century", "objectBeginDate": 1000, "objectEndDate": 1100,
      "medium": "Dry lacquer with traces of gilding and polychrome",
      "dimensions": "46 × 28 × 20 in. (116.8 × 71.1 × 50.8 cm)",
      "creditLine": "Fletcher Fund, 1928", "accessionNumber": "28.56",
      "country": "China", "classification": "Sculpture",
      "objectURL": "https://www.metmuseum.org/art/collection/search/20001",
      "primaryImage": "", "primaryImageSmall": ""
    },
    "20002": {
      "objectID": 20002, "isHighlight": false, "isPublicDomain": true,
      "department": "Asian Art", "objectName": "Vase",
      "title": "Blue-and-White Vase with Dragon", "culture": "Chinese", "artistRole": "",
      "artistDisplayName": "", "artistDisplayBio": "",
      "objectDate": "Ming dynasty (1368–1644)", "objectBeginDate": 1368, "objectEndDate": 1644,
      "medium": "Porcelain painted in underglaze blue",
      "dimensions": "17 3/4 × 8 1/4 in. (45.1 × 21 cm)",
      "creditLine": "Purchase, Mrs. Richard E. Linburn Gift, 1988", "accessionNumber": "1988.19",
      "country": "China", "classification": "Ceramics",
      "objectURL": "https://www.metmuseum.org/art/collection/search/20002",
      "primaryImage": "", "primaryImageSmall": ""
    },
    "20003": {
      "objectID": 20003, "isHighlight": false, "isPublicDomain": true,
      "department": "Asian Art", "objectName": "Sword",
      "title": "Tachi (Long Sword)", "culture": "Japanese", "artistRole": "",
      "artistDisplayName": "", "artistDisplayBio": "",
      "objectDate": "Kamakura period (1185–1333), ca. 1300",
      "objectBeginDate": 1280, "objectEndDate": 1320,
      "medium": "Steel", "dimensions": "Blade L. 28 in. (71.1 cm)",
      "creditLine": "Bequest of George Cameron Stone, 1935", "accessionNumber": "36.25.1536a",
      "country": "Japan", "classification": "Arms and Armor",
      "objectURL": "https://www.metmuseum.org/art/collection/search/20003",
      "primaryImage": "", "primaryImageSmall": ""
    },
    "20004": {
      "objectID": 20004, "isHighlight": false, "isPublicDomain": true,
      "department": "Asian Art", "objectName": "Vase",
      "title": "Maebyeong (Prunus Vase)", "culture": "Korean", "artistRole": "",
      "artistDisplayName": "", "artistDisplayBio": "",
      "objectDate": "Goryeo period (918–1392)", "objectBeginDate": 1100, "objectEndDate": 1200,
      "medium": "Celadon-glazed stoneware with inlaid decoration",
      "dimensions": "13 1/4 × 7 1/4 in. (33.7 × 18.4 cm)",
      "creditLine": "Fletcher Fund, 1927", "accessionNumber": "27.119.10",
      "country": "Korea", "classification": "Ceramics",
      "objectURL": "https://www.metmuseum.org/art/collection/search/20004",
      "primaryImage": "", "primaryImageSmall": ""
    },
    "20005": {
      "objectID": 20005, "isHighlight": true, "isPublicDomain": true,
      "department": "Asian Art", "objectName": "Sculpture",
      "title": "Nataraja: Shiva as Lord of Dance", "culture": "South Indian", "artistRole": "",
      "artistDisplayName": "", "artistDisplayBio": "",
      "objectDate": "ca. 1000", "objectBeginDate": 975, "objectEndDate": 1025,
      "medium": "Copper alloy",
      "dimensions": "30 1/8 × 22 1/2 × 7 in. (76.5 × 57.2 × 17.8 cm)",
      "creditLine": "Purchase, Anonymous Gift, 1964", "accessionNumber": "64.51",
      "country": "India", "classification": "Sculpture",
      "objectURL": "https://www.metmuseum.org/art/collection/search/20005",
      "primaryImage": "", "primaryImageSmall": ""
    },
    "30001": {
      "objectID": 30001, "isHighlight": false, "isPublicDomain": true,
      "department": "Egyptian Art", "objectName": "Shabti",
      "title": "Shabti of Sennedjem", "culture": "Egyptian", "artistRole": "",
      "artistDisplayName": "", "artistDisplayBio": "",
      "objectDate": "ca. 1295–1213 BC", "objectBeginDate": -1295, "objectEndDate": -1213,
      "medium": "Faience", "dimensions": "7 1/4 × 2 1/4 in. (18.4 × 5.7 cm)",
      "creditLine": "Rogers Fund, 1923", "accessionNumber": "23.3.1",
      "country": "Egypt", "classification": "Faience",
      "objectURL": "https://www.metmuseum.org/art/collection/search/30001",
      "primaryImage": "", "primaryImageSmall": ""
    },
    "30002": {
      "objectID": 30002, "isHighlight": false, "isPublicDomain": true,
      "department": "Egyptian Art", "objectName": "Canopic Jar",
      "title": "Canopic Jar of Neskhons", "culture": "Egyptian", "artistRole": "",
      "artistDisplayName": "", "artistDisplayBio": "",
      "objectDate": "ca. 1040–945 BC", "objectBeginDate": -1040, "objectEndDate": -945,
      "medium": "Limestone", "dimensions": "16 × 5 1/2 in. (40.6 × 14 cm)",
      "creditLine": "Museum Accession", "accessionNumber": "30.8.54",
      "country": "Egypt", "classification": "Stone",
      "objectURL": "https://www.metmuseum.org/art/collection/search/30002",
      "primaryImage": "", "primaryImageSmall": ""
    },
    "30003": {
      "objectID": 30003, "isHighlight": false, "isPublicDomain": true,
      "department": "Egyptian Art", "objectName": "Papyrus",
      "title": "Fragment of a Book of the Dead", "culture": "Egyptian", "artistRole": "",
      "artistDisplayName": "", "artistDisplayBio": "",
      "objectDate": "ca. 1479–1425 BC", "objectBeginDate": -1479, "objectEndDate": -1425,
      "medium": "Papyrus, ink", "dimensions": "16 1/2 × 10 3/4 in. (41.9 × 27.3 cm)",
      "creditLine": "Rogers Fund, 1930", "accessionNumber": "30.3.31",
      "country": "Egypt", "classification": "Papyrus",
      "objectURL": "https://www.metmuseum.org/art/collection/search/30003",
      "primaryImage": "", "primaryImageSmall": ""
    },
    "30004": {
      "objectID": 30004, "isHighlight": false, "isPublicDomain": true,
      "department": "Egyptian Art", "objectName": "Statuette",
      "title": "Standing Female Figure", "culture": "Egyptian", "artistRole": "",
      "artistDisplayName": "", "artistDisplayBio": "",
      "objectDate": "ca. 1353–1336 BC", "objectBeginDate": -1353, "objectEndDate": -1336,
      "medium": "Limestone", "dimensions": "11 1/4 × 3 1/2 × 2 in. (28.6 × 8.9 × 5.1 cm)",
      "creditLine": "Purchase, Edward S. Harkness Gift, 1926", "accessionNumber": "26.7.1394",
      "country": "Egypt", "classification": "Stone",
      "objectURL": "https://www.metmuseum.org/art/collection/search/30004",
      "primaryImage": "", "primaryImageSmall": ""
    },
    "30005": {
      "objectID": 30005, "isHighlight": false, "isPublicDomain": true,
      "department": "Egyptian Art", "objectName": "Amulet",
      "title": "Amulet of a Frog", "culture": "Egyptian", "artistRole": "",
      "artistDisplayName": "", "artistDisplayBio": "",
      "objectDate": "ca. 664–332 BC", "objectBeginDate": -664, "objectEndDate": -332,
      "medium": "Faience", "dimensions": "1 1/8 × 1 5/8 in. (2.9 × 4.1 cm)",
      "creditLine": "Museum Accession", "accessionNumber": "10.130.1620",
      "country": "Egypt", "classification": "Faience",
      "objectURL": "https://www.metmuseum.org/art/collection/search/30005",
      "primaryImage": "", "primaryImageSmall": ""
    },
    "45734": {
      "objectID": 45734, "isHighlight": true, "isPublicDomain": true,
      "department": "European Paintings", "objectName": "Painting",
      "title": "Self-Portrait with a Straw Hat", "culture": "Dutch", "artistRole": "Artist",
      "artistDisplayName": "Vincent van Gogh",
      "artistDisplayBio": "Dutch, Zundert 1853–1890 Auvers-sur-Oise",
      "objectDate": "1887", "objectBeginDate": 1887, "objectEndDate": 1887,
      "medium": "Oil on canvas",
      "dimensions": "15 7/8 × 12 3/8 in. (40.3 × 31.4 cm)",
      "creditLine": "Bequest of Miss Adelaide Milton de Groot (1876–1967), 1967",
      "accessionNumber": "67.187.70a",
      "country": "Netherlands", "classification": "Paintings",
      "objectURL": "https://www.metmuseum.org/art/collection/search/45734",
      "primaryImage": "", "primaryImageSmall": ""
    },
    "45801": {
      "objectID": 45801, "isHighlight": true, "isPublicDomain": true,
      "department": "European Paintings", "objectName": "Painting",
      "title": "Young Woman with a Water Pitcher", "culture": "Dutch", "artistRole": "Artist",
      "artistDisplayName": "Johannes Vermeer",
      "artistDisplayBio": "Dutch, Delft 1632–1675 Delft",
      "objectDate": "ca. 1662", "objectBeginDate": 1660, "objectEndDate": 1665,
      "medium": "Oil on canvas",
      "dimensions": "18 × 16 in. (45.7 × 40.6 cm)",
      "creditLine": "Gift of Henry G. Marquand, 1889", "accessionNumber": "89.15.21",
      "country": "Netherlands", "classification": "Paintings",
      "objectURL": "https://www.metmuseum.org/art/collection/search/45801",
      "primaryImage": "", "primaryImageSmall": ""
    },
    "45802": {
      "objectID": 45802, "isHighlight": true, "isPublicDomain": true,
      "department": "European Paintings", "objectName": "Painting",
      "title": "Self-Portrait", "culture": "Dutch", "artistRole": "Artist",
      "artistDisplayName": "Rembrandt van Rijn",
      "artistDisplayBio": "Dutch, Leiden 1606–1669 Amsterdam",
      "objectDate": "1660", "objectBeginDate": 1660, "objectEndDate": 1660,
      "medium": "Oil on canvas",
      "dimensions": "33 3/4 × 26 in. (85.8 × 66 cm)",
      "creditLine": "Bequest of Benjamin Altman, 1913", "accessionNumber": "14.40.618",
      "country": "Netherlands", "classification": "Paintings",
      "objectURL": "https://www.metmuseum.org/art/collection/search/45802",
      "primaryImage": "", "primaryImageSmall": ""
    },
    "45803": {
      "objectID": 45803, "isHighlight": false, "isPublicDomain": true,
      "department": "European Paintings", "objectName": "Painting",
      "title": "La Grenouillère", "culture": "French", "artistRole": "Artist",
      "artistDisplayName": "Claude Monet",
      "artistDisplayBio": "French, Paris 1840–1926 Giverny",
      "objectDate": "1869", "objectBeginDate": 1869, "objectEndDate": 1869,
      "medium": "Oil on canvas",
      "dimensions": "29 1/8 × 39 1/4 in. (74 × 99.7 cm)",
      "creditLine": "H. O. Havemeyer Collection, Bequest of Mrs. H. O. Havemeyer, 1929",
      "accessionNumber": "29.100.112",
      "country": "France", "classification": "Paintings",
      "objectURL": "https://www.metmuseum.org/art/collection/search/45803",
      "primaryImage": "", "primaryImageSmall": ""
    },
    "45804": {
      "objectID": 45804, "isHighlight": true, "isPublicDomain": true,
      "department": "European Paintings", "objectName": "Painting",
      "title": "Vase with Fifteen Sunflowers", "culture": "Dutch", "artistRole": "Artist",
      "artistDisplayName": "Vincent van Gogh",
      "artistDisplayBio": "Dutch, Zundert 1853–1890 Auvers-sur-Oise",
      "objectDate": "1888", "objectBeginDate": 1888, "objectEndDate": 1888,
      "medium": "Oil on canvas",
      "dimensions": "36 1/4 × 28 3/4 in. (92.1 × 73 cm)",
      "creditLine": "Purchase, The Annenberg Foundation Gift, 1993", "accessionNumber": "1993.400",
      "country": "Netherlands", "classification": "Paintings",
      "objectURL": "https://www.metmuseum.org/art/collection/search/45804",
      "primaryImage": "", "primaryImageSmall": ""
    },
    "60001": {
      "objectID": 60001, "isHighlight": true, "isPublicDomain": true,
      "department": "Modern and Contemporary Art", "objectName": "Painting",
      "title": "Gertrude Stein", "culture": "", "artistRole": "Artist",
      "artistDisplayName": "Pablo Picasso",
      "artistDisplayBio": "Spanish, Málaga 1881–1973 Mougins, France",
      "objectDate": "1905–1906", "objectBeginDate": 1905, "objectEndDate": 1906,
      "medium": "Oil on canvas",
      "dimensions": "39 3/8 × 32 in. (100 × 81.3 cm)",
      "creditLine": "Bequest of Gertrude Stein, 1946", "accessionNumber": "47.106",
      "country": "", "classification": "Paintings",
      "objectURL": "https://www.metmuseum.org/art/collection/search/60001",
      "primaryImage": "", "primaryImageSmall": ""
    },
    "60002": {
      "objectID": 60002, "isHighlight": true, "isPublicDomain": false,
      "department": "Modern and Contemporary Art", "objectName": "Painting",
      "title": "Autumn Rhythm (Number 30)", "culture": "", "artistRole": "Artist",
      "artistDisplayName": "Jackson Pollock",
      "artistDisplayBio": "American, Cody, Wyoming 1912–1956 East Hampton, New York",
      "objectDate": "1950", "objectBeginDate": 1950, "objectEndDate": 1950,
      "medium": "Enamel on canvas",
      "dimensions": "105 × 207 in. (266.7 × 525.8 cm)",
      "creditLine": "George A. Hearn Fund, 1957", "accessionNumber": "57.92",
      "country": "", "classification": "Paintings",
      "objectURL": "https://www.metmuseum.org/art/collection/search/60002",
      "primaryImage": "", "primaryImageSmall": ""
    },
    "60003": {
      "objectID": 60003, "isHighlight": false, "isPublicDomain": false,
      "department": "Modern and Contemporary Art", "objectName": "Painting",
      "title": "Red Poppy", "culture": "", "artistRole": "Artist",
      "artistDisplayName": "Georgia O'Keeffe",
      "artistDisplayBio": "American, Sun Prairie, Wisconsin 1887–1986 Santa Fe, New Mexico",
      "objectDate": "1927", "objectBeginDate": 1927, "objectEndDate": 1927,
      "medium": "Oil on canvas",
      "dimensions": "7 × 9 in. (17.8 × 22.9 cm)",
      "creditLine": "The Alfred Stieglitz Collection, Bequest of Georgia O'Keeffe, 1986",
      "accessionNumber": "1987.377.1",
      "country": "", "classification": "Paintings",
      "objectURL": "https://www.metmuseum.org/art/collection/search/60003",
      "primaryImage": "", "primaryImageSmall": ""
    },
    "60004": {
      "objectID": 60004, "isHighlight": false, "isPublicDomain": false,
      "department": "Modern and Contemporary Art", "objectName": "Painting",
      "title": "Office in a Small City", "culture": "", "artistRole": "Artist",
      "artistDisplayName": "Edward Hopper",
      "artistDisplayBio": "American, Nyack, New York 1882–1967 New York City",
      "objectDate": "1953", "objectBeginDate": 1953, "objectEndDate": 1953,
      "medium": "Oil on canvas",
      "dimensions": "28 × 40 in. (71.1 × 101.6 cm)",
      "creditLine": "George A. Hearn Fund, 1953", "accessionNumber": "53.183",
      "country": "", "classification": "Paintings",
      "objectURL": "https://www.metmuseum.org/art/collection/search/60004",
      "primaryImage": "", "primaryImageSmall": ""
    },
    "60005": {
      "objectID": 60005, "isHighlight": false, "isPublicDomain": false,
      "department": "Modern and Contemporary Art", "objectName": "Painting",
      "title": "No. 16 (Red, Brown, and Black)", "culture": "", "artistRole": "Artist",
      "artistDisplayName": "Mark Rothko",
      "artistDisplayBio": "American, Dvinsk, Russia 1903–1970 New York City",
      "objectDate": "1958", "objectBeginDate": 1958, "objectEndDate": 1958,
      "medium": "Oil on canvas",
      "dimensions": "105 3/4 × 116 1/4 in. (268.6 × 295.3 cm)",
      "creditLine": "Gift of the artist, 1969", "accessionNumber": "69.13",
      "country": "", "classification": "Paintings",
      "objectURL": "https://www.metmuseum.org/art/collection/search/60005",
      "primaryImage": "", "primaryImageSmall": ""
    }
  }
}
```

- [ ] **Step 3: Write failing unit tests**

Create `tests/unit/test_mock_routes.py`:

```python
from drummer.api.routes.mock import get_departments, get_object, get_object_ids, search_objects


def test_get_departments_returns_five() -> None:
    depts = get_departments()
    assert len(depts) == 5


def test_get_departments_has_required_keys() -> None:
    for d in get_departments():
        assert "departmentId" in d
        assert "displayName" in d


def test_get_object_ids_returns_25() -> None:
    assert len(get_object_ids()) == 25


def test_get_object_ids_filters_by_department() -> None:
    ids = get_object_ids(department_ids=[11])
    assert len(ids) == 5
    assert 45734 in ids


def test_get_object_ids_multiple_departments() -> None:
    ids = get_object_ids(department_ids=[11, 21])
    assert len(ids) == 10


def test_get_object_ids_unknown_department_returns_empty() -> None:
    ids = get_object_ids(department_ids=[999])
    assert ids == []


def test_get_object_returns_van_gogh() -> None:
    obj = get_object(45734)
    assert obj is not None
    assert obj["title"] == "Self-Portrait with a Straw Hat"
    assert obj["artistDisplayName"] == "Vincent van Gogh"


def test_get_object_returns_none_for_unknown() -> None:
    assert get_object(99999) is None


def test_search_finds_sunflowers_by_title() -> None:
    ids = search_objects("sunflowers")
    assert 45804 in ids


def test_search_finds_van_gogh_by_artist() -> None:
    ids = search_objects("van gogh")
    assert 45734 in ids
    assert 45804 in ids


def test_search_is_case_insensitive() -> None:
    assert set(search_objects("van gogh")) == set(search_objects("Van Gogh"))


def test_search_no_match_returns_empty() -> None:
    assert search_objects("xyzzy_no_match_qwerty") == []


def test_search_finds_by_medium() -> None:
    ids = search_objects("enamel on canvas")
    assert 60002 in ids
```

- [ ] **Step 4: Run tests to confirm they fail**

```bash
pytest tests/unit/test_mock_routes.py -v
```

Expected: `ImportError` — `drummer.api.routes.mock` does not exist yet.

- [ ] **Step 5: Implement mock query functions**

Create `drummer/api/routes/mock.py`:

```python
import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

_SNAPSHOT_PATH = Path(__file__).parent.parent / "mock" / "met_snapshot.json"
_data: dict[str, Any] = json.loads(_SNAPSHOT_PATH.read_text(encoding="utf-8"))
_dept_id_to_name: dict[int, str] = {
    d["departmentId"]: d["displayName"] for d in _data["departments"]
}

router = APIRouter(prefix="/mock/met", tags=["mock"])


def get_departments() -> list[dict[str, Any]]:
    return _data["departments"]


def get_object_ids(department_ids: list[int] | None = None) -> list[int]:
    ids = sorted(int(k) for k in _data["objects"])
    if department_ids is None:
        return ids
    allowed = {_dept_id_to_name[did] for did in department_ids if did in _dept_id_to_name}
    return [i for i in ids if _data["objects"][str(i)]["department"] in allowed]


def get_object(object_id: int) -> dict[str, Any] | None:
    return _data["objects"].get(str(object_id))


def search_objects(q: str) -> list[int]:
    q_lower = q.lower()
    return [
        int(k)
        for k, obj in _data["objects"].items()
        if q_lower in " ".join([
            obj.get("title", ""),
            obj.get("artistDisplayName", ""),
            obj.get("medium", ""),
        ]).lower()
    ]


@router.get("/departments")
def departments_route() -> JSONResponse:
    return JSONResponse({"departments": get_departments()})


@router.get("/objects")
def objects_list_route(departmentIds: str | None = None) -> JSONResponse:
    dept_ids = [int(x) for x in departmentIds.split(",")] if departmentIds else None
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
```

- [ ] **Step 6: Run unit tests to confirm they pass**

```bash
pytest tests/unit/test_mock_routes.py -v
```

Expected: All 13 tests PASS.

- [ ] **Step 7: Run full check**

```bash
make check
```

Expected: All 151 existing tests plus 13 new = 164 total pass, no lint/type errors.

- [ ] **Step 8: Commit**

```bash
git add drummer/api/mock/__init__.py drummer/api/mock/met_snapshot.json \
        drummer/api/routes/mock.py tests/unit/test_mock_routes.py
git commit -m "feat: add Met Museum snapshot and mock query functions"
```

---

### Task 2: Mount mock router + integration tests

**Files:**
- Modify: `drummer/api/app.py`
- Create: `tests/integration/test_mock_routes.py`

- [ ] **Step 1: Write failing integration tests**

Create `tests/integration/test_mock_routes.py`:

```python
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_departments_returns_200(client: AsyncClient) -> None:
    response = await client.get("/mock/met/departments")
    assert response.status_code == 200
    data = response.json()
    assert "departments" in data
    assert len(data["departments"]) == 5


@pytest.mark.asyncio
async def test_departments_has_expected_fields(client: AsyncClient) -> None:
    data = (await client.get("/mock/met/departments")).json()
    for dept in data["departments"]:
        assert "departmentId" in dept
        assert "displayName" in dept


@pytest.mark.asyncio
async def test_objects_returns_all_25(client: AsyncClient) -> None:
    response = await client.get("/mock/met/objects")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 25
    assert len(data["objectIDs"]) == 25


@pytest.mark.asyncio
async def test_objects_filters_by_department(client: AsyncClient) -> None:
    response = await client.get("/mock/met/objects?departmentIds=11")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 5
    assert 45734 in data["objectIDs"]


@pytest.mark.asyncio
async def test_object_detail_returns_van_gogh(client: AsyncClient) -> None:
    response = await client.get("/mock/met/objects/45734")
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Self-Portrait with a Straw Hat"
    assert data["artistDisplayName"] == "Vincent van Gogh"


@pytest.mark.asyncio
async def test_object_detail_returns_404_for_unknown(client: AsyncClient) -> None:
    response = await client.get("/mock/met/objects/99999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_search_finds_sunflowers(client: AsyncClient) -> None:
    response = await client.get("/mock/met/search?q=sunflowers")
    assert response.status_code == 200
    data = response.json()
    assert 45804 in data["objectIDs"]


@pytest.mark.asyncio
async def test_search_empty_query_returns_all(client: AsyncClient) -> None:
    response = await client.get("/mock/met/search")
    assert response.status_code == 200
    assert response.json()["total"] == 25
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/integration/test_mock_routes.py -v
```

Expected: All 8 tests FAIL — router is not mounted yet.

- [ ] **Step 3: Mount the mock router in app.py**

In `drummer/api/app.py`, add this import after the existing route imports:

```python
from drummer.api.routes import mock as mock_routes
```

Then add this line inside `create_app()`, after `app.include_router(cookie_routes.router, prefix="/api")`:

```python
    app.include_router(mock_routes.router)
```

Note: the mock router already has its own prefix `/mock/met`, so no additional prefix is needed here.

- [ ] **Step 4: Run integration tests to confirm they pass**

```bash
pytest tests/integration/test_mock_routes.py -v
```

Expected: All 8 tests PASS.

- [ ] **Step 5: Run full check**

```bash
make check
```

Expected: All 172 tests pass.

- [ ] **Step 6: Commit**

```bash
git add drummer/api/app.py tests/integration/test_mock_routes.py
git commit -m "feat: mount mock Met router and add integration tests"
```

---

### Task 3: Tutorial step specs + unit tests

**Files:**
- Create: `drummer/api/routes/tutorial.py` (step specs and model only — no router yet)
- Create: `tests/unit/test_tutorial.py`

- [ ] **Step 1: Write failing unit tests**

Create `tests/unit/test_tutorial.py`:

```python
from drummer.api.routes.tutorial import STEPS, TutorialStep


def test_steps_has_seven_entries() -> None:
    assert len(STEPS) == 7


def test_all_steps_are_tutorial_step_instances() -> None:
    for step in STEPS:
        assert isinstance(step, TutorialStep)


def test_first_step_has_no_method() -> None:
    assert STEPS[0].method is None


def test_steps_with_requests_have_method_and_url() -> None:
    for step in STEPS[1:]:
        assert step.method is not None
        assert step.url != ""


def test_step_4_has_base_url_variable_override() -> None:
    # Index 4 = "Environment variables"
    assert "base_url" in STEPS[4].variable_overrides


def test_step_4_url_uses_base_url_variable() -> None:
    assert "{{base_url}}" in STEPS[4].url


def test_step_5_pre_script_is_not_empty() -> None:
    # Index 5 = "Pre-request scripts"
    assert STEPS[5].pre_script != ""


def test_step_5_pre_script_sets_header() -> None:
    assert "dm.request.headers" in STEPS[5].pre_script


def test_step_6_post_script_is_not_empty() -> None:
    # Index 6 = "Post-request scripts"
    assert STEPS[6].post_script != ""


def test_step_6_post_script_reads_response_json() -> None:
    assert "dm.response.json()" in STEPS[6].post_script


def test_all_steps_have_non_empty_title() -> None:
    for step in STEPS:
        assert step.title != ""


def test_all_steps_have_non_empty_instructions() -> None:
    for step in STEPS:
        assert step.instructions != ""
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/unit/test_tutorial.py -v
```

Expected: `ImportError` — `drummer.api.routes.tutorial` does not exist yet.

- [ ] **Step 3: Implement step specs**

Create `drummer/api/routes/tutorial.py`:

```python
import json
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, Annotated, cast

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

if TYPE_CHECKING:
    pass

from drummer.api.deps import get_cookie_jar
from drummer.core.cookies import CookieJar
from drummer.core.engine import send as engine_send
from drummer.core.storage.formats import HttpMethod, RequestFile, RequestFrontmatter
from drummer.core.variables import resolve

router = APIRouter(prefix="/api/tutorial", tags=["tutorial"])

CookieJarDep = Annotated[CookieJar, Depends(get_cookie_jar)]


class TutorialStep(BaseModel):
    title: str
    instructions: str
    method: HttpMethod | None = None
    url: str = ""
    params: dict[str, str] = Field(default_factory=dict)
    headers: dict[str, str] = Field(default_factory=dict)
    body: str = ""
    pre_script: str = ""
    post_script: str = ""
    variable_overrides: dict[str, str] = Field(default_factory=dict)


STEPS: list[TutorialStep] = [
    TutorialStep(
        title="Welcome to Drummer",
        instructions=(
            "Welcome to Drummer!\n\n"
            "This tutorial walks you through the core features using a sample of the "
            "Metropolitan Museum of Art's collection.\n\n"
            "You'll learn:\n"
            "  • How to send HTTP GET requests\n"
            "  • How to use path and query parameters\n"
            "  • How to manage environment variables\n"
            "  • How to run pre- and post-request scripts\n\n"
            "The mock Met API is built into Drummer — no internet connection required.\n\n"
            "Click Next to send your first request."
        ),
    ),
    TutorialStep(
        title="Your first GET request",
        instructions=(
            "The simplest HTTP request is a GET with no parameters. "
            "It retrieves a resource and returns JSON.\n\n"
            "This request fetches all museum departments — five major collection areas "
            "used to organize the Met's 1.5 million objects.\n\n"
            "Click Send to try it. The response appears on the right."
        ),
        method="GET",
        url="http://localhost:8000/mock/met/departments",
    ),
    TutorialStep(
        title="Path parameters",
        instructions=(
            "REST APIs use path parameters to identify a specific resource. "
            "Instead of listing all objects, you can fetch one by its ID.\n\n"
            "Object 45734 is Van Gogh's Self-Portrait with a Straw Hat (1887). "
            "The ID is embedded directly in the URL path.\n\n"
            "Click Send to retrieve it."
        ),
        method="GET",
        url="http://localhost:8000/mock/met/objects/45734",
    ),
    TutorialStep(
        title="Query parameters",
        instructions=(
            "Query parameters (after the ?) filter or refine a request without "
            "changing the path.\n\n"
            "The search endpoint accepts ?q= to search across title, artist, "
            "and medium. After sending, try changing 'sunflowers' to another term.\n\n"
            "Click Send to search."
        ),
        method="GET",
        url="http://localhost:8000/mock/met/search",
        params={"q": "sunflowers"},
    ),
    TutorialStep(
        title="Environment variables",
        instructions=(
            "Hardcoding http://localhost:8000 in every URL is brittle. "
            "Environment variables let you define base_url once and reuse it.\n\n"
            "Notice the URL uses {{base_url}}. Drummer substitutes the variable "
            "value before sending. The 'local' environment defines "
            "base_url=http://localhost:8000.\n\n"
            "Click Send to see variable substitution in action."
        ),
        method="GET",
        url="{{base_url}}/mock/met/departments",
        variable_overrides={"base_url": "http://localhost:8000"},
    ),
    TutorialStep(
        title="Pre-request scripts",
        instructions=(
            "Pre-request scripts run JavaScript before the HTTP call. "
            "They can read and modify the outgoing request.\n\n"
            "This script sets a custom header using dm.request:\n\n"
            "  dm.request.headers[\"X-Tutorial-Id\"] = \"drummer-tutorial-step-6\";\n"
            "  dm.console.log(\"Header set:\", dm.request.headers[\"X-Tutorial-Id\"]);\n\n"
            "The dm.console.log output appears in the script output panel below the response.\n\n"
            "Click Send to run it."
        ),
        method="GET",
        url="http://localhost:8000/mock/met/objects/45734",
        pre_script=(
            'dm.request.headers["X-Tutorial-Id"] = "drummer-tutorial-step-6";\n'
            'dm.console.log("Header set:", dm.request.headers["X-Tutorial-Id"]);'
        ),
    ),
    TutorialStep(
        title="Post-request scripts",
        instructions=(
            "Post-request scripts run JavaScript after the HTTP call. "
            "They can read the response and extract data.\n\n"
            "This script reads the JSON response and logs the artwork's details:\n\n"
            "  var obj = dm.response.json();\n"
            "  dm.console.log(\"Title:\", obj.title);\n"
            "  dm.console.log(\"Artist:\", obj.artistDisplayName);\n\n"
            "Use dm.env.set(\"key\", value) to store response data as variables "
            "for use in later requests.\n\n"
            "Click Send to run it."
        ),
        method="GET",
        url="http://localhost:8000/mock/met/objects/45734",
        post_script=(
            "var obj = dm.response.json();\n"
            'dm.console.log("Title:", obj.title);\n'
            'dm.console.log("Artist:", obj.artistDisplayName);'
        ),
    ),
]


def _step_to_request_file(step: TutorialStep) -> RequestFile:
    assert step.method is not None
    fm = RequestFrontmatter(
        name=step.title,
        method=step.method,
        url=step.url,
        params=step.params,
        headers=step.headers,
        pre_script=step.pre_script,
        post_script=step.post_script,
    )
    return RequestFile(frontmatter=fm, body=step.body)


@router.post("/steps/{step_index}/send")
async def send_tutorial_step(
    step_index: int,
    request: Request,
    cookie_jar: CookieJarDep,
) -> EventSourceResponse:
    if step_index < 0 or step_index >= len(STEPS):
        raise HTTPException(status_code=404, detail=f"Step {step_index} not found")
    step = STEPS[step_index]
    if step.method is None:
        raise HTTPException(status_code=400, detail="Step has no request to send")

    transport = cast("httpx.AsyncBaseTransport | None", request.app.state.transport)

    async def generate() -> AsyncGenerator[dict[str, str], None]:
        try:
            request_file = _step_to_request_file(step)
            resolved = resolve(request_file, step.variable_overrides)
            result = await engine_send(resolved, cookie_jar, transport=transport)

            if result.script_error and result.status_code == 0:
                yield {
                    "event": "done",
                    "data": json.dumps({
                        "history_id": None,
                        "script_logs": result.script_logs,
                        "script_error": result.script_error,
                        "script_suggestion": result.script_suggestion,
                    }),
                }
                return

            yield {
                "event": "status",
                "data": json.dumps({"status_code": result.status_code, "url": result.url}),
            }
            yield {"event": "headers", "data": json.dumps(result.headers)}
            yield {
                "event": "body",
                "data": json.dumps({
                    "body": result.body,
                    "encoding": result.encoding,
                    "elapsed_ms": result.elapsed_ms,
                }),
            }
            yield {
                "event": "done",
                "data": json.dumps({
                    "history_id": None,
                    "script_logs": result.script_logs,
                    "script_error": result.script_error,
                    "script_suggestion": result.script_suggestion,
                }),
            }
        except Exception as exc:
            yield {"event": "error", "data": json.dumps({"message": str(exc)})}

    return EventSourceResponse(generate())
```

- [ ] **Step 4: Run unit tests to confirm they pass**

```bash
pytest tests/unit/test_tutorial.py -v
```

Expected: All 12 tests PASS.

- [ ] **Step 5: Run full check**

```bash
make check
```

Expected: All 184 tests pass.

- [ ] **Step 6: Commit**

```bash
git add drummer/api/routes/tutorial.py tests/unit/test_tutorial.py
git commit -m "feat: add tutorial step specs and TutorialStep model"
```

---

### Task 4: Mount tutorial router + integration tests

**Files:**
- Modify: `drummer/api/app.py`
- Create: `tests/integration/test_tutorial_route.py`

- [ ] **Step 1: Write failing integration tests**

Create `tests/integration/test_tutorial_route.py`:

```python
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from drummer.api.app import create_app
from drummer.api.db.session import init_db
from tests.integration.conftest import parse_sse


def _db_url(tmp_path: Path) -> str:
    return f"sqlite+aiosqlite:///{tmp_path / 'test.db'}"


def _make_tutorial_app(tmp_path: Path) -> object:
    db_url = _db_url(tmp_path)
    app = create_app(db_url=db_url)
    # Tutorial requests go to /mock/met/... on the same app — route them back
    app.state.transport = ASGITransport(app=app)
    return app


@pytest.mark.asyncio
async def test_step_0_welcome_returns_400(tmp_path: Path) -> None:
    app = _make_tutorial_app(tmp_path)
    await init_db(_db_url(tmp_path))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/tutorial/steps/0/send")
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_step_1_departments_streams_done(tmp_path: Path) -> None:
    app = _make_tutorial_app(tmp_path)
    await init_db(_db_url(tmp_path))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/tutorial/steps/1/send")
    assert response.status_code == 200
    events = parse_sse(response.text)
    event_names = [e["event"] for e in events]
    assert "status" in event_names
    assert "body" in event_names
    assert "done" in event_names
    done = next(e for e in events if e["event"] == "done")
    assert done["data"]["script_error"] is None


@pytest.mark.asyncio
async def test_step_1_returns_departments_body(tmp_path: Path) -> None:
    app = _make_tutorial_app(tmp_path)
    await init_db(_db_url(tmp_path))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/tutorial/steps/1/send")
    events = parse_sse(response.text)
    status_event = next(e for e in events if e["event"] == "status")
    assert status_event["data"]["status_code"] == 200


@pytest.mark.asyncio
async def test_step_5_pre_script_log_captured(tmp_path: Path) -> None:
    app = _make_tutorial_app(tmp_path)
    await init_db(_db_url(tmp_path))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/tutorial/steps/5/send")
    assert response.status_code == 200
    events = parse_sse(response.text)
    done = next(e for e in events if e["event"] == "done")
    assert done["data"]["script_error"] is None
    logs = done["data"]["script_logs"]
    assert any("drummer-tutorial-step-6" in log for log in logs)


@pytest.mark.asyncio
async def test_step_6_post_script_logs_title(tmp_path: Path) -> None:
    app = _make_tutorial_app(tmp_path)
    await init_db(_db_url(tmp_path))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/tutorial/steps/6/send")
    assert response.status_code == 200
    events = parse_sse(response.text)
    done = next(e for e in events if e["event"] == "done")
    assert done["data"]["script_error"] is None
    logs = done["data"]["script_logs"]
    assert any("Self-Portrait" in log for log in logs)


@pytest.mark.asyncio
async def test_step_out_of_range_returns_404(tmp_path: Path) -> None:
    app = _make_tutorial_app(tmp_path)
    await init_db(_db_url(tmp_path))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/tutorial/steps/99/send")
    assert response.status_code == 404
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/integration/test_tutorial_route.py -v
```

Expected: All 6 tests FAIL — tutorial router not mounted yet.

- [ ] **Step 3: Mount the tutorial router in app.py**

In `drummer/api/app.py`, add this import after the mock import:

```python
from drummer.api.routes import tutorial as tutorial_routes
```

Then add this line after `app.include_router(mock_routes.router)`:

```python
    app.include_router(tutorial_routes.router)
```

- [ ] **Step 4: Run integration tests to confirm they pass**

```bash
pytest tests/integration/test_tutorial_route.py -v
```

Expected: All 6 tests PASS.

- [ ] **Step 5: Run full check**

```bash
make check
```

Expected: All 190 tests pass.

- [ ] **Step 6: Commit**

```bash
git add drummer/api/app.py tests/integration/test_tutorial_route.py
git commit -m "feat: mount tutorial router and add SSE integration tests"
```

---

### Task 5: TutorialView + App.tsx integration

**Files:**
- Create: `frontend/src/store/viewStore.ts`
- Create: `frontend/src/views/TutorialView.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/views/WelcomeView.tsx`

- [ ] **Step 1: Create the view store**

Create `frontend/src/store/viewStore.ts`:

```typescript
import { create } from "zustand";

type AppView = "workspace" | "tutorial";

interface ViewState {
  view: AppView;
  setView: (v: AppView) => void;
}

export const useViewStore = create<ViewState>()((set) => ({
  view: "workspace",
  setView: (view) => set({ view }),
}));
```

- [ ] **Step 2: Create TutorialView**

Create `frontend/src/views/TutorialView.tsx`:

```tsx
import { useState } from "react";
import { useViewStore } from "../store/viewStore";

interface StepMeta {
  title: string;
  instructions: string;
  hasRequest: boolean;
  displayMethod: string;
  displayUrl: string;
}

const STEPS: StepMeta[] = [
  {
    title: "Welcome to Drummer",
    instructions:
      "Welcome to Drummer!\n\nThis tutorial walks you through the core features using a sample of the Metropolitan Museum of Art's collection.\n\nYou'll learn:\n  • How to send HTTP GET requests\n  • How to use path and query parameters\n  • How to manage environment variables\n  • How to run pre- and post-request scripts\n\nThe mock Met API is built into Drummer — no internet connection required.\n\nClick Next to send your first request.",
    hasRequest: false,
    displayMethod: "",
    displayUrl: "",
  },
  {
    title: "Your first GET request",
    instructions:
      "The simplest HTTP request is a GET with no parameters. It retrieves a resource and returns JSON.\n\nThis request fetches all museum departments — five major collection areas used to organize the Met's 1.5 million objects.\n\nClick Send to try it. The response appears on the right.",
    hasRequest: true,
    displayMethod: "GET",
    displayUrl: "http://localhost:8000/mock/met/departments",
  },
  {
    title: "Path parameters",
    instructions:
      "REST APIs use path parameters to identify a specific resource. Instead of listing all objects, you can fetch one by its ID.\n\nObject 45734 is Van Gogh's Self-Portrait with a Straw Hat (1887). The ID is embedded directly in the URL path.\n\nClick Send to retrieve it.",
    hasRequest: true,
    displayMethod: "GET",
    displayUrl: "http://localhost:8000/mock/met/objects/45734",
  },
  {
    title: "Query parameters",
    instructions:
      "Query parameters (after the ?) filter or refine a request without changing the path.\n\nThe search endpoint accepts ?q= to search across title, artist, and medium. After sending, try changing 'sunflowers' to another term.\n\nClick Send to search.",
    hasRequest: true,
    displayMethod: "GET",
    displayUrl: "http://localhost:8000/mock/met/search?q=sunflowers",
  },
  {
    title: "Environment variables",
    instructions:
      "Hardcoding http://localhost:8000 in every URL is brittle. Environment variables let you define base_url once and reuse it.\n\nNotice the URL uses {{base_url}}. Drummer substitutes the variable value before sending. The 'local' environment defines base_url=http://localhost:8000.\n\nClick Send to see variable substitution in action.",
    hasRequest: true,
    displayMethod: "GET",
    displayUrl: "{{base_url}}/mock/met/departments",
  },
  {
    title: "Pre-request scripts",
    instructions:
      'Pre-request scripts run JavaScript before the HTTP call. They can read and modify the outgoing request.\n\nThis script sets a custom header using dm.request:\n\n  dm.request.headers["X-Tutorial-Id"] = "drummer-tutorial-step-6";\n  dm.console.log("Header set:", dm.request.headers["X-Tutorial-Id"]);\n\nThe dm.console.log output appears in the script output panel below the response.\n\nClick Send to run it.',
    hasRequest: true,
    displayMethod: "GET",
    displayUrl: "http://localhost:8000/mock/met/objects/45734",
  },
  {
    title: "Post-request scripts",
    instructions:
      "Post-request scripts run JavaScript after the HTTP call. They can read the response and extract data.\n\nThis script reads the JSON response and logs the artwork's details:\n\n  var obj = dm.response.json();\n  dm.console.log(\"Title:\", obj.title);\n  dm.console.log(\"Artist:\", obj.artistDisplayName);\n\nUse dm.env.set(\"key\", value) to store response data as variables for use in later requests.\n\nClick Send to run it.",
    hasRequest: true,
    displayMethod: "GET",
    displayUrl: "http://localhost:8000/mock/met/objects/45734",
  },
];

interface TutorialResponseState {
  statusCode: number | null;
  url: string | null;
  body: string | null;
  elapsedMs: number | null;
  scriptLogs: string[];
  scriptError: string | null;
  scriptSuggestion: string | null;
  error: string | null;
}

export function TutorialView() {
  const setView = useViewStore((s) => s.setView);
  const [currentStep, setCurrentStep] = useState(0);
  const [completedSteps, setCompletedSteps] = useState<Set<number>>(new Set());
  const [response, setResponse] = useState<TutorialResponseState | null>(null);
  const [sending, setSending] = useState(false);

  const step = STEPS[currentStep];

  const handleSend = async () => {
    setSending(true);
    setResponse(null);

    const res = await fetch(`/api/tutorial/steps/${currentStep}/send`, {
      method: "POST",
    });

    if (!res.ok || !res.body) {
      setResponse({
        statusCode: null,
        url: null,
        body: null,
        elapsedMs: null,
        scriptLogs: [],
        scriptError: `HTTP ${res.status}`,
        scriptSuggestion: null,
        error: null,
      });
      setSending(false);
      return;
    }

    const partial: TutorialResponseState = {
      statusCode: null,
      url: null,
      body: null,
      elapsedMs: null,
      scriptLogs: [],
      scriptError: null,
      scriptSuggestion: null,
      error: null,
    };

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let event = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";
      for (const line of lines) {
        if (line.startsWith("event:")) {
          event = line.slice(6).trim();
        } else if (line.startsWith("data:")) {
          const data = JSON.parse(line.slice(5).trim()) as Record<string, unknown>;
          if (event === "status") {
            partial.statusCode = data.status_code as number;
            partial.url = data.url as string;
          } else if (event === "body") {
            partial.body = data.body as string;
            partial.elapsedMs = data.elapsed_ms as number;
          } else if (event === "done") {
            partial.scriptLogs = (data.script_logs as string[]) ?? [];
            partial.scriptError = (data.script_error as string | null) ?? null;
            partial.scriptSuggestion = (data.script_suggestion as string | null) ?? null;
          } else if (event === "error") {
            partial.error = data.message as string;
          }
          setResponse({ ...partial });
        }
      }
    }

    setSending(false);
  };

  const handleNext = () => {
    setCompletedSteps((prev) => new Set(prev).add(currentStep));
    setResponse(null);
    setCurrentStep((prev) => Math.min(prev + 1, STEPS.length - 1));
  };

  const handleBack = () => {
    setResponse(null);
    setCurrentStep((prev) => Math.max(prev - 1, 0));
  };

  const navigateToStep = (i: number) => {
    setResponse(null);
    setCurrentStep(i);
  };

  const hasScriptOutput =
    response !== null &&
    (response.scriptLogs.length > 0 || response.scriptError !== null);

  return (
    <div className="flex h-screen flex-col bg-gray-950 text-gray-100">
      {/* Nav bar */}
      <nav className="flex shrink-0 items-center gap-4 border-b border-gray-800 bg-gray-900 px-4 py-2">
        <span className="text-sm font-semibold text-gray-200">🥁 Drummer</span>
        <div className="flex gap-1">
          <button
            type="button"
            onClick={() => setView("workspace")}
            className="rounded px-3 py-1 text-xs text-gray-400 hover:text-gray-200"
          >
            Workspace
          </button>
          <button
            type="button"
            className="rounded bg-gray-700 px-3 py-1 text-xs text-white"
          >
            Tutorial
          </button>
        </div>
      </nav>

      {/* Two-column body */}
      <div className="flex min-h-0 flex-1 overflow-hidden">
        {/* Left column */}
        <div className="flex w-72 shrink-0 flex-col border-r border-gray-800 bg-gray-900 p-4">
          {/* Step list */}
          <div className="mb-4">
            <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-gray-500">
              Progress
            </div>
            <div className="flex flex-col gap-1">
              {STEPS.map((s, i) => (
                <button
                  key={s.title}
                  type="button"
                  onClick={() => navigateToStep(i)}
                  className={`flex items-center gap-2 rounded px-2 py-1.5 text-left text-xs ${
                    i === currentStep
                      ? "border border-blue-700 bg-blue-900/50 text-blue-300"
                      : completedSteps.has(i)
                        ? "bg-green-900/20 text-green-400"
                        : "text-gray-500 hover:text-gray-300"
                  }`}
                >
                  <span className="w-4 shrink-0 text-center">
                    {completedSteps.has(i) ? "✓" : i === currentStep ? "▶" : "○"}
                  </span>
                  {s.title}
                </button>
              ))}
            </div>
          </div>

          {/* Instructions */}
          <div className="mb-4 min-h-0 flex-1 overflow-y-auto">
            <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-gray-500">
              Instructions
            </div>
            <div className="whitespace-pre-wrap text-xs leading-relaxed text-gray-300">
              {step.instructions}
            </div>
          </div>

          {/* Back / Next */}
          <div className="flex gap-2 border-t border-gray-800 pt-3">
            <button
              type="button"
              onClick={handleBack}
              disabled={currentStep === 0}
              className="rounded bg-gray-800 px-3 py-1.5 text-xs text-gray-400 hover:text-gray-200 disabled:opacity-30"
            >
              ← Back
            </button>
            <button
              type="button"
              onClick={handleNext}
              disabled={currentStep === STEPS.length - 1}
              className="flex-1 rounded bg-blue-600 px-3 py-1.5 text-xs text-white hover:bg-blue-700 disabled:opacity-30"
            >
              Next →
            </button>
          </div>
        </div>

        {/* Right column */}
        <div className="flex flex-1 flex-col overflow-hidden p-4">
          {step.hasRequest ? (
            <>
              {/* Request card */}
              <div className="mb-4 shrink-0">
                <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Request
                </div>
                <div className="flex items-center gap-2 rounded bg-gray-800 px-3 py-2">
                  <span className="rounded bg-blue-800 px-2 py-0.5 text-xs font-semibold text-blue-200">
                    {step.displayMethod}
                  </span>
                  <span className="flex-1 truncate font-mono text-xs text-gray-200">
                    {step.displayUrl}
                  </span>
                  <button
                    type="button"
                    onClick={handleSend}
                    disabled={sending}
                    className="shrink-0 rounded bg-blue-600 px-3 py-1 text-xs text-white hover:bg-blue-700 disabled:opacity-50"
                  >
                    {sending ? "Sending…" : "Send ▶"}
                  </button>
                </div>
              </div>

              {/* Response */}
              {response && (
                <div className="flex min-h-0 flex-1 flex-col gap-2">
                  <div className="flex shrink-0 items-center gap-3">
                    <div className="text-xs font-semibold uppercase tracking-wider text-gray-500">
                      Response
                    </div>
                    {response.statusCode !== null && (
                      <>
                        <span className="rounded bg-green-900 px-2 py-0.5 text-xs text-green-300">
                          {response.statusCode} OK
                        </span>
                        <span className="text-xs text-gray-500">
                          {response.elapsedMs?.toFixed(0)}ms
                        </span>
                      </>
                    )}
                    {response.error && (
                      <span className="text-xs text-red-400">{response.error}</span>
                    )}
                  </div>
                  {response.body && (
                    <pre className="min-h-0 flex-1 overflow-auto rounded border border-gray-800 bg-gray-950 p-3 font-mono text-xs text-blue-300">
                      {response.body}
                    </pre>
                  )}
                  {hasScriptOutput && (
                    <div className="shrink-0 rounded border border-gray-800 bg-gray-950 p-2 font-mono text-xs">
                      {response.scriptLogs.map((log) => (
                        <div key={log} className="text-amber-300">
                          {log}
                        </div>
                      ))}
                      {response.scriptError && (
                        <div className="text-red-400">{response.scriptError}</div>
                      )}
                      {response.scriptSuggestion && (
                        <div className="italic text-amber-500">
                          Hint: {response.scriptSuggestion}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </>
          ) : (
            <div className="flex flex-1 items-center justify-center">
              <p className="text-sm text-gray-500">
                Use the navigation on the left to progress through the tutorial.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Update App.tsx**

Replace the contents of `frontend/src/App.tsx`:

```tsx
import { useEffect } from "react";
import { useProject } from "./api/projects";
import { useProjectStore } from "./store/projectStore";
import { useViewStore } from "./store/viewStore";
import { TutorialView } from "./views/TutorialView";
import { WelcomeView } from "./views/WelcomeView";
import { WorkspaceView } from "./views/WorkspaceView";

export default function App() {
  const view = useViewStore((s) => s.view);
  const { data: project, isLoading } = useProject();
  const setProject = useProjectStore((s) => s.setProject);

  useEffect(() => {
    if (project) setProject(project);
  }, [project, setProject]);

  if (view === "tutorial") return <TutorialView />;

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center text-sm text-gray-400">
        Loading…
      </div>
    );
  }

  if (!project) return <WelcomeView />;
  return <WorkspaceView />;
}
```

- [ ] **Step 4: Add Tutorial link to WelcomeView**

In `frontend/src/views/WelcomeView.tsx`, add the import and a link at the bottom of the card.

Add import after the existing imports:

```tsx
import { useViewStore } from "../store/viewStore";
```

Add inside the `WelcomeView` function body, after the existing `const { mutate, isPending, error }` line:

```tsx
  const setView = useViewStore((s) => s.setView);
```

Add at the bottom of the card div, after the `{error && ...}` block:

```tsx
        <div className="mt-4 border-t border-gray-100 pt-4 text-center">
          <button
            type="button"
            onClick={() => setView("tutorial")}
            className="text-xs text-purple-500 hover:text-purple-700"
          >
            No project yet? Try the interactive tutorial →
          </button>
        </div>
```

- [ ] **Step 5: Run frontend type check**

```bash
cd frontend && npm run check
```

Expected: No errors.

- [ ] **Step 6: Run full check**

```bash
make check
```

Expected: All 190 tests pass, no lint/type errors.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/store/viewStore.ts frontend/src/views/TutorialView.tsx \
        frontend/src/App.tsx frontend/src/views/WelcomeView.tsx
git commit -m "feat: add TutorialView with 7-step Met Museum walkthrough"
```

---

## Self-Review

**Spec coverage:**

| Spec requirement | Task |
|---|---|
| Met snapshot — 25 objects, 5 departments | Task 1 |
| `GET /mock/met/departments` | Task 1 |
| `GET /mock/met/objects` with optional `departmentIds` | Task 1 |
| `GET /mock/met/objects/{id}` with 404 | Task 1 |
| `GET /mock/met/search?q=` case-insensitive | Task 1 |
| Mock router mounted in app | Task 2 |
| Tutorial step specs (7 steps, correct fields) | Task 3 |
| `POST /api/tutorial/steps/{n}/send` SSE endpoint | Task 3 |
| Pre-script integration (step 5) | Task 3 |
| Post-script integration (step 6) | Task 3 |
| Tutorial router mounted in app | Task 4 |
| Self-referential transport for test isolation | Task 4 |
| `viewStore` with `"workspace" \| "tutorial"` | Task 5 |
| `TutorialView` two-column layout | Task 5 |
| Step list with ✓/▶/○ indicators | Task 5 |
| Instructions panel | Task 5 |
| Back/Next navigation | Task 5 |
| Request card with Send button | Task 5 |
| SSE parsing + response panel | Task 5 |
| Script output panel | Task 5 |
| App.tsx renders TutorialView when view==="tutorial" | Task 5 |
| WelcomeView Tutorial link | Task 5 |

All spec requirements covered. No TBDs.

**Type consistency:** `TutorialStep.method` is `HttpMethod | None` in Python and unused in TypeScript (frontend has its own `StepMeta`). `variable_overrides` in Python matches `step.variable_overrides` at call site. `parse_sse` imported from `tests.integration.conftest` in tutorial integration tests — same helper used by existing send route tests. ✓

**Placeholder check:** All code blocks are complete. No "similar to above" references. ✓
