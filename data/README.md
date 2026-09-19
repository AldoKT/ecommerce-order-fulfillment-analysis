# Dataset

## Source

Dataset: Brazilian E-Commerce Public Dataset by Olist.

Kaggle source: <https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce>

The dataset is used here as a public anonymized data source. This repository does not imply affiliation with or commissioning by Olist.

## Raw and processed files

Raw CSV files belong in `data/raw/`. Processed or derived CSV files belong in `data/processed/`.

Both raw and processed CSV files are excluded from Git by the repository `.gitignore`. This keeps the repository focused on reproducible code and documentation rather than redistributing the source data.

## Download and placement

1. Download the dataset from the Kaggle URL above.
2. Extract the archive locally.
3. Place the expected CSV files directly in `data/raw/`.
4. Run `python/01_data_profiling.ipynb` from the repository root using the project virtual environment.

The profiling notebook reads the CSV files without modifying them.

## Notebook execution

From the repository root, the standard command is:

```powershell
python -m jupyter nbconvert --to notebook --execute --inplace python/01_data_profiling.ipynb
```

In the managed Windows environment used for this repository, the standard command may fail while creating the default user Jupyter directory or applying permissions to the kernel connection file. The fallback used for this environment is:

```powershell
$jupyterTemp = Join-Path (Get-Location) '.jupyter-temp'
New-Item -ItemType Directory -Force -Path $jupyterTemp | Out-Null
$env:IPYTHONDIR = $jupyterTemp
$env:JUPYTER_CONFIG_DIR = (Join-Path $jupyterTemp 'config')
$env:JUPYTER_DATA_DIR = (Join-Path $jupyterTemp 'data')
$env:JUPYTER_RUNTIME_DIR = (Join-Path $jupyterTemp 'runtime')
New-Item -ItemType Directory -Force -Path $env:JUPYTER_CONFIG_DIR,$env:JUPYTER_DATA_DIR,$env:JUPYTER_RUNTIME_DIR | Out-Null
python -c "import jupyter_core.paths as jp; jp.win32_restrict_file_to_user=lambda _: None; import nbformat; from nbclient import NotebookClient; from pathlib import Path; path=Path('python/01_data_profiling.ipynb'); nb=nbformat.read(path, as_version=4); NotebookClient(nb, timeout=120, kernel_name='python3').execute(); nbformat.write(nb, path)"
Remove-Item -LiteralPath $jupyterTemp -Recurse -Force
```

The fallback uses the active virtual environment and removes its temporary directory after execution.

## Expected raw filenames

```text
olist_customers_dataset.csv
olist_geolocation_dataset.csv
olist_order_items_dataset.csv
olist_order_payments_dataset.csv
olist_order_reviews_dataset.csv
olist_orders_dataset.csv
olist_products_dataset.csv
olist_sellers_dataset.csv
product_category_name_translation.csv
```
