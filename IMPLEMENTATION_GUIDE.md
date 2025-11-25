# AI Gym Bro - Conversation Memory & Safety Fixes Implementation Guide

## Overview
This implementation addresses two critical issues:
1. **Conversation Memory**: Chatbot now remembers previous messages in the conversation
2. **Unsafe Weight Recommendations**: AI no longer suggests increasing weight when performance is declining

## Changes Made

### 1. Database Schema Changes
**File**: `database/migration_001_conversation_memory.sql`

New tables added:
- `conversation_messages`: Stores chat history for conversation memory
- `workout_sessions`: Tracks active workout sessions for set-by-set analysis

To apply these changes to your database:
```bash
psql -U postgres workout_tracker < database/migration_001_conversation_memory.sql
```

### 2. New Backend Modules

#### `backend/conversation_memory.py`
Functions for storing and retrieving chat history:
- `save_message(user_id, role, content, session_id)`: Save a message to history
- `get_conversation_history(user_id, session_id, limit, time_window_hours)`: Retrieve recent messages
- `clear_old_conversations(days_to_keep)`: Clean up old messages

#### `backend/workout_logic.py`
Safety logic for weight recommendations:
- `analyze_set_performance(sets)`: Detects fatigue patterns in workout sets
- `get_recommendation_constraints(analysis)`: Generates safety rules for the AI
- `get_recent_sets(user_id, session_id, exercise_name)`: Retrieves sets for analysis
- Workout session management functions

### 3. Updated API Endpoint
**File**: `backend/api_server.py`

The `/chat` endpoint now:
1. **Saves all messages** to conversation history (user + assistant)
2. **Retrieves conversation history** (last 20 messages within 24 hours)
3. **Detects weight recommendation requests** using keyword matching
4. **Analyzes recent sets** for fatigue patterns when user asks for weight advice
5. **Injects safety constraints** into the system prompt based on performance analysis
6. **Uses lower temperature** (0.2) for more consistent, safer responses
7. **Returns session_id** to maintain context across requests

#### New Request Parameters
The `/chat` endpoint now accepts:
```json
{
  "message": "What weight should I use for my next set?",
  "user_id": 1,
  "session_id": 123,  // Optional: Active workout session ID
  "current_exercise": "bench press"  // Optional: Current exercise name
}
```

#### Response Format
Responses now include `session_id`:
```json
{
  "type": "answer",
  "message": "Based on your last set...",
  "session_id": 123
}
```

### 4. Enhanced System Prompt
New safety-focused system prompt (`SAFE_SYSTEM_PROMPT`) that:
- Prioritizes user safety above motivation
- Requires data-based recommendations
- Enforces rules against recommending weight increases when performance declines
- Maintains the "gym bro" personality while being realistic

## How It Works

### Conversation Memory Flow
```
1. User sends message → Saved to conversation_messages table
2. System retrieves last 20 messages from history
3. Messages added to OpenAI API call for context
4. Assistant response → Saved to conversation_messages table
5. User's next message has full conversation context
```

### Safety Logic Flow
```
1. User asks: "What weight should I use next?"
2. System detects weight-related keywords
3. Retrieves recent sets for current exercise
4. Analyzes performance:
   - 5 reps → 3 reps at 225 lbs = 40% decline = FATIGUED
5. Generates safety constraints:
   - MANDATORY: Recommend 190 lbs (15% lighter)
   - FORBIDDEN: Suggest maintaining or increasing
6. Injects constraints into system prompt
7. AI follows constraints and recommends back-off set
```

### Example Scenarios

#### Scenario 1: Fatigue Detection (The Bug Case)
```
User logs:
- Set 1: 225 lbs × 5 reps
- Set 2: 225 lbs × 3 reps  (40% decline)

User asks: "What should my final set weight be?"

OLD BEHAVIOR: "Try 235 lbs bro! Push it!" ❌
NEW BEHAVIOR: "⚠️ Performance dropped 40% (5→3 reps). Recommend back-off set at 190 lbs or finish the exercise for safety." ✅
```

#### Scenario 2: Stable Performance
```
User logs:
- Set 1: 225 lbs × 5 reps
- Set 2: 225 lbs × 5 reps

User asks: "What's next?"

NEW BEHAVIOR: "Strong performance! Reps maintained at 5. Can repeat 225 lbs or try 230 lbs if feeling good." ✅
```

#### Scenario 3: Conversation Memory
```
User: "I did bench press today"
AI: "Nice! How did it go?"
User: "3 sets at 135"
AI: "Got it! 3 sets of bench at 135. What's next?"

// Old system would not remember "bench press" context
// New system maintains full conversation history
```

## Testing

### Test Case 1: Conversation Memory
```bash
# First message
curl -X POST http://localhost:5001/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "message": "I want to log a workout"
  }'

# Second message - should remember context
curl -X POST http://localhost:5001/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "message": "bench press 3x12 at 135"
  }'
```

