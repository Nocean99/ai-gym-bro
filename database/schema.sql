-- Create database
CREATE DATABASE workout_tracker;

-- Connect to database
\c workout_tracker;

-- Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    personality VARCHAR(20) DEFAULT 'balanced',
    experience_level VARCHAR(20) DEFAULT 'intermediate'
);

-- Workouts table
CREATE TABLE workouts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    date DATE NOT NULL,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Exercises table
CREATE TABLE exercises (
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
CREATE TABLE personal_records (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    exercise_name VARCHAR(100) NOT NULL,
    weight DECIMAL(10,2),
    reps INTEGER,
    date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_workouts_user_date ON workouts(user_id, date DESC);
CREATE INDEX idx_exercises_workout ON exercises(workout_id);
CREATE INDEX idx_exercises_name ON exercises(exercise_name);
CREATE INDEX idx_pr_user_exercise ON personal_records(user_id, exercise_name);

-- Insert test user
INSERT INTO users (username, email) VALUES ('testuser', 'test@example.com');
