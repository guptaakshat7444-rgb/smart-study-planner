import math
import sqlite3
from datetime import date, datetime

DATABASE = "study_planner.db"


def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def load_topics(student_id):
    conn = get_db_connection()

    rows = conn.execute(
        """
        SELECT
            t.topic_id,
            t.subject_id,
            t.name AS topic_name,
            t.description,
            t.difficulty,
            t.priority,
            t.estimated_hours,
            s.name AS subject_name
        FROM topics t
        JOIN subjects s
            ON t.subject_id = s.subject_id
        WHERE s.student_id = ?
        ORDER BY t.topic_id
        """,
        (student_id,)
    ).fetchall()

    conn.close()

    return [dict(row) for row in rows]


def load_progress(student_id):
    conn = get_db_connection()

    rows = conn.execute(
        """
        SELECT
            progress_id,
            topic_id,
            progress_percentage,
            completed_hours,
            is_completed,
            last_studied_at
        FROM topic_progress
        WHERE student_id = ?
        """,
        (student_id,)
    ).fetchall()

    conn.close()

    progress = {}

    for row in rows:
        progress[row["topic_id"]] = dict(row)

    return progress


def load_exams(student_id):
    conn = get_db_connection()

    rows = conn.execute(
        """
        SELECT
            e.exam_id,
            e.subject_id,
            e.exam_name,
            e.exam_date,
            e.exam_type
        FROM exams e
        JOIN subjects s
            ON e.subject_id = s.subject_id
        WHERE s.student_id = ?
        ORDER BY e.exam_date
        """,
        (student_id,)
    ).fetchall()

    conn.close()

    return [dict(row) for row in rows]


def load_preferences(student_id):
    conn = get_db_connection()

    row = conn.execute(
        """
        SELECT
            preference_id,
            student_id,
            preferred_time,
            daily_study_hours,
            preferred_session_minutes,
            break_minutes
        FROM study_preferences
        WHERE student_id = ?
        LIMIT 1
        """,
        (student_id,)
    ).fetchone()

    conn.close()

    if row is None:
        return None

    return dict(row)


def load_availability(student_id):
    conn = get_db_connection()

    rows = conn.execute(
        """
        SELECT
            availability_id,
            student_id,
            available_date,
            available_hours,
            start_time,
            end_time
        FROM availability
        WHERE student_id = ?
        ORDER BY available_date, start_time
        """,
        (student_id,)
    ).fetchall()

    conn.close()

    return [dict(row) for row in rows]


def load_existing_sessions(student_id):
    """Load existing sessions that should reserve time slots."""
    conn = get_db_connection()

    rows = conn.execute(
        """
        SELECT
            ss.session_id,
            ss.student_id,
            ss.topic_id,
            ss.session_date,
            ss.start_time,
            ss.duration_minutes,
            ss.status,
            ss.notes
        FROM study_sessions ss
        WHERE ss.student_id = ?
        AND ss.status != 'Planned'
        ORDER BY ss.session_date, ss.start_time
        """,
        (student_id,)
    ).fetchall()

    conn.close()

    return [dict(row) for row in rows]

def time_to_minutes(time_string):
    if not time_string:
        return 0

    time_string = str(time_string)

    try:
        hours, minutes = time_string.split(":")[:2]
        return int(hours) * 60 + int(minutes)
    except ValueError:
        return 0


def minutes_to_time(total_minutes):
    total_minutes = int(total_minutes)

    hours = total_minutes // 60
    minutes = total_minutes % 60

    hours %= 24

    return f"{hours:02d}:{minutes:02d}"


def get_preferred_time_window(preferred_time):
    if not preferred_time:
        return 0, 24 * 60

    preferred_time = preferred_time.strip().lower()

    windows = {
        "morning": (6 * 60, 12 * 60),
        "afternoon": (12 * 60, 17 * 60),
        "evening": (17 * 60, 21 * 60),
        "night": (21 * 60, 24 * 60)
    }

    return windows.get(preferred_time, (0, 24 * 60))


def get_window_intersection(
    availability_start,
    availability_end,
    preferred_start,
    preferred_end
):
    start = max(
        availability_start,
        preferred_start
    )

    end = min(
        availability_end,
        preferred_end
    )

    if start >= end:
        return None

    return start, end


