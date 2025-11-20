import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import '../config/api_config.dart';
import '../services/auth_service.dart';

class BulkImportScreen extends StatefulWidget {
  const BulkImportScreen({Key? key}) : super(key: key);

  @override
  State<BulkImportScreen> createState() => _BulkImportScreenState();
}

class _BulkImportScreenState extends State<BulkImportScreen> {
  final TextEditingController _textController = TextEditingController();
  bool _isProcessing = false;
  double _progress = 0.0;
  String _statusMessage = '';
  int _totalChunks = 0;
  int _processedChunks = 0;
  int _successfulExercises = 0;
  List<String> _errors = [];

  @override
  void dispose() {
    _textController.dispose();
    super.dispose();
  }

  /// Split text into chunks by date sections
  List<String> _splitIntoChunks(String text) {
    // Split by year headers (e.g., "2023 –", "2024 -")
    final yearPattern = RegExp(r'\d{4}\s*[–-]');
    final chunks = <String>[];

    final matches = yearPattern.allMatches(text);
    if (matches.isEmpty) {
      // No year headers found, split by blank lines
      return text.split('\n\n').where((s) => s.trim().isNotEmpty).toList();
    }

    int lastEnd = 0;
    for (final match in matches) {
      if (lastEnd > 0) {
        // Add previous section
        chunks.add(text.substring(lastEnd, match.start).trim());
      }
      lastEnd = match.start;
    }
    // Add final section
    if (lastEnd < text.length) {
      chunks.add(text.substring(lastEnd).trim());
    }

    // Further split large chunks by month sections
    final result = <String>[];
    for (final chunk in chunks) {
      final monthPattern = RegExp(r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d+');
      final monthMatches = monthPattern.allMatches(chunk).toList();

      if (monthMatches.length <= 3) {
        // Small enough, keep as is
        result.add(chunk);
      } else {
        // Split by months
        int lastMonthEnd = 0;
        for (int i = 0; i < monthMatches.length; i++) {
          if (i > 0) {
            result.add(chunk.substring(lastMonthEnd, monthMatches[i].start).trim());
          }
          lastMonthEnd = monthMatches[i].start;
        }
        if (lastMonthEnd < chunk.length) {
          result.add(chunk.substring(lastMonthEnd).trim());
        }
      }
    }

    return result.where((s) => s.trim().isNotEmpty).toList();
  }

  /// Process a single chunk
  Future<Map<String, dynamic>> _processChunk(String chunk) async {
    final userId = await AuthService().getUserId();
    if (userId == null) {
      return {'success': false, 'error': 'Not logged in'};
    }

    try {
      final response = await http.post(
        Uri.parse('${ApiConfig.baseUrl}/chat'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'message': chunk,
          'user_id': userId,
        }),
      ).timeout(const Duration(seconds: 30));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return {'success': true, 'data': data};
      } else {
        return {'success': false, 'error': 'Server error ${response.statusCode}'};
      }
    } catch (e) {
      return {'success': false, 'error': e.toString()};
    }
  }

  /// Start the bulk import process
  Future<void> _startImport() async {
    final text = _textController.text.trim();
    if (text.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please paste your workout data first!')),
      );
      return;
    }

    setState(() {
      _isProcessing = true;
      _progress = 0.0;
      _processedChunks = 0;
      _successfulExercises = 0;
      _errors.clear();
      _statusMessage = 'Splitting data into chunks...';
    });

    // Split into chunks
    final chunks = _splitIntoChunks(text);
    setState(() {
      _totalChunks = chunks.length;
      _statusMessage = 'Processing ${chunks.length} chunks...';
    });

    // Process each chunk
    for (int i = 0; i < chunks.length; i++) {
      setState(() {
        _statusMessage = 'Processing chunk ${i + 1} of ${chunks.length}...';
      });

      final result = await _processChunk(chunks[i]);

      setState(() {
        _processedChunks++;
        _progress = (_processedChunks / _totalChunks);
      });

      if (result['success'] == true) {
        final data = result['data'];
        if (data['type'] == 'workout_logged') {
          final loggedSets = data['logged_sets'] as List?;
          _successfulExercises += loggedSets?.length ?? 0;
        }
      } else {
        _errors.add('Chunk ${i + 1}: ${result['error']}');
      }

      // Small delay to avoid overwhelming the server
      await Future.delayed(const Duration(milliseconds: 500));
    }

    setState(() {
      _isProcessing = false;
      _statusMessage = 'Import complete!';
    });

    // Show results
    if (mounted) {
      showDialog(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('Import Complete! 🎉'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('✓ Processed: $_processedChunks chunks'),
              Text('✓ Imported: $_successfulExercises exercises'),
              if (_errors.isNotEmpty) ...[
                const SizedBox(height: 12),
                Text('⚠️ Errors: ${_errors.length}',
                    style: const TextStyle(color: Colors.orange)),
                const SizedBox(height: 8),
                ...(_errors.take(3).map((e) => Text('• $e',
                    style: const TextStyle(fontSize: 12)))),
                if (_errors.length > 3)
                  Text('... and ${_errors.length - 3} more'),
              ],
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('OK'),
            ),
          ],
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        title: const Text('Bulk Import'),
        backgroundColor: Colors.grey[900],
        foregroundColor: Colors.white,
      ),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Instructions
            Card(
              color: Colors.grey[850],
              child: Padding(
                padding: const EdgeInsets.all(12.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: const [
                        Icon(Icons.info_outline, color: Colors.orange, size: 20),
                        SizedBox(width: 8),
                        Text(
                          'How to use',
                          style: TextStyle(
                            color: Colors.orange,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Paste your entire workout history below in natural language. '
                      'The app will automatically split it into smaller chunks and process them one by one.',
                      style: TextStyle(color: Colors.grey[300], fontSize: 13),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'This may take 30-60 seconds for large datasets. Keep the app open!',
                      style: TextStyle(
                        color: Colors.grey[400],
                        fontSize: 12,
                        fontStyle: FontStyle.italic,
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),

            // Text input
            Expanded(
              child: TextField(
                controller: _textController,
                maxLines: null,
                expands: true,
                enabled: !_isProcessing,
                style: const TextStyle(color: Colors.white),
                decoration: InputDecoration(
                  hintText: 'Paste your workout history here...\n\n'
                      'Example:\n'
                      '2023 – Bench Press\n'
                      'Nov 5: 225×4, 235×2\n'
                      'Dec 6: 245×3×3\n\n'
                      '2024 – Bench Press\n'
                      'Jan 10: 255×3, 265×2',
                  hintStyle: TextStyle(color: Colors.grey[600]),
                  filled: true,
                  fillColor: Colors.grey[900],
                  border: const OutlineInputBorder(),
                ),
              ),
            ),
            const SizedBox(height: 16),

            // Progress indicator
            if (_isProcessing) ...[
              LinearProgressIndicator(
                value: _progress,
                backgroundColor: Colors.grey[800],
                valueColor: const AlwaysStoppedAnimation<Color>(Colors.orange),
              ),
              const SizedBox(height: 8),
              Text(
                _statusMessage,
                textAlign: TextAlign.center,
                style: const TextStyle(color: Colors.orange),
              ),
              const SizedBox(height: 16),
            ],

            // Import button
            ElevatedButton(
              onPressed: _isProcessing ? null : _startImport,
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.orange,
                padding: const EdgeInsets.symmetric(vertical: 16),
              ),
              child: _isProcessing
                  ? const SizedBox(
                      height: 20,
                      width: 20,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                      ),
                    )
                  : const Text(
                      'Start Import',
                      style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                    ),
            ),
          ],
        ),
      ),
    );
  }
}
