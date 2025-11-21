import 'package:flutter/material.dart';
import '../config/api_config.dart';
import '../models/message.dart';
import '../services/api_service.dart';
import '../widgets/workout_recap_card.dart';
import '../widgets/progress_chart.dart';
import '../services/auth_service.dart';
import 'login_screen.dart';
import 'bulk_import_screen.dart';

class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final TextEditingController _textController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  final ApiService _apiService = ApiService();
  final List<Message> _messages = [];
  bool _isLoading = false;
  bool _isConnected = false;

  @override
  void initState() {
    super.initState();
    _checkConnection();
    _loadWelcomeMessage();
  }

  Future<void> _checkConnection() async {
    final connected = await _apiService.checkHealth();
    setState(() {
      _isConnected = connected;
    });
  }

  void _loadWelcomeMessage() {
    setState(() {
      _messages.add(Message(
        role: 'assistant',
        content: "What's up bro! 💪 Ready to crush some weights? Tell me what you're working on today!",
        timestamp: DateTime.now(),
      ));
    });
  }

  Future<void> _handleSubmitted(String text) async {
    if (text.trim().isEmpty) return;

    _textController.clear();

    setState(() {
      _messages.add(Message(
        role: 'user',
        content: text,
        timestamp: DateTime.now(),
      ));
      _isLoading = true;
    });

    _scrollToBottom();

    try {
      final responseData = await _apiService.sendMessage(text);

      print('=== DEBUG: Response Data ===');
      print('Response type: ${responseData['type']}');
      print('Has chart_data: ${responseData['chart_data'] != null}');
      if (responseData['chart_data'] != null) {
        print('Chart data: ${responseData['chart_data']}');
      }
      print('===========================');

      setState(() {
        _messages.add(Message(
          role: 'assistant',
          content: responseData['message'] ?? 'No response',
        ));

        if (responseData['type'] == 'chart' &&
            responseData['chart_data'] != null) {
          _messages.add(Message(
            role: 'assistant',
            content: '',
            type: 'chart',
            chartData: responseData['chart_data'],
          ));
        }

        final loggedSets = responseData['logged_sets'];
        if (loggedSets != null && loggedSets is List && loggedSets.isNotEmpty) {
          _messages.add(Message(
            role: 'assistant',
            content: '',
            type: 'recap_card',
            loggedSets: loggedSets,
          ));
        }

        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _messages.add(Message(
          role: 'assistant',
          content:
              "Yo bro, connection's acting up. Make sure the backend is running! 🏋️",
        ));
        _isLoading = false;
      });
    }

    _scrollToBottom();
  }

  void _scrollToBottom() {
    Future.delayed(const Duration(milliseconds: 100), () {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.grey[900],
      appBar: AppBar(
        backgroundColor: Colors.black,
        title: Row(
          children: [
            ClipRRect(
              borderRadius: BorderRadius.circular(6),
              child: Image.asset(
                'assets/logo.png',
                width: 28,
                height: 28,
                fit: BoxFit.cover,
              ),
            ),
            const SizedBox(width: 8),
            const Text(
              'AI Gym Bro',
              style: TextStyle(
                color: Colors.orange,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(width: 8),
            Container(
              width: 12,
              height: 12,
              decoration: BoxDecoration(
                color: _isConnected ? Colors.green : Colors.red,
                shape: BoxShape.circle,
              ),
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.logout, color: Colors.orange),
            onPressed: () async {
              await AuthService().logout();
              if (mounted) {
                Navigator.pushReplacement(
                  context,
                  MaterialPageRoute(
                    builder: (context) => const LoginScreen(),
                  ),
                );
              }
            },
            tooltip: 'Logout',
          ),
        ],
      ),
      body: Column(
        children: [
          Expanded(
            child: ListView.builder(
              controller: _scrollController,
              padding: const EdgeInsets.all(8.0),
              itemCount: _messages.length,
              itemBuilder: (context, index) {
                final message = _messages[index];

                if (message.type == 'chart' && message.chartData != null) {
                  return ProgressChart(chartData: message.chartData!);
                }

                if (message.type == 'recap_card' &&
                    message.loggedSets != null) {
                  return WorkoutRecapCard(
                    loggedSets: message.loggedSets!,
                    backendUrl: ApiConfig.baseUrl,
                  );
                }

                return _buildMessageBubble(message);
              },
            ),
          ),
          if (_isLoading)
            const Padding(
              padding: EdgeInsets.all(8.0),
              child: Row(
                children: [
                  CircularProgressIndicator(color: Colors.orange),
                  SizedBox(width: 16),
                  Text(
                    'Bro is thinking...',
                    style: TextStyle(color: Colors.orange),
                  ),
                ],
              ),
            ),
          _buildInputArea(),
        ],
      ),
    );
  }

  Widget _buildInputArea() {
    return Container(
      decoration: BoxDecoration(
        color: Colors.grey[850],
        border: Border(
          top: BorderSide(color: Colors.orange.withOpacity(0.3)),
        ),
      ),
      padding: const EdgeInsets.symmetric(horizontal: 8.0),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: _textController,
              style: const TextStyle(color: Colors.white),
              decoration: InputDecoration(
                hintText: 'Log your workout...',
                hintStyle: TextStyle(color: Colors.grey[600]),
                border: InputBorder.none,
              ),
              onSubmitted: _handleSubmitted,
            ),
          ),
          IconButton(
            icon: const Icon(Icons.send, color: Colors.orange),
            onPressed: () => _handleSubmitted(_textController.text),
          ),
        ],
      ),
    );
  }

  Widget _buildMessageBubble(Message message) {
    final isUser = message.role == 'user';
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4.0, horizontal: 8.0),
      child: Align(
        alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
        child: Container(
          constraints: BoxConstraints(
            maxWidth: MediaQuery.of(context).size.width * 0.75,
          ),
          padding: const EdgeInsets.all(12.0),
          decoration: BoxDecoration(
            color: isUser ? Colors.orange : Colors.grey[800],
            borderRadius: BorderRadius.circular(12.0),
          ),
          child: Text(
            message.content,
            style: TextStyle(
              color: isUser ? Colors.black : Colors.white,
            ),
          ),
        ),
      ),
    );
  }

  @override
  void dispose() {
    _textController.dispose();
    _scrollController.dispose();
    super.dispose();
  }
}
