@echo off
echo.
echo ==============================================
echo          GudaZip - 系统压缩管理器
echo ==============================================
echo.
echo 强制以管理员模式启动 GudaZip...
echo （跳过权限选择对话框）
echo.

REM 检查是否已经是管理员权限
net session >nul 2>&1
if %errorLevel% == 0 (
    echo ✅ 已具有管理员权限，启动程序...
    python main.py --admin
) else (
    echo ⚠️  需要管理员权限，正在申请...
    echo.
    echo 如果出现UAC提示，请点击"是"来授权...
    powershell -Command "Start-Process python -ArgumentList 'main.py --admin' -Verb RunAs"
)

echo.
echo 程序已启动，可以关闭此窗口。
pause 