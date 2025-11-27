import 'package:flutter_dotenv/flutter_dotenv.dart';

/// Application configuration
/// Loads environment variables from .env file
/// Never store API keys or secrets in the mobile app!
class AppConfig {
  /// Backend API base URL
  static String get apiBaseUrl {
    return dotenv.env['API_BASE_URL'] ?? 'http://localhost:5001';
  }

  /// Current environment (development, staging, production)
  static String get environment {
    return dotenv.env['ENVIRONMENT'] ?? 'development';
  }

  /// Check if running in development mode
  static bool get isDevelopment => environment == 'development';

  /// Check if running in production mode
  static bool get isProduction => environment == 'production';

  /// API endpoints
  static String get registerEndpoint => '$apiBaseUrl/register';
  static String get loginEndpoint => '$apiBaseUrl/login';
  static String get chatEndpoint => '$apiBaseUrl/chat';
  static String get historyEndpoint => '$apiBaseUrl/history';
  static String get deleteSetEndpoint => '$apiBaseUrl/delete-set';
  static String get healthEndpoint => '$apiBaseUrl/health';

  /// Initialize configuration
  /// Call this in main() before runApp()
  static Future<void> initialize() async {
    try {
      await dotenv.load(fileName: '.env');
    } catch (e) {
      // .env file not found, using defaults
      print('Warning: .env file not found, using default configuration');
    }
  }
}
