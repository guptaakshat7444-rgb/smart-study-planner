PRAGMA foreign_keys = ON;

------------------------------------------------------------
-- DROP EXISTING TABLES
-- Useful during development/testing
------------------------------------------------------------

DROP TABLE IF EXISTS study_sessions;
DROP TABLE IF EXISTS topic_progress;
DROP TABLE IF EXISTS availability;
DROP TABLE IF EXISTS study_preferences;
DROP TABLE IF EXISTS exams;
DROP TABLE IF EXISTS topics;
DROP TABLE IF EXISTS subjects;
DROP TABLE IF EXISTS students;


------------------------------------------------------------
-- 1. STUDENTS
------------------------------------------------------------

CREATE TABLE students (
    student_id INTEGER PRIMARY KEY AUTOINCREMENT,

    name TEXT NOT NULL,

    email TEXT NOT NULL UNIQUE,

    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);


------------------------------------------------------------
-- 2. SUBJECTS
------------------------------------------------------------

CREATE TABLE subjects (
    subject_id INTEGER PRIMARY KEY AUTOINCREMENT,

    student_id INTEGER NOT NULL,

    name TEXT NOT NULL,

    description TEXT,

    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (student_id)
        REFERENCES students(student_id)
        ON DELETE CASCADE,

    UNIQUE(student_id, name)
);


------------------------------------------------------------
-- 3. TOPICS
------------------------------------------------------------

CREATE TABLE topics (
    topic_id INTEGER PRIMARY KEY AUTOINCREMENT,

    subject_id INTEGER NOT NULL,

    name TEXT NOT NULL,

    description TEXT,

    difficulty INTEGER NOT NULL DEFAULT 3,

    priority INTEGER NOT NULL DEFAULT 3,

    estimated_hours REAL NOT NULL,

    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (subject_id)
        REFERENCES subjects(subject_id)
        ON DELETE CASCADE,

    CHECK (difficulty BETWEEN 1 AND 5),

    CHECK (priority BETWEEN 1 AND 5),

    CHECK (estimated_hours > 0),

    UNIQUE(subject_id, name)
);


------------------------------------------------------------
-- 4. EXAMS
------------------------------------------------------------

CREATE TABLE exams (
    exam_id INTEGER PRIMARY KEY AUTOINCREMENT,

    subject_id INTEGER NOT NULL,

    exam_name TEXT NOT NULL,

    exam_date TEXT NOT NULL,

    exam_type TEXT NOT NULL DEFAULT 'Final',

    FOREIGN KEY (subject_id)
        REFERENCES subjects(subject_id)
        ON DELETE CASCADE,

    CHECK (
        exam_type IN (
            'Minor',
            'Midterm',
            'Final',
            'Assignment',
            'Practical',
            'Other'
        )
    )
);


------------------------------------------------------------
-- 5. STUDY PREFERENCES
------------------------------------------------------------

CREATE TABLE study_preferences (
    preference_id INTEGER PRIMARY KEY AUTOINCREMENT,

    student_id INTEGER NOT NULL UNIQUE,

    preferred_time TEXT NOT NULL DEFAULT 'Evening',

    daily_study_hours REAL NOT NULL DEFAULT 3.0,

    preferred_session_minutes INTEGER NOT NULL DEFAULT 60,

    break_minutes INTEGER NOT NULL DEFAULT 10,

    FOREIGN KEY (student_id)
        REFERENCES students(student_id)
        ON DELETE CASCADE,

    CHECK (
        preferred_time IN (
            'Morning',
            'Afternoon',
            'Evening',
            'Night'
        )
    ),

    CHECK (daily_study_hours > 0),

    CHECK (preferred_session_minutes > 0),

    CHECK (break_minutes >= 0)
);


------------------------------------------------------------
-- 6. AVAILABILITY
------------------------------------------------------------

CREATE TABLE availability (
    availability_id INTEGER PRIMARY KEY AUTOINCREMENT,

    student_id INTEGER NOT NULL,

    available_date TEXT NOT NULL,

    available_hours REAL NOT NULL,

    start_time TEXT,

    end_time TEXT,

    FOREIGN KEY (student_id)
        REFERENCES students(student_id)
        ON DELETE CASCADE,

    CHECK (available_hours >= 0),

    UNIQUE(student_id, available_date)
);


------------------------------------------------------------
-- 7. TOPIC PROGRESS
------------------------------------------------------------

