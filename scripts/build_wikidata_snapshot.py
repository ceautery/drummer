"""One-time dev utility: build drummer/api/mock/wikidata_snapshot.json from real Wikidata data.

Run manually with `venv/bin/python scripts/build_wikidata_snapshot.py`.
NOT imported or executed by the app or its build — the app reads only the committed JSON.
"""

import json
from pathlib import Path
from typing import Any

import httpx

# Curated, interlinked entity set. Relation targets outside this set are dropped so the
# snapshot graph is closed (no dangling references). Comments are the EXPECTED entity for
# each Q-id — verify the printed labels match and correct any Q-id that doesn't.
QIDS = [
    "Q42",  # Douglas Adams (human)
    "Q3107329",  # The Hitchhiker's Guide to the Galaxy (novel)
    "Q47152",  # Mary Shelley (human)
    "Q150827",  # Frankenstein (novel)
    "Q692",  # William Shakespeare (human)
    "Q41567",  # Hamlet (play)
    "Q350",  # Cambridge
    "Q84",  # London
    "Q189288",  # Stratford-upon-Avon
    "Q145",  # United Kingdom
    "Q5",  # human (class)
    "Q8261",  # novel (class)
    "Q25379",  # play (class)
    "Q7725634",  # literary work (class)
    "Q515",  # city (class)
]

SINGLE_REL = {"author": "P50", "placeOfBirth": "P19", "country": "P17"}
LIST_REL = {"instanceOf": "P31", "notableWork": "P800"}
PUB_DATE_PID = "P577"
ENTITY_DATA = "https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"


def _claim_ids(entity: dict[str, Any], pid: str) -> list[str]:
    ids: list[str] = []
    for claim in entity.get("claims", {}).get(pid, []):
        val = claim.get("mainsnak", {}).get("datavalue", {}).get("value")
        if isinstance(val, dict) and "id" in val:
            ids.append(val["id"])
    return ids


def _pub_date(entity: dict[str, Any]) -> str | None:
    for claim in entity.get("claims", {}).get(PUB_DATE_PID, []):
        val = claim.get("mainsnak", {}).get("datavalue", {}).get("value")
        if isinstance(val, dict) and "time" in val:
            # "+1979-10-12T00:00:00Z" -> "1979-10-12"
            return str(val["time"]).lstrip("+").split("T")[0]
    return None


def main() -> None:
    qset = set(QIDS)
    snapshot: dict[str, Any] = {}
    ua = (
        "drummer-wikidata-snapshot/1.0"
        " (https://github.com/ceautery/drummer; ceautery@gmail.com)"
        " httpx/0.27"
    )
    with httpx.Client(timeout=30, follow_redirects=True, headers={"User-Agent": ua}) as client:
        for qid in QIDS:
            resp = client.get(ENTITY_DATA.format(qid=qid))
            resp.raise_for_status()
            entity = resp.json()["entities"][qid]
            label = entity.get("labels", {}).get("en", {}).get("value", qid)
            record: dict[str, Any] = {
                "id": qid,
                "label": label,
                "description": entity.get("descriptions", {}).get("en", {}).get("value"),
                "publicationDate": _pub_date(entity),
            }
            for field, pid in LIST_REL.items():
                record[field] = [i for i in _claim_ids(entity, pid) if i in qset]
            for field, pid in SINGLE_REL.items():
                record[field] = next((i for i in _claim_ids(entity, pid) if i in qset), None)
            snapshot[qid] = record
            print(f"{qid}: {label}")
    out_path = Path("drummer/api/mock/wikidata_snapshot.json")
    out_path.write_text(
        json.dumps(snapshot, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"wrote {len(snapshot)} entities to {out_path}")


if __name__ == "__main__":
    main()
