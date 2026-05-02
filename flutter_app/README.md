# Crypto Signal Bot — Flutter App

Мобильное приложение и сайт для отображения сигналов.

## Установка Flutter

Если Flutter ещё не установлен — https://docs.flutter.dev/get-started/install

Проверить, что всё готово:

```bash
flutter doctor
```

## Подготовка

В папке проекта пока нет платформенных файлов (web/, android/, ios/ и т.д.) — они генерируются Flutter автоматически. Запустите один раз:

```bash
cd flutter_app
flutter create .        # создаст web/, android/, ios/, ... — lib/ и pubspec.yaml НЕ трогает
flutter pub get
```

Это одноразовое действие, в будущем повторять не надо.

**Если в консоли во время `flutter run` сыпятся сообщения** `DebugService: Error serving requests ... Cannot send Null` — это шумные логи Flutter DevTools, **они не мешают работе**. Приложение всё равно откроется в браузере.

## Запуск backend

В ОТДЕЛЬНОМ терминале запустите API:

```bash
cd ..   # в корень проекта crypto_trading_bot
uvicorn api:app --reload --host 0.0.0.0 --port 8765
```

Проверьте, что backend отвечает: откройте http://localhost:8765/health — должно вернуться `{"status":"ok", ...}`.

**Рекомендация:** параллельно запустите `python main.py`, чтобы бот непрерывно сканировал рынок и наполнял историю.

## Запуск приложения

### На компьютере (сайт)

```bash
flutter run -d chrome
```

Откроется браузер с вашим приложением. Это и есть ваш **сайт**.

Собрать статические файлы для деплоя сайта:

```bash
flutter build web
```

Готовые файлы будут в `build/web/` — их можно залить на любой статический хостинг (Netlify, Vercel, GitHub Pages).

### На Android

Подключите телефон через USB с включённой отладкой и:

```bash
flutter run -d android
```

Или сначала посмотрите доступные устройства:

```bash
flutter devices
```

**Важно:** на реальном телефоне поменяйте `baseUrl` в `lib/services/api_service.dart` на IP-адрес вашего компьютера в локалке (например `http://192.168.1.100:8765`). Узнать IP: Windows `ipconfig`, Mac/Linux `ifconfig`.

### На Android-эмуляторе

```bash
flutter run
```

По умолчанию `baseUrl` для эмулятора = `http://10.0.2.2:8000` — это специальный IP, за которым Android-эмулятор видит localhost хост-машины. Менять ничего не надо.

### На iOS (только macOS)

```bash
flutter run -d ios
```

## Структура

```
flutter_app/
├── pubspec.yaml              — зависимости Flutter
├── lib/
│   ├── main.dart             — точка входа, нижняя навигация (3 вкладки)
│   ├── models/signal.dart    — модели данных
│   ├── services/
│   │   └── api_service.dart  — HTTP-клиент для backend
│   ├── widgets/
│   │   └── signal_card.dart  — карточка сигнала
│   └── screens/
│       ├── home_screen.dart       — активные сигналы
│       ├── history_screen.dart    — история (WIN/LOSS/EXPIRED)
│       ├── stats_screen.dart      — статистика и графики
│       └── signal_detail_screen.dart — детали сделки
```

## Что делает каждый экран

**Активные сигналы** — текущие открытые позиции. Показывает: символ, направление (LONG/SHORT), вход, SL, TP, уверенность. Pull-to-refresh для обновления.

**История** — закрытые сделки. Фильтры: все/WIN/LOSS/EXPIRED. Для каждой видно P&L в R.

**Статистика** — переключатель периода (день/неделя/месяц). Показывает:
- Кол-во сделок
- Win rate
- Прибыль в R
- Приблизительный % от депозита (при риске 1% на сделку)
- График кумулятивного P&L по дням

**Экран деталей** — открывается по тапу на карточку: вся информация включая полное обоснование сигнала.

## Советы по разработке

- Вся логика в Python — Flutter только отображает. Если что-то нужно изменить в сигналах, редактируйте `ai/signal_engine.py`, а не Dart-код.
- Хотите добавить новый экран? Создайте файл в `lib/screens/`, добавьте вкладку в `main.dart` или маршрут.
- Работа с API — только через `ApiService`. Не делайте прямых `http.get` из экранов.
- Хотите push-уведомления? Это уже другая история — потребуется Firebase Cloud Messaging и доработка backend.
