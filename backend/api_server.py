from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
import psycopg2
import json
import random
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

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
        dbname=os.getenv('DB_NAME', 'workout_tracker'),
        user=os.getenv('DB_USER', 'noah'),
        password=os.getenv('DB_PASSWORD', ''),
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', '5432')
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
        cur.execute("""
            SELECT MAX(w.date) as last_leg_day,
                   CURRENT_DATE - MAX(w.date) as days_since
            FROM exercises e
            JOIN workouts w ON e.workout_id = w.id
            WHERE (e.exercise_name ILIKE '%squat%' 
               OR e.exercise_name ILIKE '%leg%'
               OR e.exercise_name ILIKE '%deadlift%')
              AND w.user_id = %s
        """, (user_id,))
        
        result = cur.fetchone()
        if result and result[1]:
            return result[1]
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

def classify_user_intent(user_input):
    """Determine if user is logging a workout or asking a question"""
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": """Classify the user's intent as either 'LOG_WORKOUT' or 'ASK_QUESTION'.
                    
                    LOG_WORKOUT examples:
                    - "did 3x12 bench at 225"
                    - "just finished squats 315 for 5"
                    - "ran 5k in 30 minutes"
                    
                    ASK_QUESTION examples:
                    - "what should I bench today?"
                    - "how much did I squat last week?"
                    - "when was my last leg day?"
                    
                    Return ONLY a JSON object with:
                    {
                        "intent": "LOG_WORKOUT" or "ASK_QUESTION",
                        "exercise": "name of exercise if mentioned, else null",
                        "confidence": 0.0 to 1.0
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
        return {"intent": "ASK_QUESTION", "exercise": None, "confidence": 0.5}

def parse_workout(description):
    """Parse natural language workout into structured data"""
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": """You are a workout parser. Extract structured data from workout descriptions.
                    Return ONLY valid JSON with these fields:
                    - exercise: name of the exercise (REQUIRED)
                    - sets: number of sets
                    - reps: number of reps
                    - weight: weight used
                    - unit: "lbs" or "kg" (default to lbs)
                    - duration: duration in minutes
                    - distance: distance covered
                    - notes: any additional info
                    
                    Return as a single object or array of objects if multiple exercises."""
                },
                {
                    "role": "user",
                    "content": description
                }
            ],
            temperature=0
        )
        
        result = response.choices[0].message.content
        parsed = json.loads(result)
        
        if isinstance(parsed, dict):
            return [parsed]
        return parsed
    
    except Exception as e:
        return None

def save_workout(user_id, exercises_data):
    """Save workout and exercises to database"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute(
            "INSERT INTO workouts (user_id, date, notes) VALUES (%s, %s, %s) RETURNING id",
            (user_id, datetime.now().date(), "")
        )
        workout_id = cur.fetchone()[0]
        
        for exercise in exercises_data:
            if not exercise.get('exercise'):
                continue
                
            cur.execute("""
                INSERT INTO exercises 
                (workout_id, exercise_name, sets, reps, weight, unit, duration, distance, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
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
        
        conn.commit()
        return workout_id
    
    except Exception as e:
        conn.rollback()
        return None
    
    finally:
        cur.close()
        conn.close()

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
            model="gpt-4",
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
    intent = classify_user_intent(question)
    exercise = intent.get('exercise')
    
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
            model="gpt-4",
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
        user_id = data.get('user_id', 1)  # Default to user 1 for now
        
        if not user_message:
            return jsonify({"error": "No message provided"}), 400
        
        # Classify intent
        intent_data = classify_user_intent(user_message)
        intent = intent_data['intent']
        
        if intent == 'LOG_WORKOUT':
            # Parse workout
            parsed = parse_workout(user_message)
            
            if not parsed:
                return jsonify({
                    "type": "error",
                    "message": "Didn't quite catch that, bro. Try again?"
                })
            
            # Compare performance before saving
            performance = compare_performance(user_id, parsed)
            
            # Save workout
            workout_id = save_workout(user_id, parsed)
            
            if not workout_id:
                return jsonify({
                    "type": "error",
                    "message": "Had trouble saving that. Try again?"
                })
            
            # Get celebration
            celebration = get_celebration_response(parsed, performance)
            
            # Add Arnold quote for PRs
            arnold = ""
            if performance and performance.get('is_pr'):
                arnold = f"\n\n💪 Arnold says: \"{random.choice(ARNOLD_QUOTES)}\""
            
            return jsonify({
                "type": "workout_logged",
                "message": celebration + arnold,
                "workout_id": workout_id,
                "performance": performance
            })
        
        else:  # ASK_QUESTION
            answer = answer_workout_question(user_id, user_message)
            
            return jsonify({
                "type": "answer",
                "message": answer
            })
    
    except Exception as e:
        return jsonify({
            "type": "error",
            "message": f"Something went wrong, bro! {str(e)}"
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
    print("  POST /chat - Main chat endpoint")
    print("  GET  /history - Get workout history")
    print("  GET  /health - Health check")
    print("\n" + "=" * 60 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5001)
