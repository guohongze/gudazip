@echo off
chcp 65001 >nul
echo 🔧 GudaZip文件关联最终修复脚本
echo 📌 修复关键：指向打包的exe文件，而不是开发环境的python脚本
echo.

REM 检查管理员权限
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 需要管理员权限运行此脚本
    echo 请右键点击此文件，选择"以管理员身份运行"
    pause
    exit /b 1
)

echo ✅ 管理员权限确认

REM 检查exe文件是否存在
set EXE_PATH=%~dp0build\exe\GudaZip.exe
if not exist "%EXE_PATH%" (
    echo ❌ 错误：找不到GudaZip.exe文件
    echo 路径：%EXE_PATH%
    echo 请确保项目已正确构建
    pause
    exit /b 1
)

echo ✅ 找到exe文件：%EXE_PATH%

echo.
echo 🧹 第一步：清理旧的注册表设置...
reg delete "HKLM\SOFTWARE\Classes\GudaZip.Archive" /f >nul 2>&1
reg delete "HKCU\SOFTWARE\Classes\GudaZip.Archive" /f >nul 2>&1
echo ✅ 旧设置已清理

echo.
echo 📝 第二步：重新注册文件类型（指向exe）...
reg add "HKLM\SOFTWARE\Classes\GudaZip.Archive" /f /ve /d "GudaZip压缩文件"
reg add "HKLM\SOFTWARE\Classes\GudaZip.Archive\DefaultIcon" /f /ve /d "\"%EXE_PATH%\",0"
reg add "HKLM\SOFTWARE\Classes\GudaZip.Archive\shell\open" /f /ve /d "打开"
reg add "HKLM\SOFTWARE\Classes\GudaZip.Archive\shell\open\command" /f /ve /d "\"%EXE_PATH%\" \"%%1\""
echo ✅ 文件类型注册完成

echo.
echo 🔗 第三步：设置文件关联...
reg add "HKLM\SOFTWARE\Classes\.7z" /f /ve /d "GudaZip.Archive"
reg add "HKLM\SOFTWARE\Classes\.zip" /f /ve /d "GudaZip.Archive"
echo ✅ 文件关联设置完成

echo.
echo 🧹 第四步：清理图标缓存...
del "%localappdata%\IconCache.db" /f /q >nul 2>&1
del "%localappdata%\Microsoft\Windows\Explorer\iconcache_*.db" /f /q >nul 2>&1
echo ✅ 图标缓存已清理

echo.
echo 🔄 第五步：重启资源管理器...
taskkill /f /im explorer.exe >nul 2>&1
timeout /t 3 /nobreak >nul
start explorer.exe
echo ✅ 资源管理器已重启

echo.
echo ✅ 修复完成！
echo.
echo 📋 现在的设置：
echo    程序：%EXE_PATH%
echo    图标：从exe文件获取
echo    类型：GudaZip压缩文件
echo.
echo 🎯 验证方法：
echo    查看.7z和.zip文件应该显示："GudaZip压缩文件"
echo    图标应该是GudaZip的程序图标（从exe获取）
echo.
pause 