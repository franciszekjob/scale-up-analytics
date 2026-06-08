#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path

import duckdb


PROJECT_ROOT = Path(os.environ.get("PROJECT_ROOT", "/net/pr2/projects/plgrid/plggmpr2025"))
DATA_DIR = Path(os.environ.get("DATA_DIR", PROJECT_ROOT / "data"))
PARQUET_DIR = Path(os.environ.get("PARQUET_DIR", PROJECT_ROOT / "parquet"))

PARQUET_DIR.mkdir(parents=True, exist_ok=True)

SCHEMAS: dict[str, dict[str, str]] = {
    "lineitem": {
        "l_orderkey": "BIGINT",
        "l_partkey": "BIGINT",
        "l_suppkey": "BIGINT",
        "l_linenumber": "INTEGER",
        "l_quantity": "DOUBLE",
        "l_extendedprice": "DOUBLE",
        "l_discount": "DOUBLE",
        "l_tax": "DOUBLE",
        "l_returnflag": "VARCHAR",
        "l_linestatus": "VARCHAR",
        "l_shipdate": "DATE",
        "l_commitdate": "DATE",
        "l_receiptdate": "DATE",
        "l_shipinstruct": "VARCHAR",
        "l_shipmode": "VARCHAR",
        "l_comment": "VARCHAR",
    },
    "orders": {
        "o_orderkey": "BIGINT",
        "o_custkey": "BIGINT",
        "o_orderstatus": "VARCHAR",
        "o_totalprice": "DOUBLE",
        "o_orderdate": "DATE",
        "o_orderpriority": "VARCHAR",
        "o_clerk": "VARCHAR",
        "o_shippriority": "INTEGER",
        "o_comment": "VARCHAR",
    },
    "customer": {
        "c_custkey": "BIGINT",
        "c_name": "VARCHAR",
        "c_address": "VARCHAR",
        "c_nationkey": "BIGINT",
        "c_phone": "VARCHAR",
        "c_acctbal": "DOUBLE",
        "c_mktsegment": "VARCHAR",
        "c_comment": "VARCHAR",
    },
    "part": {
        "p_partkey": "BIGINT",
        "p_name": "VARCHAR",
        "p_mfgr": "VARCHAR",
        "p_brand": "VARCHAR",
        "p_type": "VARCHAR",
        "p_size": "INTEGER",
        "p_container": "VARCHAR",
        "p_retailprice": "DOUBLE",
        "p_comment": "VARCHAR",
    },
    "supplier": {
        "s_suppkey": "BIGINT",
        "s_name": "VARCHAR",
        "s_address": "VARCHAR",
        "s_nationkey": "BIGINT",
        "s_phone": "VARCHAR",
        "s_acctbal": "DOUBLE",
        "s_comment": "VARCHAR",
    },
    "partsupp": {
        "ps_partkey": "BIGINT",
        "ps_suppkey": "BIGINT",
        "ps_availqty": "INTEGER",
        "ps_supplycost": "DOUBLE",
        "ps_comment": "VARCHAR",
    },
    "nation": {
        "n_nationkey": "BIGINT",
        "n_name": "VARCHAR",
        "n_regionkey": "BIGINT",
        "n_comment": "VARCHAR",
    },
    "region": {
        "r_regionkey": "BIGINT",
        "r_name": "VARCHAR",
        "r_comment": "VARCHAR",
    },
}


def sql_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def sql_string_list(values: list[str]) -> str:
    return "[" + ", ".join(sql_string(value) for value in values) + "]"


def sql_schema(schema: dict[str, str]) -> str:
    items = [f"{sql_string(name)}: {sql_string(dtype)}" for name, dtype in schema.items()]
    return "{" + ", ".join(items) + "}"


def resolve_input(table: str) -> str | None:
    single_file = DATA_DIR / f"{table}.tbl"
    if single_file.exists():
        return sql_string(str(single_file))

    parts = sorted(DATA_DIR.glob(f"{table}.tbl.*"))
    if parts:
        return sql_string_list([str(part) for part in parts])

    return None


def get_parts(table: str) -> list[Path] | None:
    single_file = DATA_DIR / f"{table}.tbl"
    if single_file.exists():
        return [single_file]
    parts = sorted(DATA_DIR.glob(f"{table}.tbl.*"))
    return list(parts) if parts else None


def convert_part(connection: duckdb.DuckDBPyConnection, part: Path, schema: dict[str, str], tmp_path: Path) -> None:
    query = f"""
    COPY (
        SELECT * FROM read_csv(
            {sql_string(str(part))},
            delim='|',
            header=false,
            columns={sql_schema(schema)},
            ignore_errors=true,
            null_padding=true
        )
    ) TO {sql_string(str(tmp_path))}
    (FORMAT PARQUET, COMPRESSION ZSTD, ROW_GROUP_SIZE 1000000)
    """
    connection.execute(query)


def main() -> None:
    tmp_dir = PARQUET_DIR / "_tmp"
    tmp_dir.mkdir(exist_ok=True)

    for table, schema in SCHEMAS.items():
        parts = get_parts(table)
        if parts is None:
            print(f"BRAK PLIKU: {table}")
            continue

        output_path = PARQUET_DIR / f"{table}.parquet"
        print(f"Konwertuję {table} ({len(parts)} {'część' if len(parts)==1 else 'części'})...")

        if len(parts) == 1:
            connection = duckdb.connect()
            convert_part(connection, parts[0], schema, output_path)
            connection.close()
        else:
            # Konwertuj każdą część osobno
            tmp_paths = []
            for i, part in enumerate(parts):
                tmp_path = tmp_dir / f"{table}_{i}.parquet"
                print(f"  część {i+1}/{len(parts)}: {part.name}...", flush=True)
                connection = duckdb.connect()
                convert_part(connection, part, schema, tmp_path)
                connection.close()
                tmp_paths.append(tmp_path)

            # Merge wszystkich części w jeden plik
            print(f"  scalanie {len(tmp_paths)} części...")
            tmp_list = sql_string_list([str(p) for p in tmp_paths])
            connection = duckdb.connect()
            connection.execute(f"""
                COPY (SELECT * FROM parquet_scan({tmp_list}))
                TO {sql_string(str(output_path))}
                (FORMAT PARQUET, COMPRESSION ZSTD, ROW_GROUP_SIZE 1000000)
            """)
            connection.close()

            for tmp_path in tmp_paths:
                tmp_path.unlink()

        print(f"  -> {output_path}")

    tmp_dir.rmdir()
    print("Konwersja zakończona!")


if __name__ == "__main__":
    main()
