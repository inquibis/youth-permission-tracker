# # Instead of:
# DB = DatabaseEngine(DB_PATH)

# # Use:
# DB = PostgreSQLEngine("postgresql://user:password@localhost:5432/youth_tracker")
# DB = PostgreSQLEngine("$DATABASE_URL")  # Reads from DATABASE_URL env var
# DB = MySQLEngine("mysql://user:password@localhost:3306/youth_tracker")
# DB = MySQLEngine("$DATABASE_URL")  # Reads from DATABASE_URL env var

import sqlite3
from pathlib import Path as PathlibPath
from db_setup import DBSetup
from abc import ABC, abstractmethod
from typing import Generator, Any
import os

try:
    import psycopg2
    from psycopg2 import sql
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False

try:
    import mysql.connector
    HAS_MYSQL = True
except ImportError:
    HAS_MYSQL = False


class DatabaseEngineInterface(ABC):
    """Abstract interface for database backends"""
    
    @abstractmethod
    def connect(self, db_path: str) -> Any:
        """Establish a connection to the database"""
        pass
    
    @abstractmethod
    def close(self, connection: Any) -> None:
        """Close a database connection"""
        pass
    
    @abstractmethod
    def execute(self, connection: Any, query: str, params: tuple = ()) -> Any:
        """Execute a SQL query and return results"""
        pass
    
    @abstractmethod
    def get_db(self) -> Generator:
        """Get a per-request database connection (generator)"""
        pass
    
    @abstractmethod
    def startup(self, db_path: str, app: Any) -> Any:
        """Initialize the database on application startup"""
        pass


