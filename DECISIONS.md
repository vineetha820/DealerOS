# Decisions

1. **Django 5.2 and Django REST Framework.** Alternative: another backend framework. Reason: it follows the preferred stack and keeps the backend easy to review for this assignment.
2. **React with Vite.** Alternative: Next.js. Reason: the app is a single internal screen, so Vite keeps the frontend smaller than a full Next.js setup.
3. **SQLite for local development.** Alternative: PostgreSQL. Reason: the dataset is tiny and the reviewer should be able to run the app without a separate database service.
4. **Keep raw CSV rows beside parsed fields.** Alternative: store only cleaned values. Reason: dirty rows must survive import and remain auditable.
5. **Store import warnings on imported rows.** Alternative: create a separate import-issue table. Reason: row-level warnings satisfy the dirty-data requirement with less schema overhead.
6. **Normalize System B references while preserving originals.** Alternative: overwrite the dirty reference value. Reason: comparison needs a clean key, but review/debugging needs the source value.
7. **Compare System A `total_value` with System B `value` using decimals.** Alternative: compare other fields or use floats. Reason: these are the matching amount fields, and decimal arithmetic avoids rounding surprises.
8. **Treat blank or invalid amounts as data issues.** Alternative: coerce blanks and bad numbers to `0`. Reason: zero is a real amount, while blank or invalid data means the row cannot be trusted for amount comparison.
9. **Match records only within the same organization.** Alternative: match globally by record id. Reason: `locations.csv` defines tenant ownership, and cross-tenant matching would leak data.
10. **Handle `REC-1055` as a narrow split exception and leave date/state checks out of scope.** Alternative: accept any equal-sum split and also reconcile dates/states now. Reason: the documented label plus matching sum makes `REC-1055` defensible, while broader split/date/state rules would add ambiguity to the first working slice.
