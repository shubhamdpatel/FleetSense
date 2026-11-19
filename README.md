# FleetSense – Taxi Operations Analytics Platform

FleetSense is a taxi operations analytics project focused on analyzing NYC Yellow Taxi trip data to identify demand patterns, revenue trends, and operational insights.

## Tech Stack

- Python 3.13
- Pandas
- DuckDB
- PyArrow
- Streamlit
- Pytest

## Project Structure

```text
FleetSense/
├── pipeline/
│   ├── ingest.py
│   └── validate.py
├── sql/
│   └── warehouse/
│       ├── facts.sql
│       ├── dimensions.sql
│       └── hourly_demand.sql
├── metrics/
│   └── metrics.py
├── notebooks/
├── dashboard/
│   └── app.py
├── tests/
├── data/
│   ├── raw/
│   └── clean/
├── .github/
│   └── workflows/
│       └── ci.yml
├── requirements.txt
├── Makefile
├── README.md
└── .gitignore
```

## Prerequisites

- Python 3.13 or higher
- Git
- VS Code (recommended)

## Getting Started

### 1. Clone the repository

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
cd FleetSense
```

### 2. Create a virtual environment

**macOS / Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows:**

```bash
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Run tests

```bash
make test
```

### 5. Run the dashboard

```bash
make run
```

The dashboard will be available at:

```text
http://localhost:8501
```

Note: Dashboard functionality will be available once the Streamlit application is implemented.

## Available Make Commands

| Command | Description |
|---|---|
| `make install` | Install project dependencies |
| `make test` | Run automated tests |
| `make run` | Start Streamlit dashboard |
| `make clean` | Remove Python cache files |

## Git Workflow

We maintain two main branches:

- `main` – Stable and finalized Phase 1 code.
- `development` – Active development and integration.

Always work on the `development` branch for ongoing tasks.

```bash
git checkout development
git pull origin development
```

After completing your work:

```bash
git add .
git commit -m "Describe your changes"
git push origin development
```

Merge into `main` only after testing and review.

## Data Management

- `data/raw/` – Original downloaded datasets.
- `data/clean/` – Cleaned and processed datasets.

**Important:** Dataset files are excluded from Git and should not be committed to the repository.

## Testing and CI

GitHub Actions automatically runs the test suite when code is pushed to or a pull request targets the `main` or `development` branches.

## Team Development

All team members should:

- Work on the development branch.
- Write clean and reusable code.
- Add tests for new functionality.
- Keep documentation updated.
- Review changes before merging into main.
