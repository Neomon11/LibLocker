"""
Тестовый скрипт для отправки команды начала сессии клиенту
"""
import asyncio
import socketio

async def test_session_start():
    """Отправить команду SESSION_START клиенту"""
    # Подключаемся к серверу как admin tool
    sio = socketio.AsyncClient()

    try:
        # Подключение к серверу
        await sio.connect('http://localhost:8765')
        print("✅ Подключено к серверу")

        # Ждем немного
        await asyncio.sleep(1)

        # Отправляем команду start_session через HTTP API или напрямую
        print("⚠️ Этот скрипт не может отправить команду напрямую.")
        print("Пожалуйста, используйте GUI сервера для начала сессии.")
        print("\nШаги:")
        print("1. Откройте окно сервера")
        print("2. Выберите подключенного клиента в таблице")
        print("3. Нажмите кнопку 'Начать сессию'")
        print("4. Установите длительность (например, 1 минута)")
        print("5. Нажмите OK")

    except Exception as e:
        print(f"❌ Ошибка: {e}")
    finally:
        await sio.disconnect()

if __name__ == "__main__":
    asyncio.run(test_session_start())

