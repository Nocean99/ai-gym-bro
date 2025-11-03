import requests
import json

# API base URL
BASE_URL = "http://localhost:5001"

def test_health():
    """Test health check endpoint"""
    print("\n" + "="*60)
    print("Testing Health Check...")
    print("="*60)
    
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

def test_log_workout():
    """Test logging a workout"""
    print("\n" + "="*60)
    print("Testing Workout Logging...")
    print("="*60)
    
    data = {
        "user_id": 1,
        "message": "did 3x12 bench at 225"
    }
    
    response = requests.post(f"{BASE_URL}/chat", json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

def test_ask_question():
    """Test asking a question"""
    print("\n" + "="*60)
    print("Testing Question Asking...")
    print("="*60)
    
    data = {
        "user_id": 1,
        "message": "what should I bench today?"
    }
    
    response = requests.post(f"{BASE_URL}/chat", json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

def test_get_history():
    """Test getting workout history"""
    print("\n" + "="*60)
    print("Testing Workout History...")
    print("="*60)
    
    response = requests.get(f"{BASE_URL}/history?user_id=1&days=30")
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Found {len(data['data'])} workout entries")
    
    # Show first 3 entries
    if data['data']:
        print("\nFirst 3 entries:")
        for entry in data['data'][:3]:
            print(f"  {entry['date']}: {entry['exercise']} - {entry['sets']}x{entry['reps']} @ {entry['weight']} {entry['unit']}")

if __name__ == "__main__":
    print("\n🏋️  AI GYM BRO API - TEST SUITE")
    print("="*60)
    print("\nMake sure the API server is running first!")
    print("Run: python3 api_server.py")
    print("\nPress Enter to continue...")
    input()
    
    try:
        # Run all tests
        test_health()
        test_log_workout()
        test_ask_question()
        test_get_history()
        
        print("\n" + "="*60)
        print("✅ All tests completed!")
        print("="*60 + "\n")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Could not connect to API server.")
        print("Make sure the API is running on http://localhost:5000")
        print("\nRun: python3 api_server.py")
    
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