class DatabaseEngine(DatabaseEngineInterface):
    def __init__(self, DB_PATH: str):
        self.DB_PATH = DB_PATH
    
    def startup(self, app):
        db_path = PathlibPath(self.DB_PATH)
        # 1. DB_PATH must include a filename
        if not db_path.suffix:
            raise RuntimeError(
                f"Invalid DB_PATH '{db_path}'. "
                "DB_PATH must point to a SQLite file, e.g. '/data/data.sqlite3'."
            )

        # 2. Parent directory must be creatable
        try:
            db_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise RuntimeError(
                f"Cannot create database directory '{db_path.parent}': {e}"
            ) from e

        # 3. Parent path must be a directory
        if not db_path.parent.is_dir():
            raise RuntimeError(
                f"DB_PATH parent '{db_path.parent}' exists but is not a directory."
            )

        # 4. Try opening SQLite to catch permission/locking issues early
        try:
            # conn = sqlite3.connect(DB_PATH, check_same_thread=False)
            conn = self.connect(str(db_path))
            conn.execute("PRAGMA journal_mode=WAL;")
        except Exception as e:
            raise RuntimeError(
                f"SQLite failed to open database at '{db_path}': {e}"
            ) from e

        conn.row_factory = sqlite3.Row

        # Helpful pragmas for reliability/performance on SQLite
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")

        db_setup=DBSetup(conn)
        db_setup.create_tables()
        db_setup.load_admins()
        app.state._db = conn
        return app

    def connect(self, db_path: str) -> sqlite3.Connection:
        """Establish a connection to SQLite database"""
        conn = sqlite3.connect(db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    
    def close(self, connection: sqlite3.Connection) -> None:
        """Close a SQLite database connection"""
        if connection:
            connection.close()
    
    def get_db(self) -> Generator:
        """
        Per-request SQLite connection.
        Ensures each request gets a fresh connection that is closed after the request.
        """
        db_path = PathlibPath(self.DB_PATH)

        # Fail loudly if DB_PATH is invalid
        if not db_path.suffix:
            raise RuntimeError(
                f"Invalid DB_PATH '{self.DB_PATH}'. DB_PATH must point to a SQLite file, e.g. '/data/data.sqlite3'."
            )

        # Ensure directory exists
        db_path.parent.mkdir(parents=True, exist_ok=True)

        conn = self.connect(str(db_path))

        # Pragmas (safe to do per connection)
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")

        try:
            yield conn
        finally:
            self.close(conn)
    
    def execute(self, connection: sqlite3.Connection, query: str, params: tuple = ()) -> Any:
        """
        Execute a SQL query on the given connection.
        Returns the cursor for further operations.
        """
        cursor = connection.cursor()
        cursor.execute(query, params)
        return cursor


class PostgreSQLEngine(DatabaseEngineInterface):
    """PostgreSQL database backend implementation"""
    
    def __init__(self, connection_string: str):
        """
        Initialize PostgreSQL engine.
        
        Args:
            connection_string: PostgreSQL connection string (e.g., 'postgresql://user:password@localhost:5432/dbname')
                              or environment variable name containing the connection string
        """
        if connection_string.startswith('$'):
            # If connection string starts with $, treat it as an env var
            self.connection_string = os.getenv(connection_string[1:], connection_string)
        else:
            self.connection_string = connection_string
        
        if not HAS_PSYCOPG2:
            raise ImportError("psycopg2 is required for PostgreSQL backend. Install it with: pip install psycopg2-binary")
    
    def connect(self, connection_string: str) -> Any:
        """Establish a connection to PostgreSQL database"""
        try:
            conn = psycopg2.connect(connection_string)
            conn.autocommit = False
            return conn
        except psycopg2.Error as e:
            raise RuntimeError(f"PostgreSQL connection failed: {e}") from e
    
    def close(self, connection: Any) -> None:
        """Close a PostgreSQL database connection"""
        if connection:
            try:
                connection.close()
            except psycopg2.Error:
                pass
    
    def get_db(self) -> Generator:
        """
        Per-request PostgreSQL connection.
        Ensures each request gets a fresh connection that is closed after the request.
        """
        conn = self.connect(self.connection_string)
        
        try:
            yield conn
        finally:
            self.close(conn)
    
    def execute(self, connection: Any, query: str, params: tuple = ()) -> Any:
        """
        Execute a SQL query on the given PostgreSQL connection.
        Returns the cursor for further operations.
        """
        cursor = connection.cursor()
        cursor.execute(query, params)
        return cursor
    
    def startup(self, connection_string: str, app: Any) -> Any:
        """
        Initialize the database on application startup.
        
        Args:
            connection_string: PostgreSQL connection string
            app: FastAPI application instance
        """
        try:
            conn = self.connect(connection_string)
        except Exception as e:
            raise RuntimeError(f"PostgreSQL failed to connect at startup: {e}") from e
        
        try:
            # Test the connection
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            
            # Initialize database schema
            db_setup = DBSetup(conn)
            db_setup.create_tables()
            db_setup.load_admins()
            
            # Store connection in app state for potential global use
            app.state._db = conn
            
            return app
        except Exception as e:
            self.close(conn)
            raise RuntimeError(f"PostgreSQL startup initialization failed: {e}") from e


class MySQLEngine(DatabaseEngineInterface):
    """MySQL database backend implementation"""
    
    def __init__(self, connection_string: str):
        """
        Initialize MySQL engine.
        
        Args:
            connection_string: MySQL connection string in format 'mysql://user:password@host:port/dbname'
                              or environment variable name containing the connection string
        """
        if connection_string.startswith('$'):
            # If connection string starts with $, treat it as an env var
            self.connection_string = os.getenv(connection_string[1:], connection_string)
        else:
            self.connection_string = connection_string
        
        if not HAS_MYSQL:
            raise ImportError("mysql-connector-python is required for MySQL backend. Install it with: pip install mysql-connector-python")
        
        # Parse connection string
        self.config = self._parse_connection_string(self.connection_string)
    
    def _parse_connection_string(self, conn_str: str) -> dict:
        """
        Parse MySQL connection string.
        Expected format: mysql://user:password@host:port/dbname
        """
        if not conn_str.startswith('mysql://'):
            raise ValueError("MySQL connection string must start with 'mysql://'")
        
        conn_str = conn_str[8:]  # Remove 'mysql://'
        
        # Extract database name
        if '/' in conn_str:
            conn_str, dbname = conn_str.rsplit('/', 1)
        else:
            dbname = 'youth_tracker'
        
        # Extract credentials and host
        if '@' in conn_str:
            creds, hostport = conn_str.rsplit('@', 1)
            if ':' in creds:
                user, password = creds.split(':', 1)
            else:
                user = creds
                password = ''
        else:
            user = 'root'
            password = ''
            hostport = conn_str
        
        # Extract host and port
        if ':' in hostport:
            host, port = hostport.split(':', 1)
            port = int(port)
        else:
            host = hostport
            port = 3306
        
        return {
            'host': host,
            'user': user,
            'password': password,
            'database': dbname,
            'port': port,
            'autocommit': False,
            'use_unicode': True,
            'charset': 'utf8mb4'
        }
    
    def connect(self, connection_string: str = None) -> Any:
        """Establish a connection to MySQL database"""
        try:
            config = self.config if connection_string is None else self._parse_connection_string(connection_string)
            conn = mysql.connector.connect(**config)
            return conn
        except mysql.connector.Error as e:
            raise RuntimeError(f"MySQL connection failed: {e}") from e
    
    def close(self, connection: Any) -> None:
        """Close a MySQL database connection"""
        if connection:
            try:
                connection.close()
            except mysql.connector.Error:
                pass
    
    def get_db(self) -> Generator:
        """
        Per-request MySQL connection.
        Ensures each request gets a fresh connection that is closed after the request.
        """
        conn = self.connect()
        
        try:
            yield conn
        finally:
            self.close(conn)
    
    def execute(self, connection: Any, query: str, params: tuple = ()) -> Any:
        """
        Execute a SQL query on the given MySQL connection.
        Returns the cursor for further operations.
        """
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query, params)
        return cursor
    
    def startup(self, connection_string: str, app: Any) -> Any:
        """
        Initialize the database on application startup.
        
        Args:
            connection_string: MySQL connection string
            app: FastAPI application instance
        """
        try:
            conn = self.connect(connection_string)
        except Exception as e:
            raise RuntimeError(f"MySQL failed to connect at startup: {e}") from e
        
        try:
            # Test the connection
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            
            # Initialize database schema
            db_setup = DBSetup(conn)
            db_setup.create_tables()
            db_setup.load_admins()
            
            # Store connection in app state for potential global use
            app.state._db = conn
            
            return app
        except Exception as e:
            self.close(conn)
            raise RuntimeError(f"MySQL startup initialization failed: {e}") from e