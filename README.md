# DealerOS Reconciliation

A take-home project for comparing System A and System B records within organization boundaries.

## What I Built

This project imports the three supplied CSV files into SQLite, preserves the original row data, records row-level import warnings for dirty values, compares System A records against System B entries, and shows disagreements in a React table.

The backend is Django with Django REST Framework. It includes:

- a CSV importer for `locations.csv`, `system_a.csv`, and `system_b.csv`
- models for organizations, locations, System A records, and System B entries
- comparison logic for missing B entries, unknown B references, duplicate B entries, value mismatches, and data issues
- tenant-scoped matching through the organization derived from `locations.csv`
- a REST endpoint for disagreement results
- tests for the comparison rules

The frontend is React with Vite. It includes:

- a reason filter
- value sorting
- a plain table showing the reason, record, location, System A value, System B value, System B entry ids, and message

## How To Run It

From the repository root in PowerShell:

```powershell
python -m venv backend/.venv
backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
backend/.venv/Scripts/python.exe backend/manage.py migrate
backend/.venv/Scripts/python.exe backend/manage.py import_reconciliation_data --reset
backend/.venv/Scripts/python.exe backend/manage.py runserver
```

In a second terminal:

```powershell
cd frontend
npm.cmd ci
npm.cmd run dev
```

Open the frontend URL printed by Vite, normally:

```text
http://localhost:5173
```

Django runs at:

```text
http://127.0.0.1:8000
```

During development, Vite proxies `/api` requests to Django.


## Re-run The Database Import

Use these commands when you want to apply migrations and reload the CSV data into SQLite:

```powershell
python backend\manage.py migrate
python backend\manage.py import_reconciliation_data --reset
```
## API

The backend exposes disagreements at:

```text
GET /api/disagreements/
```

Supported query parameters:

- `reason`: optional filter, for example `value_mismatch`
- `sort=value`: optional amount sort for the results table

## Verify The Project

From the repository root:

```powershell
backend/.venv/Scripts/python.exe backend/manage.py check
backend/.venv/Scripts/python.exe backend/manage.py test reconciliation
cd frontend
npm.cmd run lint
npm.cmd run build
```

The current supplied dataset imports as 5 locations, 120 System A records, 121 System B entries, and 1 row warning. The comparison finds 11 disagreements split across the two organizations.

## Repository Structure

- `backend/`: Django project, importer, models, comparison logic, API endpoint, and tests.
- `frontend/`: React disagreement table, Vite proxy configuration, and npm dependency lockfile.
- `data/`: Original input CSVs.
- `DECISIONS.md`: Implementation choices and rejected alternatives.

## Comparison Rules

- Compare System A `total_value` against System B `value`.
- Normalize supported System B reference formats while preserving original CSV values.
- Use decimal arithmetic for amounts.
- Treat blank or invalid amounts as data issues, never zero.
- Match records only within the same organization from `locations.csv`.
- Treat `REC-1055` as a likely legitimate split only when same-org split labels and the combined amount support that interpretation; an equal sum alone is not enough.
- Date differences and voided-record handling are outside the initial comparison scope.

## Deliberately Did Not Build

I did not build authentication because the brief says to skip it.

I did not add background jobs or performance tuning because the supplied dataset has only a few hundred rows and the brief says performance is not the focus.

I did not reconcile date differences or voided-record semantics in the first pass. Those need product rules beyond the minimum disagreement types requested in the brief.

I kept the visual design plain. The screen is meant to prove the data flow and comparison behavior, not to be a polished product dashboard.

## How I Worked With The Agent


I used an AI agent to understand the requirements, create an implementation plan, and break the work into smaller steps.

I used AI for the initial full-stack boilerplate, database models, CSV import logic, APIs, and frontend setup. I chose SQLite because this is a small take-home project.

I reviewed and verified the generated code myself by running the application, checking the imported data, debugging issues, and testing the comparison logic. I also used the agent to help with debugging and test cases, but made the final implementation decisions myself.


### What did the AI agent get wrong, and how did you notice?

The agent initially suggested keeping dirty import problems in a separate database table. I noticed this might be extra because the brief only says dirty rows should survive and not be silently dropped. After checking that requirement, I changed the approach so each imported row keeps its own `import_warnings` and original `raw_data` instead.

### Which part are you least confident about, and why?

I am least confident about the special split handling for `REC-1055`. The current rule checks that the entries are in the same organization, have a split-like label, and their combined amount equals the System A amount. It works for the provided data, but in a real product I would want confirmation from the team before applying that rule more generally.

### If you had a second day, what would you fix first?

I would improve the review experience for each disagreement. The first thing I would add is a simple way to view the original raw System A and System B row values from the CSVs, so it is easier to understand why a row was flagged.





