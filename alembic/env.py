import os
from sqlalchemy import create_engine
from logging.config import fileConfig
from alembic import context

# this is the Alembic Config object, which provides access to values within the .ini file in use.
config = context.config
fileConfig(config.config_file_name)

# Read ENV
ENV = os.getenv("ENV", "prod")

if ENV == "test":
    # Local SQLite database for tests
    SQLALCHEMY_DATABASE_URL = "sqlite:///./activitydb.db"
else:
    # MySQL for everything else
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_NAME = os.getenv("DB_NAME", "mydatabase")
    SQLALCHEMY_DATABASE_URL = f"mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"

# Import models’ metadata
from models import Base  # make sure models.Base exists
target_metadata = Base.metadata

def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    context.configure(
        url=SQLALCHEMY_DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    """Run migrations in 'online' mode."""
    connectable = create_engine(SQLALCHEMY_DATABASE_URL)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
