import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/main.dart';
import 'package:mobile/src/screens/login_screen.dart';

void main() {
  testWidgets('ShwaasAI App launches with LoginScreen', (WidgetTester tester) async {
    await tester.pumpWidget(const ShwaasAIApp());
    expect(find.byType(LoginScreen), findsOneWidget);
    expect(find.text('ShwaasAI'), findsWidgets);
  });
}
