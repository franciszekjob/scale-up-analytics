from __future__ import annotations

import argparse
import sys
from pathlib import Path

from scale_up_analytics.data import REQUIRED_TABLES, validate_dataset_layout
from scale_up_analytics.results import save_benchmark_artifact
from scale_up_analytics.summary import (
    load_artifacts_from_directory,
    summarize_artifacts,
    write_summary_csv,
    write_summary_markdown,
)


def generate_data(scale_factor: int, output_dir: str) -> None:
    import duckdb

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    connection = duckdb.connect(database=":memory:")
    connection.execute("install tpch")
    connection.execute("load tpch")
    connection.execute(f"call dbgen(sf = {scale_factor})")

    for table_name in REQUIRED_TABLES:
        connection.execute(
            f"copy (select * from {table_name}) to "
            f"'{output_path / f'{table_name}.parquet'}' (format parquet)"
        )
    connection.close()


def parse_spark_conf(items: list[str]) -> dict[str, str]:
    configs: dict[str, str] = {}
    for item in items:
        if "=" not in item:
            raise ValueError(
                f"Invalid spark config '{item}'. Expected key=value syntax."
            )
        key, value = item.split("=", 1)
        configs[key] = value
    return configs


def command_generate_data(args: argparse.Namespace) -> int:
    generate_data(args.scale_factor, args.output_dir)
    print(f"Generated TPC-H data in {args.output_dir}")
    return 0


def command_validate_data(args: argparse.Namespace) -> int:
    locations = validate_dataset_layout(args.data_root)
    print(f"Validated {len(locations)} tables under {args.data_root}")
    for location in locations:
        print(f"- {location.name}: {location.kind} -> {location.path}")
    return 0


def command_benchmark(args: argparse.Namespace) -> int:
    if args.engine == "duckdb":
        from scale_up_analytics.duckdb_runner import run_duckdb_benchmark

        artifact = run_duckdb_benchmark(
            data_root=args.data_root,
            scale_label=args.scale_label,
            warmup_runs=args.warmup_runs,
            measured_runs=args.measured_runs,
        )
    elif args.engine == "pandas":
        from scale_up_analytics.pandas_runner import run_pandas_benchmark

        artifact = run_pandas_benchmark(
            data_root=args.data_root,
            scale_label=args.scale_label,
            warmup_runs=args.warmup_runs,
            measured_runs=args.measured_runs,
        )
    else:
        from scale_up_analytics.spark_runner import run_spark_benchmark

        artifact = run_spark_benchmark(
            data_root=args.data_root,
            scale_label=args.scale_label,
            warmup_runs=args.warmup_runs,
            measured_runs=args.measured_runs,
            spark_master=args.spark_master,
            spark_configs=parse_spark_conf(args.spark_conf),
        )

    output_path = save_benchmark_artifact(artifact, args.output_dir)
    print(f"Saved benchmark artifact to {output_path}")
    return 0


def command_summarize(args: argparse.Namespace) -> int:
    artifacts = load_artifacts_from_directory(args.results_dir)
    rows = summarize_artifacts(artifacts)
    csv_path = write_summary_csv(rows, args.output_csv)
    markdown_path = write_summary_markdown(rows, args.output_markdown)
    print(f"Wrote summary CSV to {csv_path}")
    print(f"Wrote summary markdown to {markdown_path}")
    return 0


def command_plot(args: argparse.Namespace) -> int:
    import matplotlib.pyplot as plt

    artifacts = load_artifacts_from_directory(args.results_dir)
    rows = summarize_artifacts(artifacts)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    by_scale: dict[str, list[dict[str, object]]] = {}
    for row in rows:
        by_scale.setdefault(str(row["scale_label"]), []).append(row)

    for scale_label, scale_rows in by_scale.items():
        filtered = [row for row in scale_rows if row["avg_runtime_seconds"] == row["avg_runtime_seconds"]]
        labels = [f"{row['query_id']}:{row['engine']}" for row in filtered]
        values = [float(row["avg_runtime_seconds"]) for row in filtered]

        plt.figure(figsize=(12, 6))
        plt.bar(labels, values)
        plt.xticks(rotation=45, ha="right")
        plt.ylabel("Average runtime (seconds)")
        plt.title(f"Benchmark runtime summary for {scale_label}")
        plt.tight_layout()
        plot_path = output_dir / f"{scale_label}_avg_runtime.png"
        plt.savefig(plot_path)
        plt.close()
        print(f"Wrote plot to {plot_path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scale-up analytics benchmark CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate_parser = subparsers.add_parser("generate-data", help="Generate TPC-H parquet data")
    generate_parser.add_argument("--scale-factor", type=int, required=True)
    generate_parser.add_argument("--output-dir", required=True)
    generate_parser.set_defaults(func=command_generate_data)

    validate_parser = subparsers.add_parser("validate-data", help="Validate parquet dataset layout")
    validate_parser.add_argument("--data-root", required=True)
    validate_parser.set_defaults(func=command_validate_data)

    benchmark_parser = subparsers.add_parser("benchmark", help="Run one benchmark engine")
    benchmark_parser.add_argument("--engine", choices=("duckdb", "pandas", "spark"), required=True)
    benchmark_parser.add_argument("--data-root", required=True)
    benchmark_parser.add_argument("--scale-label", required=True)
    benchmark_parser.add_argument("--warmup-runs", type=int, default=1)
    benchmark_parser.add_argument("--measured-runs", type=int, default=3)
    benchmark_parser.add_argument("--output-dir", default="results/raw")
    benchmark_parser.add_argument("--spark-master")
    benchmark_parser.add_argument("--spark-conf", action="append", default=[])
    benchmark_parser.set_defaults(func=command_benchmark)

    summarize_parser = subparsers.add_parser("summarize", help="Aggregate benchmark artifacts")
    summarize_parser.add_argument("--results-dir", required=True)
    summarize_parser.add_argument("--output-csv", required=True)
    summarize_parser.add_argument("--output-markdown", required=True)
    summarize_parser.set_defaults(func=command_summarize)

    plot_parser = subparsers.add_parser("plot", help="Render basic runtime plots")
    plot_parser.add_argument("--results-dir", required=True)
    plot_parser.add_argument("--output-dir", required=True)
    plot_parser.set_defaults(func=command_plot)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
