.PHONY: migrate migrate-fresh makemigrations migrate-down

# Apply all pending migrations
migrate:
	DB_HOST=localhost uv run alembic upgrade head

# Drop the entire public schema and re-apply all migrations from scratch.
# Equivalent to `php artisan migrate:fresh`. Destructive — wipes data.
# Drops the schema outright (rather than `alembic downgrade base`) so it works
# even if alembic_version is out of sync with what's actually in the database.
migrate-fresh:
	PGPASSWORD=$$(grep '^DB_PASSWORD=' .env | cut -d '=' -f2) psql \
		-h localhost \
		-p $$(grep '^DB_PORT=' .env | cut -d '=' -f2) \
		-U $$(grep '^DB_USER=' .env | cut -d '=' -f2) \
		-d $$(grep '^DBNAME=' .env | cut -d '=' -f2) \
		-c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
	DB_HOST=localhost uv run alembic upgrade head

# Roll back the last migration
migrate-down:
	DB_HOST=localhost uv run alembic downgrade -1

# Generate a new migration from model changes
# Usage: make makemigrations m="add foo column"
makemigrations:
	DB_HOST=localhost uv run alembic revision --autogenerate -m "$(m)"
