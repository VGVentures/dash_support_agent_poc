import 'dart:convert';

import 'package:http/http.dart' as http;

/// Thrown when the backend responds with a non-200 status.
class ChatRequestFailure implements Exception {
  const ChatRequestFailure(this.statusCode, this.body);

  final int statusCode;
  final String body;

  @override
  String toString() => 'ChatRequestFailure($statusCode): $body';
}

/// The shape returned by POST /chat: a friendly reply, the raw Anthropic
/// message list, and the conversation id. The repository keeps both so the
/// next turn has context.
class ChatResponse {
  const ChatResponse({
    required this.reply,
    required this.messages,
    required this.conversationId,
  });

  final String reply;
  final List<Map<String, dynamic>> messages;
  final String conversationId;
}

class ChatApiClient {
  ChatApiClient({required String baseUrl, http.Client? httpClient})
      : _baseUrl = baseUrl,
        _httpClient = httpClient ?? http.Client();

  final String _baseUrl;
  final http.Client _httpClient;

  Future<ChatResponse> sendChat({
    required String userId,
    required List<Map<String, dynamic>> messages,
    String? conversationId,
  }) async {
    final uri = Uri.parse('$_baseUrl/chat');
    final response = await _httpClient.post(
      uri,
      headers: const {'Content-Type': 'application/json'},
      body: jsonEncode({
        'user_id': userId,
        'conversation_id': conversationId,
        'messages': messages,
      }),
    );

    if (response.statusCode != 200) {
      throw ChatRequestFailure(response.statusCode, response.body);
    }

    final decoded = jsonDecode(response.body) as Map<String, dynamic>;
    final rawMessages = (decoded['messages'] as List)
        .map((m) => Map<String, dynamic>.from(m as Map))
        .toList();

    return ChatResponse(
      reply: decoded['reply'] as String,
      messages: rawMessages,
      conversationId: decoded['conversation_id'] as String,
    );
  }
}
