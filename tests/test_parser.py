import os

from openai import OpenAI
import json

# Read the API key from the environment; never hard-code it
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

# Test workout descriptions (how real people would describe workouts)
test_workouts = [
    "3x12 bench at 225",
    "Did squats today, worked up to 315 for 5",
    "30 min treadmill, incline 10, speed 3 mph",
    "Deadlifts: 135x10, 225x5, 315x3, 405x1",
    "Overhead press 5 sets of 5 at 135",
    "Did 4 sets of 8 pull-ups",
    "Leg press 3x15 at 400 lbs",
    "Ran 5k in 28 minutes",
    "Bicep curls 3x12 with 30 lb dumbbells",
    "Hit 225 bench for a new PR today! Got 8 reps"
]

def parse_workout(description):
    """
    Send workout description to OpenAI and get structured data back
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": """You are a workout parser. Extract structured data from workout descriptions.
                    Return ONLY valid JSON with these fields:
                    - exercise: name of the exercise
                    - sets: number of sets (null if not applicable)
                    - reps: number of reps (null if not applicable)
                    - weight: weight used (null if not applicable)
                    - unit: "lbs" or "kg" (null if not applicable)
                    - duration: duration in minutes (null if not applicable)
                    - distance: distance covered (null if not applicable)
                    - notes: any additional info like "PR" or special conditions
                    
                    If multiple sets with different weights, create an array of set objects."""
                },
                {
                    "role": "user",
                    "content": description
                }
            ],
            temperature=0
        )
        
        result = response.choices[0].message.content
        return json.loads(result)
    
    except Exception as e:
        return {"error": str(e)}

# Test each workout description
print("=" * 60)
print("WORKOUT NLP PARSING TEST")
print("=" * 60)
print()

for i, workout in enumerate(test_workouts, 1):
    print(f"Test {i}: {workout}")
    print("-" * 60)
    
    result = parse_workout(workout)
    print(json.dumps(result, indent=2))
    print()
    print("=" * 60)
    print()

print("\nTest complete! Review the results above to see if parsing is accurate.")
