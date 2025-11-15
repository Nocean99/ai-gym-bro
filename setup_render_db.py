#!/usr/bin/env python3
"""
Setup script for Render database
Run this to create all tables and indexes
"""

import psycopg2
import sys

# Render database URL
DATABASE_URL = "postgresql://gym_bro_db_user:mboE3QQWaZhLdw88iSndFcfu33I5vFhd@dpg-d4cdqs49c44c738oq7dg-a.ohio-postgres.render.com/gym_bro_db"

# SQL schema
SCHEMA_SQL = """
-- Users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE,
    password_hash VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    personality VARCHAR(20) DEFAULT 'balanced',
    experience_level VARCHAR(20) DEFAULT 'intermediate'
);

-- Workouts table
CREATE TABLE IF NOT EXISTS workouts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    date DATE NOT NULL,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Exercises table
CREATE TABLE IF NOT EXISTS exercises (
    id SERIAL PRIMARY KEY,
    workout_id INTEGER REFERENCES workouts(id),
    exercise_name VARCHAR(100) NOT NULL,
    sets INTEGER,
    reps INTEGER,
    weight DECIMAL(10,2),
    unit VARCHAR(10) DEFAULT 'lbs',
    duration INTEGER,
    distance DECIMAL(10,2),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Personal Records table
CREATE TABLE IF NOT EXISTS personal_records (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    exercise_name VARCHAR(100) NOT NULL,
    weight DECIMAL(10,2),
    reps INTEGER,
    date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_workouts_user_date ON workouts(user_id, date DESC);
CREATE INDEX IF NOT EXISTS idx_exercises_workout ON exercises(workout_id);
CREATE INDEX IF NOT EXISTS idx_exercises_name ON exercises(exercise_name);
CREATE INDEX IF NOT EXISTS idx_pr_user_exercise ON personal_records(user_id, exercise_name);

-- Insert test user (only if not exists)
INSERT INTO users (username, email) VALUES ('testuser', 'test@example.com')
ON CONFLICT (username) DO NOTHING;
"""

def main():
    print("=" * 60)
    print("🏋️  GYM BRO - RENDER DATABASE SETUP")
    print("=" * 60)
    print("\nConnecting to Render database...")

    try:
        # Connect to database
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        print("✅ Connected successfully!")
        print("\nCreating tables and indexes...")

        # Execute schema
        cur.execute(SCHEMA_SQL)
        conn.commit()

        print("✅ Schema created successfully!")

        # Verify tables
        cur.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)

        tables = cur.fetchall()
        print(f"\n📊 Created {len(tables)} tables:")
        for table in tables:
            print(f"   - {table[0]}")

        # Count test user
        cur.execute("SELECT COUNT(*) FROM users;")
        user_count = cur.fetchone()[0]
        print(f"\n👤 Users in database: {user_count}")

        cur.close()
        conn.close()

        print("\n" + "=" * 60)
        print("✅ DATABASE SETUP COMPLETE!")
        print("=" * 60)
        print("\nYou can now deploy your web service on Render.")
        print("\n")

        return 0

    except psycopg2.Error as e:
        print(f"\n❌ Database error: {e}")
        print("\nPlease check:")
        print("  1. Your internet connection")
        print("  2. The database URL is correct")
        print("  3. The database is running on Render")
        return 1

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
