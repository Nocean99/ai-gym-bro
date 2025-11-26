"""
Test script for conversation memory and safety logic
Run this after applying the database migration
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from conversation_memory import save_message, get_conversation_history, get_conversation_summary
from workout_logic import analyze_set_performance, get_recommendation_constraints


def test_conversation_memory():
    """Test conversation memory functions"""
    print("\n" + "="*60)
    print("TEST 1: Conversation Memory")
    print("="*60)

    user_id = 999  # Test user

    # Save some messages
    print("\n1. Saving test messages...")
    save_message(user_id, 'user', 'I want to do bench press today')
    save_message(user_id, 'assistant', 'Great! What weight are you thinking?')
    save_message(user_id, 'user', 'Maybe 135 lbs')
    save_message(user_id, 'assistant', 'Solid starting point! How many sets?')

    # Retrieve history
    print("2. Retrieving conversation history...")
    history = get_conversation_history(user_id, limit=10)

    print(f"3. Retrieved {len(history)} messages:")
    for msg in history:
        print(f"   {msg['role']}: {msg['content'][:50]}...")

    # Get summary
    print("\n4. Getting conversation summary...")
    summary = get_conversation_summary(user_id)
    print(f"   Total messages: {summary['message_count']}")
    print(f"   First message: {summary['first_message']}")
    print(f"   Last message: {summary['last_message']}")

    # Verify
    if len(history) >= 4:
        print("\n✅ TEST 1 PASSED: Conversation memory working!")
        return True
    else:
        print("\n❌ TEST 1 FAILED: Not enough messages retrieved")
        return False


def test_fatigue_detection():
    """Test workout safety logic"""
    print("\n" + "="*60)
    print("TEST 2: Fatigue Detection & Safety Logic")
    print("="*60)

    # Test Case 1: Severe Fatigue (the original bug)
    print("\n--- Test Case 1: Severe Fatigue (5 reps → 3 reps) ---")
    sets_fatigued = [
        {'weight': 225, 'reps': 5},
        {'weight': 225, 'reps': 3}
    ]

    analysis = analyze_set_performance(sets_fatigued)
    print(f"State: {analysis['state']}")
    print(f"Message: {analysis['message']}")
    print(f"Recommendation: {analysis['recommendation_type']}")
    if 'suggested_weight' in analysis:
        print(f"Suggested weight: {analysis['suggested_weight']} lbs")

    constraints = get_recommendation_constraints(analysis)
    if constraints:
        print("\nSafety Constraints Generated:")
        print(constraints[:200] + "...")

    # Verify
    test1_passed = (
        analysis['state'] == 'fatigued' and
        analysis['is_dangerous'] == True and
        analysis['suggested_weight'] < 225
    )

    if test1_passed:
        print("\n✅ Test Case 1 PASSED: Correctly detected severe fatigue")
    else:
        print("\n❌ Test Case 1 FAILED: Did not detect fatigue properly")

    # Test Case 2: Stable Performance
    print("\n--- Test Case 2: Stable Performance (5 reps → 5 reps) ---")
    sets_stable = [
        {'weight': 225, 'reps': 5},
        {'weight': 225, 'reps': 5}
    ]

    analysis = analyze_set_performance(sets_stable)
    print(f"State: {analysis['state']}")
    print(f"Message: {analysis['message']}")
    print(f"Recommendation: {analysis['recommendation_type']}")

    test2_passed = analysis['state'] == 'stable'

    if test2_passed:
        print("\n✅ Test Case 2 PASSED: Correctly identified stable performance")
    else:
        print("\n❌ Test Case 2 FAILED: Misidentified performance state")

    # Test Case 3: Progressive Overload
    print("\n--- Test Case 3: Progressive Overload (225 lbs → 230 lbs) ---")
    sets_progressing = [
        {'weight': 225, 'reps': 5},
        {'weight': 230, 'reps': 4}
    ]

    analysis = analyze_set_performance(sets_progressing)
    print(f"State: {analysis['state']}")
    print(f"Message: {analysis['message']}")

    test3_passed = analysis['state'] in ['progressing', 'weight_too_heavy']

    if test3_passed:
        print("\n✅ Test Case 3 PASSED: Handled weight progression")
    else:
        print("\n❌ Test Case 3 FAILED: Did not handle progression properly")

    # Test Case 4: Weight Too Heavy
    print("\n--- Test Case 4: Weight Too Heavy (225×10 reps → 275×3 reps) ---")
    sets_too_heavy = [
        {'weight': 225, 'reps': 10},
        {'weight': 275, 'reps': 3}  # Only 30% of previous reps
    ]

    analysis = analyze_set_performance(sets_too_heavy)
    print(f"State: {analysis['state']}")
    print(f"Message: {analysis['message']}")

    test4_passed = analysis['state'] == 'weight_too_heavy' and analysis['is_dangerous'] == True

    if test4_passed:
        print("\n✅ Test Case 4 PASSED: Detected excessive weight jump")
    else:
        print("\n❌ Test Case 4 FAILED: Did not detect dangerous weight increase")

    # Overall
    all_passed = test1_passed and test2_passed and test3_passed and test4_passed

    if all_passed:
        print("\n" + "="*60)
        print("✅ TEST 2 PASSED: All fatigue detection tests passed!")
        print("="*60)
        return True
    else:
        print("\n" + "="*60)
        print("❌ TEST 2 FAILED: Some tests failed")
        print("="*60)
        return False


def test_recommendation_constraints():
    """Test that constraints are properly formatted"""
    print("\n" + "="*60)
    print("TEST 3: Constraint Generation")
    print("="*60)

    sets = [
        {'weight': 225, 'reps': 5},
        {'weight': 225, 'reps': 2}  # 60% decline
    ]

    analysis = analyze_set_performance(sets)
    constraints = get_recommendation_constraints(analysis)

    print("\nGenerated Constraints:")
    print(constraints)

    # Check that constraints contain key safety phrases
    has_mandatory = 'MANDATORY' in constraints
    has_forbidden = 'FORBIDDEN' in constraints
    has_weight = 'lbs' in constraints.lower() or 'weight' in constraints.lower()

    if has_mandatory and has_forbidden and has_weight:
        print("\n✅ TEST 3 PASSED: Constraints properly formatted")
        return True
    else:
        print("\n❌ TEST 3 FAILED: Constraints missing key elements")
        return False


if __name__ == "__main__":
    print("\n" + "="*60)
    print("AI GYM BRO - IMPLEMENTATION TEST SUITE")
    print("="*60)
    print("\nTesting conversation memory and safety logic...")
    print("Make sure you've run the database migration first!")
    print("="*60)

    try:
        # Run tests
        test1_result = test_conversation_memory()
        test2_result = test_fatigue_detection()
        test3_result = test_recommendation_constraints()

        # Summary
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        print(f"Conversation Memory: {'✅ PASSED' if test1_result else '❌ FAILED'}")
        print(f"Fatigue Detection:   {'✅ PASSED' if test2_result else '❌ FAILED'}")
        print(f"Constraint Format:   {'✅ PASSED' if test3_result else '❌ FAILED'}")

        all_passed = test1_result and test2_result and test3_result

        if all_passed:
            print("\n🎉 ALL TESTS PASSED! Implementation is working correctly.")
        else:
            print("\n⚠️  SOME TESTS FAILED. Check the output above for details.")

        print("="*60 + "\n")

    except Exception as e:
        print("\n❌ ERROR running tests:")
        print(f"   {type(e).__name__}: {str(e)}")
        print("\nMake sure:")
        print("1. Database migration has been applied")
        print("2. Database connection settings are correct in .env")
        print("3. PostgreSQL is running")
        import traceback
        traceback.print_exc()