CREATE TABLE topic_progress (
    progress_id INTEGER PRIMARY KEY AUTOINCREMENT,

    student_id INTEGER NOT NULL,

    topic_id INTEGER NOT NULL,

    progress_percentage INTEGER NOT NULL DEFAULT 0,

    completed_hours REAL NOT NULL DEFAULT 0,

    is_completed INTEGER NOT NULL DEFAULT 0,

    last_studied_at TEXT,

    FOREIGN KEY (student_id)
        REFERENCES students(student_id)
        ON DELETE CASCADE,

    FOREIGN KEY (topic_id)
        REFERENCES topics(topic_id)
        ON DELETE CASCADE,

    CHECK (progress_percentage BETWEEN 0 AND 100),

    CHECK (completed_hours >= 0),

    CHECK (is_completed IN (0, 1)),

    UNIQUE(student_id, topic_id)
);


------------------------------------------------------------
-- 8. STUDY SESSIONS
------------------------------------------------------------

CREATE TABLE study_sessions (
    session_id INTEGER PRIMARY KEY AUTOINCREMENT,

    student_id INTEGER NOT NULL,

    topic_id INTEGER NOT NULL,

    session_date TEXT NOT NULL,

    start_time TEXT,

    duration_minutes INTEGER NOT NULL,

    status TEXT NOT NULL DEFAULT 'Planned',

    notes TEXT,

    FOREIGN KEY (student_id)
        REFERENCES students(student_id)
        ON DELETE CASCADE,

    FOREIGN KEY (topic_id)
        REFERENCES topics(topic_id)
        ON DELETE CASCADE,

    CHECK (duration_minutes > 0),

    CHECK (
        status IN (
            'Planned',
            'Completed',
            'Skipped',
            'Cancelled'
        )
    )
);


------------------------------------------------------------
-- INDEXES
------------------------------------------------------------

CREATE INDEX idx_subjects_student
ON subjects(student_id);

CREATE INDEX idx_topics_subject
ON topics(subject_id);

CREATE INDEX idx_exams_subject
ON exams(subject_id);

CREATE INDEX idx_exams_date
ON exams(exam_date);

CREATE INDEX idx_topic_progress_student
ON topic_progress(student_id);

CREATE INDEX idx_topic_progress_topic
ON topic_progress(topic_id);

CREATE INDEX idx_sessions_student
ON study_sessions(student_id);

CREATE INDEX idx_sessions_topic
ON study_sessions(topic_id);

CREATE INDEX idx_sessions_date
ON study_sessions(session_date);


------------------------------------------------------------
-- SAMPLE DATA
------------------------------------------------------------


------------------------------------------------------------
-- STUDENT
------------------------------------------------------------

INSERT INTO students (name, email)
VALUES (
    'Arjun Sharma',
    'arjun.student@example.com'
);


------------------------------------------------------------
-- SUBJECTS
------------------------------------------------------------

INSERT INTO subjects
    (student_id, name, description)
VALUES
    (
        1,
        'Data Structures',
        'Fundamental data structures and algorithms'
    ),
    (
        1,
        'Database Management Systems',
        'Database concepts, SQL and normalization'
    ),
    (
        1,
        'Operating Systems',
        'Processes, scheduling, memory and synchronization'
    ),
    (
        1,
        'Computer Networks',
        'Networking fundamentals and protocols'
    ),
    (
        1,
        'Java Programming',
        'Object-oriented programming and Java concepts'
    );


------------------------------------------------------------
-- DATA STRUCTURES TOPICS
------------------------------------------------------------

INSERT INTO topics
    (subject_id, name, description, difficulty, priority, estimated_hours)
VALUES
    (
        1,
        'Arrays',
        'Array operations and problem solving',
        2,
        3,
        3
    ),
    (
        1,
        'Linked Lists',
        'Singly and doubly linked lists',
        3,
        4,
        4
    ),
    (
        1,
        'Stacks and Queues',
        'Stack and queue implementations and applications',
        3,
        4,
        3
    ),
    (
        1,
        'Trees',
        'Binary trees, BST and tree traversal',
        5,
        5,
        7
    ),
    (
        1,
        'Graphs',
        'BFS, DFS, shortest paths and MST',
        5,
        5,
        8
    );


------------------------------------------------------------
-- DBMS TOPICS
------------------------------------------------------------

INSERT INTO topics
    (subject_id, name, description, difficulty, priority, estimated_hours)
