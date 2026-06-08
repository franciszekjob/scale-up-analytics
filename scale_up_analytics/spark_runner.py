from __future__ import annotations

import time

from scale_up_analytics.data import REQUIRED_TABLES, resolve_table_location
from scale_up_analytics.measurement import measure
from scale_up_analytics.queries import dataframe_digest, load_all_query_specs
from scale_up_analytics.results import BenchmarkArtifact, QueryRunResult, utc_now_iso


def run_spark_benchmark(
    data_root: str,
    scale_label: str,
    warmup_runs: int,
    measured_runs: int,
    spark_master: str | None,
    spark_configs: dict[str, str],
) -> BenchmarkArtifact:
    from pyspark.sql import SparkSession

    startup_started = time.perf_counter()
    builder = SparkSession.builder.appName("scale-up-analytics")
    if spark_master:
        builder = builder.master(spark_master)
    for key, value in spark_configs.items():
        builder = builder.config(key, value)
    spark = builder.getOrCreate()
    startup_overhead_seconds = time.perf_counter() - startup_started

    for table_name in REQUIRED_TABLES:
        location = resolve_table_location(data_root, table_name)
        spark.read.parquet(location.path).createOrReplaceTempView(table_name)

    artifact = BenchmarkArtifact(
        engine="spark",
        scale_label=scale_label,
        data_root=data_root,
        started_at_utc=utc_now_iso(),
        startup_overhead_seconds=startup_overhead_seconds,
        metadata={
            "spark_master": spark_master,
            "spark_configs": spark_configs,
        },
    )

    for query in load_all_query_specs():
        for phase, run_count in (("warmup", warmup_runs), ("measured", measured_runs)):
            for run_index in range(1, run_count + 1):
                try:
                    result = measure(lambda: spark.sql(query.sql).toPandas())
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
    spark.stop()
    return artifact
