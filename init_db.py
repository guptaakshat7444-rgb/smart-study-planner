import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent

DATABASE = BASE_DIR / "study_planner.db"
SQL_FILE = BASE_DIR / "database.sql"


def initialize_database():
    print("Initializing database...")

    connection = sqlite3.connect(DATABASE)

    try:
        with open(SQL_FILE, "r", encoding="utf-8") as file:
            sql_script = file.read()

        connection.executescript(sql_script)
        connection.commit()

        print("Database initialized successfully.")
        print(f"Database location: {DATABASE}")

    except Exception as error:
        connection.rollback()
        print("Database initialization failed.")
        print("Error:", error)

    finally:
        connection.close()


if __name__ == "__main__":
    initialize_database()