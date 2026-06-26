import 'package:dash_support/app/app.dart';
import 'package:dash_support/bootstrap.dart';
import 'package:chat_repository/chat_repository.dart';

void main() {
  // Override per device with --dart-define=BASE_URL=...
  // Default 10.0.2.2 reaches the host from the Android emulator.
  // Chrome, desktop, and the iOS simulator use http://localhost:8000.
  const baseUrl = String.fromEnvironment(
    'BASE_URL',
    defaultValue: 'http://10.0.2.2:8000',
  );
  final chatApiClient = ChatApiClient(baseUrl: baseUrl);
  final chatRepository = ChatRepository(apiClient: chatApiClient);

  bootstrap(() => App(chatRepository: chatRepository));
}
