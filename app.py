from scheduler import save_generated_plan
from flask import Flask, render_template, request, redirect, url_for, g
import sqlite3
from datetime import date
from datetime import datetime
from pathlib import Path


app = Flask(__name__)


# --------------------------------------------------
# DATABASE CONFIGURATION
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "study_planner.db"


# --------------------------------------------------
# DATABASE CONNECTION
# --------------------------------------------------

def get_db():
    """
    Create or retrieve the database connection
    for the current Flask request.
    """

    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)

        # Allows us to access columns by name
        g.db.row_factory = sqlite3.Row

        # Enable foreign key enforcement
        g.db.execute("PRAGMA foreign_keys = ON")

    return g.db


# --------------------------------------------------
# CLOSE DATABASE CONNECTION
# --------------------------------------------------

@app.teardown_appcontext
def close_db(exception=None):
    """
    Close the database connection
    after the request finishes.
    """

    db = g.pop("db", None)

    if db is not None:
        db.close()


# --------------------------------------------------
# HOME
# --------------------------------------------------

@app.route("/")
def home():
    db = get_db()

    stats_cursor = db.execute(
        """
        SELECT
            COUNT(*) AS total_topics,
            SUM(
                CASE
                    WHEN COALESCE(tp.is_completed, 0) = 1
                    THEN 1
                    ELSE 0
                END
            ) AS completed_topics,
            COALESCE(
                SUM(tp.completed_hours),
                0
            ) AS completed_hours,
            COALESCE(
                SUM(t.estimated_hours),
                0
            ) AS estimated_hours
        FROM topics t
        JOIN subjects s
            ON t.subject_id = s.subject_id
        LEFT JOIN topic_progress tp
            ON t.topic_id = tp.topic_id
            AND tp.student_id = ?
        WHERE s.student_id = ?
        """,
        (1, 1)
    )

    stats = stats_cursor.fetchone()

    session_cursor = db.execute(
        """
        SELECT
            status,
            COUNT(*) AS count
        FROM study_sessions
        WHERE student_id = ?
        GROUP BY status
        """,
        (1,)
    )

    session_counts = {
        "Planned": 0,
        "Completed": 0,
        "Skipped": 0,
        "Cancelled": 0
    }

    for row in session_cursor.fetchall():
        session_counts[row["status"]] = row["count"]

    overall_progress = 0

    if stats["estimated_hours"] > 0:
        overall_progress = (
            stats["completed_hours"]
            / stats["estimated_hours"]
        ) * 100

    overall_progress = min(
        100,
        round(overall_progress, 1)
    )

    exam_cursor = db.execute(
        """
        SELECT
            exams.exam_id,
            exams.exam_name,
            exams.exam_date,
            exams.exam_type,
            subjects.name AS subject_name
        FROM exams
        JOIN subjects
            ON exams.subject_id = subjects.subject_id
        WHERE subjects.student_id = ?
        AND exams.exam_date >= date('now', 'localtime')
        ORDER BY exams.exam_date
        LIMIT 5
        """,
        (1,)
    )

    upcoming_exams = exam_cursor.fetchall()

    session_cursor = db.execute(
        """
        SELECT
            ss.session_id,
            ss.session_date,
            ss.start_time,
            ss.duration_minutes,
            t.name AS topic_name,
            s.name AS subject_name
        FROM study_sessions ss
        JOIN topics t
            ON ss.topic_id = t.topic_id
        JOIN subjects s
            ON t.subject_id = s.subject_id
        WHERE ss.student_id = ?
        AND ss.status = 'Planned'
        AND ss.session_date >= date('now', 'localtime')
        ORDER BY
            ss.session_date,
            ss.start_time
        LIMIT 5
        """,
        (1,)
    )

    upcoming_sessions = session_cursor.fetchall()

    return render_template(
        "index.html",
        stats=stats,
        session_counts=session_counts,
        overall_progress=overall_progress,
        upcoming_exams=upcoming_exams,
        upcoming_sessions=upcoming_sessions
    )

# --------------------------------------------------
# TEST DATABASE
# --------------------------------------------------

@app.route("/test-db")
def test_db():

    db = get_db()

    cursor = db.execute("""
        SELECT subject_id, name
        FROM subjects
        ORDER BY subject_id
    """)

    subjects = cursor.fetchall()

    return render_template(
        "test_db.html",
        subjects=subjects
    )


# --------------------------------------------------
# SUBJECTS - VIEW ALL
# --------------------------------------------------

@app.route("/subjects")
def subjects():

    db = get_db()

    cursor = db.execute("""
        SELECT subject_id, name, description
        FROM subjects
        WHERE student_id = ?
        ORDER BY subject_id
    """, (1,))

    subjects = cursor.fetchall()

    return render_template(
        "subjects.html",
        subjects=subjects
    )


