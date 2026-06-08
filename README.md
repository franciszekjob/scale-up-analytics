# Scale-Up Analytics

`Scale-Up Analytics` is a reproducible benchmark scaffold for comparing
`scale-up` analytics on one large node against `scale-out` execution on a
Spark cluster.

The repository is centered on a `TPC-H` workload stored in `Parquet` and
targets three execution engines:

- `DuckDB` on one high-memory HPC node
- `Pandas` on the same node as a single-machine baseline
- `Spark` on AWS EMR or another Spark cluster with comparable total RAM

The main project question is:

**When is one strong machine enough, and when does a cluster become the better option?**

## Benchmark scope

Fixed benchmark decisions:

- Dataset: `TPC-H`
- Main scale: `SF 100` / roughly `100 GB`
- Optional pilot scale: any smaller `SF` used only to validate the pipeline
- Storage format: `Parquet`
- Measurement policy: `1` warm-up run and `3` measured runs per query

Selected queries:

- `Q1`
- `Q3`
- `Q5`
- `Q6`
- `Q9`
- `Q18`

Primary metrics:

- query runtime
- peak process memory
- success or failure at a given scale
- engine startup overhead
- result digest for cross-engine correctness checks

## Repository layout

```text
.
├── CONTEXT.md
├── README.md
├── data/
├── notebooks/
├── queries/
│   ├── q1.sql
│   ├── q3.sql
│   ├── q5.sql
│   ├── q6.sql
│   ├── q9.sql
│   ├── q18.sql
│   └── README.md
├── report/
│   ├── README.md
│   └── report_template.md
├── results/
│   ├── plots/
│   └── raw/
├── scale_up_analytics/
│   ├── cli.py
│   ├── data.py
│   ├── duckdb_runner.py
│   ├── measurement.py
│   ├── pandas_queries.py
│   ├── pandas_runner.py
│   ├── queries.py
│   ├── results.py
│   ├── spark_runner.py
│   └── summary.py
├── tests/
└── requirements.txt
```

## Data layout

The benchmark expects one dataset directory per scale, for example:

```text
data/
└── tpch_sf100/
    ├── customer.parquet
    ├── lineitem.parquet
    ├── nation.parquet
    ├── orders.parquet
    ├── part.parquet
    ├── partsupp.parquet
    ├── region.parquet
    └── supplier.parquet
```

Table directories containing multiple `*.parquet` files are also supported.

## Setup

Create an environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

## CLI workflow

The project is driven through `python3 -m scale_up_analytics.cli`.

### 1. Generate TPC-H data with DuckDB

This uses DuckDB's `tpch` extension and exports all required tables to
`Parquet`.

```bash
python3 -m scale_up_analytics.cli generate-data \
  --scale-factor 100 \
  --output-dir data/tpch_sf100
```

If DuckDB extensions are unavailable on the target machine, generate the same
tables externally and place them in the expected layout under `data/`.

### 2. Validate the dataset

```bash
python3 -m scale_up_analytics.cli validate-data \
  --data-root data/tpch_sf100
```

### 3. Run a benchmark

Single engine:

```bash
python3 -m scale_up_analytics.cli benchmark \
  --engine duckdb \
  --data-root data/tpch_sf100 \
  --scale-label sf100
```

Spark example:

```bash
python3 -m scale_up_analytics.cli benchmark \
  --engine spark \
  --data-root s3://bucket/tpch_sf100 \
  --scale-label sf100 \
  --spark-master yarn \
  --spark-conf spark.executor.instances=2 \
  --spark-conf spark.executor.memory=64g
```

The command writes a timestamped JSON artifact to `results/raw/`.

### 4. Build summaries and plots

```bash
python3 -m scale_up_analytics.cli summarize \
  --results-dir results/raw \
  --output-csv results/raw/summary.csv \
  --output-markdown results/raw/summary.md
```

```bash
python3 -m scale_up_analytics.cli plot \
  --results-dir results/raw \
  --output-dir results/plots
```

## Benchmark methodology

- Keep the same `Parquet` input across all engines.
- Keep query logic equivalent across engines.
- Use the same query set for every engine.
- Run `1` warm-up iteration and `3` measured iterations per query.
- Record failures such as out-of-memory or timeout as benchmark results.
- Treat `Pandas` failure at larger scale as a valid conclusion, not a reason to
  change the workload.

## AWS Spark guidance

The project assumes `Spark` is the primary `scale-out` comparison.

- Prefer an EMR or equivalent cluster with total RAM close to the HPC node.
- Start with a small pilot run to verify correctness and estimate costs.
- Keep cluster sizing documented in the report.
