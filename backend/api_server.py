from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
import psycopg2
import json
import random
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)  # Allow mobile app to connect

# OpenAI setup - using environment variable
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Arnold Quotes
ARNOLD_QUOTES = [
    "The last three or four reps is what makes the muscle grow. This area of pain divides the champion from someone else who is not a champion.",
    "Strength does not come from winning. Your struggles develop your strengths.",
    "The mind is the limit. As long as the mind can envision the fact that you can do something, you can do it.",
    "For me life is continuously being hungry. The meaning of life is not simply to exist, to survive, but to move ahead, to go up, to achieve, to conquer.",
    "The worst thing I can be is the same as everybody else. I hate that.",
    "You can't climb the ladder of success with your hands in your pockets.",
    "The resistance that you fight physically in the gym and the resistance that you fight in life can only build a strong character.",
]

# Gym Bro Phrases
GYM_MEMES = [
    "Light weight baby!",
    "It's still your set!",
    "We're all gonna make it, bro!",
    "No pain, no gain!",
    "Do you even lift?",
    "Gains goblin spotted - chase those gains!",
    "Time to get huge!",
    "Abs are made in the kitchen, but built in the gym!",
]

# Database connection
def get_db_connection():
    return psycopg2.connect(
        dbname="workout_tracker",
        user="postgres",
        password="@Nocean99",  # Your password
        host="localhost",
        port="5432"
    )

def get_workout_data(user_id, exercise_name=None, days_back=30):
    """Get workout history from database"""
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        if exercise_name:
            cur.execute("""
                SELECT w.date, e.exercise_name, e.sets, e.reps, e.weight, e.unit, e.notes
                FROM exercises e
                JOIN workouts w ON e.workout_id = w.id
                WHERE e.exercise_name ILIKE %s
                  AND w.user_id = %s
                  AND w.date >= %s
                ORDER BY w.date DESC
            """, (f'%{exercise_name}%', user_id, datetime.now().date() - timedelta(days=days_back)))
        else:
            cur.execute("""
                SELECT w.date, e.exercise_name, e.sets, e.reps, e.weight, e.unit, e.notes
                FROM exercises e
                JOIN workouts w ON e.workout_id = w.id
                WHERE w.user_id = %s
                  AND w.date >= %s
                ORDER BY w.date DESC
            """, (user_id, datetime.now().date() - timedelta(days=days_back)))

        results = cur.fetchall()

        formatted_data = []
        for row in results:
            date, exercise, sets, reps, weight, unit, notes = row
            entry = {
                'date': str(date),
                'exercise': exercise,
                'sets': sets,
                'reps': reps,
                'weight': float(weight) if weight else None,
                'unit': unit,
                'notes': notes
            }
            formatted_data.append(entry)

        return formatted_data

    finally:
        cur.close()
        conn.close()

def get_workout_session(user_id, workout_id=None, date=None):
    """Get a complete workout session with all exercises

    Args:
        user_id: The user ID
        workout_id: Specific workout session ID (optional)
        date: Get workout from specific date (optional)

    Returns:
        Dictionary with workout session details and all exercises
    """
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        if workout_id:
            # Get specific workout session
            cur.execute("""
                SELECT w.id, w.date, w.created_at, w.notes
                FROM workouts w
                WHERE w.id = %s AND w.user_id = %s
            """, (workout_id, user_id))
        elif date:
            # Get workout from specific date (most recent if multiple)
            cur.execute("""
                SELECT w.id, w.date, w.created_at, w.notes
                FROM workouts w
                WHERE w.date = %s AND w.user_id = %s
                ORDER BY w.created_at DESC
                LIMIT 1
            """, (date, user_id))
        else:
            # Get most recent workout session
            cur.execute("""
                SELECT w.id, w.date, w.created_at, w.notes
                FROM workouts w
                WHERE w.user_id = %s
                ORDER BY w.created_at DESC
                LIMIT 1
            """, (user_id,))

        workout_row = cur.fetchone()

        if not workout_row:
            return None

        workout_id, date, created_at, notes = workout_row

        # Get all exercises for this workout session
        cur.execute("""
            SELECT e.id, e.exercise_name, e.sets, e.reps, e.weight, e.unit,
                   e.duration, e.distance, e.notes, e.created_at
            FROM exercises e
            WHERE e.workout_id = %s
            ORDER BY e.created_at ASC
        """, (workout_id,))

        exercises = []
        for ex_row in cur.fetchall():
            ex_id, ex_name, sets, reps, weight, unit, duration, distance, ex_notes, ex_created = ex_row
            exercises.append({
                'id': ex_id,
                'exercise': ex_name,
                'sets': sets,
                'reps': reps,
                'weight': float(weight) if weight else None,
                'unit': unit,
                'duration': duration,
                'distance': float(distance) if distance else None,
                'notes': ex_notes,
                'logged_at': str(ex_created)
            })

        return {
            'workout_id': workout_id,
            'date': str(date),
            'started_at': str(created_at),
            'notes': notes,
            'exercises': exercises,
            'total_exercises': len(exercises)
        }

    finally:
        cur.close()
        conn.close()