VALUES
    (
        2,
        'ER Model',
        'Entities, relationships and ER diagrams',
        2,
        3,
        3
    ),
    (
        2,
        'SQL Queries',
        'SELECT, JOIN, GROUP BY and subqueries',
        4,
        5,
        6
    ),
    (
        2,
        'Normalization',
        '1NF, 2NF, 3NF and BCNF',
        5,
        5,
        7
    ),
    (
        2,
        'Transactions',
        'ACID properties and transaction management',
        4,
        4,
        4
    ),
    (
        2,
        'Indexing',
        'Indexes and database performance',
        3,
        3,
        3
    );


------------------------------------------------------------
-- OPERATING SYSTEMS TOPICS
------------------------------------------------------------

INSERT INTO topics
    (subject_id, name, description, difficulty, priority, estimated_hours)
VALUES
    (
        3,
        'Process Management',
        'Processes, states and PCB',
        3,
        4,
        4
    ),
    (
        3,
        'CPU Scheduling',
        'FCFS, SJF, SRTF, Round Robin and Priority Scheduling',
        5,
        5,
        7
    ),
    (
        3,
        'Threads',
        'Multithreading and thread concepts',
        3,
        3,
        3
    ),
    (
        3,
        'Synchronization',
        'Critical sections, mutex and semaphores',
        5,
        5,
        6
    ),
    (
        3,
        'Deadlocks',
        'Deadlock conditions and avoidance',
        5,
        4,
        6
    );


------------------------------------------------------------
-- COMPUTER NETWORKS TOPICS
------------------------------------------------------------

INSERT INTO topics
    (subject_id, name, description, difficulty, priority, estimated_hours)
VALUES
    (
        4,
        'OSI Model',
        'Seven-layer networking model',
        2,
        3,
        2
    ),
    (
        4,
        'TCP/IP',
        'TCP/IP protocol architecture',
        3,
        3,
        3
    ),
    (
        4,
        'IP Addressing',
        'IPv4, subnetting and addressing',
        4,
        4,
        5
    ),
    (
        4,
        'Routing Algorithms',
        'Routing and shortest path algorithms',
        5,
        4,
        6
    ),
    (
        4,
        'Transport Layer',
        'TCP, UDP and transport protocols',
        4,
        3,
        4
    );


------------------------------------------------------------
-- JAVA TOPICS
------------------------------------------------------------

INSERT INTO topics
    (subject_id, name, description, difficulty, priority, estimated_hours)
VALUES
    (
        5,
        'OOP Concepts',
        'Classes, objects, encapsulation and abstraction',
        3,
        4,
        4
    ),
    (
        5,
        'Inheritance',
        'Inheritance and method overriding',
        3,
        4,
        3
    ),
    (
        5,
        'Polymorphism',
        'Compile-time and runtime polymorphism',
        4,
        4,
        3
    ),
    (
        5,
        'Exception Handling',
        'Try, catch, finally and custom exceptions',
        3,
        3,
        3
    ),
    (
        5,
        'Multithreading',
        'Threads and synchronization in Java',
        5,
        5,
        6
    );


------------------------------------------------------------
-- EXAMS
------------------------------------------------------------

INSERT INTO exams
    (subject_id, exam_name, exam_date, exam_type)
VALUES
    (
        1,
        'Data Structures Final Exam',
        '2026-10-05',
        'Final'
    ),
    (
        2,
        'DBMS Final Exam',
        '2026-10-10',
        'Final'
    ),
    (
        3,
        'Operating Systems Final Exam',
        '2026-09-28',
        'Final'
    ),
    (
        4,
        'Computer Networks Final Exam',
        '2026-10-18',
        'Final'
    ),
    (
        5,
        'Java Programming Final Exam',
        '2026-10-25',
        'Final'
    );


------------------------------------------------------------
-- STUDY PREFERENCES
------------------------------------------------------------

INSERT INTO study_preferences
    (
        student_id,
        preferred_time,
        daily_study_hours,
        preferred_session_minutes,
        break_minutes
    )
VALUES
    (
        1,
        'Evening',
        4.0,
        60,
        10
    );


------------------------------------------------------------
-- AVAILABILITY
------------------------------------------------------------

INSERT INTO availability
    (
        student_id,
        available_date,
        available_hours,
        start_time,
        end_time
    )
