import 'package:dash_support/chat/chat.dart';
import 'package:chat_repository/chat_repository.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:gpt_markdown/gpt_markdown.dart';

class ChatView extends StatefulWidget {
  const ChatView({super.key});

  @override
  State<ChatView> createState() => _ChatViewState();
}

class _ChatViewState extends State<ChatView> {
  final _controller = TextEditingController();
  final _scrollController = ScrollController();

  @override
  void dispose() {
    _controller.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  void _send() {
    final text = _controller.text.trim();
    if (text.isEmpty) return;
    context.read<ChatBloc>().add(ChatMessageSent(text));
    _controller.clear();
  }

  void _scrollToBottom() {
    if (!_scrollController.hasClients) return;
    _scrollController.animateTo(
      _scrollController.position.maxScrollExtent,
      duration: const Duration(milliseconds: 200),
      curve: Curves.easeOut,
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Dash support')),
      body: Column(
        children: [
          Expanded(
            child: BlocConsumer<ChatBloc, ChatState>(
              listener: (context, state) {
                if (state.status == ChatStatus.failure) {
                  ScaffoldMessenger.of(context)
                    ..hideCurrentSnackBar()
                    ..showSnackBar(
                      SnackBar(
                        content: Text(state.error ?? 'Something went wrong'),
                      ),
                    );
                }
                WidgetsBinding.instance
                    .addPostFrameCallback((_) => _scrollToBottom());
              },
              builder: (context, state) {
                final isLoading = state.status == ChatStatus.loading;
                final count = state.messages.length + (isLoading ? 1 : 0);
                return SelectionArea(
                  child: ListView.builder(
                    controller: _scrollController,
                    padding: const EdgeInsets.all(16),
                    itemCount: count,
                    itemBuilder: (context, index) {
                      if (isLoading && index == state.messages.length) {
                        return const _TypingIndicator();
                      }
                      return _MessageBubble(message: state.messages[index]);
                    },
                  ),
                );
              },
            ),
          ),
          _Composer(controller: _controller, onSend: _send),
        ],
      ),
    );
  }
}

class _MessageBubble extends StatelessWidget {
  const _MessageBubble({required this.message});

  final ChatMessage message;

  @override
  Widget build(BuildContext context) {
    final isUser = message.role == ChatRole.user;
    final scheme = Theme.of(context).colorScheme;
    final background =
        isUser ? scheme.primaryContainer : scheme.surfaceContainerHighest;
    final foreground =
        isUser ? scheme.onPrimaryContainer : scheme.onSurface;
    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: LayoutBuilder(
        builder: (context, constraints) {
          final maxWidth = (constraints.maxWidth * 0.8).clamp(200.0, 600.0);
          return Container(
            margin: const EdgeInsets.symmetric(vertical: 4),
            padding: const EdgeInsets.all(12),
            constraints: BoxConstraints(maxWidth: maxWidth),
            decoration: BoxDecoration(
              color: background,
              borderRadius: BorderRadius.circular(12),
            ),
            child: isUser
                ? Text(message.text, style: TextStyle(color: foreground))
                : GptMarkdown(
                    message.text,
                    style: TextStyle(color: foreground),
                  ),
          );
        },
      ),
    );
  }
}

class _TypingIndicator extends StatelessWidget {
  const _TypingIndicator();

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 4),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceContainerHighest,
          borderRadius: BorderRadius.circular(12),
        ),
        child: const SizedBox(width: 28, child: Text('...')),
      ),
    );
  }
}

class _Composer extends StatelessWidget {
  const _Composer({required this.controller, required this.onSend});

  final TextEditingController controller;
  final VoidCallback onSend;

  @override
  Widget build(BuildContext context) {
    final isLoading = context.select(
      (ChatBloc bloc) => bloc.state.status == ChatStatus.loading,
    );
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(12, 8, 12, 12),
        child: Row(
          children: [
            Expanded(
              child: TextField(
                controller: controller,
                minLines: 1,
                maxLines: 4,
                textInputAction: TextInputAction.send,
                onSubmitted: (_) => onSend(),
                decoration: const InputDecoration(
                  hintText: 'Ask about an order or refund',
                  border: OutlineInputBorder(),
                ),
              ),
            ),
            const SizedBox(width: 8),
            IconButton.filled(
              onPressed: isLoading ? null : onSend,
              icon: const Icon(Icons.send),
            ),
          ],
        ),
      ),
    );
  }
}
