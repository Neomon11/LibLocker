# Скрипт тестирования LibLocker
# Этот скрипт запускает сервер и клиент для тестирования

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "LibLocker - Тестирование исправлений" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# Останавливаем существующие процессы
Write-Host "[1/5] Остановка существующих процессов..." -ForegroundColor Yellow
Stop-Process -Name python -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# Очищаем логи для чистого теста
Write-Host "[2/5] Очистка логов..." -ForegroundColor Yellow
if (Test-Path "logs\client.log") {
    Clear-Content "logs\client.log"
}
if (Test-Path "logs\server.log") {
    Clear-Content "logs\server.log"
}

# Запускаем сервер
Write-Host "[3/5] Запуск сервера..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; python run_server.py" -WindowStyle Normal

# Ожидаем запуска сервера
Write-Host "[4/5] Ожидание запуска сервера..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# Запускаем клиент
Write-Host "[5/5] Запуск клиента..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; python run_client.py" -WindowStyle Normal

Write-Host ""
Write-Host "✅ Сервер и клиент запущены!" -ForegroundColor Green
Write-Host ""
Write-Host "Следующие шаги:" -ForegroundColor Cyan
Write-Host "1. Проверьте, что клиент показывает '✅ Подключено к серверу'" -ForegroundColor White
Write-Host "2. В панели администратора выберите клиента" -ForegroundColor White
Write-Host "3. Нажмите 'Начать сессию' и установите время (например, 1 минута)" -ForegroundColor White
Write-Host "4. Проверьте появление виджета таймера в левом верхнем углу" -ForegroundColor White
Write-Host "5. Дождитесь окончания сессии и проверьте блокировку" -ForegroundColor White
Write-Host ""
Write-Host "Для просмотра логов используйте:" -ForegroundColor Cyan
Write-Host "  Get-Content logs\client.log -Tail 30" -ForegroundColor Gray
Write-Host "  Get-Content logs\server.log -Tail 30" -ForegroundColor Gray
Write-Host ""
Write-Host "Для остановки всех процессов:" -ForegroundColor Cyan
Write-Host "  Stop-Process -Name python -Force" -ForegroundColor Gray

