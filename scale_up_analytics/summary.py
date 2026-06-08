from __future__ import annotations

import csv
import math
from collections import defaultdict
from pathlib import Path
from statistics import mean

from scale_up_analytics.results import BenchmarkArtifact, load_benchmark_artifact


def load_artifacts_from_directory(results_dir: str | Path) -> list[BenchmarkArtifact]:
    root = Path(results_dir)
    return [load_benchmark_artifact(path) for path in sorted(root.glob("*.json"))]


def summarize_artifacts(artifacts: list[BenchmarkArtifact]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str, str], list[float]] = defaultdict(list)
    statuses: dict[tuple[str, str, str], list[str]] = defaultdict(list)
    digests: dict[tuple[str, str, str], list[str]] = defaultdict(list)
    peaks: dict[tuple[str, str, str], list[int]] = defaultdict(list)

    for artifact in artifacts:
        for run in artifact.query_runs:
            if run.phase != "measured":
                continue
            key = (artifact.scale_label, artifact.engine, run.query_id)
            statuses[key].append(run.status)
            if run.runtime_seconds is not None:
                grouped[key].append(run.runtime_seconds)
            if run.result_digest:
                digests[key].append(run.result_digest)
            if run.peak_rss_bytes is not None:
                peaks[key].append(run.peak_rss_bytes)

    rows: list[dict[str, object]] = []
    for key in sorted(statuses):
        scale_label, engine, query_id = key
        runtimes = grouped.get(key, [])
        peak_samples = peaks.get(key, [])
        digest_values = sorted(set(digests.get(key, [])))
        status_values = statuses[key]
        rows.append(
            {
                "scale_label": scale_label,
                "engine": engine,
                "query_id": query_id,
                "measured_runs": len(status_values),
                "successful_runs": sum(1 for status in status_values if status == "ok"),
                "avg_runtime_seconds": round(mean(runtimes), 6) if runtimes else math.nan,
                "min_runtime_seconds": round(min(runtimes), 6) if runtimes else math.nan,
                "max_runtime_seconds": round(max(runtimes), 6) if runtimes else math.nan,
                "max_peak_rss_bytes": max(peak_samples) if peak_samples else "",
                "digest_count": len(digest_values),
                "digests": ",".join(digest_values),
            }
        )
    return rows


def write_summary_csv(rows: list[dict[str, object]], output_csv: str | Path) -> Path:
    path = Path(output_csv)
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else [
        "scale_label",
        "engine",
        "query_id",
        "measured_runs",
        "successful_runs",
        "avg_runtime_seconds",
        "min_runtime_seconds",
        "max_runtime_seconds",
        "max_peak_rss_bytes",
        "digest_count",
        "digests",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return path


def write_summary_markdown(rows: list[dict[str, object]], output_markdown: str | Path) -> Path:
    path = Path(output_markdown)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Benchmark Summary",
        "",
        "| Scale | Engine | Query | Success | Avg runtime (s) | Peak RSS bytes | Digests |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            "| {scale_label} | {engine} | {query_id} | {successful_runs}/{measured_runs} | "
            "{avg_runtime_seconds} | {max_peak_rss_bytes} | {digests} |".format(**row)
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
