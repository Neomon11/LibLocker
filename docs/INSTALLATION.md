# Установка и запуск LibLocker

## Системные требования

- Windows 10/11 (x64)
- Python 3.12 или выше
- Минимум 2 ГБ RAM
- 500 МБ свободного места на диске

## Установка

### 1. Клонирование репозитория

```bash
git clone <repository-url>
cd LibLocker
```

### 2. Создание виртуального окружения

```bash
python -m venv venv
```

### 3. Активация виртуального окружения

**Windows PowerShell:**
```powershell
.\venv\Scripts\Activate.ps1
```

**Windows CMD:**
```cmd
venv\Scripts\activate.bat
```

### 4. Установка зависимостей

```bash
pip install -r requirements.txt
```

Если возникают проблемы с таймаутом:
```bash
pip install --timeout 120 -r requirements.txt
```

### 5. Создание конфигурационного файла (опционально)

```bash
copy config.example.ini config.ini
```

Отредактируйте `config.ini` под ваши нужды.

## Запуск приложений

### Запуск серверного приложения (Панель администратора)

```bash
python run_server.py
```

Откроется графический интерфейс панели администратора.

### Запуск клиентского приложения (Агент)

**На локальной машине:**
```bash
python run_client.py
```

**С указанием адреса сервера:**
```bash
python run_client.py http://192.168.1.100:8765
```

## Настройка PyCharm

1. Откройте проект в PyCharm
2. Перейдите в `File → Settings → Project → Python Interpreter`
3. Нажмите на шестеренку → `Add...`
4. Выберите `Existing Environment`
5. Укажите путь к интерпретатору: `C:\Users\123qw\PycharmProjects\LibLocker\venv\Scripts\python.exe`
6. Нажмите `OK`

## Структура файлов данных

После первого запуска будут созданы следующие директории:

- `data/` - база данных SQLite
- `logs/` - файлы логов (если настроено)

## Решение проблем

### Ошибка "No module named..."

Убедитесь, что виртуальное окружение активировано:
```bash
.\venv\Scripts\Activate.ps1
```

Переустановите зависимости:
```bash
pip install -r requirements.txt
```

### Ошибка подключения клиента к серверу

1. Проверьте, что сервер запущен
2. Проверьте настройки firewall (откройте порт 8765)
3. Убедитесь, что указан правильный IP-адрес сервера

### Окно блокировки не перехватывает все клавиши

Это ограничение Windows. Для полной защиты требуется:
1. Запуск клиента с правами администратора
2. Установка клиента как службы Windows (в разработке)

## Компиляция в исполняемые файлы

### Установка PyInstaller

```bash
pip install pyinstaller
```

### Компиляция сервера

```bash
pyinstaller --name LibLocker-Server --onefile --windowed run_server.py
```

### Компиляция клиента

```bash
pyinstaller --name LibLocker-Client --onefile --windowed run_client.py
```

Исполняемые файлы будут в папке `dist/`.

## Разработка

### Запуск тестов

```bash
pytest tests/
```

### Проверка стиля кода

```bash
flake8 src/
black src/
```

## Дополнительная информация

Смотрите файл `README.md` для полной документации проекта.