def get_recent_workout_sessions(user_id, days_back=30, limit=10):
    """Get recent workout sessions (grouped by workout_id)

    Returns a list of workout sessions with all their exercises
    """
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Get recent workout IDs
        cur.execute("""
            SELECT w.id, w.date, w.created_at, w.notes
            FROM workouts w
            WHERE w.user_id = %s
              AND w.date >= %s
            ORDER BY w.created_at DESC
            LIMIT %s
        """, (user_id, datetime.now().date() - timedelta(days=days_back), limit))

        workout_rows = cur.fetchall()

        sessions = []
        for workout_row in workout_rows:
            workout_id, date, created_at, notes = workout_row

            # Get exercises for this workout
            cur.execute("""
                SELECT e.id, e.exercise_name, e.sets, e.reps, e.weight, e.unit,
                       e.duration, e.distance, e.notes
                FROM exercises e
                WHERE e.workout_id = %s
                ORDER BY e.created_at ASC
            """, (workout_id,))

            exercises = []
            for ex_row in cur.fetchall():
                ex_id, ex_name, sets, reps, weight, unit, duration, distance, ex_notes = ex_row
                exercises.append({
                    'id': ex_id,
                    'exercise': ex_name,
                    'sets': sets,
                    'reps': reps,
                    'weight': float(weight) if weight else None,
                    'unit': unit,
                    'duration': duration,
                    'distance': float(distance) if distance else None,
                    'notes': ex_notes
                })

            sessions.append({
                'workout_id': workout_id,
                'date': str(date),
                'started_at': str(created_at),
                'notes': notes,
                'exercises': exercises,
                'total_exercises': len(exercises)
            })

        return sessions

    finally:
        cur.close()
        conn.close()

