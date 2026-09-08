# Decisions

1. **Django 5.2 and Django REST Framework.** Alternative: another backend framework. Reason: follows the preferred stack and supports the available Python 3.10 environment.
2. **React with Vite.** Alternative: Next.js. Reason: a single internal screen does not need server-side rendering.
3. **SQLite for local development.** Alternative: PostgreSQL. Reason: the small dataset needs no separately managed database server.
4. **Keep raw CSV rows beside parsed fields.** Alternative: store only cleaned values. Reason: dirty rows must survive import so comparison mistakes can be audited.
5. **Store import warnings on the affected rows instead of creating a separate issue table.** Alternative: keep a separate import-issue database table. Reason: the brief only requires dirty rows to survive, and row-level warnings keep the schema smaller while still making bad values visible.
6. **Normalize System B references during import.** Alternative: normalize only inside comparison code. Reason: storing the normalized key makes later matching code simpler and easier to inspect.
7. **Compare System A `total_value` against System B `value`.** Alternative: compare base value, adjustment, or other event fields. Reason: the brief asks for disagreement in the systems' reported value, and these are the directly comparable amount fields.
8. **Use decimal arithmetic for all amounts.** Alternative: parse amounts as floats. Reason: currency-like values need exact comparison without binary floating-point rounding surprises.
9. **Treat blank or invalid amounts as data issues, not zero.** Alternative: coerce blank or bad values to `0`. Reason: zero is a real amount, while a missing or unparseable amount means the source data cannot support a trustworthy comparison.
10. **Match records only within the same organization.** Alternative: match globally by record id alone. Reason: the brief says tenant data must not leak, so the organization from `locations.csv` is part of the comparison boundary.
11. **Allow only a documented likely split exception for `REC-1055`.** Alternative: consider any entries with an equal combined sum to be a valid split. Reason: an equal sum alone could hide duplicate or unrelated entries, so `REC-1055` is treated as likely legitimate only when the entries are in the same organization, their labels indicate they are split parts, and their combined amount equals System A's amount.
12. **Leave date differences and voided-record handling outside the initial comparison scope.** Alternative: add date/state reconciliation in the first comparison pass. Reason: the minimum required value disagreements should be completed and tested first, while date/state interpretation can be documented as future work.


