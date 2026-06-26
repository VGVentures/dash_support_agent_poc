import 'package:dash_support/chat/chat.dart';
import 'package:chat_repository/chat_repository.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

class App extends StatelessWidget {
  const App({required this.chatRepository, super.key});

  final ChatRepository chatRepository;

  @override
  Widget build(BuildContext context) {
    return RepositoryProvider.value(
      value: chatRepository,
      child: MaterialApp(
        title: 'Dash support',
        theme: ThemeData(
          useMaterial3: true,
          colorSchemeSeed: const Color(0xFF534AB7),
        ),
        home: const ChatPage(),
      ),
    );
  }
}
