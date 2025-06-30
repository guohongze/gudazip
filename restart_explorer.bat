@echo off
echo 正在重启Windows资源管理器以刷新右键菜单...
echo.

echo 关闭资源管理器...
taskkill /f /im explorer.exe

echo 等待2秒...
timeout /t 2 /nobreak > nul

echo 重新启动资源管理器...
start explorer.exe

echo.
echo 完成！右键菜单应该已经更新。
echo.
pause 