# --------------------------------------------------
# SUBJECTS - ADD
# --------------------------------------------------

@app.route("/subjects/add", methods=["GET", "POST"])
def add_subject():

    if request.method == "POST":

        name = request.form["name"].strip()
        description = request.form["description"].strip()

        if not name:
            return "Subject name is required", 400

        db = get_db()

        try:
            db.execute("""
                INSERT INTO subjects
                (student_id, name, description)
                VALUES (?, ?, ?)
            """, (1, name, description))

            db.commit()

        except sqlite3.IntegrityError:
            return "A subject with this name already exists.", 400

        return redirect(url_for("subjects"))

    return render_template("add_subject.html")


# --------------------------------------------------
# SUBJECTS - EDIT
# --------------------------------------------------

@app.route("/subjects/edit/<int:subject_id>", methods=["GET", "POST"])
def edit_subject(subject_id):

    db = get_db()

    if request.method == "POST":

        name = request.form["name"].strip()
        description = request.form["description"].strip()

        if not name:
            return "Subject name is required", 400

        try:
            db.execute("""
                UPDATE subjects
                SET name = ?, description = ?
                WHERE subject_id = ?
                AND student_id = ?
            """, (name, description, subject_id, 1))

            db.commit()

        except sqlite3.IntegrityError:
            return "A subject with this name already exists.", 400

        return redirect(url_for("subjects"))

    cursor = db.execute("""
        SELECT subject_id, name, description
        FROM subjects
        WHERE subject_id = ?
        AND student_id = ?
    """, (subject_id, 1))

    subject = cursor.fetchone()

    if subject is None:
        return "Subject not found", 404

    return render_template(
        "edit_subject.html",
        subject=subject
    )


# --------------------------------------------------
# SUBJECTS - DELETE
# --------------------------------------------------

@app.route("/subjects/delete/<int:subject_id>", methods=["POST"])
def delete_subject(subject_id):

    db = get_db()

    db.execute("""
        DELETE FROM subjects
        WHERE subject_id = ?
        AND student_id = ?
    """, (subject_id, 1))

    db.commit()

    return redirect(url_for("subjects"))


# --------------------------------------------------
# TOPICS - VIEW ALL FOR A SUBJECT
# --------------------------------------------------

@app.route("/subjects/<int:subject_id>/topics")
def topics(subject_id):

    db = get_db()

    # Get subject information
    subject_cursor = db.execute("""
        SELECT subject_id, name
        FROM subjects
        WHERE subject_id = ?
        AND student_id = ?
    """, (subject_id, 1))

    subject = subject_cursor.fetchone()

    if subject is None:
        return "Subject not found", 404

    # Get topics belonging to this subject
    cursor = db.execute("""
        SELECT topic_id,
               name,
               description,
               difficulty,
               priority,
               estimated_hours
        FROM topics
        WHERE subject_id = ?
        ORDER BY topic_id
    """, (subject_id,))

    topics = cursor.fetchall()

    return render_template(
        "topics.html",
        subject=subject,
        topics=topics
    )


# --------------------------------------------------
# TOPICS - ADD
# --------------------------------------------------

