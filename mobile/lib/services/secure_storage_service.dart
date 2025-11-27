import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Secure storage service for sensitive data
/// Uses platform-specific secure storage (Keychain on iOS, KeyStore on Android)
/// NEVER store API keys here - API keys should be on the backend only!
class SecureStorageService {
  static final SecureStorageService _instance = SecureStorageService._internal();
  factory SecureStorageService() => _instance;
  SecureStorageService._internal();

  final FlutterSecureStorage _storage = const FlutterSecureStorage(
    aOptions: AndroidOptions(
      encryptedSharedPreferences: true,
    ),
    iOptions: IOSOptions(
      accessibility: KeychainAccessibility.first_unlock,
    ),
  );

  // Storage keys
  static const String _keyUserId = 'user_id';
  static const String _keyUsername = 'username';
  static const String _keySessionToken = 'session_token';

  /// Save user authentication data
  Future<void> saveUserAuth({
    required String userId,
    required String username,
    String? sessionToken,
  }) async {
    await Future.wait([
      _storage.write(key: _keyUserId, value: userId),
      _storage.write(key: _keyUsername, value: username),
      if (sessionToken != null)
        _storage.write(key: _keySessionToken, value: sessionToken),
    ]);
  }

  /// Get stored user ID
  Future<String?> getUserId() async {
    return await _storage.read(key: _keyUserId);
  }

  /// Get stored username
  Future<String?> getUsername() async {
    return await _storage.read(key: _keyUsername);
  }

  /// Get stored session token
  Future<String?> getSessionToken() async {
    return await _storage.read(key: _keySessionToken);
  }

  /// Check if user is logged in
  Future<bool> isLoggedIn() async {
    final userId = await getUserId();
    return userId != null && userId.isNotEmpty;
  }

  /// Clear all stored authentication data (logout)
  Future<void> clearAuth() async {
    await Future.wait([
      _storage.delete(key: _keyUserId),
      _storage.delete(key: _keyUsername),
      _storage.delete(key: _keySessionToken),
    ]);
  }

  /// Clear all stored data
  Future<void> clearAll() async {
    await _storage.deleteAll();
  }

  /// Get all stored keys (for debugging only - remove in production)
  Future<Map<String, String>> getAllValues() async {
    return await _storage.readAll();
  }
}
