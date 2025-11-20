class Message {
  final String role; // 'user' or 'assistant'
  final String content;
  final DateTime timestamp;
  final String? type; // 'text', 'recap_card', 'chart', etc.
  final List<dynamic>? loggedSets; // For workout recap cards
  final Map<String, dynamic>? chartData; // For progress charts

  Message({
    required this.role,
    required this.content,
    DateTime? timestamp,
    this.type,
    this.loggedSets,
    this.chartData,
  }) : timestamp = timestamp ?? DateTime.now();

  Map<String, dynamic> toJson() {
    return {
      'role': role,
      'content': content,
      'timestamp': timestamp.toIso8601String(),
      'type': type,
      'logged_sets': loggedSets,
      'chart_data': chartData,
    };
  }

  factory Message.fromJson(Map<String, dynamic> json) {
    return Message(
      role: json['role'],
      content: json['content'],
      timestamp: DateTime.parse(json['timestamp']),
      type: json['type'],
      loggedSets: json['logged_sets'],
      chartData: json['chart_data'],
    );
  }
}