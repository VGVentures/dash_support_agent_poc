import 'package:bloc/bloc.dart';
import 'package:chat_repository/chat_repository.dart';
import 'package:equatable/equatable.dart';

part 'chat_event.dart';
part 'chat_state.dart';

class ChatBloc extends Bloc<ChatEvent, ChatState> {
  ChatBloc({required ChatRepository chatRepository})
      : _chatRepository = chatRepository,
        super(const ChatState()) {
    on<ChatMessageSent>(_onMessageSent);
  }

  final ChatRepository _chatRepository;

  Future<void> _onMessageSent(
    ChatMessageSent event,
    Emitter<ChatState> emit,
  ) async {
    final text = event.text.trim();
    if (text.isEmpty) return;

    final outgoing = ChatMessage(role: ChatRole.user, text: text);
    final pending = [...state.messages, outgoing];
    emit(state.copyWith(status: ChatStatus.loading, messages: pending));

    try {
      final reply = await _chatRepository.sendMessage(text);
      emit(
        state.copyWith(
          status: ChatStatus.success,
          messages: [...pending, reply],
        ),
      );
    } catch (error) {
      emit(state.copyWith(status: ChatStatus.failure, error: '$error'));
    }
  }
}