def get_session_interval(session):
    start = time_to_minutes(session["start_time"])

    duration = int(session["duration_minutes"])

    end = start + duration

    return start, end


def merge_intervals(intervals):
    if not intervals:
        return []

    intervals = sorted(intervals, key=lambda item: item[0])

    merged = [intervals[0]]

    for start, end in intervals[1:]:
        previous_start, previous_end = merged[-1]

        if start <= previous_end:
            merged[-1] = (
                previous_start,
                max(previous_end, end)
            )
        else:
            merged.append((start, end))

    return merged


def get_occupied_intervals(sessions, available_date):
    occupied = []

    for session in sessions:
        if str(session["session_date"]) != str(available_date):
            continue

        interval = get_session_interval(session)

        occupied.append(interval)

    return merge_intervals(occupied)


def get_free_intervals(
    window_start,
    window_end,
    occupied_intervals
):
    free_intervals = []

    current = window_start

    for occupied_start, occupied_end in occupied_intervals:
        if occupied_end <= window_start:
            continue

        if occupied_start >= window_end:
            break

        occupied_start = max(
            occupied_start,
            window_start
        )

        occupied_end = min(
            occupied_end,
            window_end
        )

        if current < occupied_start:
            free_intervals.append(
                (current, occupied_start)
            )

        current = max(current, occupied_end)

    if current < window_end:
        free_intervals.append(
            (current, window_end)
        )

    return free_intervals


def calculate_free_study_minutes(
    availability_record,
    sessions,
    preferred_time
):
    available_date = availability_record["available_date"]

    availability_start = time_to_minutes(
        availability_record["start_time"]
    )

    availability_end = time_to_minutes(
        availability_record["end_time"]
    )

    preferred_start, preferred_end = (
        get_preferred_time_window(preferred_time)
    )

    preferred_overlap = get_window_intersection(
        availability_start,
        availability_end,
        preferred_start,
        preferred_end
    )

    occupied_intervals = get_occupied_intervals(
        sessions,
        available_date
    )

    if preferred_overlap:
        window_start, window_end = preferred_overlap

        free_intervals = get_free_intervals(
            window_start,
            window_end,
            occupied_intervals
        )

        free_minutes = sum(
            end - start
            for start, end in free_intervals
        )

        return {
            "date": available_date,
            "free_intervals": free_intervals,
            "free_minutes": free_minutes,
            "preferred_overlap": True
        }

    return {
        "date": available_date,
        "free_intervals": [],
        "free_minutes": 0,
        "preferred_overlap": False
    }


def calculate_fallback_free_time(
    availability_record,
    sessions
):
    available_date = availability_record["available_date"]

    availability_start = time_to_minutes(
        availability_record["start_time"]
    )

    availability_end = time_to_minutes(
        availability_record["end_time"]
    )

    occupied_intervals = get_occupied_intervals(
        sessions,
        available_date
    )

    free_intervals = get_free_intervals(
        availability_start,
        availability_end,
        occupied_intervals
    )

    free_minutes = sum(
        end - start
        for start, end in free_intervals
    )

    return {
        "date": available_date,
        "free_intervals": free_intervals,
        "free_minutes": free_minutes
    }


def calculate_remaining_hours(topic, progress_data):
    topic_id = topic["topic_id"]

    estimated_hours = float(
        topic["estimated_hours"] or 0
    )

    progress = progress_data.get(topic_id)

    if not progress:
        progress_percentage = 0
        is_completed = False
    else:
        progress_percentage = float(
            progress["progress_percentage"] or 0
        )
        is_completed = bool(
            progress["is_completed"]
        )

    progress_percentage = max(
        0,
        min(100, progress_percentage)
    )

    if is_completed or progress_percentage >= 100:
        return 0

    remaining_hours = (
        estimated_hours
        * (1 - progress_percentage / 100)
    )

    return max(
        0,
        min(estimated_hours, remaining_hours)
    )


def calculate_exam_urgency(exam_date):
    if not exam_date:
        return 0

    try:
        exam = date.fromisoformat(
            str(exam_date)
        )
    except ValueError:
        return 0

    today = date.today()

    days_remaining = (
        exam - today
    ).days

    if days_remaining <= 0:
        return 100

    urgency = (
        100
        * math.exp(-days_remaining / 14)
    )

    return round(
        min(100, urgency),
        2
    )


