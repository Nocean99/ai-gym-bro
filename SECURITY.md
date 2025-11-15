# Security Best Practices for Gym Bro

This document outlines the security measures implemented in the Gym Bro application.

## API Key Security

### Backend (Python/Flask)

#### OpenAI API Key
- **NEVER** commit API keys to version control
- Store in `.env` file (already in `.gitignore`)
- Load using `python-dotenv` library
- Access via `os.getenv('OPENAI_API_KEY')`

#### Database Credentials
- **NEVER** hardcode database passwords
- Store all DB credentials in `.env` file
- Use environment variables in production

### Mobile App (Flutter)

#### Critical Security Rules
1. **NEVER store API keys in the mobile app**
   - OpenAI API key stays on the backend only
   - Mobile app communicates only with your backend API
   - No direct calls to third-party APIs from the mobile app

2. **Backend API URL Configuration**
   - Stored in `.env` file (not committed to git)
   - Use `flutter_dotenv` to load configuration
   - Copy `.env.example` to `.env` and customize

3. **User Authentication Tokens**
   - Use `flutter_secure_storage` for session tokens
   - Stored in iOS Keychain / Android Keystore
   - Never in SharedPreferences or regular storage
   - Automatically cleared on logout

## Setup Instructions

### Backend Setup

1. Copy the environment template:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your actual credentials:
   ```bash
   # OpenAI API Configuration
   OPENAI_API_KEY=sk-your-actual-api-key-here

   # Database Configuration
   DB_NAME=workout_tracker
   DB_USER=postgres
   DB_PASSWORD=your_actual_db_password
   DB_HOST=localhost
   DB_PORT=5432
   ```

3. **NEVER commit the `.env` file** - it's already in `.gitignore`

### Mobile App Setup

1. Navigate to the mobile directory:
   ```bash
   cd mobile
   ```

2. Copy the environment template:
   ```bash
   cp .env.example .env
   ```

3. Edit `.env` with your backend URL:
   ```bash
   # For local development
   API_BASE_URL=http://localhost:5001
   ENVIRONMENT=development

   # For production
   API_BASE_URL=https://api.gymbro.app
   ENVIRONMENT=production
   ```

4. **NEVER commit the `.env` file** - it's already in `.gitignore`

5. Install dependencies:
   ```bash
   flutter pub get
   ```

## Production Deployment Checklist

### Backend

- [ ] Use environment variables for all secrets
- [ ] Never use `DEBUG=True` in production
- [ ] Use HTTPS only (SSL/TLS certificates)
- [ ] Implement rate limiting on API endpoints
- [ ] Use strong database passwords
- [ ] Enable CORS only for your mobile app domain
- [ ] Implement proper authentication/authorization
- [ ] Add API request validation
- [ ] Log security events
- [ ] Regular security audits

### Mobile App

- [ ] Update `API_BASE_URL` to production URL
- [ ] Set `ENVIRONMENT=production` in `.env`
- [ ] Build in release mode: `flutter build ios --release`
- [ ] Code obfuscation enabled
- [ ] Remove all debug print statements
- [ ] Certificate pinning (optional but recommended)
- [ ] Implement biometric authentication (optional)
- [ ] Test on multiple iOS versions and devices

## What NOT to Do

### ❌ NEVER Do This:

```dart
// BAD - Hardcoded API key in mobile app
const String openAiKey = 'sk-abc123...';

// BAD - Hardcoded backend URL
const String apiUrl = 'http://myserver.com:5001';

// BAD - Storing sensitive data in SharedPreferences
prefs.setString('api_key', key);

// BAD - Committing .env file
git add .env
```

### ✅ ALWAYS Do This:

```dart
// GOOD - Load from environment
import 'package:gym_bro/config/app_config.dart';
final apiUrl = AppConfig.apiBaseUrl;

// GOOD - Use secure storage for auth tokens
import 'package:gym_bro/services/secure_storage_service.dart';
final storage = SecureStorageService();
await storage.saveUserAuth(userId: userId, username: username);

// GOOD - Backend handles API keys
// Mobile app only talks to your backend, never directly to OpenAI
```

## File Structure

```
ai-gym-bro/
├── .env                  # Backend secrets (NEVER commit)
├── .env.example          # Backend template (commit this)
├── .gitignore            # Includes .env, config.py
├── backend/
│   ├── api_server.py     # Uses os.getenv() for secrets
│   └── config/
│       ├── config.py     # (gitignored)
│       └── config.example.py
└── mobile/
    ├── .env              # Mobile config (NEVER commit)
    ├── .env.example      # Mobile template (commit this)
    ├── lib/
    │   ├── config/
    │   │   └── app_config.dart        # Loads .env
    │   └── services/
    │       └── secure_storage_service.dart  # Secure auth storage
    └── pubspec.yaml      # Includes flutter_secure_storage
```

## Security Packages Used

### Backend
- `python-dotenv` - Environment variable management
- `werkzeug.security` - Password hashing
- `flask-cors` - CORS control

### Mobile
- `flutter_secure_storage` - Secure storage (Keychain/KeyStore)
- `flutter_dotenv` - Environment configuration
- `http` - Secure HTTPS requests

## Incident Response

If API keys are accidentally committed:

1. **Immediately revoke** the exposed keys
2. Generate new API keys
3. Update `.env` with new keys
4. Use `git filter-branch` or BFG Repo-Cleaner to remove from history
5. Force push to remote (if applicable)
6. Notify team members to pull latest changes
7. Monitor for unauthorized usage

## Additional Resources

- [OWASP Mobile Security](https://owasp.org/www-project-mobile-security/)
- [Flutter Security Best Practices](https://flutter.dev/security)
- [OpenAI API Best Practices](https://platform.openai.com/docs/guides/safety-best-practices)

## Questions?

For security concerns, please review this document first. Never share API keys, database passwords, or other secrets in issues, pull requests, or public forums.
