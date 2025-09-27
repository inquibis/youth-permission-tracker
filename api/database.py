import os
from urllib.parse import quote_plus
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base


# Require ENV to be set explicitly
ENV = os.getenv("ENV")
if not ENV:
    raise RuntimeError("ENV must be set (e.g., 'test' or 'prod').")

if ENV == "test":
    # --- SQLite for local/CI testing ---
    # Always use a fixed absolute path to avoid multiple accidental DB files
    base_dir = os.path.dirname(os.path.abspath(__file__))
    default_sqlite_path = os.path.join(base_dir, "activitydb.db")

    SQLALCHEMY_DATABASE_URL = os.getenv(
        "TEST_DATABASE_URL",
        f"sqlite:///{default_sqlite_path}"
    )
    connect_args = {"check_same_thread": False}

else:
    # --- MySQL for dev/staging/prod ---
    try:
        DB_USER = os.environ["DB_USER"]
        DB_PASSWORD = os.environ["DB_PASSWORD"]
        DB_HOST = os.environ["DB_HOST"]
        DB_PORT = os.environ.get("DB_PORT", "3306")
        DB_NAME = os.environ["DB_NAME"]
    except KeyError as e:
        raise RuntimeError(f"Missing required environment variable: {e.args[0]}")

    SQLALCHEMY_DATABASE_URL = os.getenv(
        "DATABASE_URL",
        f"mysql+mysqlconnector://{DB_USER}:{quote_plus(DB_PASSWORD)}"
        f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
    connect_args = {}

# Engine & session factory
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,
    future=True,
    connect_args=connect_args,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
