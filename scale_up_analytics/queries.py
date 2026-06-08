from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import pandas as pd
except ImportError:  # pragma: no cover - exercised only without optional deps
    pd = None


QUERY_IDS: tuple[str, ...] = ("q1", "q3", "q5", "q6", "q9", "q18")


@dataclass(frozen=True)
class QuerySpec:
    query_id: str
    description: str
    sql: str


QUERY_DESCRIPTIONS: dict[str, str] = {
    "q1": "Scan and aggregation over lineitem.",
    "q3": "Join, filter, sort, and top-N selection.",
    "q5": "Multi-table join and grouped revenue aggregation.",
    "q6": "Filter-heavy revenue aggregation.",
    "q9": "Complex join with yearly profit aggregation.",
    "q18": "Heavy grouped query with subquery filter.",
}


def _queries_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "queries"


def load_query_spec(query_id: str) -> QuerySpec:
    query_path = _queries_dir() / f"{query_id}.sql"
    sql = query_path.read_text(encoding="utf-8").strip()
    return QuerySpec(
        query_id=query_id,
        description=QUERY_DESCRIPTIONS[query_id],
        sql=sql,
    )


def load_all_query_specs() -> list[QuerySpec]:
    return [load_query_spec(query_id) for query_id in QUERY_IDS]


def dataframe_digest(frame: Any) -> str:
    if pd is None:
        raise RuntimeError("pandas is required to build result digests.")
    if not isinstance(frame, pd.DataFrame):
        frame = pd.DataFrame(frame)

    normalized = frame.copy()
    normalized.columns = [str(column) for column in normalized.columns]
    normalized = normalized.fillna("<NA>")
    payload = normalized.to_csv(index=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]
