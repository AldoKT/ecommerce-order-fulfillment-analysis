# Project reproduction guide

Run these commands from the repository root in Windows PowerShell. Raw source files and generated processed CSVs are Git-ignored; the Power BI `.pbix` file is also not included in Git. The tracked screenshots are a visual record of the dashboard.

## 1. Create the environment

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If PowerShell execution policy blocks activation, run the remaining commands with `& .\.venv\Scripts\python.exe` instead.

## 2. Confirm raw files

Place the public Olist CSV files in `data/raw/`, then confirm the expected nine files:

```powershell
Get-ChildItem data\raw\*.csv
```

The required files are the eight `olist_*_dataset.csv` files plus `product_category_name_translation.csv` (including `olist_geolocation_dataset.csv`).

## 3. Run profiling and cleaning notebooks

```powershell
& .\.venv\Scripts\jupyter.exe nbconvert --to notebook --execute --inplace python\01_data_profiling.ipynb --ExecutePreprocessor.timeout=120
& .\.venv\Scripts\jupyter.exe nbconvert --to notebook --execute --inplace python\02_data_cleaning.ipynb --ExecutePreprocessor.timeout=120
```

On managed Windows installations, Jupyter may fail while applying its user-only permission check. Use this documented fallback for each notebook in that case:

```powershell
& .\.venv\Scripts\python.exe -c "import jupyter_core.paths as jp; jp.win32_restrict_file_to_user=lambda _: None; import nbformat; from nbclient import NotebookClient; from pathlib import Path; path=Path('python/01_data_profiling.ipynb'); nb=nbformat.read(path, as_version=4); NotebookClient(nb, timeout=120, kernel_name='python3').execute(); nbformat.write(nb, path)"
& .\.venv\Scripts\python.exe -c "import jupyter_core.paths as jp; jp.win32_restrict_file_to_user=lambda _: None; import nbformat; from nbclient import NotebookClient; from pathlib import Path; path=Path('python/02_data_cleaning.ipynb'); nb=nbformat.read(path, as_version=4); NotebookClient(nb, timeout=120, kernel_name='python3').execute(); nbformat.write(nb, path)"
```

Notebook execution updates the notebook outputs and regenerates `docs/data-quality-report.md`, `data/processed/*.csv`, and (where produced by the notebook) related generated artifacts. These data CSVs are ignored by Git.

## 4. Validate the model and run SQL analysis

```powershell
& .\.venv\Scripts\python.exe python\03_power_bi_validation.py
& .\.venv\Scripts\python.exe python\04_sql_analysis.py
& .\.venv\Scripts\python.exe -m unittest testing\test_sql_analysis.py -v
& .\.venv\Scripts\python.exe python\05_final_project_validation.py
```

`04_sql_analysis.py` uses an in-memory SQLite database and regenerates the deterministic `docs/sql-analysis.md` report. It does not create a persistent database file. `05_final_project_validation.py` is read-only and checks project packaging, documentation, source-control ignores, dashboard assets, and headline reconciliation.

## 5. Power BI

Import the five processed CSVs described in the [model specification](power-bi-model-spec.md), create `DimDate` and the documented DAX measures, then follow the [dashboard guide](dashboard-guide.md). The PBIX file is intentionally excluded from Git; use `dashboard/screenshots/` to compare the visible pages.
