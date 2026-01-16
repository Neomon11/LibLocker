# PyInstaller Path Handling Fix

## Проблема

При компиляции приложения через PyInstaller возникала ошибка при запуске сервера:

```
sqlite3.OperationalError: unable to open database file
```

### Причина

1. **Относительные пути**: Код использовал относительный путь `data/liblocker.db` для базы данных
2. **Рабочая директория**: В PyInstaller рабочая директория может отличаться от расположения исполняемого файла
3. **Отсутствие директорий**: Директория `data` не создавалась автоматически

## Решение

### 1. Определение базового пути приложения

Добавлена функция `get_application_path()` в `src/shared/utils.py`:

```python
def get_application_path() -> str:
    """
    Получение базового пути приложения
    Учитывает запуск через PyInstaller (использует sys._MEIPASS)
    """
    if getattr(sys, 'frozen', False):
        # Запуск из PyInstaller executable
        return os.path.dirname(sys.executable)
    else:
        # Обычный запуск Python скрипта
        return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
```

**Как это работает:**
- `sys.frozen` устанавливается в `True` когда приложение запущено из PyInstaller
- `sys.executable` указывает на путь к `.exe` файлу в режиме PyInstaller
- В обычном режиме возвращается путь к корню проекта

### 2. Автоматическое создание директории данных

Добавлена функция `get_data_directory()` в `src/shared/utils.py`:

```python
def get_data_directory() -> str:
    """
    Получение пути к директории данных приложения
    Создает директорию, если она не существует
    """
    base_path = get_application_path()
    data_dir = os.path.join(base_path, 'data')
    os.makedirs(data_dir, exist_ok=True)
    return data_dir
```

### 3. Обновление Database класса

В `src/shared/database.py`:

```python
def __init__(self, db_path: str = "data/liblocker.db"):
    # Если путь относительный, преобразуем в абсолютный
    if not os.path.isabs(db_path):
        from .utils import get_data_directory
        db_filename = os.path.basename(db_path)
        data_dir = get_data_directory()
        db_path = os.path.join(data_dir, db_filename)
    else:
        # Для абсолютных путей создаем родительскую директорию
        parent_dir = os.path.dirname(db_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
    
    self.engine = create_engine(f'sqlite:///{db_path}', echo=False)
    # ... остальной код
```

### 4. Обновление конфигурации

В `src/shared/config.py` обновлены свойства `database_path` и `log_file`:

```python
@property
def database_path(self) -> str:
    path = self.get('database', 'path', 'data/liblocker.db')
    if not os.path.isabs(path):
        from .utils import get_data_directory
        db_filename = os.path.basename(path)
        data_dir = get_data_directory()
        path = os.path.join(data_dir, db_filename)
    return path

@property
def log_file(self) -> str:
    path = self.get('logging', 'file', 'logs/server.log')
    if not os.path.isabs(path):
        from .utils import get_application_path
        app_path = get_application_path()
        path = os.path.join(app_path, path)
    return path
```

## Структура файлов после исправления

### Обычный запуск (python run_server.py)
```
LibLocker/
├── run_server.py
├── src/
├── data/              # Создается автоматически
│   └── liblocker.db
└── logs/              # Создается автоматически
    └── server.log
```

### PyInstaller (LibLockerServer.exe)
```
<директория с exe>/
├── LibLockerServer.exe
├── data/              # Создается автоматически
│   └── liblocker.db
└── logs/              # Создается автоматически
    └── server.log
```

## Тестирование

Созданы тесты для проверки корректности работы:

### test_pyinstaller_paths.py
- Тест обычного выполнения
- Тест создания директорий
- Тест преобразования относительных путей
- Тест обработки абсолютных путей
- Симуляция PyInstaller frozen mode

### test_server_integration.py
- Полный цикл инициализации сервера
- Тест в режиме PyInstaller frozen
- Проверка работоспособности базы данных

## Запуск тестов

```bash
python test_pyinstaller_paths.py
python test_server_integration.py
python test_database_migration.py
```

## Компиляция через PyInstaller

Команды компиляции остаются прежними:

```powershell
# Сервер
pyinstaller --onefile --noconsole --name LibLockerServer --add-data 'src;src' --paths src .\run_server.py

# Клиент
pyinstaller --onefile --windowed --name LibLockerClient --add-data 'src;src' --paths src .\run_client.py
```

Теперь при первом запуске:
1. Автоматически создастся директория `data` рядом с `.exe`
2. База данных создастся в `data/liblocker.db`
3. Логи будут писаться в `logs/server.log` или `logs/client.log`

## Преимущества решения

1. ✅ **Совместимость**: Работает как в обычном Python, так и в PyInstaller
2. ✅ **Автоматическое создание**: Все необходимые директории создаются автоматически
3. ✅ **Гибкость**: Поддерживает как относительные, так и абсолютные пути
4. ✅ **Обратная совместимость**: Не ломает существующий код
5. ✅ **Протестировано**: Покрыто unit и интеграционными тестами
