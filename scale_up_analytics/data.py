from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


REQUIRED_TABLES: tuple[str, ...] = (
    "customer",
    "lineitem",
    "nation",
    "orders",
    "part",
    "partsupp",
    "region",
    "supplier",
)


@dataclass(frozen=True)
class TableLocation:
    name: str
    path: str
    kind: str


def _is_remote_root(data_root: str | Path) -> bool:
    return "://" in str(data_root)


def _existing_paths(candidates: Iterable[Path]) -> list[Path]:
    return [candidate for candidate in candidates if candidate.exists()]


def resolve_table_location(data_root: str | Path, table_name: str) -> TableLocation:
    if _is_remote_root(data_root):
        root = str(data_root).rstrip("/")
        return TableLocation(
            name=table_name,
            path=f"{root}/{table_name}.parquet",
            kind="remote-file",
        )

    root = Path(data_root)
    candidates = _existing_paths(
        (
            root / f"{table_name}.parquet",
            root / table_name,
        )
    )
    if not candidates:
        raise FileNotFoundError(
            f"Missing table '{table_name}' under '{root}'. "
            f"Expected either '{table_name}.parquet' or '{table_name}/'."
        )

    path = candidates[0]
    if path.is_file():
        return TableLocation(name=table_name, path=str(path), kind="file")

    parquet_files = sorted(path.rglob("*.parquet"))
    if not parquet_files:
        raise FileNotFoundError(
            f"Directory '{path}' exists but contains no parquet files for table "
            f"'{table_name}'."
        )
    return TableLocation(name=table_name, path=str(path), kind="directory")


def validate_dataset_layout(data_root: str | Path) -> list[TableLocation]:
    return [resolve_table_location(data_root, table) for table in REQUIRED_TABLES]


def table_source_glob(data_root: str | Path, table_name: str) -> str:
    location = resolve_table_location(data_root, table_name)
    if location.kind == "file":
        return location.path
    return str(Path(location.path) / "*.parquet")
