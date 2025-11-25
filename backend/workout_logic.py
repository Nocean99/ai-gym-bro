"""
Workout Logic and Safety Module
Provides fatigue detection, set analysis, and safe weight recommendations
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


def get_recent_sets(user_id, session_id, exercise_name, limit=10):
    """
    Retrieve recent sets for an exercise in the current workout session.

    Args:
        user_id: User ID
        session_id: Active workout session ID (can be None for recent history)
        exercise_name: Name of the exercise
        limit: Maximum number of sets to retrieve

    Returns:
        List of dicts with 'weight', 'reps', 'timestamp' keys
    """
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        if session_id:
            # Get sets from current session
            cur.execute("""
                SELECT e.weight, e.reps, e.created_at
                FROM exercises e
                JOIN workouts w ON e.workout_id = w.id
                WHERE w.user_id = %s
                  AND e.workout_session_id = %s
                  AND e.exercise_name ILIKE %s
                  AND e.weight IS NOT NULL
                  AND e.reps IS NOT NULL
                ORDER BY e.created_at ASC
                LIMIT %s
            """, (user_id, session_id, f'%{exercise_name}%', limit))
        else:
            # Get recent sets across all workouts (fallback)
            cur.execute("""
                SELECT e.weight, e.reps, e.created_at
                FROM exercises e
                JOIN workouts w ON e.workout_id = w.id
                WHERE w.user_id = %s
                  AND e.exercise_name ILIKE %s
                  AND e.weight IS NOT NULL
                  AND e.reps IS NOT NULL
                  AND w.date >= %s
                ORDER BY e.created_at ASC
                LIMIT %s
            """, (user_id, f'%{exercise_name}%', datetime.now().date() - timedelta(days=1), limit))

        results = cur.fetchall()

        return [
            {
                'weight': float(row[0]),
                'reps': int(row[1]),
                'timestamp': row[2]
            }
            for row in results
        ]

    finally:
        cur.close()
        conn.close()


def analyze_set_performance(sets):
    """
    Analyzes workout sets to detect fatigue and progression patterns.

    Args:
        sets: List of dicts with 'weight' and 'reps' keys
        Example: [{'weight': 225, 'reps': 5}, {'weight': 225, 'reps': 3}]

    Returns:
        dict with analysis results including:
        - state: 'fatigued', 'stable', 'progressing', etc.
        - recommendation_type: 'backoff', 'maintain', 'increase', etc.
        - suggested_weight: recommended weight for next set
        - message: human-readable explanation
    """
    if not sets or len(sets) < 1:
        return {
            'state': 'insufficient_data',
            'recommendation_type': 'continue',
            'message': 'Log at least one set to get recommendations',
            'suggested_weight': None
        }

    # If only one set, suggest maintaining or slight increase
    if len(sets) == 1:
        first_set = sets[0]
        return {
            'state': 'first_set',
            'recommendation_type': 'assess',
            'suggested_weight_maintain': first_set['weight'],
            'suggested_weight_increase': round(first_set['weight'] + 5, 1),
            'message': f"First set completed at {first_set['weight']} lbs for {first_set['reps']} reps. How did it feel?"
        }

    last_set = sets[-1]
    previous_set = sets[-2]

    # Check if using same weight (most common scenario for fatigue detection)
    if last_set['weight'] == previous_set['weight']:
        rep_change = last_set['reps'] - previous_set['reps']
        rep_change_percent = (rep_change / previous_set['reps']) * 100 if previous_set['reps'] > 0 else 0

        # CRITICAL: Rep drop of 20% or more = significant fatigue
        if rep_change_percent <= -20:
            backoff_weight = round(last_set['weight'] * 0.85, 1)  # 15% lighter
            return {
                'state': 'fatigued',
                'recommendation_type': 'backoff',
                'suggested_weight': backoff_weight,
                'suggested_weight_stop': None,  # Option to stop
                'message': f"⚠️ Performance declined {abs(int(rep_change_percent))}% ({previous_set['reps']}→{last_set['reps']} reps). SAFETY: Recommend back-off set at {backoff_weight} lbs or ending the exercise.",
                'is_dangerous': True
            }

        # Moderate rep drop (10-20%)
        elif rep_change_percent <= -10:
            return {
                'state': 'mild_fatigue',
                'recommendation_type': 'maintain_or_stop',
                'suggested_weight': last_set['weight'],
                'message': f"Slight fatigue detected ({previous_set['reps']}→{last_set['reps']} reps, {abs(int(rep_change_percent))}% drop). Maintain {last_set['weight']} lbs or consider finishing.",
                'is_dangerous': False
            }

        # Reps stayed same or increased = stable/strong
        elif rep_change >= 0:
            return {
                'state': 'stable',
                'recommendation_type': 'repeat_or_increase',
                'suggested_weight_maintain': last_set['weight'],
                'suggested_weight_increase': round(last_set['weight'] + 5, 1),
                'message': f"Strong performance! Reps maintained at {last_set['reps']}. Can repeat {last_set['weight']} lbs or try {round(last_set['weight'] + 5, 1)} lbs.",
                'is_dangerous': False
            }

        # Small decline (< 10%)
        else:
            return {
                'state': 'slight_fatigue',
                'recommendation_type': 'maintain',
                'suggested_weight': last_set['weight'],
                'message': f"Slight fatigue ({abs(int(rep_change_percent))}% drop). Stick with {last_set['weight']} lbs.",
                'is_dangerous': False
            }

    # Weight increased between sets
    elif last_set['weight'] > previous_set['weight']:
        # Check if reps dropped significantly despite weight increase
        rep_change = last_set['reps'] - previous_set['reps']

        # Expected to do fewer reps with more weight, but check if it's too much
        if last_set['reps'] < previous_set['reps'] * 0.6:  # Less than 60% of previous reps
            return {
                'state': 'weight_too_heavy',
                'recommendation_type': 'reduce',
                'suggested_weight': previous_set['weight'],
                'message': f"⚠️ Weight jump was too large ({previous_set['weight']}→{last_set['weight']} lbs). Reps dropped significantly. Go back to {previous_set['weight']} lbs.",
                'is_dangerous': True
            }
        else:
            return {
                'state': 'progressing',
                'recommendation_type': 'assess',
                'suggested_weight': last_set['weight'],
                'message': f"Progressed to {last_set['weight']} lbs. Completed {last_set['reps']} reps. Assess how it felt before next set.",
                'is_dangerous': False
            }

    # Weight decreased (already doing back-off)
    else:
        return {
            'state': 'backing_off',
            'recommendation_type': 'maintain',
            'suggested_weight': last_set['weight'],
            'message': f"In back-off phase at {last_set['weight']} lbs. Maintain or finish exercise.",
            'is_dangerous': False
        }


def get_recommendation_constraints(analysis):
    """
    Generate hard constraints based on set analysis that the AI MUST follow.
    These constraints are injected into the system prompt to enforce safety rules.

    Args:
        analysis: Output from analyze_set_performance()

    Returns:
        String with mandatory constraints for the AI
    """
    if not analysis:
        return ""

    constraints = []
    state = analysis.get('state')

    if state == 'fatigued':
        constraints.append("=" * 60)
        constraints.append("🚨 CRITICAL SAFETY ALERT 🚨")
        constraints.append("=" * 60)
        constraints.append(f"ANALYSIS: {analysis['message']}")
        constraints.append("")
        constraints.append("MANDATORY RULES (YOU MUST FOLLOW THESE):")
        constraints.append(f"1. RECOMMEND: Decrease weight to {analysis['suggested_weight']} lbs (15% lighter)")
        constraints.append("2. ALTERNATIVE: Suggest ending this exercise")
        constraints.append(f"3. FORBIDDEN: NEVER suggest maintaining {analysis.get('suggested_weight_maintain', 'current')} lbs")
        constraints.append("4. FORBIDDEN: NEVER suggest increasing weight")
        constraints.append("")
        constraints.append("REASONING: Performance declined >20%, indicating significant fatigue.")
        constraints.append("Continuing at same/higher weight risks injury and overtraining.")
        constraints.append("=" * 60)

    elif state == 'weight_too_heavy':
        constraints.append("=" * 60)
        constraints.append("⚠️  WEIGHT TOO HEAVY WARNING ⚠️")
        constraints.append("=" * 60)
        constraints.append(f"ANALYSIS: {analysis['message']}")
        constraints.append("")
        constraints.append("MANDATORY RULES:")
        constraints.append(f"1. RECOMMEND: Go back to {analysis['suggested_weight']} lbs")
        constraints.append("2. EXPLAIN: Weight jump was too aggressive")
        constraints.append("3. FORBIDDEN: Do NOT suggest maintaining or increasing current weight")
        constraints.append("=" * 60)

    elif state == 'mild_fatigue' or state == 'slight_fatigue':
        constraints.append("-" * 60)
        constraints.append("⚠️  FATIGUE DETECTED")
        constraints.append("-" * 60)
        constraints.append(f"ANALYSIS: {analysis['message']}")
        constraints.append("")
        constraints.append("RECOMMENDED APPROACH:")
        constraints.append(f"1. SAFE OPTION: Maintain {analysis['suggested_weight']} lbs")
        constraints.append("2. ALTERNATIVE: Consider finishing exercise")
        constraints.append("3. FORBIDDEN: Do NOT suggest increasing weight")
        constraints.append("-" * 60)

    elif state == 'stable':
        constraints.append("-" * 60)
        constraints.append("✅ STABLE PERFORMANCE")
        constraints.append("-" * 60)
        constraints.append(f"ANALYSIS: {analysis['message']}")
        constraints.append("")
        constraints.append("OPTIONS:")
        constraints.append(f"1. MAINTAIN: {analysis.get('suggested_weight_maintain')} lbs (safe choice)")
        constraints.append(f"2. INCREASE: {analysis.get('suggested_weight_increase')} lbs (if feeling strong)")
        constraints.append("3. Let user decide based on how they feel")
        constraints.append("-" * 60)

    elif state == 'progressing':
        constraints.append("-" * 60)
        constraints.append("📈 PROGRESSIVE OVERLOAD")
        constraints.append("-" * 60)
        constraints.append(f"ANALYSIS: {analysis['message']}")
        constraints.append("")
        constraints.append("APPROACH:")
        constraints.append("1. Ask user how the set felt")
        constraints.append("2. Provide guidance based on their response")
        constraints.append("-" * 60)

    return "\n".join(constraints)


def get_active_workout_session(user_id):
    """
    Get or create an active workout session for the user.

    Args:
        user_id: User ID

    Returns:
        session_id: ID of active session, or None if no active session
    """
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Check for active session
        cur.execute("""
            SELECT id, current_exercise
            FROM workout_sessions
            WHERE user_id = %s AND is_active = TRUE
            ORDER BY started_at DESC
            LIMIT 1
        """, (user_id,))

        result = cur.fetchone()

        if result:
            return {'session_id': result[0], 'current_exercise': result[1]}

        return None

    finally:
        cur.close()
        conn.close()


def start_workout_session(user_id, exercise_name=None):
    """
    Start a new workout session.

    Args:
        user_id: User ID
        exercise_name: Optional starting exercise

    Returns:
        session_id: ID of the new session
    """
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # End any existing active sessions first (safety)
        cur.execute("""
            UPDATE workout_sessions
            SET is_active = FALSE, ended_at = CURRENT_TIMESTAMP
            WHERE user_id = %s AND is_active = TRUE
        """, (user_id,))

        # Create new session
        cur.execute("""
            INSERT INTO workout_sessions (user_id, current_exercise)
            VALUES (%s, %s)
            RETURNING id
        """, (user_id, exercise_name))

        session_id = cur.fetchone()[0]
        conn.commit()

        return session_id

    finally:
        cur.close()
        conn.close()


def update_session_exercise(session_id, exercise_name):
    """Update the current exercise in a workout session"""
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            UPDATE workout_sessions
            SET current_exercise = %s
            WHERE id = %s
        """, (exercise_name, session_id))

        conn.commit()

    finally:
        cur.close()
        conn.close()


def end_workout_session(session_id):
    """End a workout session"""
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            UPDATE workout_sessions
            SET is_active = FALSE, ended_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (session_id,))

        conn.commit()

    finally:
        cur.close()
        conn.close()