def get_nearest_exam(subject_id, exams):
    subject_exams = [
        exam
        for exam in exams
        if exam["subject_id"] == subject_id
    ]

    if not subject_exams:
        return None

    today = date.today()

    future_exams = []

    for exam in subject_exams:
        try:
            exam_date = date.fromisoformat(
                str(exam["exam_date"])
            )
        except ValueError:
            continue

        future_exams.append(
            (exam_date, exam)
        )

    if not future_exams:
        return None

    future_exams.sort(
        key=lambda item: item[0]
    )

    for exam_date, exam in future_exams:
        if exam_date >= today:
            return exam

    return future_exams[-1][1]


def calculate_topic_score(
    topic,
    remaining_hours,
    exams
):
    priority = float(
        topic["priority"] or 1
    )

    difficulty = float(
        topic["difficulty"] or 1
    )

    priority_score = (
        max(1, min(5, priority))
        / 5
        * 100
    )

    difficulty_score = (
        max(1, min(5, difficulty))
        / 5
        * 100
    )

    all_remaining = [
        calculate_remaining_hours(
            other_topic,
            {}
        )
        for other_topic in []
    ]

    nearest_exam = get_nearest_exam(
        topic["subject_id"],
        exams
    )

    if nearest_exam:
        urgency_score = calculate_exam_urgency(
            nearest_exam["exam_date"]
        )
    else:
        urgency_score = 0

    return {
        "urgency": urgency_score,
        "priority": round(priority_score, 2),
        "difficulty": round(difficulty_score, 2),
        "remaining_hours": remaining_hours
    }


def build_topic_priority(student_id):
    topics = load_topics(student_id)
    progress_data = load_progress(student_id)
    exams = load_exams(student_id)

    topic_data = []

    remaining_values = {}

    for topic in topics:
        remaining_hours = calculate_remaining_hours(
            topic,
            progress_data
        )

        if remaining_hours <= 0:
            continue

        remaining_values[
            topic["topic_id"]
        ] = remaining_hours

    if not remaining_values:
        return []

    max_remaining = max(
        remaining_values.values()
    )

    if max_remaining <= 0:
        max_remaining = 1

    for topic in topics:
        topic_id = topic["topic_id"]

        remaining_hours = remaining_values.get(
            topic_id,
            0
        )

        if remaining_hours <= 0:
            continue

        priority_score = (
            max(
                1,
                min(
                    5,
                    float(topic["priority"] or 1)
                )
            )
            / 5
            * 100
        )

        difficulty_score = (
            max(
                1,
                min(
                    5,
                    float(topic["difficulty"] or 1)
                )
            )
            / 5
            * 100
        )

        remaining_work_score = (
            remaining_hours
            / max_remaining
            * 100
        )

        nearest_exam = get_nearest_exam(
            topic["subject_id"],
            exams
        )

        if nearest_exam:
            urgency_score = calculate_exam_urgency(
                nearest_exam["exam_date"]
            )
            exam_date = nearest_exam["exam_date"]
            exam_name = nearest_exam["exam_name"]
        else:
            urgency_score = 0
            exam_date = None
            exam_name = None

        score = (
            0.40 * urgency_score
            + 0.25 * priority_score
            + 0.15 * difficulty_score
            + 0.20 * remaining_work_score
        )

        topic_data.append({
            "topic_id": topic_id,
            "subject_id": topic["subject_id"],
            "topic_name": topic["topic_name"],
            "subject_name": topic["subject_name"],
            "difficulty": topic["difficulty"],
            "priority": topic["priority"],
            "estimated_hours": topic["estimated_hours"],
            "remaining_hours": round(
                remaining_hours,
                2
            ),
            "urgency_score": round(
                urgency_score,
                2
            ),
            "priority_score": round(
                priority_score,
                2
            ),
            "difficulty_score": round(
                difficulty_score,
                2
            ),
            "remaining_work_score": round(
                remaining_work_score,
                2
            ),
            "score": round(score, 2),
            "exam_name": exam_name,
            "exam_date": exam_date
        })

    topic_data.sort(
        key=lambda topic: (
            topic["score"],
            topic["urgency_score"],
            topic["priority_score"]
        ),
        reverse=True
    )

    return topic_data


