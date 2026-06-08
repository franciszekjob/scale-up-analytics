from __future__ import annotations

from typing import TYPE_CHECKING, Callable

try:
    import pandas as pd
except ImportError:  # pragma: no cover - exercised only without optional deps
    pd = None

if TYPE_CHECKING:
    import pandas as pandas_module


def _require_pandas() -> "pandas_module":
    if pd is None:
        raise RuntimeError(
            "pandas is required to run the Pandas benchmark. "
            "Install dependencies from requirements.txt first."
        )
    return pd


def _revenue(frame: pd.DataFrame) -> pd.Series:
    _require_pandas()
    return frame["l_extendedprice"] * (1 - frame["l_discount"])


def run_q1(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    pd_module = _require_pandas()
    lineitem = tables["lineitem"].copy()
    filtered = lineitem[lineitem["l_shipdate"] <= pd_module.Timestamp("1998-09-02")].copy()
    filtered["disc_price"] = filtered["l_extendedprice"] * (1 - filtered["l_discount"])
    filtered["charge"] = filtered["disc_price"] * (1 + filtered["l_tax"])

    result = (
        filtered.groupby(["l_returnflag", "l_linestatus"], as_index=False)
        .agg(
            sum_qty=("l_quantity", "sum"),
            sum_base_price=("l_extendedprice", "sum"),
            sum_disc_price=("disc_price", "sum"),
            sum_charge=("charge", "sum"),
            avg_qty=("l_quantity", "mean"),
            avg_price=("l_extendedprice", "mean"),
            avg_disc=("l_discount", "mean"),
            count_order=("l_orderkey", "count"),
        )
        .sort_values(["l_returnflag", "l_linestatus"], ignore_index=True)
    )
    return result


def run_q3(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    pd_module = _require_pandas()
    customer = tables["customer"]
    orders = tables["orders"]
    lineitem = tables["lineitem"]

    merged = customer.loc[customer["c_mktsegment"] == "BUILDING", ["c_custkey"]]
    merged = merged.merge(
        orders.loc[
            orders["o_orderdate"] < pd_module.Timestamp("1995-03-15"),
            ["o_orderkey", "o_custkey", "o_orderdate", "o_shippriority"],
        ],
        left_on="c_custkey",
        right_on="o_custkey",
        how="inner",
    )
    merged = merged.merge(
        lineitem.loc[
            lineitem["l_shipdate"] > pd_module.Timestamp("1995-03-15"),
            ["l_orderkey", "l_extendedprice", "l_discount"],
        ],
        left_on="o_orderkey",
        right_on="l_orderkey",
        how="inner",
    )
    merged["revenue"] = _revenue(merged)

    result = (
        merged.groupby(["l_orderkey", "o_orderdate", "o_shippriority"], as_index=False)
        .agg(revenue=("revenue", "sum"))
        .sort_values(["revenue", "o_orderdate"], ascending=[False, True], ignore_index=True)
        .head(10)
    )
    return result


def run_q5(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    pd_module = _require_pandas()
    customer = tables["customer"][["c_custkey", "c_nationkey"]]
    orders = tables["orders"].loc[
        (tables["orders"]["o_orderdate"] >= pd_module.Timestamp("1994-01-01"))
        & (tables["orders"]["o_orderdate"] < pd_module.Timestamp("1995-01-01")),
        ["o_orderkey", "o_custkey"],
    ]
    lineitem = tables["lineitem"][["l_orderkey", "l_suppkey", "l_extendedprice", "l_discount"]]
    supplier = tables["supplier"][["s_suppkey", "s_nationkey"]]
    nation = tables["nation"][["n_nationkey", "n_name", "n_regionkey"]]
    region = tables["region"].loc[
        tables["region"]["r_name"] == "ASIA",
        ["r_regionkey"],
    ]

    merged = customer.merge(orders, left_on="c_custkey", right_on="o_custkey", how="inner")
    merged = merged.merge(lineitem, left_on="o_orderkey", right_on="l_orderkey", how="inner")
    merged = merged.merge(supplier, left_on="l_suppkey", right_on="s_suppkey", how="inner")
    merged = merged.loc[merged["c_nationkey"] == merged["s_nationkey"]]
    merged = merged.merge(nation, left_on="s_nationkey", right_on="n_nationkey", how="inner")
    merged = merged.merge(region, left_on="n_regionkey", right_on="r_regionkey", how="inner")
    merged["revenue"] = _revenue(merged)

    result = (
        merged.groupby("n_name", as_index=False)
        .agg(revenue=("revenue", "sum"))
        .sort_values("revenue", ascending=False, ignore_index=True)
    )
    return result


def run_q6(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    pd_module = _require_pandas()
    lineitem = tables["lineitem"]
    filtered = lineitem.loc[
        (lineitem["l_shipdate"] >= pd_module.Timestamp("1994-01-01"))
        & (lineitem["l_shipdate"] < pd_module.Timestamp("1995-01-01"))
        & (lineitem["l_discount"] >= 0.05)
        & (lineitem["l_discount"] <= 0.07)
        & (lineitem["l_quantity"] < 24),
        ["l_extendedprice", "l_discount"],
    ]
    revenue = (filtered["l_extendedprice"] * filtered["l_discount"]).sum()
    return pd_module.DataFrame({"revenue": [revenue]})


def run_q9(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    _require_pandas()
    part = tables["part"].loc[
        tables["part"]["p_name"].str.lower().str.contains("green", regex=False),
        ["p_partkey"],
    ]
    lineitem = tables["lineitem"][
        ["l_orderkey", "l_partkey", "l_suppkey", "l_extendedprice", "l_discount", "l_quantity"]
    ]
    supplier = tables["supplier"][["s_suppkey", "s_nationkey"]]
    partsupp = tables["partsupp"][["ps_partkey", "ps_suppkey", "ps_supplycost"]]
    orders = tables["orders"][["o_orderkey", "o_orderdate"]]
    nation = tables["nation"][["n_nationkey", "n_name"]]

    merged = part.merge(lineitem, left_on="p_partkey", right_on="l_partkey", how="inner")
    merged = merged.merge(supplier, left_on="l_suppkey", right_on="s_suppkey", how="inner")
    merged = merged.merge(
        partsupp,
        left_on=["l_partkey", "l_suppkey"],
        right_on=["ps_partkey", "ps_suppkey"],
        how="inner",
    )
    merged = merged.merge(orders, left_on="l_orderkey", right_on="o_orderkey", how="inner")
    merged = merged.merge(nation, left_on="s_nationkey", right_on="n_nationkey", how="inner")
    merged["amount"] = _revenue(merged) - merged["ps_supplycost"] * merged["l_quantity"]
    merged["o_year"] = merged["o_orderdate"].dt.year

    result = (
        merged.groupby(["n_name", "o_year"], as_index=False)
        .agg(sum_profit=("amount", "sum"))
        .sort_values(["n_name", "o_year"], ascending=[True, False], ignore_index=True)
        .rename(columns={"n_name": "nation"})
    )
    return result


def run_q18(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    _require_pandas()
    customer = tables["customer"][["c_custkey", "c_name"]]
    orders = tables["orders"][["o_orderkey", "o_custkey", "o_orderdate", "o_totalprice"]]
    lineitem = tables["lineitem"][["l_orderkey", "l_quantity"]]

    eligible_orders = (
        lineitem.groupby("l_orderkey", as_index=False)
        .agg(total_quantity=("l_quantity", "sum"))
        .loc[lambda frame: frame["total_quantity"] > 300, ["l_orderkey"]]
    )
    merged = eligible_orders.merge(orders, left_on="l_orderkey", right_on="o_orderkey", how="inner")
    merged = merged.merge(customer, left_on="o_custkey", right_on="c_custkey", how="inner")
    merged = merged.merge(lineitem, left_on="o_orderkey", right_on="l_orderkey", how="inner")

    result = (
        merged.groupby(
            ["c_name", "c_custkey", "o_orderkey", "o_orderdate", "o_totalprice"],
            as_index=False,
        )
        .agg(sum_quantity=("l_quantity", "sum"))
        .sort_values(["o_totalprice", "o_orderdate"], ascending=[False, True], ignore_index=True)
        .head(100)
    )
    return result


PANDAS_QUERY_RUNNERS: dict[str, Callable[[dict[str, pd.DataFrame]], pd.DataFrame]] = {
    "q1": run_q1,
    "q3": run_q3,
    "q5": run_q5,
    "q6": run_q6,
    "q9": run_q9,
    "q18": run_q18,
}
