-- Migration 001: Add conversation memory and workout session tracking
-- Run this on your database to add conversation history and session tracking

-- Note: Already connected via connection string, no need to switch databases
-- \c workout_tracker;

-- Conversation messages table for chat history
CREATE TABLE IF NOT EXISTS conversation_messages (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    workout_session_id INTEGER,  -- Optional: link to active workout session
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Workout sessions table for tracking active workouts
CREATE TABLE IF NOT EXISTS workout_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    current_exercise VARCHAR(100),  -- Track what exercise they're currently doing
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    notes TEXT
);

-- Link exercises to workout sessions for set-by-set tracking
ALTER TABLE exercises
ADD COLUMN IF NOT EXISTS workout_session_id INTEGER REFERENCES workout_sessions(id);

-- Add index for fast conversation history retrieval
CREATE INDEX IF NOT EXISTS idx_conversation_user_time
ON conversation_messages(user_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_conversation_session
ON conversation_messages(workout_session_id, timestamp ASC);

-- Add index for active workout sessions
CREATE INDEX IF NOT EXISTS idx_workout_sessions_active
ON workout_sessions(user_id, is_active)
WHERE is_active = TRUE;

-- Add index for exercises by session
CREATE INDEX IF NOT EXISTS idx_exercises_session
ON exercises(workout_session_id, created_at DESC);

COMMENT ON TABLE conversation_messages IS 'Stores chat history for conversation memory';
COMMENT ON TABLE workout_sessions IS 'Tracks active workout sessions for set-by-set analysis';
COMMENT ON COLUMN exercises.workout_session_id IS 'Links sets to the active workout session';
