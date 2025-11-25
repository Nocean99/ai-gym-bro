"""
Conversation Memory Module
Handles storing and retrieving chat conversation history
"""
import psycopg2
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()


def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(
        dbname=os.getenv('DB_NAME', 'workout_tracker'),
        user=os.getenv('DB_USER', 'noah'),
        password=os.getenv('DB_PASSWORD', ''),
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', '5432')
    )


def save_message(user_id, role, content, session_id=None):
    """
    Save a conversation message to the database.

    Args:
        user_id: User ID
        role: 'user' or 'assistant'
        content: Message content
        session_id: Optional workout session ID

    Returns:
        message_id: ID of the saved message
    """
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            INSERT INTO conversation_messages
            (user_id, workout_session_id, role, content)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (user_id, session_id, role, content))

        message_id = cur.fetchone()[0]
        conn.commit()

        return message_id

    except Exception as e:
        conn.rollback()
        print(f"Error saving message: {e}")
        return None

    finally:
        cur.close()
        conn.close()


def get_conversation_history(user_id, session_id=None, limit=20, time_window_hours=24):
    """
    Retrieve recent conversation history for a user.

    Args:
        user_id: User ID
        session_id: Optional workout session ID (if provided, gets session-specific history)
        limit: Maximum number of messages to retrieve (default 20)
        time_window_hours: Only get messages within this time window (default 24 hours)

    Returns:
        List of dicts with 'role' and 'content' keys, in chronological order
    """
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        time_cutoff = datetime.now() - timedelta(hours=time_window_hours)

        if session_id:
            # Get messages for this specific workout session
            cur.execute("""
                SELECT role, content, timestamp
                FROM conversation_messages
                WHERE user_id = %s
                  AND workout_session_id = %s
                  AND timestamp >= %s
                ORDER BY timestamp DESC
                LIMIT %s
            """, (user_id, session_id, time_cutoff, limit))
        else:
            # Get recent messages across all sessions
            cur.execute("""
                SELECT role, content, timestamp
                FROM conversation_messages
                WHERE user_id = %s
                  AND timestamp >= %s
                ORDER BY timestamp DESC
                LIMIT %s
            """, (user_id, time_cutoff, limit))

        messages = cur.fetchall()

        # Reverse to get chronological order (oldest first)
        return [
            {
                'role': msg[0],
                'content': msg[1]
            }
            for msg in reversed(messages)
        ]

    except Exception as e:
        print(f"Error retrieving conversation history: {e}")
        return []

    finally:
        cur.close()
        conn.close()


def clear_old_conversations(days_to_keep=30):
    """
    Clean up old conversation messages to prevent database bloat.

    Args:
        days_to_keep: Number of days of history to keep (default 30)

    Returns:
        Number of messages deleted
    """
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)

        cur.execute("""
            DELETE FROM conversation_messages
            WHERE timestamp < %s
            RETURNING id
        """, (cutoff_date,))

        deleted_count = len(cur.fetchall())
        conn.commit()

        return deleted_count

    except Exception as e:
        conn.rollback()
        print(f"Error cleaning old conversations: {e}")
        return 0

    finally:
        cur.close()
        conn.close()


def get_conversation_summary(user_id, session_id=None):
    """
    Get a summary of recent conversation for context.

    Args:
        user_id: User ID
        session_id: Optional workout session ID

    Returns:
        Dict with conversation statistics
    """
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        if session_id:
            cur.execute("""
                SELECT COUNT(*), MIN(timestamp), MAX(timestamp)
                FROM conversation_messages
                WHERE user_id = %s AND workout_session_id = %s
            """, (user_id, session_id))
        else:
            cur.execute("""
                SELECT COUNT(*), MIN(timestamp), MAX(timestamp)
                FROM conversation_messages
                WHERE user_id = %s
                  AND timestamp >= %s
            """, (user_id, datetime.now() - timedelta(hours=24)))

        result = cur.fetchone()

        return {
            'message_count': result[0] or 0,
            'first_message': result[1],
            'last_message': result[2]
        }

    finally:
        cur.close()
        conn.close()
