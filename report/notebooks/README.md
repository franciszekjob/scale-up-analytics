# Notebook Guidance

Use notebooks for interactive exploration after the dataset and benchmark code
are already working from the CLI.

Recommended notebook split:

- `duckdb.ipynb`
  focused on local SQL exploration, plan inspection, and pilot runs
- `pandas.ipynb`
  focused on memory behavior and failure analysis on the single node
- `spark.ipynb`
  focused on cluster-side verification and ad hoc result inspection

Recommended structure in each notebook:

1. environment setup and version capture
2. dataset validation
3. one-query pilot run
4. result preview and digest check
5. exploratory profiling or visualization

Keep benchmark runs themselves in the CLI so the experiment remains repeatable.
