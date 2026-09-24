import 'chat_api_client.dart';
import 'models/models.dart';

/// Owns the conversation context. The app talks only to this class, never to
/// HTTP directly. The raw message list is kept private so multi-turn context
/// survives across sends.
class ChatRepository {
  ChatRepository({
    required ChatApiClient apiClient,
    String userId = 'demo-user',
  })  : _apiClient = apiClient,
        _userId = userId;

  final ChatApiClient _apiClient;
  final String _userId;

  final List<Map<String, dynamic>> _history = [];

  /// Issued by the backend on the first turn. The backend keeps per-conversation
  /// state (like whether the customer was verified) under this id.
  String? _conversationId;

  Future<ChatMessage> sendMessage(String text) async {
    _history.add({'role': 'user', 'content': text});

    final response = await _apiClient.sendChat(
      userId: _userId,
      messages: _history,
      conversationId: _conversationId,
    );
    _conversationId = response.conversationId;

    // The backend returns the full message list including assistant tool turns.
    // Replace local history with it so the next call carries the same context.
    _history
      ..clear()
      ..addAll(response.messages);

    return ChatMessage(role: ChatRole.assistant, text: response.reply);
  }
}
