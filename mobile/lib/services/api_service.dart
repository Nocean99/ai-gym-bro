import 'dart:convert';
import 'package:http/http.dart' as http;
import '../config/api_config.dart';
import 'auth_service.dart';

class ApiService {
  Future<bool> checkHealth() async {
    try {
      final response = await http
          .get(Uri.parse('${ApiConfig.baseUrl}/health'))
          .timeout(const Duration(seconds: 5));
      return response.statusCode == 200;
    } catch (e) {
      return false;
    }
  }

  Future<Map<String, dynamic>> sendMessage(String message) async {
    try {
      final userId = await AuthService().getUserId();

      if (userId == null) {
        return {
          'message': 'Not logged in',
          'type': 'error'
        };
      }

      final response = await http.post(
        Uri.parse('${ApiConfig.baseUrl}/chat'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'message': message,
          'user_id': userId,
        }),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return data;
      } else {
        return {
          'message': 'Error: ${response.statusCode}',
          'type': 'error'
        };
      }
    } catch (e) {
      return {
        'message': 'Connection error: $e',
        'type': 'error'
      };
    }
  }

  Future<bool> deleteSet(int setId) async {
    try {
      final userId = await AuthService().getUserId();

      if (userId == null) return false;

      final response = await http.delete(
        Uri.parse('${ApiConfig.baseUrl}/delete-set'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'set_id': setId,
          'user_id': userId,
        }),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return data['success'] ?? false;
      }
      return false;
    } catch (e) {
      return false;
    }
  }
}