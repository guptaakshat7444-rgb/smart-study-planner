import sqlite3
from datetime import date

DB_NAME = "study_planner.db"


def cleanup_old_data():
    today = date.today().isoformat()
    conn = sqlite3.connect(DB_NAME)

    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("BEGIN")

        # Remove past availability records.
        availability_result = conn.execute(
            """
            DELETE FROM availability
            WHERE date(available_date) < date(?)
            """,
            (today,)
        )

        # Remove past planned sessions only.
        # Completed and skipped sessions are preserved.
        sessions_result = conn.execute(
            """
            DELETE FROM study_sessions
            WHERE date(session_date) < date(?)
              AND status = 'Planned'
            """,
            (today,)
        )

        conn.commit()

        print("Cleanup completed successfully.")
        print("Today's date:", today)
        print(
            "Old availability records removed:",
            availability_result.rowcount
        )
        print(
            "Past planned sessions removed:",
            sessions_result.rowcount
        )

    except sqlite3.Error as error:
        conn.rollback()
        print("Cleanup failed. Changes rolled back.")
        print("Error:", error)

    finally:
        conn.close()


if __name__ == "__main__":
    cleanup_old_data()