import os
import psycopg2
from psycopg2.extras import RealDictCursor


def get_connection():
    """Create and return a PostgreSQL database connection."""

    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is not configured."
        )

    return psycopg2.connect(database_url)


def init_database():
    """Create and maintain the Golfing Warriors database."""

    connection = get_connection()

    try:

        with connection.cursor() as cursor:

            # =====================================================
            # PLAYERS
            # =====================================================

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS players (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    nickname VARCHAR(100),
                    current_handicap NUMERIC(5,1),
                    active BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMP NOT NULL
                        DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # =====================================================
            # SEASONS
            # =====================================================

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS seasons (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    year INTEGER NOT NULL,
                    active BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMP NOT NULL
                        DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # =====================================================
            # COURSES
            # =====================================================

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS courses (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(150) NOT NULL,
                    location VARCHAR(150),
                    active BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMP NOT NULL
                        DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # =====================================================
            # COURSE HOLES
            # =====================================================

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS course_holes (
                    id SERIAL PRIMARY KEY,

                    course_id INTEGER NOT NULL
                        REFERENCES courses(id)
                        ON DELETE CASCADE,

                    hole_number INTEGER NOT NULL
                        CHECK (hole_number BETWEEN 1 AND 18),

                    par INTEGER NOT NULL
                        CHECK (par BETWEEN 3 AND 6),

                    stroke_index INTEGER NOT NULL
                        CHECK (stroke_index BETWEEN 1 AND 18),

                    UNIQUE(course_id, hole_number),

                    UNIQUE(course_id, stroke_index)
                );
            """)

            # =====================================================
            # EVENTS
            # =====================================================

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id SERIAL PRIMARY KEY,

                    season_id INTEGER NOT NULL
                        REFERENCES seasons(id),

                    course_id INTEGER
                        REFERENCES courses(id),

                    name VARCHAR(150) NOT NULL,

                    event_date DATE NOT NULL,

                    course VARCHAR(150),

                    format VARCHAR(20) NOT NULL
                        CHECK (format IN ('NET', 'IPS')),

                    status VARCHAR(20) NOT NULL
                        DEFAULT 'DRAFT'
                        CHECK (
                            status IN (
                                'DRAFT',
                                'LIVE',
                                'PENDING_CLOSE',
                                'CLOSED'
                            )
                        ),

                    created_at TIMESTAMP NOT NULL
                        DEFAULT CURRENT_TIMESTAMP,

                    closed_at TIMESTAMP
                );
            """)

            # =====================================================
            # MIGRATION FOR EXISTING EVENTS
            # =====================================================

            cursor.execute("""
                ALTER TABLE events
                ADD COLUMN IF NOT EXISTS course_id INTEGER
                REFERENCES courses(id);
            """)

            # =====================================================
            # EVENT HOLES
            # =====================================================

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS event_holes (
                    id SERIAL PRIMARY KEY,

                    event_id INTEGER NOT NULL
                        REFERENCES events(id)
                        ON DELETE CASCADE,

                    hole_number INTEGER NOT NULL
                        CHECK (hole_number BETWEEN 1 AND 18),

                    par INTEGER NOT NULL
                        CHECK (par BETWEEN 3 AND 6),

                    stroke_index INTEGER NOT NULL
                        CHECK (stroke_index BETWEEN 1 AND 18),

                    UNIQUE(event_id, hole_number),

                    UNIQUE(event_id, stroke_index)
                );
            """)

            # =====================================================
            # EVENT PLAYERS
            # =====================================================

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS event_players (
                    id SERIAL PRIMARY KEY,

                    event_id INTEGER NOT NULL
                        REFERENCES events(id)
                        ON DELETE CASCADE,

                    player_id INTEGER NOT NULL
                        REFERENCES players(id),

                    event_handicap NUMERIC(5,1) NOT NULL,

                    group_number INTEGER,

                    is_scorer BOOLEAN NOT NULL
                        DEFAULT FALSE,

                    UNIQUE(event_id, player_id)
                );
            """)

            # =====================================================
            # HOLE SCORES
            # =====================================================

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS hole_scores (
                    id SERIAL PRIMARY KEY,

                    event_id INTEGER NOT NULL
                        REFERENCES events(id)
                        ON DELETE CASCADE,

                    player_id INTEGER NOT NULL
                        REFERENCES players(id),

                    hole_number INTEGER NOT NULL
                        CHECK (hole_number BETWEEN 1 AND 18),

                    gross_score INTEGER NOT NULL
                        CHECK (gross_score BETWEEN 1 AND 20),

                    recorded_by_player_id INTEGER
                        REFERENCES players(id),

                    created_at TIMESTAMP NOT NULL
                        DEFAULT CURRENT_TIMESTAMP,

                    updated_at TIMESTAMP NOT NULL
                        DEFAULT CURRENT_TIMESTAMP,

                    UNIQUE(event_id, player_id, hole_number)
                );
            """)

            # =====================================================
            # EVENT RESULTS
            # =====================================================

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS event_results (
                    id SERIAL PRIMARY KEY,

                    event_id INTEGER NOT NULL
                        REFERENCES events(id)
                        ON DELETE CASCADE,

                    player_id INTEGER NOT NULL
                        REFERENCES players(id),

                    gross_total INTEGER,

                    net_total INTEGER,

                    ips_total INTEGER,

                    last_6_score INTEGER,

                    last_3_score INTEGER,

                    last_hole_score INTEGER,

                    final_position INTEGER,

                    ranking_points NUMERIC(10,2),

                    UNIQUE(event_id, player_id)
                );
            """)

            # =====================================================
            # RANKING SETTINGS
            # =====================================================

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ranking_settings (
                    id SERIAL PRIMARY KEY,

                    position INTEGER NOT NULL UNIQUE,

                    points NUMERIC(10,2) NOT NULL,

                    active BOOLEAN NOT NULL DEFAULT TRUE
                );
            """)

            # =====================================================
            # RANKING POINTS
            # =====================================================

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ranking_points (
                    id SERIAL PRIMARY KEY,

                    season_id INTEGER NOT NULL
                        REFERENCES seasons(id),

                    event_id INTEGER NOT NULL
                        REFERENCES events(id),

                    player_id INTEGER NOT NULL
                        REFERENCES players(id),

                    points NUMERIC(10,2) NOT NULL,

                    created_at TIMESTAMP NOT NULL
                        DEFAULT CURRENT_TIMESTAMP,

                    UNIQUE(event_id, player_id)
                );
            """)

            # =====================================================
            # DEFAULT RANKING POINTS
            # =====================================================

            cursor.execute("""
                INSERT INTO ranking_settings
                    (position, points)
                VALUES
                    (1, 500),
                    (2, 300),
                    (3, 150),
                    (4, 75),
                    (5, 50),
                    (6, 30),
                    (7, 20),
                    (8, 15)
                ON CONFLICT (position) DO NOTHING;
            """)

        connection.commit()

    finally:
        connection.close()


def test_connection():
    """Test the PostgreSQL connection."""

    connection = get_connection()

    try:

        with connection.cursor(
            cursor_factory=RealDictCursor
        ) as cursor:

            cursor.execute(
                "SELECT NOW() AS current_time;"
            )

            result = cursor.fetchone()

            return result["current_time"]

    finally:
        connection.close()
