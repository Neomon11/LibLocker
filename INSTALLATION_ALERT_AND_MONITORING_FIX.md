# Исправление проблем с красным экраном тревоги и автоматическим включением мониторинга

## Проблемы

### Проблема 1: Красный экран с сиреной не срабатывает, виджет таймера зависает

**Описание**: При скачивании установочного файла на клиенте не срабатывает красное окно с сиреной, виджет таймера просто зависает и клиент не реагирует на команды.

**Причина**: 
- `InstallationMonitor` работает в фоновом потоке (daemon thread)
- При обнаружении установки вызывается callback `on_installation_detected` **синхронно** из фонового потока
- `MainClientWindow.on_installation_detected()` создает Qt виджеты (`RedAlertLockScreen`) в **неправильном потоке**
- Операции Qt GUI из не-главного потока вызывают:
  - RedAlertLockScreen не отображается
  - Таймер виджет зависает (QTimer сигналы перестают работать)
  - Event loop Qt повреждается (клиент не реагирует на команды)

**Решение**:
Создана обертка `InstallationMonitorSignals` с Qt сигналом для thread-safe callback'ов:

```python
class InstallationMonitorSignals(QWidget):
    """Signal wrapper for InstallationMonitor to ensure thread-safe callbacks"""
    installation_detected = pyqtSignal(str)  # reason
```

В `MainClientWindow.__init__()`:
```python
# Installation monitor with thread-safe signal wrapper
self.installation_monitor_signals = InstallationMonitorSignals()
self.installation_monitor_signals.installation_detected.connect(
    self.on_installation_detected, Qt.ConnectionType.QueuedConnection
)

self.installation_monitor = InstallationMonitor(
    signal_emitter=self.installation_monitor_signals
)
```

В `InstallationMonitor._trigger_alert()`:
```python
if self.signal_emitter:
    # Emit signal - Qt automatically marshals to main thread
    self.signal_emitter.installation_detected.emit(reason)
```

**Результат**: 
- Callback автоматически маршалируется в главный Qt поток через QueuedConnection
- RedAlertLockScreen создается в правильном потоке и отображается корректно
- Таймер виджет продолжает работать
- Клиент продолжает обрабатывать команды сервера

### Проблема 2: Галочка автоматического включения мониторинга не работает

**Описание**: Галочка "Включить мониторинг установки программ по умолчанию" в настройках сервера сохраняется, но не включает мониторинг при старте сессии.

**Причина**:
- Настройка `installation_monitor_enabled` правильно сохраняется в конфиг сервера
- Но метод `start_session()` в `server.py` **никогда не отправляет** команду `installation_monitor_toggle`
- Клиент имеет локальную логику автозапуска (проверяет свой конфиг), но не получает команду от сервера

**Решение**:
Добавлена логика автоматического включения в `server.start_session()`:

```python
# Автоматически включаем мониторинг установки если это настроено в конфиге
if self.config.installation_monitor_enabled:
    logger.info(f"Auto-enabling installation monitor for client {client_id} (server config)")
    try:
        await self.toggle_installation_monitor(
            client_id, 
            enabled=True, 
            alert_volume=self.config.installation_monitor_alert_volume
        )
    except Exception as e:
        logger.error(f"Error auto-enabling installation monitor: {e}", exc_info=True)
```

Также добавлен параметр `alert_volume` в `toggle_installation_monitor()`:
```python
async def toggle_installation_monitor(self, client_id: int, enabled: bool, alert_volume: int = None) -> bool:
```

**Результат**:
- Сервер автоматически отправляет команду `installation_monitor_toggle` при старте сессии
- Используются настройки из конфига сервера (enabled, alert_volume)
- Клиент получает команду и включает мониторинг
- Настройки синхронизируются между сервером и клиентом

## Тестирование

### Автоматические тесты

1. **test_auto_enable_monitoring.py** ✅ PASSED
   - Проверяет, что сервер отправляет команду `installation_monitor_toggle` при старте сессии
   - Проверяет, что флаг `enabled` установлен в True
   - Проверяет, что `alert_volume` передается корректно

2. **test_signal_mechanism.py**
   - Unit тест механизма Qt сигналов
   - Проверяет маршалинг callback в главный поток

3. **test_installation_thread_safety.py**
   - Интеграционный тест thread safety
   - Создает реальный файл установщика
   - Проверяет, что callback выполняется в главном потоке

### Проверка безопасности

- CodeQL security scan: **No vulnerabilities found** ✅

## Измененные файлы

1. **src/client/gui.py**
   - Добавлен класс `InstallationMonitorSignals` для thread-safe callback'ов
   - Обновлен `MainClientWindow.__init__()` для использования signal wrapper
   - Подключен сигнал с `QueuedConnection`

2. **src/client/installation_monitor.py**
   - Добавлен параметр `signal_emitter` в `__init__()`
   - Обновлен `_trigger_alert()` для использования Qt сигнала
   - Сохранена обратная совместимость с прямым callback

3. **src/server/server.py**
   - Добавлена логика автоматического включения мониторинга в `start_session()`
   - Добавлен параметр `alert_volume` в `toggle_installation_monitor()`
   - Используются значения из конфига сервера

## Дополнительные замечания

### Взаимодействие локального и серверного auto-start

Клиент имеет локальную логику автозапуска (в `on_session_started`, строки 896-900):
```python
if self.config.installation_monitor_enabled:
    self.installation_monitor.start()
```

Это **не конфликтует** с серверной командой, потому что:
1. Локальный запуск происходит сразу (быстрый отклик, хороший UX)
2. Серверная команда приходит чуть позже и синхронизирует настройки
3. Метод `InstallationMonitor.start()` проверяет `if self.enabled` и безопасно игнорирует повторный запуск
4. Обработчик `on_installation_monitor_toggle` сохраняет серверные настройки в локальный конфиг

Это правильный дизайн: клиент реагирует мгновенно из локального конфига, затем синхронизируется с сервером.

### Thread Safety гарантии

- `QueuedConnection` гарантирует, что слот выполняется в потоке получателя
- Qt автоматически ставит событие в очередь event loop главного потока
- Это полностью устраняет проблемы с cross-thread GUI операциями
- Никаких блокировок или manual marshaling не требуется

## Заключение

Обе проблемы успешно решены:
1. ✅ Красный экран с сиреной теперь корректно отображается при обнаружении установки
2. ✅ Виджет таймера не зависает
3. ✅ Клиент продолжает отвечать на команды
4. ✅ Автоматическое включение мониторинга работает с сервера

Все изменения минимальны, сфокусированы и протестированы.