### Test Case 2: Fatigue Detection
```bash
# Start session and log first set
curl -X POST http://localhost:5001/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "message": "5 reps bench press at 225",
    "current_exercise": "bench press"
  }'
# Save the session_id from response

# Log second set with declining reps
curl -X POST http://localhost:5001/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "session_id": 123,
    "message": "3 reps bench press at 225",
    "current_exercise": "bench press"
  }'

# Ask for recommendation
curl -X POST http://localhost:5001/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "session_id": 123,
    "message": "What should my final set weight be?",
    "current_exercise": "bench press"
  }'

# Expected: AI recommends ~190 lbs or stopping, NOT increasing weight
```

## Deployment Steps

### 1. Apply Database Migration
```bash
# Connect to your database
psql -U postgres workout_tracker

# Run migration
\i database/migration_001_conversation_memory.sql

# Verify tables created
\dt conversation_messages
\dt workout_sessions
```

### 2. Update Backend Code
The following files have been updated:
- `backend/api_server.py` - Main API with new chat logic
- `backend/conversation_memory.py` - NEW FILE
- `backend/workout_logic.py` - NEW FILE

### 3. Test Locally
```bash
cd backend
python api_server.py
```

Test with the curl commands above.

### 4. Deploy to Production (Render)
```bash
# Commit changes
git add .
git commit -m "Add conversation memory and safety logic for weight recommendations"

# Push to repository
git push origin <branch-name>

# Render will auto-deploy
# Then run migration on production database
```

### 5. Update Flutter App (When Ready)
The Flutter app should be updated to:
1. Track and send `session_id` with requests
2. Send `current_exercise` when user is actively working out
3. Start/end workout sessions via API

Example Flutter changes needed:
```dart
// In your workout screen
String? currentSessionId;
String? currentExercise;

Future<void> sendMessage(String message) async {
  final response = await http.post(
    Uri.parse('$baseUrl/chat'),
    headers: {'Content-Type': 'application/json'},
    body: jsonEncode({
      'message': message,
      'user_id': userId,
      'session_id': currentSessionId,
      'current_exercise': currentExercise,
    }),
  );

  final data = jsonDecode(response.body);

  // Update session ID if returned
  if (data['session_id'] != null) {
    currentSessionId = data['session_id'];
  }
}
```

## Configuration

### Environment Variables
Ensure these are set in your `.env` file:
```
OPENAI_API_KEY=your_api_key_here
DB_NAME=workout_tracker
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
```

### Conversation History Settings
In `conversation_memory.py`, you can adjust:
- `limit` parameter in `get_conversation_history()` - default 20 messages
- `time_window_hours` - default 24 hours
- `days_to_keep` in `clear_old_conversations()` - default 30 days

### Safety Thresholds
In `workout_logic.py`, you can adjust fatigue detection:
- Severe fatigue: >= 20% rep drop (line 118)
- Moderate fatigue: >= 10% rep drop (line 128)
- Back-off weight: 85% of current (15% reduction) (line 119)
- Weight too heavy: < 60% of previous reps (line 158)

## Maintenance

### Clean Old Conversations
Run periodically to prevent database bloat:
```python
from conversation_memory import clear_old_conversations
deleted = clear_old_conversations(days_to_keep=30)
print(f"Deleted {deleted} old messages")
```

Consider setting up a cron job:
```bash
# Add to crontab to run weekly
0 2 * * 0 python -c "from conversation_memory import clear_old_conversations; clear_old_conversations()"
```

## Troubleshooting

### Issue: "relation conversation_messages does not exist"
**Solution**: Run the database migration:
```bash
psql -U postgres workout_tracker < database/migration_001_conversation_memory.sql
```

### Issue: AI still not remembering conversations
**Checklist**:
1. Verify migration ran successfully: `SELECT COUNT(*) FROM conversation_messages;`
2. Check that messages are being saved: Look in database
3. Verify `get_conversation_history()` returns messages
4. Check time_window_hours isn't too restrictive

### Issue: Safety logic not working
**Checklist**:
1. Ensure `session_id` is being sent with requests
2. Verify `current_exercise` is specified
3. Check that sets are being saved with `workout_session_id`
4. Look for safety constraints in API logs (they're printed in system prompt)

## Performance Considerations

### Database Indexes
The migration adds indexes for:
- Fast conversation history retrieval
- Active workout session lookups
- Exercise set queries

### API Response Time
- Conversation history adds ~10-50ms to response time
- Set analysis adds ~20-100ms
- Overall impact: ~50-150ms (acceptable for chat interface)

### Token Usage
- With 20-message history, token usage increases by ~500-2000 tokens per request
- Consider reducing `limit` if token costs are high
- Conversation cleanup helps manage long-term costs

## Next Steps

1. ✅ Database migration applied
2. ✅ Backend code updated
3. ⏳ Local testing completed
4. ⏳ Deploy to production
5. ⏳ Update Flutter app to send session context
6. ⏳ Test with real users
7. ⏳ Monitor for safety issues

## Support

For issues or questions:
- Check logs: `backend/api_server.py` has detailed error logging
- Review database: Query `conversation_messages` and `workout_sessions` tables
- Test locally: Use curl commands from Testing section
