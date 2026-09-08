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
- tests for the importer, comparison rules, and API behavior

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

## API

The backend exposes disagreements at:

```text
GET /api/disagreements/
```

Supported query parameters:

- `reason`: optional filter, for example `value_mismatch`
- `sort=value`: optional amount sort for the results table
- `page`: optional page number, defaults to `1`
- `page_size`: optional page size, defaults to `10`

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

I did not add pagination, background jobs, or performance tuning because the supplied dataset has only a few hundred rows and the brief says performance is not the focus.

I did not reconcile date differences or voided-record semantics in the first pass. Those need product rules beyond the minimum disagreement types requested in the brief.

I kept the visual design plain. The screen is meant to prove the data flow and comparison behavior, not to be a polished product dashboard.

## How I Worked With The Agent

I used the agent to read the brief, inspect the CSV files, scaffold the Django and React project, and move through the work in small steps. I asked it to explain code back to me while building so I could check whether the implementation was understandable enough to defend in a follow-up call.

I reviewed the agent's choices as we went. One example was the initial `ImportIssue` database table. After asking whether the brief required it, I decided it was extra structure and had the agent remove it in favor of row-level `import_warnings`.

The agent also helped run verification after each meaningful step: Django checks, importer runs, comparison tests, API tests, frontend lint, frontend build, and local endpoint checks.

## Required Reflection Questions

### What did the AI agent get wrong, and how did you notice?

The agent initially added a separate import-issue database table. I noticed this was probably more than the brief required when reviewing the model design and asking whether the assignment specifically requested that table. The brief only says dirty rows must survive without being silently dropped, so I simplified the design to keep warnings directly on the imported rows.

### Which part are you least confident about, and why?

I am least confident about the special handling for `REC-1055`. The rule is documented and intentionally narrow: it checks the same organization, a split-like label, and the combined amount. Still, split handling is usually a product/business rule, so I would want confirmation before generalizing it beyond this one record.

### If you had a second day, what would you fix first?

I would improve the UI and API around auditability. The next useful improvement would be showing the original raw System A and System B row values in an expandable detail area so a reviewer can quickly understand why each disagreement was flagged.



