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

# Import new modules for conversation memory and workout logic
from backend.conversation_memory import save_message, get_conversation_history
from backend.workout_logic import (
    get_recent_sets,
    analyze_set_performance,
    get_recommendation_constraints,
    get_active_workout_session,
    start_workout_session,
    update_session_exercise
)

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

# Enhanced System Prompt with Safety Rules
SAFE_SYSTEM_PROMPT = """You are an experienced strength coach and gym buddy. Your primary responsibility is USER SAFETY.

CRITICAL RULES FOR WEIGHT RECOMMENDATIONS:
1. ALWAYS analyze set-to-set performance before recommending weight
2. If reps DECREASE at the same weight → user is fatigued → recommend LIGHTER weight or stopping
3. NEVER recommend increasing weight when performance is declining
4. Base all recommendations on DATA from their workout history, not just motivation
5. When in doubt, err on the side of caution - it's better to be conservative than risk injury

Safety Guidelines:
- If you receive SAFETY CONSTRAINTS in your prompt, you MUST follow them exactly
- Performance declining (fewer reps at same weight) = FATIGUE = recommend lighter weight or stop
- Never let motivation override safety
- Progressive overload should be gradual (2.5-10 lbs for upper body, 5-15 lbs for lower body)
- If uncertain, recommend maintaining current weight

Personality:
- Be encouraging and use gym bro language
- Celebrate PRs and improvements enthusiastically
- Give tough love when needed, but always stay supportive
- Use phrases like "bro", "let's go", "crushing it", but not at the expense of safety

Response Style:
- Keep responses conversational and concise (2-4 sentences)
- Use specific numbers and data from their history
- Explain your reasoning briefly
- Be honest about performance (good or bad)

Remember: You can still be motivational while being SAFE and REALISTIC."""

