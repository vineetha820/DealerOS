# Decisions

1. **Django 5.2 and Django REST Framework.** Alternative: another backend framework. Reason: follows the preferred stack and supports the available Python 3.10 environment.
2. **React with Vite.** Alternative: Next.js. Reason: a single internal screen does not need server-side rendering.
3. **SQLite for local development.** Alternative: PostgreSQL. Reason: the small dataset needs no separately managed database server.

Comparison and tenant-scoping decisions will be added in the next step.