VALUES
    (1, '2026-09-18', 4.0, '18:00', '22:00'),
    (1, '2026-09-19', 5.0, '16:00', '22:00'),
    (1, '2026-09-20', 3.0, '18:00', '21:00'),
    (1, '2026-09-21', 4.0, '18:00', '22:00'),
    (1, '2026-09-22', 4.0, '18:00', '22:00'),
    (1, '2026-09-23', 2.0, '19:00', '21:00'),
    (1, '2026-09-24', 5.0, '17:00', '22:00'),
    (1, '2026-09-25', 4.0, '18:00', '22:00'),
    (1, '2026-09-26', 5.0, '16:00', '22:00'),
    (1, '2026-09-27', 3.0, '18:00', '21:00');


------------------------------------------------------------
-- TOPIC PROGRESS
------------------------------------------------------------

INSERT INTO topic_progress
    (
        student_id,
        topic_id,
        progress_percentage,
        completed_hours,
        is_completed,
        last_studied_at
    )
VALUES

    -- Data Structures
    (1, 1, 100, 3.0, 1, '2026-09-10 19:00:00'),
    (1, 2, 60, 2.4, 0, '2026-09-16 19:00:00'),
    (1, 3, 40, 1.2, 0, '2026-09-15 20:00:00'),
    (1, 4, 20, 1.4, 0, '2026-09-16 20:00:00'),
    (1, 5, 10, 0.8, 0, '2026-09-12 18:00:00'),

    -- DBMS
    (1, 6, 100, 3.0, 1, '2026-09-08 19:00:00'),
    (1, 7, 50, 3.0, 0, '2026-09-16 18:00:00'),
    (1, 8, 25, 1.75, 0, '2026-09-15 19:00:00'),
    (1, 9, 30, 1.2, 0, '2026-09-14 20:00:00'),
    (1, 10, 0, 0.0, 0, NULL),

    -- Operating Systems
    (1, 11, 50, 2.0, 0, '2026-09-15 18:00:00'),
    (1, 12, 15, 1.05, 0, '2026-09-16 20:00:00'),
    (1, 13, 80, 2.4, 0, '2026-09-13 19:00:00'),
    (1, 14, 20, 1.2, 0, '2026-09-16 18:00:00'),
    (1, 15, 10, 0.6, 0, '2026-09-11 20:00:00'),

    -- Computer Networks
    (1, 16, 100, 2.0, 1, '2026-09-09 18:00:00'),
    (1, 17, 70, 2.1, 0, '2026-09-14 19:00:00'),
    (1, 18, 30, 1.5, 0, '2026-09-15 18:00:00'),
    (1, 19, 20, 1.2, 0, '2026-09-12 20:00:00'),
    (1, 20, 60, 2.4, 0, '2026-09-13 19:00:00'),

    -- Java
    (1, 21, 80, 3.2, 0, '2026-09-15 19:00:00'),
    (1, 22, 100, 3.0, 1, '2026-09-10 18:00:00'),
    (1, 23, 40, 1.2, 0, '2026-09-14 19:00:00'),
    (1, 24, 100, 3.0, 1, '2026-09-12 18:00:00'),
    (1, 25, 15, 0.9, 0, '2026-09-16 19:00:00');


------------------------------------------------------------
-- STUDY SESSIONS
------------------------------------------------------------

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
VALUES

    -- Completed sessions
    (1, 2, '2026-09-16', '19:00', 60, 'Completed',
        'Practiced linked list insertion and deletion'),

    (1, 4, '2026-09-16', '20:00', 60, 'Completed',
        'Studied binary tree traversal'),

    (1, 7, '2026-09-16', '18:00', 60, 'Completed',
        'Solved SQL JOIN problems'),

    (1, 12, '2026-09-16', '20:00', 60, 'Completed',
        'Practiced CPU scheduling algorithms'),

    (1, 14, '2026-09-16', '18:00', 60, 'Completed',
        'Studied critical section problem'),

    (1, 25, '2026-09-16', '19:00', 60, 'Completed',
        'Started Java multithreading'),

    -- Planned sessions
    (1, 12, '2026-09-18', '18:00', 60, 'Planned',
        'CPU Scheduling practice'),

    (1, 14, '2026-09-18', '19:10', 60, 'Planned',
        'Synchronization problems'),

    (1, 5, '2026-09-18', '20:20', 60, 'Planned',
        'Graph algorithms'),

    (1, 8, '2026-09-19', '17:00', 60, 'Planned',
        'Normalization problems'),

    (1, 19, '2026-09-19', '18:10', 60, 'Planned',
        'Routing algorithms'),

    (1, 25, '2026-09-19', '19:20', 60, 'Planned',
        'Java thread synchronization');


------------------------------------------------------------
-- END
------------------------------------------------------------