from openai import OpenAI
import psycopg2
import json
import random
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

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
    "If it bleeds, we can kill it... wait, wrong movie. But if it's heavy, we can lift it!",
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
    "Every day is chest day... except when it's leg day!",
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
            # Specific exercise history
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
            # All recent workouts
            cur.execute("""
                SELECT w.date, e.exercise_name, e.sets, e.reps, e.weight, e.unit, e.notes
                FROM exercises e
                JOIN workouts w ON e.workout_id = w.id
                WHERE w.user_id = %s
                  AND w.date >= %s
                ORDER BY w.date DESC
            """, (user_id, datetime.now().date() - timedelta(days=days_back)))
        
        results = cur.fetchall()
        
        # Format for AI
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
            return result[1]  # days since leg day
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
    
    # Get previous workout for this exercise
    history = get_workout_data(user_id, exercise_name, days_back=60)
    
    if len(history) < 2:  # Need at least previous + current
        return None
    
    # Get the second most recent (most recent will be current workout after save)
    previous = history[0]
    prev_weight = previous.get('weight')
    prev_reps = previous.get('reps')
    prev_sets = previous.get('sets')
    
    if not prev_weight or not prev_reps:
        return None
    
    # Calculate total volume
    current_volume = current_weight * current_reps * (current_sets or 1)
    prev_volume = prev_weight * prev_reps * (prev_sets or 1)
    
    # Calculate percentage change
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
                    - "am I getting stronger on bench?"
                    - "what weight should I use for deadlifts?"
                    
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
        print(f"Error classifying intent: {e}")
        return {"intent": "ASK_QUESTION", "exercise": None, "confidence": 0.5}

