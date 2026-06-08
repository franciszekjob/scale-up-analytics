from __future__ import annotations

import time

from scale_up_analytics.data import REQUIRED_TABLES, table_source_glob
from scale_up_analytics.measurement import measure
from scale_up_analytics.queries import dataframe_digest, load_all_query_specs
from scale_up_analytics.results import BenchmarkArtifact, QueryRunResult, utc_now_iso


def run_duckdb_benchmark(
    data_root: str,
    scale_label: str,
    warmup_runs: int,
    measured_runs: int,
) -> BenchmarkArtifact:
    import duckdb

    startup_started = time.perf_counter()
    connection = duckdb.connect(database=":memory:")
    startup_overhead_seconds = time.perf_counter() - startup_started

    for table_name in REQUIRED_TABLES:
        source = table_source_glob(data_root, table_name)
        connection.execute(
            f"create or replace view {table_name} as select * from parquet_scan('{source}')"
        )

    artifact = BenchmarkArtifact(
        engine="duckdb",
        scale_label=scale_label,
        data_root=data_root,
        started_at_utc=utc_now_iso(),
        startup_overhead_seconds=startup_overhead_seconds,
        metadata={"database": ":memory:"},
    )

    for query in load_all_query_specs():
        for phase, run_count in (("warmup", warmup_runs), ("measured", measured_runs)):
            for run_index in range(1, run_count + 1):
                try:
                    result = measure(lambda: connection.execute(query.sql).fetch_df())
                    frame = result.value
                    artifact.query_runs.append(
                        QueryRunResult(
                            query_id=query.query_id,
                            phase=phase,
                            run_index=run_index,
                            runtime_seconds=result.runtime_seconds,
                            peak_rss_bytes=result.peak_rss_bytes,
                            row_count=len(frame),
                            result_digest=dataframe_digest(frame),
                            status="ok",
                        )
                    )
                except Exception as exc:  # pragma: no cover - runtime-dependent
                    artifact.query_runs.append(
                        QueryRunResult(
                            query_id=query.query_id,
                            phase=phase,
                            run_index=run_index,
                            runtime_seconds=None,
                            peak_rss_bytes=None,
                            row_count=None,
                            result_digest=None,
                            status="error",
                            error=str(exc),
                        )
                    )
    connection.close()
    return artifact
