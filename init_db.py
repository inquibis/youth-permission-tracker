import os
from dotenv import load_dotenv
import sqlite3

load_dotenv()
if os.getenv("ENV") == "test":
    conn = sqlite3.connect("./activitydb.db")
    conn.execute("CREATE TABLE IF NOT EXISTS dummy (id INTEGER PRIMARY KEY)")
    conn.close()