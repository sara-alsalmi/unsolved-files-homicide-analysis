# Unsolved Files: Homicide Analysis

Exploratory data analysis and an interactive Streamlit dashboard of U.S. homicide records, comparing cases reported **solved** and **unsolved**.

**Main question:** What characteristics are associated with homicides reported as unsolved, and how do the patterns vary by place and time?

## Dataset

| | |
|---|---|
| **Name** | Supplementary Homicide Report (`SHR76_25a.csv`) |
| **Source** | Murder Accountability Project (MAP): https://www.murderdata.org/p/data-docs.html |
| **Data dictionary** | [MAPdefinitionsSHR.pdf](https://www.dropbox.com/s/lo6tgo8nnbpqeru/MAPdefinitionsSHR.pdf?dl=1) |
| **Size** | 929,433 victim records, 31 columns (1976–2025) |
| **After cleaning** | 857,379 victim records (1976–2024) |

Each row is one victim. Columns include the reporting agency and place, year and month, victim and offender details, weapon, relationship, circumstance, and whether the case was **solved** (an offender was identified when the report was made).

## Project Structure

```
├── analysis_shr.ipynb           # EDA notebook: loading, cleaning, charts and insights
├── .streamlit/config.toml       # dashboard theme (dark)
├── dataset/                     # original data (not uploaded, see "How to Run")
└── streamlit_app/               # dashboard
    ├── app.py                   # main app: pages and filters
    ├── views.py                 # dashboard pages
    ├── charts.py                # chart helpers
    ├── data_utils.py            # loading, filters and summary tables
    ├── game.py                  # Cold Case game
    ├── clean_data_shr.parquet   # cleaned dataset used by the app
    ├── assets/                  # logo, styles, map boundaries and game files
    └── requirements.txt
```

## How to Run

1. **Install the libraries**
   ```
   pip install -r streamlit_app/requirements.txt
   pip install jupyter matplotlib seaborn
   ```
2. **Run the dashboard** from the project folder (the cleaned data is already included)
   ```
   streamlit run streamlit_app/app.py
   ```
3. **Run the notebook (optional):** download `SHR76_25a.csv` from the source link, place it in `dataset/`, and run `analysis_shr.ipynb`. It creates `clean_data_shr.csv`.

## Workflow

1. **Data exploration:** shape, data types, statistics, missing values and "Unknown" labels.
2. **Data cleaning**
   - Kept murder and non-negligent manslaughter only
   - Removed 2025 (incomplete) and justifiable homicides
   - Converted age code 999 to missing
   - Kept repeated rows (different victims of the same incident)
   - Renamed columns and saved the cleaned data
3. **EDA:** histograms, countplots, boxplots, bar charts, heatmaps, a scatter plot and a correlation heatmap.
4. **Dashboard:** interactive Plotly charts with filters (year slider, state multi-select, dropdowns).

## Dashboard Pages

| Page | Content |
|---|---|
| Overview | Summary cards, solved vs unsolved, trends by year and month |
| Geographic Analysis | State map, state ranking, metro areas |
| Victim Analysis | Age, sex, age groups, race |
| Weapons & Circumstances | Counts and unsolved % by weapon and circumstance |
| Unsolved Patterns | Common profiles, state-period comparison, missing information |
| Cold Case Game | Short fictional detective game |
| Data & Definitions | Cleaning steps, column definitions, data preview and downloads |

## Main Insights

- About **31%** of victim records were reported unsolved.
- **Circumstance shows the largest difference:** gang killings 48.8% unsolved, drugs 35.0%, arguments and brawls 7.4%.
- **Handguns** account for about half of all unsolved records.
- Ages **18–24** have the highest unsolved % (34.7%); ages 0–12 the lowest (12.1%).
- Male victim records are more often unsolved than female records (33.3% vs 22.7%).
- **Washington D.C.** has the highest unsolved % (61.1%).
- **Missing information:** 56.6% of unsolved records have an undetermined circumstance.

These are patterns in the records, not causes.

## Limitations

- "Solved" means an offender was identified when the report was made, not the current case status.
- Not all agencies report every year, so places and years are not fully comparable.
- Many unsolved records have missing details.
- Places refer to the reporting agency, not the exact crime location.

## Tools

Python, pandas, NumPy, Matplotlib, Seaborn, Plotly, Streamlit, Jupyter

*Independent student project. Not affiliated with any police or government agency.*
