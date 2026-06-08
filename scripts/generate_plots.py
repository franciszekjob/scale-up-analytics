import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import os

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "report", "figures")
os.makedirs(OUTPUT_DIR, exist_ok=True)

QUERIES = ["Q1", "Q3", "Q5", "Q6", "Q10", "Q21"]

DUCKDB = {
    "Q1":  {"min": 17.90, "mean": 18.49, "max": 19.38, "std": 0.78},
    "Q3":  {"min": 15.13, "mean": 15.59, "max": 15.91, "std": 0.41},
    "Q5":  {"min": 16.03, "mean": 17.20, "max": 19.09, "std": 1.65},
    "Q6":  {"min": 11.56, "mean": 12.04, "max": 12.57, "std": 0.51},
    "Q10": {"min": 25.01, "mean": 25.17, "max": 25.26, "std": 0.14},
    "Q21": {"min": 29.92, "mean": 31.30, "max": 33.30, "std": 1.77},
}

SPARK = {
    "Q1":  {"min":  8.89, "mean":  9.35, "max":  9.89, "std": 0.50},
    "Q3":  {"min": 15.94, "mean": 16.16, "max": 16.40, "std": 0.23},
    "Q5":  {"min": 26.46, "mean": 26.79, "max": 27.11, "std": 0.33},
    "Q6":  {"min":  2.91, "mean":  3.07, "max":  3.34, "std": 0.23},
    "Q10": {"min": 13.97, "mean": 14.01, "max": 14.08, "std": 0.06},
    "Q21": {"min": 54.71, "mean": 55.36, "max": 55.75, "std": 0.57},
}

duck_means = [DUCKDB[q]["mean"] for q in QUERIES]
duck_stds  = [DUCKDB[q]["std"]  for q in QUERIES]
spark_means = [SPARK[q]["mean"] for q in QUERIES]
spark_stds  = [SPARK[q]["std"]  for q in QUERIES]
speedup = [SPARK[q]["mean"] / DUCKDB[q]["mean"] for q in QUERIES]

# ── Wykres 1: Grouped bar chart ──────────────────────────────
fig, ax = plt.subplots(figsize=(12, 6))
x = np.arange(len(QUERIES))
w = 0.35

bars_duck  = ax.bar(x - w/2, duck_means,  w, yerr=duck_stds,  capsize=4,
                    label="DuckDB (HPC)", color="#1f77b4", alpha=0.85)
bars_spark = ax.bar(x + w/2, spark_means, w, yerr=spark_stds, capsize=4,
                    label="Spark (EMR)",  color="#ff7f0e", alpha=0.85)

for bar in bars_duck:
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.8,
            f"{bar.get_height():.1f}s", ha="center", va="bottom", fontsize=8)
for bar in bars_spark:
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.8,
            f"{bar.get_height():.1f}s", ha="center", va="bottom", fontsize=8)

ax.set_xlabel("Zapytanie TPC-H", fontsize=12)
ax.set_ylabel("Czas wykonania (s)", fontsize=12)
ax.set_title("TPC-H 100 GB — Porównanie czasów wykonania\nDuckDB (scale-up) vs Spark (scale-out)",
             fontsize=13, fontweight="bold")
ax.set_xticks(x)
ax.set_xticklabels(QUERIES)
ax.legend(fontsize=11)
ax.grid(axis="y", alpha=0.3)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "01_execution_time_comparison.png"), dpi=150, bbox_inches="tight")
plt.close()
print("Zapisano: 01_execution_time_comparison.png")

# ── Wykres 2: Speedup ratio ──────────────────────────────────
fig, ax = plt.subplots(figsize=(10, 5))
colors = ["#2ca02c" if s >= 1 else "#d62728" for s in speedup]
bars = ax.bar(QUERIES, speedup, color=colors, alpha=0.85, edgecolor="black", linewidth=0.8)
ax.axhline(1.0, color="black", linewidth=2, linestyle="--", label="parytet (1×)")

for bar, val in zip(bars, speedup):
    label = f"{val:.2f}×"
    ypos = val + 0.04 if val >= 1 else val - 0.1
    va = "bottom" if val >= 1 else "top"
    ax.text(bar.get_x() + bar.get_width()/2, ypos, label,
            ha="center", va=va, fontweight="bold", fontsize=10)

ax.set_ylabel("Speedup (Spark / DuckDB)", fontsize=12)
ax.set_xlabel("Zapytanie TPC-H", fontsize=12)
ax.set_title("Speedup: DuckDB vs Spark\n(zielony > 1 = DuckDB szybszy, czerwony < 1 = Spark szybszy)",
             fontsize=13, fontweight="bold")
ax.legend(fontsize=11)
ax.grid(axis="y", alpha=0.3)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "02_speedup_ratio.png"), dpi=150, bbox_inches="tight")
plt.close()
print("Zapisano: 02_speedup_ratio.png")

# ── Wykres 3: Heatmapa znormalizowana ────────────────────────
try:
    import seaborn as sns
    data = np.array([duck_means, spark_means])
    norm_data = data / data.min(axis=0)

    fig, ax = plt.subplots(figsize=(10, 3))
    sns.heatmap(norm_data, annot=True, fmt=".2f", cmap="RdYlGn_r",
                xticklabels=QUERIES, yticklabels=["DuckDB", "Spark"],
                linewidths=0.5, ax=ax,
                cbar_kws={"label": "Czas względny (1.0 = najszybszy)"})
    ax.set_title("Heatmapa wydajności (1.0 = najszybszy dla danego zapytania)",
                 fontsize=12, fontweight="bold")
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "03_heatmap.png"), dpi=150, bbox_inches="tight")
    plt.close()
    print("Zapisano: 03_heatmap.png")
except ImportError:
    print("Pominięto heatmapę (brak seaborn)")

print("Gotowe! Wykresy zapisane w:", OUTPUT_DIR)
