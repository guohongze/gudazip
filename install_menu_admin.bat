@echo off
echo === 以管理员身份安装GudaZip独立菜单项 ===
echo.

REM 检查是否已经有管理员权限
net session >nul 2>&1
if %errorLevel% == 0 (
    echo 检测到管理员权限，开始安装...
    echo.
    python install_simple_menu.py
    echo.
    echo 安装完成，现在验证结果...
    python test_simple_menu.py
    echo.
    echo 请右键点击任意文件，应该看到5个独立的GudaZip菜单项
    pause
) else (
    echo 需要管理员权限，正在请求提升权限...
    echo.
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
) 