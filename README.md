# DealerOS Reconciliation

A take-home project for comparing System A and System B records within organization boundaries.

## Current status

Step 2 is complete: Django and Django REST Framework backend, React/Vite frontend, SQLite configuration, original CSV inputs, a durable importer, and documented comparison rules. Comparison logic, tenant-scoped APIs, and the results table are not implemented yet.

## Requirements

- Python 3.10 or later compatible with Django 5.2 (verified with Python 3.10.11).
- Node.js 24 and npm (verified with Node.js 24.18.0).

## Run locally (PowerShell, from the repository root)

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

Open the frontend URL printed by Vite (normally http://localhost:5173). Django runs at http://127.0.0.1:8000. The frontend currently shows a placeholder and does not call the backend.

Django settings are for local development; the checked-in key is an explicit development placeholder.

## Verify setup

```powershell
backend/.venv/Scripts/python.exe backend/manage.py check
backend/.venv/Scripts/python.exe backend/manage.py test reconciliation
cd frontend
npm.cmd run lint
npm.cmd run build
```

## Repository structure

- `backend/`: Django project, importer command, data models, and pinned Python dependencies.
- `frontend/`: React application and npm dependency lockfile.
- `data/`: Original input CSVs, unchanged (5 locations, 120 A records, 121 B entries).
- `DECISIONS.md`: Implementation choices and rejected alternatives.

## Comparison rules to implement next

- Compare System A `total_value` against System B `value`.
- Normalize supported System B reference formats while preserving original CSV values.
- Use decimal arithmetic for amounts.
- Treat blank or invalid amounts as data issues, never zero.
- Match records only within the same organization from `locations.csv`.
- Treat `REC-1055` as a likely legitimate split only when same-org split labels and the combined amount support that interpretation; an equal sum alone is not enough.
- Date differences and voided-record handling are outside the initial comparison scope.

## Deliberately omitted

Authentication, elaborate visual design, and performance optimization are outside the initial assignment scope. Reconciliation features remain planned work, not completed omissions.

## How I worked with the agent

The agent inspected the brief and CSV files, outlined the implementation plan, and scaffolded the project. The agent added the importer and I checked it by running migrations, importing the supplied CSVs, and adding a focused test for dirty-row preservation. The first visible correction was that Django needed defaults for new non-null migration fields, which was fixed before continuing.

## Required reflection questions

### What did the AI agent get wrong, and how did you notice?

To be completed with a real example from implementation and review.

### Which part are you least confident about, and why?

To be completed after implementing and testing the comparison rules.

### If you had a second day, what would you fix first?

To be completed after the working slice is evaluated.