def get_planning_intervals(student_id):
    preferences = load_preferences(student_id)
    availability = load_availability(student_id)
    sessions = load_existing_sessions(student_id)

    if not preferences:
        return []

    preferred_time = preferences["preferred_time"]
    planning_intervals = []

    for record in availability:
        result = calculate_free_study_minutes(
            record,
            sessions,
            preferred_time
        )

        if result["preferred_overlap"]:
            planning_intervals.append({
                "date": result["date"],
                "free_intervals": result["free_intervals"],
                "free_minutes": result["free_minutes"],
                "preferred": True
            })
        else:
            fallback = calculate_fallback_free_time(
                record,
                sessions
            )

            planning_intervals.append({
                "date": fallback["date"],
                "free_intervals": fallback["free_intervals"],
                "free_minutes": fallback["free_minutes"],
                "preferred": False
            })

    planning_intervals.sort(
        key=lambda item: item["date"]
    )

    return planning_intervals


def choose_balanced_topic(
    topics,
    topic_remaining,
    proposed_sessions,
    planning_date
):
    unfinished_topics = [
        topic
        for topic in topics
        if topic_remaining.get(
            topic["topic_id"],
            0
        ) >= 15
    ]

    if not unfinished_topics:
        return None

    topic_stats = []

    for topic in unfinished_topics:
        topic_id = topic["topic_id"]

        sessions_today = sum(
            1
            for session in proposed_sessions
            if session["session_date"] == planning_date
            and session["topic_id"] == topic_id
        )

        total_sessions = sum(
            1
            for session in proposed_sessions
            if session["topic_id"] == topic_id
        )

        topic_stats.append({
            "topic": topic,
            "sessions_today": sessions_today,
            "total_sessions": total_sessions
        })

    fresh_topics = [
        item
        for item in topic_stats
        if item["sessions_today"] == 0
    ]

    if fresh_topics:
        fresh_topics.sort(
            key=lambda item: (
                item["topic"]["score"],
                item["topic"]["urgency_score"],
                item["topic"]["remaining_work_score"]
            ),
            reverse=True
        )

        return fresh_topics[0]["topic"]

    topic_stats.sort(
        key=lambda item: (
            item["sessions_today"],
            item["total_sessions"],
            -item["topic"]["score"]
        )
    )

    minimum_today = topic_stats[0]["sessions_today"]

    candidates = [
        item
        for item in topic_stats
        if item["sessions_today"] == minimum_today
    ]

    candidates.sort(
        key=lambda item: (
            item["topic"]["score"],
            item["topic"]["urgency_score"],
            item["topic"]["remaining_work_score"]
        ),
        reverse=True
    )

    return candidates[0]["topic"]


def allocate_sessions(student_id):
    """Allocate study sessions using preferences and topic priorities."""
    preferences = load_preferences(student_id)
    planning_intervals = get_planning_intervals(student_id)
    priority_topics = build_topic_priority(student_id)

    if not preferences or not planning_intervals or not priority_topics:
        return []

    preferred_session_minutes = max(
        15,
        int(preferences["preferred_session_minutes"] or 60)
    )
    break_minutes = max(
        0,
        int(preferences["break_minutes"] or 0)
    )

    topic_remaining = {
        topic["topic_id"]: round(topic["remaining_hours"] * 60, 2)
        for topic in priority_topics
    }

    proposed_sessions = []

    for planning_day in planning_intervals:
        planning_date = planning_day["date"]
        available_intervals = list(
            planning_day["free_intervals"]
        )

        while available_intervals:
            selected_topic = choose_balanced_topic(
                priority_topics,
                topic_remaining,
                proposed_sessions,
                planning_date
            )

            if selected_topic is None:
                break

            topic_id = selected_topic["topic_id"]
            interval_start, interval_end = available_intervals.pop(0)

            available_minutes = interval_end - interval_start
            remaining_minutes = topic_remaining[topic_id]

            if remaining_minutes < 15:
                continue

            # Prefer the configured duration. Allow a shorter session
            # only when less work remains for the selected topic.
            if remaining_minutes < preferred_session_minutes:
                session_duration = remaining_minutes
            else:
                session_duration = preferred_session_minutes

            # Do not create a short session just to fill leftover time.
            if available_minutes < session_duration:
                continue

            session_duration = int(session_duration)

            if session_duration < 15:
                continue

            session_end = interval_start + session_duration

            proposed_sessions.append({
                "session_date": planning_date,
                "topic_id": topic_id,
                "topic_name": selected_topic["topic_name"],
                "subject_name": selected_topic["subject_name"],
                "start_time": minutes_to_time(interval_start),
                "end_time": minutes_to_time(session_end),
                "duration_minutes": session_duration,
                "score": selected_topic["score"],
                "urgency_score": selected_topic["urgency_score"],
                "priority_score": selected_topic["priority_score"],
                "difficulty_score": selected_topic["difficulty_score"],
                "remaining_work_score": selected_topic[
                    "remaining_work_score"
                ]
            })

            topic_remaining[topic_id] -= session_duration

            remaining_interval_minutes = interval_end - session_end

            # Apply the configured break before the next session.
            if remaining_interval_minutes >= break_minutes + 15:
                next_start = session_end + break_minutes
                available_intervals.insert(
                    0,
                    (next_start, interval_end)
                )
            elif remaining_interval_minutes >= 15:
                # A leftover interval shorter than the preferred
                # duration will be skipped by the next iteration.
                available_intervals.insert(
                    0,
                    (session_end, interval_end)
                )

    return proposed_sessions

    