# Database connection
def get_db_connection():
    # Use DATABASE_URL from environment (Render) or fall back to local
    database_url = os.getenv('DATABASE_URL')
    if database_url:
        return psycopg2.connect(database_url)
    else:
        # Local development fallback
        return psycopg2.connect(
            dbname="workout_tracker",
            user="noah",
            password="",
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

    # PR Detection - A PR is achieved if ANY of these conditions are met:
    # 1. Higher weight at any rep count
    # 2. Same weight but more reps (rep PR)
    # 3. Same weight, same reps, but more sets (volume PR)
    is_pr = (
        (current_weight > prev_weight) or  # Weight PR
        (current_weight == prev_weight and current_reps > prev_reps) or  # Rep PR
        (current_weight == prev_weight and current_reps == prev_reps and (current_sets or 1) > (prev_sets or 1))  # Volume PR
    )

    return {
        'exercise': exercise_name,
        'current': {'weight': current_weight, 'reps': current_reps, 'sets': current_sets},
        'previous': {'weight': prev_weight, 'reps': prev_reps, 'sets': prev_sets, 'date': previous['date']},
        'percent_change': percent_change,
        'is_improvement': percent_change > 0,
        'is_pr': is_pr
    }

def classify_and_parse(user_input):
    """Classify intent AND parse workout data OR chart request"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """You are a workout assistant that classifies user intent and parses workout data.

CONTEXT AWARENESS:
- User may be logging multiple sets of the same exercise
- If user doesn't specify exercise name, assume continuing current exercise

CRITICAL: Only log workouts that were COMPLETED (past tense). Never infer or make up data.

Classify as:
- LOG_WORKOUT: User explicitly states they COMPLETED a workout (past tense)
  Examples: "I did 3 sets of bench", "225 for 8 reps", "just finished 5k run"
  
- ASK_QUESTION: User asking for recommendations or advice about FUTURE workouts
  Examples: "what should I bench?", "I want to do bench today", "give me my working sets"
  Keywords: "should I", "what to do", "recommend", "plan", "want to", "going to"

- WORKOUT_SUMMARY: User requesting summary/recap/review of COMPLETED workout
  This includes ANY request to see what they've logged or done
  Examples: 
  - "give me my workout summary"
  - "what did I do today?"
  - "show me my workout"
  - "recap my session"
  - "what exercises did I log?"
  - "tell me what I've done"
  - "how was my workout?"
  - "what did I accomplish?"
  - "review my training"
  - "show today's lifts"
  - "what did I bench today?"
  - "summarize my lifts"
  - ANY variation asking to see/review/summarize completed exercises
  Keywords: "what did I", "show me", "summary", "recap", "review", "tell me what", "accomplished"
  
- CHART_REQUEST: User requesting visual progress charts/graphs
  Examples: "show me a chart", "graph my progress", "plot my bench"
  Keywords: "chart", "graph", "plot", "progress over time"

WORKOUT SUMMARY vs ASK_QUESTION:
- "What did I do?" → WORKOUT_SUMMARY (reviewing past)
- "What should I do?" → ASK_QUESTION (planning future)
- "Show me my workout" → WORKOUT_SUMMARY (reviewing)
- "Give me a workout" → ASK_QUESTION (requesting plan)

WORKOUT LOGGING RULES:
1. ONLY LOG_WORKOUT if user states they COMPLETED/DID the workout
2. Past tense: "did", "completed", "finished", "just did"
3. If just numbers/weight → continuing current exercise

CONTEXT HANDLING:
- If no exercise name given but has weight/reps → return workout_data WITHOUT exercise field
- Backend fills in current_exercise from session

STRENGTH: {"exercise": "bench press", "reps": 12, "weight": 225, "unit": "lbs"}
CARDIO: {"exercise": "treadmill", "duration": 30, "notes": "incline 10"}
BODYWEIGHT: {"exercise": "push-ups", "sets": 4, "reps": 10}

Return JSON:
{
    "intent": "LOG_WORKOUT" | "ASK_QUESTION" | "WORKOUT_SUMMARY" | "CHART_REQUEST",
    "workout_data": [...],
    "chart_request": {"exercise": "...", "period": "..."},
    "summary_request": {"period": "today" | "week"}
}

EXAMPLES:

Input: "What did I do for bench today?"
Output: {"intent": "WORKOUT_SUMMARY", "summary_request": {"period": "today"}}

Input: "Tell me what I accomplished"
Output: {"intent": "WORKOUT_SUMMARY", "summary_request": {"period": "today"}}

Input: "Review my training session"
Output: {"intent": "WORKOUT_SUMMARY", "summary_request": {"period": "today"}}

Input: "Show today's lifts"
Output: {"intent": "WORKOUT_SUMMARY", "summary_request": {"period": "today"}}

Input: "What should I bench?" 
Output: {"intent": "ASK_QUESTION"}  ← Future planning, not summary

Input: "I did bench press 225 for 5"
Output: {"intent": "LOG_WORKOUT", "workout_data": [{"exercise": "bench press", "reps": 5, "weight": 225, "unit": "lbs"}]}"""
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

def save_workout(user_id, exercises_data, session_id=None):
    """Save workout and exercises to database, return workout_id and exercise details"""
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            "INSERT INTO workouts (user_id, date, notes) VALUES (%s, %s, %s) RETURNING id",
            (user_id, datetime.now().date(), "")
        )
        workout_id = cur.fetchone()[0]

        logged_exercises = []
        for exercise in exercises_data:
            if not exercise.get('exercise'):
                continue

            cur.execute("""
                INSERT INTO exercises
                (workout_id, exercise_name, sets, reps, weight, unit, duration, distance, notes, workout_session_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                exercise.get('notes'),
                session_id
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
        import traceback
        traceback.print_exc()
        return None, []

    finally:
        cur.close()
        conn.close()

def generate_chart_data(user_id, exercise_name, days_back=30):
    """Get workout data formatted for charts with dual metrics (max weight and total volume)"""
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
    chart_data.sort(key=lambda x: x['date'])  # Sort chronologically (oldest to newest)

    # Create dual metric series for easy charting
    max_weight_series = [{'date': d['date'], 'value': d['max_weight']} for d in chart_data]
    total_volume_series = [{'date': d['date'], 'value': d['total_volume']} for d in chart_data]

    return {
        'exercise': exercise_name,
        'data_points': chart_data,  # Complete data with all metrics
        'chart_type': 'line',
        'metrics': {
            'max_weight': {
                'label': 'Max Weight (lbs)',
                'data': max_weight_series
            },
            'total_volume': {
                'label': 'Total Volume (lbs)',
                'data': total_volume_series
            }
        }
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
    """Main chat endpoint - handles both logging and questions with conversation memory"""
    try:
        data = request.json
        user_message = data.get('message', '')
        user_id = data.get('user_id', 1)
        session_id = data.get('session_id', None)  # Optional workout session ID
        current_exercise = data.get('current_exercise', None)  # Optional current exercise

        if not user_message:
            return jsonify({"error": "No message provided"}), 400

        # === STEP 1: Save user's message to conversation history ===
        save_message(user_id, 'user', user_message, session_id)

        # === STEP 2: Classify intent ===
        result = classify_and_parse(user_message)
        intent = result['intent']

        # === STEP 3: Handle different intents ===
        if intent == 'LOG_WORKOUT':
            parsed = result['workout_data']

            if not parsed or len(parsed) == 0:
                error_msg = "Didn't quite catch that, bro. Try again?"
                save_message(user_id, 'assistant', error_msg, session_id)
                return jsonify({
                    "type": "error",
                    "message": error_msg
                })

            # Get or create workout session if not provided
            if not session_id:
                workout_session = get_active_workout_session(user_id)
                if workout_session:
                    session_id = workout_session['session_id']
                else:
                    # Start new session with first exercise
                    exercise_name = parsed[0].get('exercise') if parsed else None
                    session_id = start_workout_session(user_id, exercise_name)

            # Update current exercise in session
            if current_exercise or (parsed and parsed[0].get('exercise')):
                exercise_name = current_exercise or parsed[0].get('exercise')
                update_session_exercise(session_id, exercise_name)

            # Fill in missing exercise names from session context
            for exercise_data in parsed:
                if not exercise_data.get('exercise') and exercise_name:
                    exercise_data['exercise'] = exercise_name


            # Compare performance before saving
            performance = compare_performance(user_id, parsed)

            # Save workout - returns workout_id AND logged exercises
            workout_id, logged_exercises = save_workout(user_id, parsed, session_id)

            if not workout_id:
                error_msg = "Had trouble saving that. Try again?"
                save_message(user_id, 'assistant', error_msg, session_id)
                return jsonify({
                    "type": "error",
                    "message": error_msg
                })

            # Get celebration (with performance context!)
            celebration = get_celebration_response(parsed, performance)

            # Add Arnold quote for PRs
            arnold = ""
            if performance and performance.get('is_pr'):
                arnold = f"\n\n💪 Arnold says: \"{random.choice(ARNOLD_QUOTES)}\""

            final_message = celebration + arnold

            # Save assistant response
            save_message(user_id, 'assistant', final_message, session_id)

            return jsonify({
                "type": "workout_logged",
                "message": final_message,
                "workout_id": workout_id,
                "logged_sets": logged_exercises,
                "performance": performance,
                "session_id": session_id
            })


        elif intent == 'WORKOUT_SUMMARY':
            # Get summary request details
            summary_req = result.get('summary_request', {})
            period = summary_req.get('period', 'today')
            
            # Determine days to look back
            if period == 'today':
                days_back = 1
            elif period == 'week':
                days_back = 7
            else:
                days_back = 1
            
            # Get workout data from database
            conn = get_db_connection()
            cur = conn.cursor()
            
            try:
                cur.execute("""
                    SELECT e.exercise_name, e.sets, e.reps, e.weight, e.unit,
                           e.duration, e.distance, e.notes, e.created_at
                    FROM exercises e
                    JOIN workouts w ON e.workout_id = w.id
                    WHERE w.user_id = %s
                      AND w.date >= CURRENT_DATE - INTERVAL '%s days'
                    ORDER BY e.created_at ASC
                """, (user_id, days_back))
                
                exercises = cur.fetchall()
                
                if not exercises:
                    msg = f"No workouts logged in the past {period}. Let's get after it! 💪"
                    save_message(user_id, 'assistant', msg, session_id)
                    return jsonify({
                        "type": "answer",
                        "message": msg
                    })
                
                # Format the summary
                summary_lines = [f"**Workout Summary - {period.title()}:**\n"]
                
                for ex in exercises:
                    exercise_name, sets, reps, weight, unit, duration, distance, notes, created = ex
                    
                    if weight and reps:  # Strength exercise
                        if sets:
                            summary_lines.append(f"• {exercise_name}: {sets}x{reps} @ {weight} {unit}")
                        else:
                            summary_lines.append(f"• {exercise_name}: {reps} reps @ {weight} {unit}")
                    elif duration:  # Cardio with duration
                        line = f"• {exercise_name}: {duration} min"
                        if distance:
                            line += f", {distance} km"
                        if notes:
                            line += f" ({notes})"
                        summary_lines.append(line)
                    elif distance:  # Cardio with distance
                        line = f"• {exercise_name}: {distance} km"
                        if notes:
                            line += f" ({notes})"
                        summary_lines.append(line)
                    elif reps:  # Bodyweight
                        if sets:
                            summary_lines.append(f"• {exercise_name}: {sets}x{reps}")
                        else:
                            summary_lines.append(f"• {exercise_name}: {reps} reps")
                
                summary = "\n".join(summary_lines)
                summary += "\n\nKeep crushing it, bro! 💪"
                
                save_message(user_id, 'assistant', summary, session_id)
                return jsonify({
                    "type": "answer",
                    "message": summary
                })
                
            finally:
                cur.close()
                conn.close()


        elif intent == 'WORKOUT_SUMMARY':
            # Get summary request details
            summary_req = result.get('summary_request', {})
            period = summary_req.get('period', 'today')
            
            # Determine days to look back
            if period == 'today':
                days_back = 1
            elif period == 'week':
                days_back = 7
            else:
                days_back = 1
            
            # Get workout data from database
            conn = get_db_connection()
            cur = conn.cursor()
            
            try:
                cur.execute("""
                    SELECT e.exercise_name, e.sets, e.reps, e.weight, e.unit,
                           e.duration, e.distance, e.notes, e.created_at
                    FROM exercises e
                    JOIN workouts w ON e.workout_id = w.id
                    WHERE w.user_id = %s
                      AND w.date >= CURRENT_DATE - INTERVAL '%s days'
                    ORDER BY e.created_at ASC
                """, (user_id, days_back))
                
                exercises = cur.fetchall()
                
                if not exercises:
                    msg = f"No workouts logged in the past {period}. Let's get after it! 💪"
                    save_message(user_id, 'assistant', msg, session_id)
                    return jsonify({
                        "type": "answer",
                        "message": msg
                    })
                
                # Format the summary
                summary_lines = [f"**Workout Summary - {period.title()}:**\n"]
                
                for ex in exercises:
                    exercise_name, sets, reps, weight, unit, duration, distance, notes, created = ex
                    
                    if weight and reps:  # Strength exercise
                        if sets:
                            summary_lines.append(f"• {exercise_name}: {sets}x{reps} @ {weight} {unit}")
                        else:
                            summary_lines.append(f"• {exercise_name}: {reps} reps @ {weight} {unit}")
                    elif duration:  # Cardio with duration
                        line = f"• {exercise_name}: {duration} min"
                        if distance:
                            line += f", {distance} km"
                        if notes:
                            line += f" ({notes})"
                        summary_lines.append(line)
                    elif distance:  # Cardio with distance
                        line = f"• {exercise_name}: {distance} km"
                        if notes:
                            line += f" ({notes})"
                        summary_lines.append(line)
                    elif reps:  # Bodyweight
                        if sets:
                            summary_lines.append(f"• {exercise_name}: {sets}x{reps}")
                        else:
                            summary_lines.append(f"• {exercise_name}: {reps} reps")
                
                summary = "\n".join(summary_lines)
                summary += "\n\nKeep crushing it, bro! 💪"
                
                save_message(user_id, 'assistant', summary, session_id)
                return jsonify({
                    "type": "answer",
                    "message": summary
                })
                
            finally:
                cur.close()
                conn.close()

        elif intent == 'CHART_REQUEST':
            chart_req = result.get('chart_request', {})
            exercise = chart_req.get('exercise')
            period = chart_req.get('period', 'month')

            if not exercise:
                msg = "Which exercise do you want to see a chart for, bro?"
                save_message(user_id, 'assistant', msg, session_id)
                return jsonify({
                    "type": "answer",
                    "message": msg
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
                msg = f"Here's your {exercise} progress over the last {period}! 💪"
                save_message(user_id, 'assistant', msg, session_id)
                return jsonify({
                    "type": "chart",
                    "message": msg,
                    "chart_data": chart_data
                })
            else:
                msg = f"Bro, I don't have any data for {exercise} yet. Log some workouts first! 💪"
                save_message(user_id, 'assistant', msg, session_id)
                return jsonify({
                    "type": "answer",
                    "message": msg
                })

        else:  # ASK_QUESTION - This is where conversation memory and safety logic apply
            # === STEP 4: Retrieve conversation history ===
            conversation_history = get_conversation_history(user_id, session_id, limit=20)

            # === STEP 5: Build messages array with system prompt ===
            messages = [{"role": "system", "content": SAFE_SYSTEM_PROMPT}]

            # === STEP 6: Check if this looks like a weight recommendation request ===
            weight_keywords = ['what should', 'recommend', 'next set', 'final set', 'weight',
                             'how much', 'what weight', 'heavier', 'lighter', 'increase', 'decrease']
            is_weight_question = any(keyword in user_message.lower() for keyword in weight_keywords)

            if is_weight_question:
                # Try to determine exercise from context
                exercise_name = current_exercise

                # If no current exercise, try to extract from message or recent history
                if not exercise_name and conversation_history:
                    # Simple extraction: look for common exercise names in recent messages
                    for msg in reversed(conversation_history[-5:]):  # Check last 5 messages
                        content_lower = msg['content'].lower()
                        for ex in ['bench', 'squat', 'deadlift', 'press', 'row', 'curl', 'pullup', 'pull up']:
                            if ex in content_lower:
                                exercise_name = ex
                                break
                        if exercise_name:
                            break

                # Get recent sets and analyze performance
                if exercise_name and session_id:
                    recent_sets = get_recent_sets(user_id, session_id, exercise_name, limit=10)

                    if len(recent_sets) >= 1:
                        # Analyze performance
                        analysis = analyze_set_performance(recent_sets)
                        constraints = get_recommendation_constraints(analysis)

                        if constraints:
                            # Inject safety constraints into system prompt
                            enhanced_prompt = f"{SAFE_SYSTEM_PROMPT}\n\n{constraints}\n\nRecent sets for {exercise_name}: {recent_sets}"
                            messages[0] = {"role": "system", "content": enhanced_prompt}

            # === STEP 7: Add conversation history ===
            messages.extend(conversation_history)

            # === STEP 8: Add current user message ===
            messages.append({"role": "user", "content": user_message})

            # === STEP 9: Call OpenAI with LOWER temperature for safety ===
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.2  # Lower temperature = more consistent, safer responses
            )

            assistant_message = response.choices[0].message.content

            # === STEP 10: Save assistant's response ===
            save_message(user_id, 'assistant', assistant_message, session_id)

            return jsonify({
                "type": "answer",
                "message": assistant_message,
                "session_id": session_id
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
    print("  GET    /health - Health check")
    print("\n" + "=" * 60 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5001)