@app.route(
    "/subjects/<int:subject_id>/topics/add",
    methods=["GET", "POST"]
)
def add_topic(subject_id):
    db = get_db()

    subject = db.execute(
        """
        SELECT subject_id, name
        FROM subjects
        WHERE subject_id = ? AND student_id = ?
        """,
        (subject_id, 1),
    ).fetchone()

    if subject is None:
        return "Subject not found", 404

    error = None
    form_data = {
        "name": "",
        "description": "",
        "difficulty": "3",
        "priority": "3",
        "estimated_hours": "",
    }

    if request.method == "POST":
        form_data = {
            "name": request.form.get("name", "").strip(),
            "description": request.form.get("description", "").strip(),
            "difficulty": request.form.get("difficulty", "").strip(),
            "priority": request.form.get("priority", "").strip(),
            "estimated_hours": request.form.get(
                "estimated_hours", ""
            ).strip(),
        }

        name = form_data["name"]
        description = form_data["description"]

        if not name:
            error = "Topic name is required."

        difficulty = None
        priority = None
        estimated_hours = None

        if error is None:
            try:
                difficulty = int(form_data["difficulty"])
                priority = int(form_data["priority"])
                estimated_hours = float(
                    form_data["estimated_hours"]
                )
            except ValueError:
                error = "Enter valid numeric values for all fields."

        if error is None and not 1 <= difficulty <= 5:
            error = "Difficulty must be between 1 and 5."

        if error is None and not 1 <= priority <= 5:
            error = "Priority must be between 1 and 5."

        if error is None and not (
            0 < estimated_hours <= 10000
        ):
            error = "Estimated hours must be greater than 0."

        if error is None:
            try:
                db.execute(
                    """
                    INSERT INTO topics (
                        subject_id,
                        name,
                        description,
                        difficulty,
                        priority,
                        estimated_hours
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        subject_id,
                        name,
                        description,
                        difficulty,
                        priority,
                        estimated_hours,
                    ),
                )
                db.commit()

            except sqlite3.IntegrityError:
                db.rollback()
                error = "A topic with this name already exists."

            if error is None:
                return redirect(
                    url_for("topics", subject_id=subject_id)
                )

    return render_template(
        "add_topic.html",
        subject=subject,
        error=error,
        form_data=form_data,
    )

# --------------------------------------------------
# TOPICS - EDIT
# --------------------------------------------------

@app.route("/topics/edit/<int:topic_id>",
           methods=["GET", "POST"])
def edit_topic(topic_id):

    db = get_db()

    # Get topic
    cursor = db.execute("""
        SELECT topic_id,
               subject_id,
               name,
               description,
               difficulty,
               priority,
               estimated_hours
        FROM topics
        WHERE topic_id = ?
    """, (topic_id,))

    topic = cursor.fetchone()

    if topic is None:
        return "Topic not found", 404

    subject_id = topic["subject_id"]

    if request.method == "POST":

        name = request.form["name"].strip()
        description = request.form["description"].strip()

        difficulty = int(request.form["difficulty"])
        priority = int(request.form["priority"])
        estimated_hours = float(request.form["estimated_hours"])

        if not name:
            return "Topic name is required", 400

        if difficulty < 1 or difficulty > 5:
            return "Difficulty must be between 1 and 5", 400

        if priority < 1 or priority > 5:
            return "Priority must be between 1 and 5", 400

        if estimated_hours <= 0:
            return "Estimated hours must be greater than 0", 400

        try:

            db.execute("""
                UPDATE topics
                SET name = ?,
                    description = ?,
                    difficulty = ?,
                    priority = ?,
                    estimated_hours = ?
                WHERE topic_id = ?
            """, (
                name,
                description,
                difficulty,
                priority,
                estimated_hours,
                topic_id
            ))

            db.commit()

        except sqlite3.IntegrityError:
            return "A topic with this name already exists.", 400

        return redirect(
            url_for("topics", subject_id=subject_id)
        )

    return render_template(
        "edit_topic.html",
        topic=topic
    )


# --------------------------------------------------
# TOPICS - DELETE
# --------------------------------------------------

@app.route("/topics/delete/<int:topic_id>",
           methods=["POST"])
def delete_topic(topic_id):

    db = get_db()

    # Find subject before deleting
    cursor = db.execute("""
        SELECT subject_id
        FROM topics
        WHERE topic_id = ?
    """, (topic_id,))

    topic = cursor.fetchone()

    if topic is None:
        return "Topic not found", 404

    subject_id = topic["subject_id"]

    db.execute("""
        DELETE FROM topics
        WHERE topic_id = ?
    """, (topic_id,))

    db.commit()

    return redirect(
        url_for("topics", subject_id=subject_id)
    )



# --------------------------------------------------
# EXAMS - VIEW ALL
# --------------------------------------------------

@app.route("/exams")
def exams():

    db = get_db()

    cursor = db.execute("""
        SELECT
            exams.exam_id,
            exams.exam_name,
            exams.exam_date,
            exams.exam_type,
            subjects.subject_id,
            subjects.name AS subject_name
        FROM exams
        JOIN subjects
            ON exams.subject_id = subjects.subject_id
        WHERE subjects.student_id = ?
        ORDER BY exams.exam_date
    """, (1,))

    exams = cursor.fetchall()

    return render_template(
        "exams.html",
        exams=exams
    )


# --------------------------------------------------
# EXAMS - ADD
# --------------------------------------------------

@app.route("/exams/add", methods=["GET", "POST"])
def add_exam():

    db = get_db()

    # Get all subjects for the dropdown
    subject_cursor = db.execute("""
        SELECT subject_id, name
        FROM subjects
        WHERE student_id = ?
        ORDER BY name
    """, (1,))

    subjects = subject_cursor.fetchall()

    if request.method == "POST":

        exam_name = request.form["exam_name"].strip()
        subject_id = request.form["subject_id"]
        exam_date = request.form["exam_date"]
        exam_type = request.form["exam_type"]

        if not exam_name:
            return "Exam name is required", 400

        if not subject_id:
            return "Subject is required", 400

        if not exam_date:
            return "Exam date is required", 400

        try:

            db.execute("""
                INSERT INTO exams
                (
                    subject_id,
                    exam_name,
                    exam_date,
                    exam_type
                )
                VALUES (?, ?, ?, ?)
            """, (
                subject_id,
                exam_name,
                exam_date,
                exam_type
            ))

            db.commit()

        except sqlite3.IntegrityError:
            return "Unable to add exam.", 400

        return redirect(url_for("exams"))

    return render_template(
        "add_exam.html",
        subjects=subjects
    )


# --------------------------------------------------
# EXAMS - EDIT
# --------------------------------------------------

@app.route("/exams/edit/<int:exam_id>",
           methods=["GET", "POST"])
def edit_exam(exam_id):

    db = get_db()

    # Get all subjects
    subject_cursor = db.execute("""
        SELECT subject_id, name
        FROM subjects
        WHERE student_id = ?
        ORDER BY name
    """, (1,))

    subjects = subject_cursor.fetchall()

    # Get the exam
    cursor = db.execute("""
        SELECT
            exam_id,
            subject_id,
            exam_name,
            exam_date,
            exam_type
        FROM exams
        WHERE exam_id = ?
    """, (exam_id,))

    exam = cursor.fetchone()

    if exam is None:
        return "Exam not found", 404

    if request.method == "POST":

        exam_name = request.form["exam_name"].strip()
        subject_id = request.form["subject_id"]
        exam_date = request.form["exam_date"]
        exam_type = request.form["exam_type"]

        if not exam_name:
            return "Exam name is required", 400

        if not subject_id:
            return "Subject is required", 400

        if not exam_date:
            return "Exam date is required", 400

        db.execute("""
            UPDATE exams
            SET subject_id = ?,
                exam_name = ?,
                exam_date = ?,
                exam_type = ?
            WHERE exam_id = ?
        """, (
            subject_id,
            exam_name,
            exam_date,
            exam_type,
            exam_id
        ))

        db.commit()

        return redirect(url_for("exams"))

    return render_template(
        "edit_exam.html",
        exam=exam,
        subjects=subjects
    )


# --------------------------------------------------
# EXAMS - DELETE
# --------------------------------------------------

@app.route("/exams/delete/<int:exam_id>",
           methods=["POST"])
def delete_exam(exam_id):

    db = get_db()

    db.execute("""
        DELETE FROM exams
        WHERE exam_id = ?
    """, (exam_id,))

    db.commit()

    return redirect(url_for("exams"))


# --------------------------------------------------
# STUDY PREFERENCES - VIEW
# --------------------------------------------------

@app.route("/preferences")
def preferences():

    db = get_db()

    cursor = db.execute("""
        SELECT
            preference_id,
            preferred_time,
            daily_study_hours,
            preferred_session_minutes,
            break_minutes
        FROM study_preferences
        WHERE student_id = ?
    """, (1,))

    preferences = cursor.fetchone()

    return render_template(
        "preferences.html",
        preferences=preferences
    )


# --------------------------------------------------
# STUDY PREFERENCES - ADD / UPDATE
# --------------------------------------------------

@app.route("/preferences/edit", methods=["GET", "POST"])
def edit_preferences():

    db = get_db()

    if request.method == "POST":

        preferred_time = request.form["preferred_time"]

        daily_study_hours = float(
            request.form["daily_study_hours"]
        )

        preferred_session_minutes = int(
            request.form["preferred_session_minutes"]
        )

        break_minutes = int(
            request.form["break_minutes"]
        )

        # ------------------------------
        # Validation
        # ------------------------------

        valid_times = [
            "Morning",
            "Afternoon",
            "Evening",
            "Night"
        ]

        if preferred_time not in valid_times:
            return "Invalid preferred study time", 400

        if daily_study_hours <= 0:
            return "Daily study hours must be greater than 0", 400

        if preferred_session_minutes <= 0:
            return "Session duration must be greater than 0", 400

        if break_minutes < 0:
            return "Break duration cannot be negative", 400

        # ------------------------------
        # Check whether preferences exist
        # ------------------------------

        cursor = db.execute("""
            SELECT preference_id
            FROM study_preferences
            WHERE student_id = ?
        """, (1,))

        existing = cursor.fetchone()

        # ------------------------------
        # UPDATE
        # ------------------------------

        if existing:

            db.execute("""
                UPDATE study_preferences
                SET preferred_time = ?,
                    daily_study_hours = ?,
                    preferred_session_minutes = ?,
                    break_minutes = ?
                WHERE student_id = ?
            """, (
                preferred_time,
                daily_study_hours,
                preferred_session_minutes,
                break_minutes,
                1
            ))

        # ------------------------------
        # INSERT
        # ------------------------------

        else:

            db.execute("""
                INSERT INTO study_preferences
                (
                    student_id,
                    preferred_time,
                    daily_study_hours,
                    preferred_session_minutes,
                    break_minutes
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                1,
                preferred_time,
                daily_study_hours,
                preferred_session_minutes,
                break_minutes
            ))

        db.commit()

        return redirect(url_for("preferences"))

    # GET request

    cursor = db.execute("""
        SELECT
            preference_id,
            preferred_time,
            daily_study_hours,
            preferred_session_minutes,
            break_minutes
        FROM study_preferences
        WHERE student_id = ?
    """, (1,))

    preferences = cursor.fetchone()

    return render_template(
        "edit_preferences.html",
        preferences=preferences
    )

