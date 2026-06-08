from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class QueryRunResult:
    query_id: str
    phase: str
    run_index: int
    runtime_seconds: float | None
    peak_rss_bytes: int | None
    row_count: int | None
    result_digest: str | None
    status: str
    error: str | None = None


@dataclass
class BenchmarkArtifact:
    engine: str
    scale_label: str
    data_root: str
    started_at_utc: str
    startup_overhead_seconds: float
    metadata: dict[str, Any] = field(default_factory=dict)
    query_runs: list[QueryRunResult] = field(default_factory=list)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def save_benchmark_artifact(
    artifact: BenchmarkArtifact,
    output_dir: str | Path,
) -> Path:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    safe_timestamp = artifact.started_at_utc.replace(":", "-")
    path = root / f"{artifact.engine}_{artifact.scale_label}_{safe_timestamp}.json"
    path.write_text(json.dumps(asdict(artifact), indent=2), encoding="utf-8")
    return path


def load_benchmark_artifact(path: str | Path) -> BenchmarkArtifact:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    query_runs = [QueryRunResult(**item) for item in payload.pop("query_runs")]
    return BenchmarkArtifact(query_runs=query_runs, **payload)
