#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GudaZip - Python桌面压缩管理器
主入口文件
"""

import sys
import os
import ctypes
import subprocess
from PySide6.QtWidgets import QApplication, QMessageBox, QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
from PySide6.QtCore import QCoreApplication, QTranslator, QLocale
from PySide6.QtGui import QIcon

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from gudazip.main_window import MainWindow


def is_admin():
    """检查当前进程是否具有管理员权限"""
    try:
        if os.name == 'nt':  # Windows
            return ctypes.windll.shell32.IsUserAnAdmin()
        else:  # Unix/Linux/macOS
            return os.geteuid() == 0
    except:
        return False


def request_admin_permission(reason="访问系统文件"):
    """当需要时申请管理员权限"""
    reply = QMessageBox.question(
        None,
        "需要管理员权限",
        f"当前操作需要管理员权限才能{reason}。\n\n"
        f"是否重新以管理员身份启动程序？",
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.Yes
    )
    
    if reply == QMessageBox.Yes:
        try:
            if os.name == 'nt':  # Windows
                python_exe = sys.executable
                script_path = os.path.abspath(__file__)
                
                result = ctypes.windll.shell32.ShellExecuteW(
                    None,
                    "runas",
                    python_exe,
                    f'"{script_path}" --admin',
                    None,
                    1
                )
                
                if result > 32:
                    return True
        except:
            pass
        
        QMessageBox.warning(
            None,
            "权限申请失败",
            "无法获取管理员权限，某些操作可能无法完成。"
        )
    
    return False


def main():
    """主函数"""
    # 检查是否通过命令行强制管理员模式
    force_admin = '--admin' in sys.argv
    
    app = QApplication(sys.argv)
    app.setApplicationName("GudaZip")
    app.setApplicationVersion("0.1.0")
    app.setOrganizationName("GudaZip Team")
    
    # 设置中文语言
    translator = QTranslator()
    locale = QLocale.system()
    if translator.load(locale, "gudazip", "_", "resources/translations"):
        app.installTranslator(translator)
    
    # 设置应用程序图标
    try:
        icon_path = os.path.join(os.path.dirname(__file__), "resources", "icons", "app_icon.png")
        if os.path.exists(icon_path):
            app.setWindowIcon(QIcon(icon_path))
    except Exception as e:
        print(f"设置应用图标失败: {e}")
    
    # 创建主窗口
    window = MainWindow()
    
    # 根据当前权限设置窗口标题
    if is_admin():
        window.setWindowTitle("GudaZip - 管理员模式")
        print("✅ 以管理员权限运行")
    else:
        window.setWindowTitle("GudaZip")
        print("以普通模式运行")
    
    # 检查命令行参数中是否有文件路径
    archive_file = None
    for arg in sys.argv[1:]:
        if not arg.startswith('--') and os.path.isfile(arg):
            # 检查是否为支持的压缩文件
            archive_extensions = ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz']
            _, ext = os.path.splitext(arg.lower())
            if ext in archive_extensions:
                archive_file = os.path.abspath(arg)
                break
    
    window.show()
    
    # 如果有压缩文件参数，在窗口显示后打开它
    if archive_file:
        # 使用简单的系统打开方式
        window.load_archive_from_commandline(archive_file)
    
    return app.exec()


if __name__ == "__main__":
    sys.exit(main()) 