def check_leg_day_skipping(user_id):
    """Check if user has been skipping leg day"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Convert user_id to int explicitly
        user_id = int(user_id)
        
        cur.execute("""
            SELECT MAX(w.date) as last_leg_day,
                   CURRENT_DATE - MAX(w.date) as days_since
            FROM exercises e
            JOIN workouts w ON e.workout_id = w.id
            WHERE (e.exercise_name ILIKE %s 
               OR e.exercise_name ILIKE %s
               OR e.exercise_name ILIKE %s)
              AND w.user_id = %s
        """, ('%squat%', '%leg%', '%deadlift%', user_id))
        
        result = cur.fetchone()
        if result and result[0] is not None:
            return result[1]
        return None
    
    except Exception as e:
        print(f"Error in check_leg_day_skipping: {e}")
        return None
    
    finally:
        cur.close()
        conn.close()

def compare_performance(user_id, current_workout):
    """Compare current workout to previous performance"""
    if not current_workout or not current_workout[0].get('exercise'):
        return None
    
    exercise_name = current_workout[0]['exercise']
    current_weight = current_workout[0].get('weight')
    current_reps = current_workout[0].get('reps')
    current_sets = current_workout[0].get('sets')
    
    if not current_weight or not current_reps:
        return None
    
    history = get_workout_data(user_id, exercise_name, days_back=60)
    
    if len(history) < 1:
        return None
    
    previous = history[0]
    prev_weight = previous.get('weight')
    prev_reps = previous.get('reps')
    prev_sets = previous.get('sets')
    
    if not prev_weight or not prev_reps:
        return None
    
    current_volume = current_weight * current_reps * (current_sets or 1)
    prev_volume = prev_weight * prev_reps * (prev_sets or 1)
    
    percent_change = ((current_volume - prev_volume) / prev_volume) * 100
    
    return {
        'exercise': exercise_name,
        'current': {'weight': current_weight, 'reps': current_reps, 'sets': current_sets},
        'previous': {'weight': prev_weight, 'reps': prev_reps, 'sets': prev_sets, 'date': previous['date']},
        'percent_change': percent_change,
        'is_improvement': percent_change > 0,
        'is_pr': current_weight > prev_weight and current_reps >= prev_reps
    }

def classify_and_parse(user_input):
    """Classify intent AND parse workout data OR chart request OR workout recap"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """You are a workout assistant that classifies user intent.

                    Classify as:
                    - LOG_WORKOUT: "did 3x12 bench at 225"
                    - ASK_QUESTION: "what should I bench today?"
                    - CHART_REQUEST: "show me a chart of my bench press progress"
                    - WORKOUT_RECAP: "show me my most recent workout", "what did I do today?", "recap my last workout", "what exercises did I do yesterday?"

                    For CHART_REQUEST, extract:
                    - exercise name (if specified)
                    - time period: "week", "month", "all" (default to "month" if not specified)

                    For WORKOUT_RECAP, extract:
                    - date: "today", "yesterday", "2024-01-15", or null for "most recent"
                    - scope: "latest" (most recent), "all_recent" (recent sessions), or specific date

                    Return JSON:
                    {
                        "intent": "LOG_WORKOUT" | "ASK_QUESTION" | "CHART_REQUEST" | "WORKOUT_RECAP",
                        "workout_data": [...],  // if LOG_WORKOUT
                        "chart_request": {      // if CHART_REQUEST
                            "exercise": "Bench Press",
                            "period": "month"
                        },
                        "workout_recap": {      // if WORKOUT_RECAP
                            "date": "today" | "yesterday" | "2024-01-15" | null,
                            "scope": "latest" | "all_recent"
                        }
                    }"""
                },
                {
                    "role": "user",
                    "content": user_input
                }
            ],
            temperature=0
        )

        result = json.loads(response.choices[0].message.content)
        return result

    except Exception as e:
        print(f"Error in classify_and_parse: {e}")
        return {"intent": "ASK_QUESTION", "workout_data": None}

def save_workout(user_id, exercises_data):
    """Save workout and exercises to database, return workout_id and exercise details

    Groups exercises logged within 3 hours into the same workout session
    """
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Check if there's an existing workout within the last 3 hours
        cur.execute("""
            SELECT id FROM workouts
            WHERE user_id = %s
            AND created_at >= NOW() - INTERVAL '3 hours'
            ORDER BY created_at DESC
            LIMIT 1
        """, (user_id,))

        existing_workout = cur.fetchone()

        if existing_workout:
            # Reuse existing workout session
            workout_id = existing_workout[0]
            print(f"🔄 Adding to existing workout session #{workout_id}")
        else:
            # Create new workout session
            cur.execute(
                "INSERT INTO workouts (user_id, date, notes) VALUES (%s, %s, %s) RETURNING id",
                (user_id, datetime.now().date(), "")
            )
            workout_id = cur.fetchone()[0]
            print(f"✨ Created new workout session #{workout_id}")
        
        logged_exercises = []
        for exercise in exercises_data:
            if not exercise.get('exercise'):
                continue
                
            cur.execute("""
                INSERT INTO exercises 
                (workout_id, exercise_name, sets, reps, weight, unit, duration, distance, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, exercise_name, sets, reps, weight, unit
            """, (
                workout_id,
                exercise.get('exercise'),
                exercise.get('sets'),
                exercise.get('reps'),
                exercise.get('weight'),
                exercise.get('unit', 'lbs'),
                exercise.get('duration'),
                exercise.get('distance'),
                exercise.get('notes')
            ))
            
            # Capture the returned exercise data
            result = cur.fetchone()
            logged_exercises.append({
                'id': result[0],
                'exercise': result[1],
                'sets': result[2],
                'reps': result[3],
                'weight': float(result[4]) if result[4] else None,
                'unit': result[5]
            })
        
        conn.commit()
        return workout_id, logged_exercises
    
    except Exception as e:
        conn.rollback()
        print(f"Error saving workout: {e}")
        return None, []
    
    finally:
        cur.close()
        conn.close()

def generate_chart_data(user_id, exercise_name, days_back=30):
    """Get workout data formatted for charts"""
    workout_data = get_workout_data(user_id, exercise_name, days_back)

    if not workout_data:
        return None

    chart_data = []
    seen_dates = {}

    for entry in workout_data:
        date = entry['date']
        weight = entry['weight']
        reps = entry['reps']
        sets = entry.get('sets', 1)

        volume = (weight or 0) * (reps or 0) * sets

        if date not in seen_dates:
            seen_dates[date] = {
                'date': date,
                'max_weight': weight or 0,
                'total_reps': reps or 0,
                'total_volume': volume,
                'sets': sets
            }
        else:
            if weight and weight > seen_dates[date]['max_weight']:
                seen_dates[date]['max_weight'] = weight
            seen_dates[date]['total_reps'] += (reps or 0)
            seen_dates[date]['total_volume'] += volume
            seen_dates[date]['sets'] += sets

    chart_data = list(seen_dates.values())
    chart_data.sort(key=lambda x: x['date'], reverse=True)

    return {
        'exercise': exercise_name,
        'data_points': chart_data,
        'chart_type': 'line'
    }

def get_celebration_response(workout_data, performance_comparison=None):
    """Get a gym bro celebration with performance analysis"""
    try:
        workout_summary = []
        for ex in workout_data:
            if ex.get('sets') and ex.get('reps') and ex.get('weight'):
                workout_summary.append(f"{ex['exercise']}: {ex['sets']}x{ex['reps']} @ {ex['weight']} {ex.get('unit', 'lbs')}")
            elif ex.get('duration'):
                workout_summary.append(f"{ex['exercise']}: {ex['duration']} min")
            else:
                workout_summary.append(f"{ex['exercise']}")
        
        context = f"Just logged: {', '.join(workout_summary)}"
        
        if performance_comparison:
            perf = performance_comparison
            context += f"\n\nPerformance vs last time ({perf['previous']['date']}):"
            context += f"\nLast: {perf['previous']['sets']}x{perf['previous']['reps']} @ {perf['previous']['weight']} lbs"
            context += f"\nToday: {perf['current']['sets']}x{perf['current']['reps']} @ {perf['current']['weight']} lbs"
            context += f"\nChange: {perf['percent_change']:.1f}%"
            
            if perf['is_pr']:
                context += "\n🏆 NEW PR!"
            elif perf['percent_change'] < -10:
                context += "\n⚠️ Significantly weaker than last time"
        
        gym_meme = ""
        if random.random() < 0.3:
            gym_meme = f" {random.choice(GYM_MEMES)}"
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """You're a hype gym bro who gives HONEST feedback.
                    
                    - If it's a PR, GO CRAZY! 🎉
                    - If they improved, hype them up!
                    - If they did WORSE (>10% less), CALL IT OUT motivationally
                    - Use gym bro language
                    - Keep it SHORT (2-3 sentences)"""
                },
                {
                    "role": "user",
                    "content": context
                }
            ],
            temperature=0.8
        )
        
        return response.choices[0].message.content + gym_meme
    
    except:
        return "Workout logged, bro! Keep grinding! 💪"

def generate_workout_recap(user_id, workout_session):
    """Generate an AI-powered recap of a workout session"""
    if not workout_session:
        return "Bro, I couldn't find any workout data! Log some sets first! 💪"

    exercises = workout_session['exercises']
    date = workout_session['date']
    total_exercises = workout_session['total_exercises']

    # Calculate total volume
    total_volume = 0
    exercise_summary = []
    for ex in exercises:
        if ex.get('weight') and ex.get('reps') and ex.get('sets'):
            volume = ex['weight'] * ex['reps'] * ex['sets']
            total_volume += volume
            exercise_summary.append(f"- {ex['exercise']}: {ex['sets']}x{ex['reps']} @ {ex['weight']} {ex['unit']}")
        elif ex.get('duration'):
            exercise_summary.append(f"- {ex['exercise']}: {ex['duration']} min")
        else:
            exercise_summary.append(f"- {ex['exercise']}")

    summary_text = "\n".join(exercise_summary)

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """You're a motivational gym bro who reviews workout sessions.

                    Create a brief, enthusiastic recap that:
                    - Acknowledges the exercises completed
                    - Mentions total volume if impressive
                    - Gives a motivational comment about their effort
                    - Uses gym bro language
                    - Keeps it SHORT (3-4 sentences max)

                    Be authentic and hype them up!"""
                },
                {
                    "role": "user",
                    "content": f"Workout from {date}:\n\n{summary_text}\n\nTotal volume: {total_volume:.0f} lbs\nTotal exercises: {total_exercises}"
                }
            ],
            temperature=0.8
        )

        recap = response.choices[0].message.content

        # Add Arnold quote occasionally
        if random.random() < 0.3:
            recap += f"\n\n💪 Arnold says: \"{random.choice(ARNOLD_QUOTES)}\""

        return recap

    except Exception as e:
        return f"Here's your workout from {date}:\n\n{summary_text}\n\nTotal exercises: {total_exercises}\n\nKeep crushing it, bro! 💪"

def answer_workout_question(user_id, question):
    """Use AI to answer questions about workout history"""
    intent_data = classify_and_parse(question)
    workout_data = intent_data.get('workout_data')
    exercise = None
    if isinstance(workout_data, list) and workout_data:
        exercise = workout_data[0].get('exercise')

    days_since_legs = check_leg_day_skipping(user_id)
    leg_day_warning = ""
    if days_since_legs and days_since_legs > 10:
        leg_day_warning = f"\n\n⚠️ BRO WARNING: It's been {days_since_legs} days since you trained legs! Friends don't let friends skip leg day! 🦵"

    if exercise:
        workout_data = get_workout_data(user_id, exercise_name=exercise, days_back=90)
    else:
        workout_data = get_workout_data(user_id, days_back=30)

    if not workout_data:
        return "Bro, I don't have any workout data yet! Let's log some workouts first! 💪"

    arnold_quote = ""
    if random.random() < 0.2:
        arnold_quote = f"\n\n💪 Arnold says: \"{random.choice(ARNOLD_QUOTES)}\""

    data_summary = json.dumps(workout_data, indent=2)

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """You are an expert gym bro personal trainer with the user's complete workout history.

                    - Answer with SPECIFIC DATA and NUMBERS
                    - Provide weight/rep recommendations using progressive overload
                    - CALL OUT when they're lifting less than before
                    - Use gym bro language and be honest
                    - Keep responses 3-5 sentences with specific numbers"""
                },
                {
                    "role": "user",
                    "content": f"Question: {question}\n\nWorkout history:\n{data_summary}"
                }
            ],
            temperature=0.7
        )

        return response.choices[0].message.content + arnold_quote + leg_day_warning

    except Exception as e:
        return "Had trouble with that one, bro! 💪"

# ============================================
# AUTHENTICATION ENDPOINTS
# ============================================

@app.route('/register', methods=['POST'])
def register():
    """Register a new user"""
    try:
        data = request.json
        username = data.get('username', '').strip().lower()
        password = data.get('password', '')
        
        if not username or not password:
            return jsonify({"error": "Username and password required"}), 400
        
        if len(password) < 6:
            return jsonify({"error": "Password must be at least 6 characters, bro!"}), 400
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check if username exists
        cur.execute("SELECT id FROM users WHERE username = %s", (username,))
        if cur.fetchone():
            cur.close()
            conn.close()
            return jsonify({"error": "Username already taken, bro! Try another."}), 400
        
        # Create user
        password_hash = generate_password_hash(password)
        cur.execute(
            "INSERT INTO users (username, password_hash) VALUES (%s, %s) RETURNING id",
            (username, password_hash)
        )
        user_id = cur.fetchone()[0]
        conn.commit()
        
        cur.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "user_id": user_id,
            "username": username,
            "message": "Account created! Let's get huge! 💪"
        })
    
    except Exception as e:
        print(f"Registration error: {e}")
        return jsonify({"error": "Something went wrong, bro!"}), 500


@app.route('/login', methods=['POST'])
def login():
    """Login user"""
    try:
        data = request.json
        username = data.get('username', '').strip().lower()
        password = data.get('password', '')
        
        if not username or not password:
            return jsonify({"error": "Username and password required"}), 400
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute(
            "SELECT id, password_hash FROM users WHERE username = %s",
            (username,)
        )
        result = cur.fetchone()
        
        cur.close()
        conn.close()
        
        if not result:
            return jsonify({"error": "Invalid username or password"}), 401
        
        user_id, password_hash = result
        
        if not check_password_hash(password_hash, password):
            return jsonify({"error": "Invalid username or password"}), 401
        
        return jsonify({
            "success": True,
            "user_id": user_id,
            "username": username,
            "message": "Welcome back, bro! 💪"
        })
    
    except Exception as e:
        print(f"Login error: {e}")
        return jsonify({"error": "Something went wrong!"}), 500


# ============================================
# API ENDPOINTS
# ============================================

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "message": "AI Gym Bro API is running! 💪"})

@app.route('/chat', methods=['POST'])
def chat():
    """Main chat endpoint - handles both logging and questions"""
    try:
        data = request.json
        user_message = data.get('message', '')
        user_id = data.get('user_id', 1)
        
        if not user_message:
            return jsonify({"error": "No message provided"}), 400
        
        # NEW: Classify AND parse in one call
        result = classify_and_parse(user_message)
        intent = result['intent']
        
        if intent == 'LOG_WORKOUT':
            parsed = result['workout_data']
            
            if not parsed or len(parsed) == 0:
                return jsonify({
                    "type": "error",
                    "message": "Didn't quite catch that, bro. Try again?"
                })
            
            # Compare performance before saving
            performance = compare_performance(user_id, parsed)
            
            # Save workout - returns workout_id AND logged exercises
            workout_id, logged_exercises = save_workout(user_id, parsed)
            
            if not workout_id:
                return jsonify({
                    "type": "error",
                    "message": "Had trouble saving that. Try again?"
                })
            
            # Get celebration (with performance context!)
            celebration = get_celebration_response(parsed, performance)
            
            # Add Arnold quote for PRs
            arnold = ""
            if performance and performance.get('is_pr'):
                arnold = f"\n\n💪 Arnold says: \"{random.choice(ARNOLD_QUOTES)}\""
            
            return jsonify({
                "type": "workout_logged",
                "message": celebration + arnold,
                "workout_id": workout_id,
                "logged_sets": logged_exercises,
                "performance": performance
            })
        
        elif intent == 'CHART_REQUEST':
            chart_req = result.get('chart_request', {})
            exercise = chart_req.get('exercise')
            period = chart_req.get('period', 'month')

            if not exercise:
                return jsonify({
                    "type": "answer",
                    "message": "Which exercise do you want to see a chart for, bro?"
                })

            days_map = {
                'week': 7,
                'month': 30,
                'year': 365,
                'all': 3650
            }
            days_back = days_map.get(period, 30)

            chart_data = generate_chart_data(user_id, exercise, days_back)

            if chart_data:
                return jsonify({
                    "type": "chart",
                    "message": f"Here's your {exercise} progress over the last {period}! 💪",
                    "chart_data": chart_data
                })
            else:
                return jsonify({
                    "type": "answer",
                    "message": f"Bro, I don't have any data for {exercise} yet. Log some workouts first! 💪"
                })

        elif intent == 'WORKOUT_RECAP':
            recap_req = result.get('workout_recap', {})
            date_str = recap_req.get('date')
            scope = recap_req.get('scope', 'latest')

            if scope == 'all_recent':
                # Get recent workout sessions
                sessions = get_recent_workout_sessions(user_id, days_back=30, limit=5)

                if not sessions:
                    return jsonify({
                        "type": "answer",
                        "message": "Bro, I don't have any recent workouts logged! Let's hit the gym! 💪"
                    })

                # Format all sessions
                sessions_text = []
                for session in sessions:
                    exercises_text = []
                    for ex in session['exercises']:
                        if ex.get('weight') and ex.get('reps') and ex.get('sets'):
                            exercises_text.append(f"{ex['exercise']}: {ex['sets']}x{ex['reps']} @ {ex['weight']} {ex['unit']}")
                        else:
                            exercises_text.append(f"{ex['exercise']}")

                    sessions_text.append(f"**{session['date']}** ({session['total_exercises']} exercises):\n" + "\n".join([f"  • {e}" for e in exercises_text]))

                recap_message = "Here are your recent workout sessions, bro! 💪\n\n" + "\n\n".join(sessions_text)

                return jsonify({
                    "type": "workout_recap",
                    "message": recap_message,
                    "sessions": sessions
                })
            else:
                # Get specific workout session
                target_date = None
                if date_str == 'today':
                    target_date = datetime.now().date()
                elif date_str == 'yesterday':
                    target_date = datetime.now().date() - timedelta(days=1)
                elif date_str:
                    try:
                        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    except:
                        target_date = None

                if target_date:
                    workout_session = get_workout_session(user_id, date=target_date)
                else:
                    workout_session = get_workout_session(user_id)

                if not workout_session:
                    return jsonify({
                        "type": "answer",
                        "message": "Bro, I couldn't find that workout! Log some sets first! 💪"
                    })

                # Generate AI recap
                recap = generate_workout_recap(user_id, workout_session)

                # Format exercises for display
                exercises_formatted = []
                for ex in workout_session['exercises']:
                    if ex.get('weight') and ex.get('reps') and ex.get('sets'):
                        exercises_formatted.append({
                            'text': f"{ex['exercise']}: {ex['sets']}x{ex['reps']} @ {ex['weight']} {ex['unit']}",
                            'id': ex['id']
                        })
                    else:
                        exercises_formatted.append({
                            'text': f"{ex['exercise']}",
                            'id': ex['id']
                        })

                return jsonify({
                    "type": "workout_recap",
                    "message": recap,
                    "workout_session": workout_session,
                    "exercises_formatted": exercises_formatted
                })

        else:  # ASK_QUESTION
            answer = answer_workout_question(user_id, user_message)

            return jsonify({
                "type": "answer",
                "message": answer
            })
    
    except Exception as e:
        print("\n" + "="*60)
        print("❌ ERROR in /chat endpoint:")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        print("="*60)
        import traceback
        traceback.print_exc()
        print("="*60 + "\n")
        return jsonify({
            "type": "error",
            "message": f"Something went wrong, bro! {str(e)}"
        }), 500

@app.route('/delete-set', methods=['DELETE'])
def delete_set():
    """Delete a specific exercise set"""
    try:
        data = request.json
        set_id = data.get('set_id')
        user_id = data.get('user_id')
        
        if not set_id or not user_id:
            return jsonify({
                "success": False,
                "error": "Missing set_id or user_id"
            }), 400
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Security: verify the set belongs to this user before deleting
        cur.execute("""
            DELETE FROM exercises 
            WHERE id = %s 
            AND workout_id IN (
                SELECT id FROM workouts WHERE user_id = %s
            )
            RETURNING id
        """, (set_id, user_id))
        
        deleted = cur.fetchone()
        conn.commit()
        
        cur.close()
        conn.close()
        
        if deleted:
            return jsonify({
                "success": True,
                "deleted_id": set_id,
                "message": "Set deleted successfully! 🗑️"
            })
        else:
            return jsonify({
                "success": False,
                "error": "Set not found or unauthorized"
            }), 404
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/history', methods=['GET'])
def get_history():
    """Get workout history"""
    try:
        user_id = request.args.get('user_id', 1)
        days = request.args.get('days', 30)
        exercise = request.args.get('exercise', None)

        workout_data = get_workout_data(user_id, exercise, int(days))

        return jsonify({
            "success": True,
            "data": workout_data
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/workouts/all', methods=['GET'])
def get_all_workouts():
    """Get all workouts with full details - JSON format"""
    try:
        user_id = request.args.get('user_id', 1)
        days_back = request.args.get('days', 365)  # Default to last year

        sessions = get_recent_workout_sessions(user_id, days_back=int(days_back), limit=100)

        return jsonify({
            "success": True,
            "total_workouts": len(sessions),
            "workouts": sessions
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/workouts/view', methods=['GET'])
def view_all_workouts():
    """View all workouts in browser - HTML format"""
    try:
        user_id = request.args.get('user_id', 1)
        days_back = request.args.get('days', 365)

        sessions = get_recent_workout_sessions(user_id, days_back=int(days_back), limit=100)

        # Build HTML
        html = """
<!DOCTYPE html>
<html>
<head>
    <title>AI Gym Bro - Workout History</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }
        h1 {
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }
        .stats {
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .workout-session {
            background: white;
            margin-bottom: 20px;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .workout-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px 20px;
            font-weight: bold;
        }
        .workout-date {
            font-size: 1.2em;
        }
        .workout-meta {
            font-size: 0.9em;
            opacity: 0.9;
            margin-top: 5px;
        }
        .exercises {
            padding: 20px;
        }
        .exercise {
            padding: 12px;
            margin-bottom: 8px;
            background: #f8f9fa;
            border-left: 4px solid #3498db;
            border-radius: 4px;
        }
        .exercise-name {
            font-weight: bold;
            color: #2c3e50;
            font-size: 1.1em;
        }
        .exercise-details {
            color: #7f8c8d;
            margin-top: 5px;
        }
        .no-workouts {
            text-align: center;
            padding: 40px;
            color: #7f8c8d;
        }
        .filter {
            background: white;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        select, button {
            padding: 10px 15px;
            border-radius: 4px;
            border: 1px solid #ddd;
            font-size: 14px;
        }
        button {
            background: #3498db;
            color: white;
            border: none;
            cursor: pointer;
            margin-left: 10px;
        }
        button:hover {
            background: #2980b9;
        }
    </style>
</head>
<body>
    <h1>🏋️ AI Gym Bro - Workout History</h1>

    <div class="stats">
        <strong>Total Workouts:</strong> """ + str(len(sessions)) + """
        <br>
        <strong>User ID:</strong> """ + str(user_id) + """
        <br>
        <strong>Viewing:</strong> Last """ + str(days_back) + """ days
    </div>

    <div class="filter">
        <form method="GET" style="display: inline-block;">
            <label>User ID:</label>
            <select name="user_id">
                <option value="1" """ + ('selected' if str(user_id) == '1' else '') + """>User 1</option>
                <option value="2" """ + ('selected' if str(user_id) == '2' else '') + """>User 2</option>
                <option value="3" """ + ('selected' if str(user_id) == '3' else '') + """>User 3</option>
            </select>

            <label style="margin-left: 15px;">Time Period:</label>
            <select name="days">
                <option value="7" """ + ('selected' if str(days_back) == '7' else '') + """>Last 7 days</option>
                <option value="30" """ + ('selected' if str(days_back) == '30' else '') + """>Last 30 days</option>
                <option value="90" """ + ('selected' if str(days_back) == '90' else '') + """>Last 90 days</option>
                <option value="365" """ + ('selected' if str(days_back) == '365' else '') + """>Last year</option>
                <option value="3650">All time</option>
            </select>

            <button type="submit">Filter</button>
        </form>
    </div>
"""

        if not sessions:
            html += """
    <div class="no-workouts">
        <h2>No workouts found!</h2>
        <p>Start logging some workouts to see them here! 💪</p>
    </div>
"""
        else:
            for session in sessions:
                workout_date = session['date']
                started_at = session.get('started_at', '')
                total_exercises = session['total_exercises']
                exercises = session['exercises']

                # Calculate total volume
                total_volume = 0
                for ex in exercises:
                    if ex.get('weight') and ex.get('reps') and ex.get('sets'):
                        total_volume += ex['weight'] * ex['reps'] * ex['sets']

                html += f"""
    <div class="workout-session">
        <div class="workout-header">
            <div class="workout-date">📅 {workout_date}</div>
            <div class="workout-meta">
                {total_exercises} exercise{"s" if total_exercises != 1 else ""} •
                Total Volume: {total_volume:,.0f} lbs •
                Started: {started_at.split()[1] if ' ' in started_at else started_at}
            </div>
        </div>
        <div class="exercises">
"""

                for ex in exercises:
                    ex_name = ex.get('exercise', 'Unknown')
                    sets = ex.get('sets')
                    reps = ex.get('reps')
                    weight = ex.get('weight')
                    unit = ex.get('unit', 'lbs')
                    duration = ex.get('duration')
                    notes = ex.get('notes', '')

                    details = ""
                    if sets and reps and weight:
                        details = f"{sets} sets × {reps} reps @ {weight} {unit}"
                        volume = sets * reps * weight
                        details += f" (Volume: {volume:,.0f} {unit})"
                    elif duration:
                        details = f"{duration} minutes"

                    if notes:
                        details += f" - {notes}"

                    html += f"""
            <div class="exercise">
                <div class="exercise-name">{ex_name}</div>
                <div class="exercise-details">{details}</div>
            </div>
"""

                html += """
        </div>
    </div>
"""

        html += """
</body>
</html>
"""

        return html

    except Exception as e:
        return f"""
<!DOCTYPE html>
<html>
<head><title>Error</title></head>
<body>
    <h1>Error Loading Workouts</h1>
    <p>{str(e)}</p>
</body>
</html>
""", 500

if __name__ == '__main__':
    print("=" * 60)
    print("🏋️  AI GYM BRO API SERVER")
    print("=" * 60)
    print("\nAPI is running on http://localhost:5001")
    print("\nEndpoints:")
    print("  POST   /register - Register new user")
    print("  POST   /login - Login user")
    print("  POST   /chat - Main chat endpoint")
    print("  DELETE /delete-set - Delete a specific exercise set")
    print("  GET    /history - Get workout history")
    print("  GET    /workouts/all - Get all workouts (JSON)")
    print("  GET    /workouts/view - View all workouts (HTML)")
    print("  GET    /health - Health check")
    print("\n💡 View your workouts in browser:")
    print("   http://localhost:5001/workouts/view")
    print("\n" + "=" * 60 + "\n")

    app.run(debug=True, host='0.0.0.0', port=5001)