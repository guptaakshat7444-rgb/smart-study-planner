"""Manual scheduler diagnostics moved out of scheduler.py.

Run with: python -m tests.manual_scheduler_helpers
"""
from scheduler import (
    allocate_sessions,
    build_topic_priority,
    get_db_connection,
    get_planning_intervals,
    get_preferred_time_window,
    load_availability,
    load_preferences,
    load_topics,
    save_generated_plan,
    minutes_to_time,
)


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