def save_generated_plan(student_id):
    """Generate and save a fresh study plan."""
    sessions = allocate_sessions(student_id)

    if not sessions:
        return {
            "success": False,
            "message": "No study sessions could be generated.",
            "sessions": []
        }

    conn = get_db_connection()

    try:
        conn.execute(
            """
            DELETE FROM study_sessions
            WHERE student_id = ?
            AND status = 'Planned'
            """,
            (student_id,)
        )

        for session in sessions:
            conn.execute(
                """
                INSERT INTO study_sessions (
                    student_id,
                    topic_id,
                    session_date,
                    start_time,
                    duration_minutes,
                    status,
                    notes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    student_id,
                    session["topic_id"],
                    session["session_date"],
                    session["start_time"],
                    session["duration_minutes"],
                    "Planned",
                    "Generated by Smart Study Planner"
                )
            )

        conn.commit()

        return {
            "success": True,
            "message": (
                f"{len(sessions)} study sessions "
                "generated successfully."
            ),
            "sessions": sessions
        }

    except sqlite3.Error as error:
        conn.rollback()

        return {
            "success": False,
            "message": f"Database error: {error}",
            "sessions": []
        }

    finally:
        conn.close()

def test_save_generated_plan(student_id=1):
    print("\nSAVE GENERATED PLAN TEST")
    print("=" * 80)

    result = save_generated_plan(student_id)

    print(
        f"\nSuccess: {result['success']}"
    )

    print(
        f"Message: {result['message']}"
    )

    if not result["success"]:
        return

    conn = get_db_connection()

    rows = conn.execute(
        """
        SELECT
            ss.session_id,
            ss.session_date,
            ss.start_time,
            ss.duration_minutes,
            ss.status,
            t.name AS topic_name,
            s.name AS subject_name
        FROM study_sessions ss
        JOIN topics t
            ON ss.topic_id = t.topic_id
        JOIN subjects s
            ON t.subject_id = s.subject_id
        WHERE ss.student_id = ?
        AND ss.status = 'Planned'
        ORDER BY ss.session_date, ss.start_time
        """,
        (student_id,)
    ).fetchall()

    conn.close()

    print(
        f"\nSaved planned sessions: {len(rows)}"
    )

    current_date = None

    for row in rows:
        if row["session_date"] != current_date:
            current_date = row["session_date"]

            print("\n" + "-" * 80)
            print(
                f"Date: {current_date}"
            )
            print("-" * 80)

        print(
            f"{row['start_time']} | "
            f"{row['subject_name']} | "
            f"{row['topic_name']} | "
            f"{row['duration_minutes']} min | "
            f"Status: {row['status']}"
        )

def test_topic_priority(student_id=1):
    print("\nTOPIC PRIORITY TEST")
    print("=" * 80)

    topics = build_topic_priority(student_id)

    if not topics:
        print("No unfinished topics found.")
        return

    for index, topic in enumerate(topics, start=1):
        print(
            f"\n{index}. "
            f"{topic['subject_name']} - "
            f"{topic['topic_name']}"
        )

        print(
            f"   Score: {topic['score']}"
        )

        print(
            f"   Urgency: "
            f"{topic['urgency_score']}"
        )

        print(
            f"   Priority: "
            f"{topic['priority_score']}"
        )

        print(
            f"   Difficulty: "
            f"{topic['difficulty_score']}"
        )

        print(
            f"   Remaining Work: "
            f"{topic['remaining_work_score']}"
        )

        print(
            f"   Remaining Hours: "
            f"{topic['remaining_hours']}"
        )

        print(
            f"   Exam: "
            f"{topic['exam_name'] or 'No exam'}"
        )

        print(
            f"   Exam Date: "
            f"{topic['exam_date'] or 'N/A'}"
        )


def test_time_allocation(student_id=1):
    preferences = load_preferences(student_id)

    print("\nTIME ALLOCATION TEST")
    print("=" * 80)

    if not preferences:
        print("No study preferences found.")
        return

    preferred_time = preferences["preferred_time"]

    window_start, window_end = (
        get_preferred_time_window(preferred_time)
    )

    print(
        f"\nPreferred study time: "
        f"{preferred_time}"
    )

    print(
        f"Preferred window: "
        f"{minutes_to_time(window_start)} - "
        f"{minutes_to_time(window_end)}"
    )

    planning_intervals = get_planning_intervals(
        student_id
    )

    if not planning_intervals:
        print("\nNo availability found.")
        return

    for planning_day in planning_intervals:
        print("\n" + "-" * 80)
        print(
            f"Date: {planning_day['date']}"
        )

        print(
            f"Preferred window used: "
            f"{planning_day['preferred']}"
        )

        print(
            f"Free study minutes: "
            f"{planning_day['free_minutes']}"
        )

        print(
            f"Free study hours: "
            f"{planning_day['free_minutes'] / 60:.2f}"
        )

        print("Free intervals:")

        if not planning_day["free_intervals"]:
            print("  None")
            continue

        for start, end in planning_day["free_intervals"]:
            print(
                f"  {minutes_to_time(start)} - "
                f"{minutes_to_time(end)}"
            )


def test_allocation(student_id=1):
    print("\nBALANCED ALLOCATION TEST")
    print("=" * 80)

    sessions = allocate_sessions(student_id)

    if not sessions:
        print("No sessions generated.")
        return

    current_date = None

    for session in sessions:
        if session["session_date"] != current_date:
            current_date = session["session_date"]

            print("\n" + "-" * 80)
            print(
                f"Date: {current_date}"
            )
            print("-" * 80)

        print(
            f"{session['start_time']} - "
            f"{session['end_time']} | "
            f"{session['subject_name']} | "
            f"{session['topic_name']} | "
            f"{session['duration_minutes']} min | "
            f"Score: {session['score']}"
        )

    total_minutes = sum(
        session["duration_minutes"]
        for session in sessions
    )

    unique_topics = len(
        set(
            session["topic_id"]
            for session in sessions
        )
    )

    print("\n" + "=" * 80)
    print(
        f"Total sessions: {len(sessions)}"
    )
    print(
        f"Unique topics scheduled: "
        f"{unique_topics}"
    )
    print(
        f"Total study time: "
        f"{total_minutes} minutes"
    )
    print(
        f"Total study time: "
        f"{total_minutes / 60:.2f} hours"
    )


def test_scheduler(student_id=1):
    print("\n" + "=" * 80)
    print("SMART STUDY PLANNER - SCHEDULER TEST")
    print("=" * 80)

    preferences = load_preferences(student_id)

    if not preferences:
        print("\nERROR: Study preferences not found.")
        return

    topics = load_topics(student_id)

    if not topics:
        print("\nERROR: No topics found.")
        return

    availability = load_availability(student_id)

    if not availability:
        print("\nERROR: No availability found.")
        return

    print("\nDatabase data loaded successfully.")

    print(
        f"Topics: {len(topics)}"
    )

    print(
        f"Availability records: "
        f"{len(availability)}"
    )

    print(
        f"Preferred time: "
        f"{preferences['preferred_time']}"
    )

    print(
        f"Session length: "
        f"{preferences['preferred_session_minutes']} "
        f"minutes"
    )

    print(
        f"Break length: "
        f"{preferences['break_minutes']} "
        f"minutes"
    )

    print("\nScheduler foundation is working.")


if __name__ == "__main__":
    test_scheduler(student_id=1)
    test_topic_priority(student_id=1)
    test_time_allocation(student_id=1)
    test_allocation(student_id=1)
    test_save_generated_plan(student_id=1)