import 'package:shared_preferences/shared_preferences.dart';

class UserStore {
  static const _kTelegramId = 'telegram_id';

  static Future<int?> getTelegramId() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getInt(_kTelegramId);
  }

  static Future<void> setTelegramId(int id) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setInt(_kTelegramId, id);
  }

  static Future<void> clear() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_kTelegramId);
  }
}
