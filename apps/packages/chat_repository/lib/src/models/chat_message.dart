import 'package:equatable/equatable.dart';

enum ChatRole { user, assistant }

class ChatMessage extends Equatable {
  const ChatMessage({required this.role, required this.text});

  final ChatRole role;
  final String text;

  @override
  List<Object?> get props => [role, text];
}
