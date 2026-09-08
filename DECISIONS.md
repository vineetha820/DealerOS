# Decisions

1. **Django 5.2 and Django REST Framework.** Alternative: another backend framework. Reason: follows the preferred stack and supports the available Python 3.10 environment.
2. **React with Vite.** Alternative: Next.js. Reason: a single internal screen does not need server-side rendering.
3. **SQLite for local development.** Alternative: PostgreSQL. Reason: the small dataset needs no separately managed database server.
4. **Keep raw CSV rows beside parsed fields.** Alternative: store only cleaned values. Reason: dirty rows must survive import so comparison mistakes can be audited.
5. **Record import issues instead of rejecting rows.** Alternative: fail the import on bad numbers or blank values. Reason: the assignment asks the importer to survive messy exports without silently dropping rows.
6. **Normalize System B references during import.** Alternative: normalize only inside comparison code. Reason: storing the normalized key makes later matching code simpler and easier to inspect.

Comparison and tenant-scoping decisions will be added in the next step.