# --------------------------------------------------
# AVAILABILITY - VIEW ALL
# --------------------------------------------------

@app.route("/availability")
def availability():

    db = get_db()

    cursor = db.execute("""
        SELECT
            availability_id,
            available_date,
            available_hours,
            start_time,
            end_time
        FROM availability
        WHERE student_id = ?
        ORDER BY available_date
    """, (1,))

    availability = cursor.fetchall()

    return render_template(
        "availability.html",
        availability=availability
    )


# --------------------------------------------------
# AVAILABILITY - ADD
# --------------------------------------------------

@app.route("/availability/add", methods=["GET", "POST"])
def add_availability():
    db = get_db()
    error = None
    form_data = {
        "available_date": "",
        "available_hours": "",
        "start_time": "",
        "end_time": "",
    }

    if request.method == "POST":
        form_data = {
            "available_date": request.form.get(
                "available_date", ""
            ).strip(),
            "available_hours": request.form.get(
                "available_hours", ""
            ).strip(),
            "start_time": request.form.get(
                "start_time", ""
            ).strip(),
            "end_time": request.form.get(
                "end_time", ""
            ).strip(),
        }

        available_date = form_data["available_date"]
        hours_raw = form_data["available_hours"]
        start_time = form_data["start_time"]
        end_time = form_data["end_time"]

        if not available_date or not hours_raw:
            error = "Date and available hours are required."

        else:
            try:
                selected_date = date.fromisoformat(available_date)
            except ValueError:
                error = "Please enter a valid date."

        if error is None and selected_date < date.today():
            error = "Past dates are not allowed."

        available_hours = None

        if error is None:
            try:
                available_hours = float(hours_raw)
            except ValueError:
                error = "Available hours must be a valid number."

        if error is None and not 0 < available_hours <= 24:
            error = "Available hours must be greater than 0 and at most 24."

        if error is None and bool(start_time) != bool(end_time):
            error = "Enter both times or leave both empty."

        if (
            error is None
            and start_time
            and end_time
            and start_time >= end_time
        ):
            error = "End time must be after start time."

        if error is None:
            try:
                db.execute(
                    """
                    INSERT INTO availability (
                        student_id,
                        available_date,
                        available_hours,
                        start_time,
                        end_time
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        1,
                        available_date,
                        available_hours,
                        start_time or None,
                        end_time or None,
                    ),
                )
                db.commit()

            except sqlite3.IntegrityError:
                db.rollback()
                error = "Availability already exists for this date."

            if error is None:
                return redirect(url_for("availability"))

    return render_template(
        "add_availability.html",
        error=error,
        form_data=form_data,
    )


# --------------------------------------------------
# AVAILABILITY - EDIT
# --------------------------------------------------

@app.route("/availability/edit/<int:availability_id>",
           methods=["GET", "POST"])
def edit_availability(availability_id):

    db = get_db()

    cursor = db.execute("""
        SELECT
            availability_id,
            available_date,
            available_hours,
            start_time,
            end_time
        FROM availability
        WHERE availability_id = ?
        AND student_id = ?
    """, (availability_id, 1))

    availability_record = cursor.fetchone()

    if availability_record is None:
        return "Availability record not found", 404

    if request.method == "POST":

        available_date = request.form["available_date"]

        available_hours = float(
            request.form["available_hours"]
        )

        start_time = request.form["start_time"]
        end_time = request.form["end_time"]

        if not available_date:
            return "Date is required", 400

        if available_hours < 0:
            return "Available hours cannot be negative", 400

        if start_time and end_time and start_time >= end_time:
            return "End time must be after start time", 400

        try:

            db.execute("""
                UPDATE availability
                SET available_date = ?,
                    available_hours = ?,
                    start_time = ?,
                    end_time = ?
                WHERE availability_id = ?
                AND student_id = ?
            """, (
                available_date,
                available_hours,
                start_time,
                end_time,
                availability_id,
                1
            ))

            db.commit()

        except sqlite3.IntegrityError:
            return "Availability already exists for this date.", 400

        return redirect(url_for("availability"))

    return render_template(
        "edit_availability.html",
        availability=availability_record
    )


# --------------------------------------------------
# AVAILABILITY - DELETE
# --------------------------------------------------

@app.route("/availability/delete/<int:availability_id>",
           methods=["POST"])
def delete_availability(availability_id):

    db = get_db()

    db.execute("""
        DELETE FROM availability
        WHERE availability_id = ?
        AND student_id = ?
    """, (availability_id, 1))

    db.commit()

    return redirect(url_for("availability"))



# --------------------------------------------------
# TOPIC PROGRESS - VIEW ALL
# --------------------------------------------------

@app.route("/progress")
def progress():

    db = get_db()

    cursor = db.execute("""
        SELECT
            topic_progress.progress_id,
            topic_progress.topic_id,
            topic_progress.progress_percentage,
            topic_progress.completed_hours,
            topic_progress.is_completed,
            topic_progress.last_studied_at,

            topics.name AS topic_name,
            topics.estimated_hours,

            subjects.subject_id,
            subjects.name AS subject_name

        FROM topic_progress

        JOIN topics
            ON topic_progress.topic_id = topics.topic_id

        JOIN subjects
            ON topics.subject_id = subjects.subject_id

        WHERE topic_progress.student_id = ?

        ORDER BY
            subjects.subject_id,
            topics.topic_id
    """, (1,))

    progress_records = cursor.fetchall()

    return render_template(
        "progress.html",
        progress_records=progress_records
    )


# --------------------------------------------------
# TOPIC PROGRESS - UPDATE
# --------------------------------------------------

@app.route("/progress/edit/<int:topic_id>",
           methods=["GET", "POST"])
def edit_progress(topic_id):

    db = get_db()

    # ----------------------------------------------
    # Get topic information
    # ----------------------------------------------

    topic_cursor = db.execute("""
        SELECT
            topics.topic_id,
            topics.name,
            topics.estimated_hours,
            subjects.name AS subject_name
        FROM topics

        JOIN subjects
            ON topics.subject_id = subjects.subject_id

        WHERE topics.topic_id = ?
        AND subjects.student_id = ?
    """, (topic_id, 1))

    topic = topic_cursor.fetchone()

    if topic is None:
        return "Topic not found", 404


    # ----------------------------------------------
    # Get existing progress
    # ----------------------------------------------

    progress_cursor = db.execute("""
        SELECT
            progress_id,
            progress_percentage,
            completed_hours,
            is_completed,
            last_studied_at
        FROM topic_progress
        WHERE topic_id = ?
        AND student_id = ?
    """, (topic_id, 1))

    progress_record = progress_cursor.fetchone()


    # ----------------------------------------------
    # UPDATE
    # ----------------------------------------------

    if request.method == "POST":

        progress_percentage = int(
            request.form["progress_percentage"]
        )

        completed_hours = float(
            request.form["completed_hours"]
        )

        is_completed = 1 if "is_completed" in request.form else 0

        last_studied_at = request.form["last_studied_at"]


        # ------------------------------------------
        # Validation
        # ------------------------------------------

        if progress_percentage < 0 or progress_percentage > 100:
            return "Progress must be between 0 and 100", 400

        if completed_hours < 0:
            return "Completed hours cannot be negative", 400

        if completed_hours > topic["estimated_hours"]:
            return (
                "Completed hours cannot exceed estimated hours",
                400
            )


        # ------------------------------------------
        # Automatically mark 100% as completed
        # ------------------------------------------

        if progress_percentage == 100:
            is_completed = 1

        if is_completed == 1:
            progress_percentage = 100


        # ------------------------------------------
        # UPDATE existing record
        # ------------------------------------------

        if progress_record:

            db.execute("""
                UPDATE topic_progress
                SET progress_percentage = ?,
                    completed_hours = ?,
                    is_completed = ?,
                    last_studied_at = ?
                WHERE progress_id = ?
                AND student_id = ?
            """, (
                progress_percentage,
                completed_hours,
                is_completed,
                last_studied_at if last_studied_at else None,
                progress_record["progress_id"],
                1
            ))


        # ------------------------------------------
        # INSERT if record doesn't exist
        # ------------------------------------------

        else:

            db.execute("""
                INSERT INTO topic_progress
                (
                    student_id,
                    topic_id,
                    progress_percentage,
                    completed_hours,
                    is_completed,
                    last_studied_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                1,
                topic_id,
                progress_percentage,
                completed_hours,
                is_completed,
                last_studied_at if last_studied_at else None
            ))


        db.commit()

        return redirect(url_for("progress"))


    # ----------------------------------------------
    # GET request
    # ----------------------------------------------

    return render_template(
        "edit_progress.html",
        topic=topic,
        progress=progress_record
    )


