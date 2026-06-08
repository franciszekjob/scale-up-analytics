from __future__ import annotations

import time

from scale_up_analytics.data import REQUIRED_TABLES, resolve_table_location
from scale_up_analytics.measurement import measure
from scale_up_analytics.pandas_queries import PANDAS_QUERY_RUNNERS
from scale_up_analytics.queries import dataframe_digest, load_all_query_specs
from scale_up_analytics.results import BenchmarkArtifact, QueryRunResult, utc_now_iso


def _load_tables(data_root: str) -> dict[str, "pd.DataFrame"]:
    import pandas as pd

    tables: dict[str, pd.DataFrame] = {}
    date_columns = {
        "lineitem": ["l_shipdate", "l_commitdate", "l_receiptdate"],
        "orders": ["o_orderdate"],
    }
    for table_name in REQUIRED_TABLES:
        location = resolve_table_location(data_root, table_name)
        tables[table_name] = pd.read_parquet(
            location.path,
            engine="pyarrow",
        )
        for column in date_columns.get(table_name, []):
            if column in tables[table_name].columns:
                tables[table_name][column] = pd.to_datetime(tables[table_name][column])
    return tables


def run_pandas_benchmark(
    data_root: str,
    scale_label: str,
    warmup_runs: int,
    measured_runs: int,
) -> BenchmarkArtifact:
    startup_started = time.perf_counter()
    tables = _load_tables(data_root)
    startup_overhead_seconds = time.perf_counter() - startup_started

    artifact = BenchmarkArtifact(
        engine="pandas",
        scale_label=scale_label,
        data_root=data_root,
        started_at_utc=utc_now_iso(),
        startup_overhead_seconds=startup_overhead_seconds,
        metadata={"loaded_tables": sorted(tables.keys())},
    )

    for query in load_all_query_specs():
        runner = PANDAS_QUERY_RUNNERS[query.query_id]
        for phase, run_count in (("warmup", warmup_runs), ("measured", measured_runs)):
            for run_index in range(1, run_count + 1):
                try:
                    result = measure(lambda runner=runner: runner(tables))
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
    return artifact
