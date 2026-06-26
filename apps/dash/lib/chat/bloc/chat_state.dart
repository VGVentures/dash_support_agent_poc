part of 'chat_bloc.dart';

enum ChatStatus { initial, loading, success, failure }

final class ChatState extends Equatable {
  const ChatState({
    this.status = ChatStatus.initial,
    this.messages = const [],
    this.error,
  });

  final ChatStatus status;
  final List<ChatMessage> messages;
  final String? error;

  ChatState copyWith({
    ChatStatus? status,
    List<ChatMessage>? messages,
    String? error,
  }) {
    return ChatState(
      status: status ?? this.status,
      messages: messages ?? this.messages,
      error: error ?? this.error,
    );
  }

  @override
  List<Object?> get props => [status, messages, error];
}
