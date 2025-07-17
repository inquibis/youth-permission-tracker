from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

ENV = os.getenv("ENV", "test").lower()  #change

if ENV == "test":
    DATABASE_URL = os.getenv("SQLITE_PATH", "sqlite:///./test.db")
    # can use to verify ver 
    # python -c "import sqlite3, sys; print(sys.version); print(sqlite3.sqlite_version)"
    connect_args = {"check_same_thread": False}
else:
    DATABASE_URL = os.getenv("DATABASE_URL")
    connect_args = {}

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

# DB_URL = (
#     f"mysql+mysqlconnector://{os.getenv('MYSQL_USER')}:{os.getenv('MYSQL_PASSWORD')}"
#     f"@{os.getenv('MYSQL_HOST')}:{os.getenv('MYSQL_PORT')}/{os.getenv('MYSQL_DB')}"
# )

# engine = create_engine(DB_URL, echo=True)
# SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
# Base = declarative_base()