# --------------------------------------------------
# STUDY SESSIONS - VIEW ALL
# --------------------------------------------------

@app.route("/sessions")
def sessions():

    db = get_db()

    cursor = db.execute("""
        SELECT
            study_sessions.session_id,
            study_sessions.session_date,
            study_sessions.start_time,
            study_sessions.duration_minutes,
            study_sessions.status,
            study_sessions.notes,

            topics.topic_id,
            topics.name AS topic_name,

            subjects.subject_id,
            subjects.name AS subject_name

        FROM study_sessions

        JOIN topics
            ON study_sessions.topic_id = topics.topic_id

        JOIN subjects
            ON topics.subject_id = subjects.subject_id

        WHERE study_sessions.student_id = ?

        ORDER BY
            study_sessions.session_date,
            study_sessions.start_time
    """, (1,))

    sessions = cursor.fetchall()

    return render_template(
        "sessions.html",
        sessions=sessions
    )


# --------------------------------------------------
# STUDY SESSIONS - ADD
# --------------------------------------------------

@app.route("/sessions/add", methods=["GET", "POST"])
def add_session():

    db = get_db()

    # Get all topics for dropdown
    cursor = db.execute("""
        SELECT
            topics.topic_id,
            topics.name AS topic_name,
            subjects.name AS subject_name

        FROM topics

        JOIN subjects
            ON topics.subject_id = subjects.subject_id

        WHERE subjects.student_id = ?

        ORDER BY
            subjects.name,
            topics.name
    """, (1,))

    topics = cursor.fetchall()

    if request.method == "POST":

        topic_id = request.form["topic_id"]
        session_date = request.form["session_date"]
        start_time = request.form["start_time"]

        duration_minutes = int(
            request.form["duration_minutes"]
        )

        status = request.form["status"]
        notes = request.form["notes"].strip()

        # ------------------------------
        # Validation
        # ------------------------------

        if not topic_id:
            return "Topic is required", 400

        if not session_date:
            return "Session date is required", 400

        if duration_minutes <= 0:
            return "Duration must be greater than 0", 400

        valid_statuses = [
            "Planned",
            "Completed",
            "Skipped",
            "Cancelled"
        ]

        if status not in valid_statuses:
            return "Invalid session status", 400

        # ------------------------------
        # Insert
        # ------------------------------

        db.execute("""
            INSERT INTO study_sessions
            (
                student_id,
                topic_id,
                session_date,
                start_time,
                duration_minutes,
                status,
                notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            1,
            topic_id,
            session_date,
            start_time,
            duration_minutes,
            status,
            notes
        ))

        db.commit()

        return redirect(url_for("sessions"))

    return render_template(
        "add_session.html",
        topics=topics
    )


# --------------------------------------------------
# STUDY SESSIONS - EDIT
# --------------------------------------------------

@app.route("/sessions/edit/<int:session_id>",
           methods=["GET", "POST"])
def edit_session(session_id):

    db = get_db()

    # Get all topics
    topic_cursor = db.execute("""
        SELECT
            topics.topic_id,
            topics.name AS topic_name,
            subjects.name AS subject_name

        FROM topics

        JOIN subjects
            ON topics.subject_id = subjects.subject_id

        WHERE subjects.student_id = ?

        ORDER BY
            subjects.name,
            topics.name
    """, (1,))

    topics = topic_cursor.fetchall()

    # Get session
    cursor = db.execute("""
        SELECT
            session_id,
            topic_id,
            session_date,
            start_time,
            duration_minutes,
            status,
            notes

        FROM study_sessions

        WHERE session_id = ?
        AND student_id = ?
    """, (session_id, 1))

    session = cursor.fetchone()

    if session is None:
        return "Study session not found", 404

    if request.method == "POST":

        topic_id = request.form["topic_id"]
        session_date = request.form["session_date"]
        start_time = request.form["start_time"]

        duration_minutes = int(
            request.form["duration_minutes"]
        )

        status = request.form["status"]
        notes = request.form["notes"].strip()

        if not topic_id:
            return "Topic is required", 400

        if not session_date:
            return "Session date is required", 400

        if duration_minutes <= 0:
            return "Duration must be greater than 0", 400

        valid_statuses = [
            "Planned",
            "Completed",
            "Skipped",
            "Cancelled"
        ]

        if status not in valid_statuses:
            return "Invalid session status", 400

        db.execute("""
            UPDATE study_sessions

            SET topic_id = ?,
                session_date = ?,
                start_time = ?,
                duration_minutes = ?,
                status = ?,
                notes = ?

            WHERE session_id = ?
            AND student_id = ?
        """, (
            topic_id,
            session_date,
            start_time,
            duration_minutes,
            status,
            notes,
            session_id,
            1
        ))

        db.commit()

        return redirect(url_for("sessions"))

    return render_template(
        "edit_session.html",
        session=session,
        topics=topics
    )


# --------------------------------------------------
# STUDY SESSIONS - DELETE
# --------------------------------------------------

@app.route("/sessions/delete/<int:session_id>",
           methods=["POST"])
def delete_session(session_id):

    db = get_db()

    db.execute("""
        DELETE FROM study_sessions
        WHERE session_id = ?
        AND student_id = ?
    """, (session_id, 1))

    db.commit()

    return redirect(url_for("sessions"))

# --------------------------------------------------
# STUDY PLAN - ROUTE
# --------------------------------------------------

@app.route("/study-plan")
def study_plan():
    db = get_db()

    cursor = db.execute(
        """
        SELECT
            ss.session_id,
            ss.session_date,
            ss.start_time,
            ss.duration_minutes,
            ss.status,
            ss.notes,
            t.name AS topic_name,
            s.name AS subject_name
        FROM study_sessions ss
        JOIN topics t
            ON ss.topic_id = t.topic_id
        JOIN subjects s
            ON t.subject_id = s.subject_id
        WHERE ss.student_id = ?
        AND ss.status = 'Planned'
        AND date(ss.session_date) >= date('now', 'localtime')
        ORDER BY ss.session_date, ss.start_time
        """,
        (1,)
    )

    sessions = cursor.fetchall()

    summary_cursor = db.execute(
        """
        SELECT
            session_date,
            COUNT(*) AS session_count,
            SUM(duration_minutes) AS total_minutes
        FROM study_sessions
        WHERE student_id = ?
        AND status = 'Planned'
        AND date(session_date) >= date('now', 'localtime')
        GROUP BY session_date
        ORDER BY session_date
        """,
        (1,)
    )

    daily_summary = {}

    for row in summary_cursor.fetchall():
        daily_summary[row["session_date"]] = {
            "session_count": row["session_count"],
            "total_minutes": row["total_minutes"]
        }

    return render_template(
        "study_plan.html",
        sessions=sessions,
        daily_summary=daily_summary
    )



@app.route(
    "/update-session-status/<int:session_id>",
    methods=["POST"]
)
def update_session_status(session_id):
    status = request.form.get("status")

    allowed_statuses = {
        "Completed",
        "Skipped"
    }

    if status not in allowed_statuses:
        return "Invalid session status", 400

    db = get_db()

    session_cursor = db.execute(
        """
        SELECT
            session_id,
            topic_id,
            duration_minutes,
            status
        FROM study_sessions
        WHERE session_id = ?
        AND student_id = ?
        """,
        (session_id, 1)
    )

    session = session_cursor.fetchone()

    if session is None:
        return "Study session not found", 404

    if session["status"] != "Planned":
        return redirect(url_for("study_plan"))

    if status == "Completed":
        topic_cursor = db.execute(
            """
            SELECT
                topics.estimated_hours
            FROM topics
            JOIN subjects
                ON topics.subject_id = subjects.subject_id
            WHERE topics.topic_id = ?
            AND subjects.student_id = ?
            """,
            (session["topic_id"], 1)
        )

        topic = topic_cursor.fetchone()

        if topic is None:
            return "Topic not found", 404

        progress_cursor = db.execute(
            """
            SELECT
                progress_id,
                completed_hours
            FROM topic_progress
            WHERE topic_id = ?
            AND student_id = ?
            """,
            (session["topic_id"], 1)
        )

        progress = progress_cursor.fetchone()

        if progress:
            completed_hours = progress["completed_hours"]
        else:
            completed_hours = 0

        completed_hours += session["duration_minutes"] / 60

        estimated_hours = topic["estimated_hours"]

        if completed_hours > estimated_hours:
            completed_hours = estimated_hours

        progress_percentage = (
            completed_hours / estimated_hours
        ) * 100

        progress_percentage = min(
            100,
            round(progress_percentage, 2)
        )

        is_completed = (
            1 if progress_percentage >= 100 else 0
        )

        last_studied_at = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        if progress:
            db.execute(
                """
                UPDATE topic_progress
                SET progress_percentage = ?,
                    completed_hours = ?,
                    is_completed = ?,
                    last_studied_at = ?
                WHERE progress_id = ?
                AND student_id = ?
                """,
                (
                    progress_percentage,
                    completed_hours,
                    is_completed,
                    last_studied_at,
                    progress["progress_id"],
                    1
                )
            )
        else:
            db.execute(
                """
                INSERT INTO topic_progress
                (
                    student_id,
                    topic_id,
                    progress_percentage,
                    completed_hours,
                    is_completed,
                    last_studied_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    1,
                    session["topic_id"],
                    progress_percentage,
                    completed_hours,
                    is_completed,
                    last_studied_at
                )
            )

    db.execute(
        """
        UPDATE study_sessions
        SET status = ?
        WHERE session_id = ?
        AND student_id = ?
        """,
        (
            status,
            session_id,
            1
        )
    )

    db.commit()

    return redirect(url_for("study_plan"))
# --------------------------------------------------
#  GENERATE PLAN - ROUTE
# --------------------------------------------------

@app.route("/generate-plan", methods=["POST"])
def generate_plan():
    result = save_generated_plan(1)

    if result["success"]:
        return redirect(url_for("study_plan"))

    return (
        f"Unable to generate study plan: "
        f"{result['message']}",
        500
    )

# --------------------------------------------------
# RUN APPLICATION
# --------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True)