def answer_workout_question(user_id, question):
    """Use AI to answer questions about workout history"""
    
    # First, determine what exercise they're asking about (if any)
    intent = classify_user_intent(question)
    exercise = intent.get('exercise')
    
    # Check for leg day skipping
    days_since_legs = check_leg_day_skipping(user_id)
    leg_day_warning = ""
    if days_since_legs and days_since_legs > 10:
        leg_day_warning = f"\n\n⚠️ BRO WARNING: It's been {days_since_legs} days since you trained legs! You trying to look like Johnny Bravo? 🦵 Friends don't let friends skip leg day!"
    
    # Get relevant workout data
    if exercise:
        workout_data = get_workout_data(user_id, exercise_name=exercise, days_back=90)
    else:
        workout_data = get_workout_data(user_id, days_back=30)
    
    if not workout_data:
        return "Bro, I don't have any workout data to work with yet! Let's log some workouts first! 💪"
    
    # Random Arnold quote for motivation (20% chance)
    arnold_quote = ""
    if random.random() < 0.2:
        arnold_quote = f"\n\n💪 Arnold says: \"{random.choice(ARNOLD_QUOTES)}\""
    
    # Format workout data for context
    data_summary = json.dumps(workout_data, indent=2)
    
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": """You are an expert gym bro personal trainer with access to the user's complete workout history.
                    
                    Your job is to:
                    1. Answer questions about their workout history with SPECIFIC DATA and NUMBERS
                    2. Provide personalized weight/rep recommendations using progressive overload
                    3. Track their progress and celebrate improvements
                    4. CALL OUT when they're lifting less than before - be honest but motivating
                    5. Use gym bro language, memes, and enthusiasm
                    6. Give actionable, specific advice with reasoning
                    
                    When recommending weights:
                    - Use progressive overload (2.5-10% increase typically)
                    - Consider their recent performance
                    - Be conservative if they haven't done the exercise in 2+ weeks
                    - If they haven't done it in 4+ weeks, recommend starting 10-15% lighter
                    - Explain your reasoning with their actual numbers
                    
                    When analyzing performance:
                    - Calculate percentage changes in volume/weight
                    - If they lifted LESS than last time, call it out: "Bro, that's X% less than last week when you hit [specific numbers]!"
                    - If they're improving, celebrate it: "That's X% more volume than last time! Gains city!"
                    - Compare to their best lifts
                    
                    Personality:
                    - Use phrases: "bro", "let's go", "crushing it", "beast mode", "light weight", "still your set"
                    - Be enthusiastic but HONEST about their performance
                    - Tough love when needed, celebration when deserved
                    
                    Keep responses 3-5 sentences, packed with specific numbers from their data."""
                },
                {
                    "role": "user",
                    "content": f"Question: {question}\n\nMy workout history:\n{data_summary}"
                }
            ],
            temperature=0.7
        )
        
        return response.choices[0].message.content + arnold_quote + leg_day_warning
    
    except Exception as e:
        return f"Had trouble thinking through that one, bro! But I know you got this! 💪"

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
                    - exercise: name of the exercise (REQUIRED - infer from context if possible)
                    - sets: number of sets (null if not applicable)
                    - reps: number of reps (null if not applicable)
                    - weight: weight used (null if not applicable)
                    - unit: "lbs" or "kg" (default to lbs if not specified)
                    - duration: duration in minutes (null if not applicable)
                    - distance: distance covered (null if not applicable)
                    - notes: any additional info like "PR" or special conditions
                    
                    Common exercises: bench press, squat, deadlift, overhead press, barbell row, pull-ups, etc.
                    
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
        
        # Ensure it's always a list
        if isinstance(parsed, dict):
            return [parsed]
        return parsed
    
    except Exception as e:
        print(f"Error parsing workout: {e}")
        return None

def save_workout(user_id, exercises_data, notes=""):
    """Save workout and exercises to database

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
            # Create new workout entry
            cur.execute(
                "INSERT INTO workouts (user_id, date, notes) VALUES (%s, %s, %s) RETURNING id",
                (user_id, datetime.now().date(), notes)
            )
            workout_id = cur.fetchone()[0]
            print(f"✨ Created new workout session #{workout_id}")
        
        # Save each exercise
        for exercise in exercises_data:
            # Skip if no exercise name
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
        print(f"Error saving workout: {e}")
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
        
        # Build context for AI
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
        
        # Random gym meme (30% chance)
        gym_meme = ""
        if random.random() < 0.3:
            gym_meme = f" {random.choice(GYM_MEMES)}"
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": """You're a hype gym bro who gives HONEST feedback about workout performance.
                    
                    Rules:
                    - If it's a PR, GO CRAZY with celebration! 🎉🏆
                    - If they improved (even slightly), hype them up!
                    - If they did WORSE than last time (>10% less volume), CALL IT OUT but stay motivating:
                      "Bro, that's 15% less than last week! What happened? Bad sleep? Let's get it back next time!"
                    - If they're maintaining, acknowledge the consistency
                    - Use gym bro language and be real with them
                    - Keep it SHORT (2-3 sentences max)
                    - Sometimes reference the specific percentage change if provided
                    
                    Be authentic - celebrate wins, acknowledge struggles, but always end motivating."""
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

def main():
    """Main app loop - AI-first coaching chatbot"""
    print("=" * 60)
    print("🏋️  AI GYM BRO - YOUR PERSONAL TRAINING COACH")
    print("=" * 60)
    print("\nI'm your AI gym bro who remembers EVERYTHING about your workouts!")
    print("\nYou can:")
    print("  📝 Log workouts: 'did 3x12 bench at 225'")
    print("  💬 Ask anything: 'what should I bench today?'")
    print("  📊 Get insights: 'how much did I squat last week?'")
    print("  🎯 Get recommendations: 'I haven't done deadlifts in a while, what weight?'")
    print("\nType 'quit' to exit")
    print("=" * 60 + "\n")
    
    user_id = 1  # Hardcoded for now
    
    while True:
        user_input = input("You: ").strip()
        
        if not user_input:
            continue
        
        if user_input.lower() in ['quit', 'exit', 'bye']:
            print("\nKeep crushing it, bro! See you at the gym! 💪\n")
            break
        
        # Classify user intent
        intent_data = classify_user_intent(user_input)
        intent = intent_data['intent']
        
        if intent == 'LOG_WORKOUT':
            # Parse and save the workout
            print("\n💾 Logging your workout...")
            parsed = parse_workout(user_input)
            
            if not parsed:
                print("AI Gym Bro: Didn't quite catch that, bro. Try again?\n")
                continue
            
            # Check performance vs last time BEFORE saving
            performance = compare_performance(user_id, parsed)
            
            workout_id = save_workout(user_id, parsed)
            
            if workout_id:
                celebration = get_celebration_response(parsed, performance)
                print(f"\n🎉 {celebration}")
                print(f"✅ Workout #{workout_id} saved!\n")
                
                # Add Arnold quote occasionally for big PRs
                if performance and performance.get('is_pr'):
                    print(f"💪 Arnold says: \"{random.choice(ARNOLD_QUOTES)}\"\n")
            else:
                print("AI Gym Bro: Had trouble saving that. Try again?\n")
        
        else:  # ASK_QUESTION
            # Use AI to answer based on workout history
            print("\n🤔 Let me check your history...")
            answer = answer_workout_question(user_id, user_input)
            print(f"\n💪 AI Gym Bro: {answer}\n")

if __name__ == "__main__":
    main()
