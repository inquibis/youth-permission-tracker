# Run
`alembic revision --autogenerate -m "Initial tables: Activity and User"`
`alembic upgrade head`

# Rollback
## Rollback one version
`alembic downgrade -1`
## Rollback to a specific version
`alembic downgrade <revision_id>`
