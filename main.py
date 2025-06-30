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
    try:
        # 启动时进行健康检查
        try:
            from gudazip.core.health_checker import HealthChecker
            
            print("正在进行程序健康检查...")
            is_healthy, issues = HealthChecker.check_all()
            
            if not is_healthy:
                print("⚠️ 发现以下问题：")
                for issue in issues:
                    print(f"  - {issue}")
                print()
            else:
                print("✅ 程序健康检查通过")
        except ImportError:
            print("⚠️ 无法进行健康检查，跳过...")
            is_healthy = True
            issues = []
        
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
        
        # 如果健康检查发现严重问题，显示警告对话框
        if not is_healthy:
            critical_issues = [issue for issue in issues if "缺少必需模块" in issue or "Python版本过低" in issue]
            if critical_issues:
                reply = QMessageBox.warning(
                    None, "程序环境问题", 
                    f"检测到以下问题，程序可能无法正常运行：\n\n" + 
                    "\n".join(f"• {issue}" for issue in critical_issues) + 
                    "\n\n是否继续运行？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if reply == QMessageBox.No:
                    return 0
        
        # 创建主窗口
        try:
            window = MainWindow()
        except Exception as e:
            QMessageBox.critical(None, "启动失败", f"无法创建主窗口：{str(e)}")
            return 1
        
        # 根据当前权限设置窗口标题
        if is_admin():
            window.setWindowTitle("GudaZip - 管理员模式")
            print("✅ 以管理员权限运行")
        else:
            window.setWindowTitle("GudaZip")
            print("以普通模式运行")
        
        # 检查命令行参数中是否有文件路径或右键菜单命令
        archive_file = None
        context_menu_action = None
        target_file = None
        
        # 解析命令行参数
        i = 1
        while i < len(sys.argv):
            arg = sys.argv[i]
            
            if arg.startswith('--'):
                # 处理右键菜单命令
                if arg in ['--add', '--extract-here', '--open', '--compress-zip', '--compress-7z']:
                    context_menu_action = arg
                    # 获取目标文件（下一个参数）
                    if i + 1 < len(sys.argv):
                        target_file = sys.argv[i + 1]
                        i += 1  # 跳过下一个参数
                elif arg == '--admin':
                    pass  # 管理员模式标志，已在前面处理
            elif os.path.isfile(arg) and not target_file:
                # 检查是否为支持的压缩文件
                archive_extensions = ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz']
                _, ext = os.path.splitext(arg.lower())
                if ext in archive_extensions:
                    archive_file = os.path.abspath(arg)
                else:
                    target_file = os.path.abspath(arg)
                    
            i += 1
        
        window.show()
        
        # 处理右键菜单命令
        if context_menu_action and target_file:
            try:
                handle_context_menu_action(window, context_menu_action, target_file)
            except Exception as e:
                QMessageBox.warning(window, "操作失败", f"执行右键菜单操作失败：{str(e)}")
        
        # 如果有压缩文件参数，在窗口显示后打开它
        elif archive_file:
            try:
                window.load_archive_from_commandline(archive_file)
            except Exception as e:
                QMessageBox.warning(window, "打开失败", f"无法打开压缩包：{str(e)}")
        
        return app.exec()
        
    except Exception as e:
        # 全局异常处理
        try:
            QMessageBox.critical(None, "程序错误", f"程序运行时发生错误：{str(e)}\n\n程序将退出。")
        except:
            # 如果连消息框都无法显示，则使用print
            print(f"严重错误：{str(e)}")
        return 1


def handle_context_menu_action(window, action, target_file):
    """处理右键菜单操作"""
    from gudazip.ui.create_archive_dialog import CreateArchiveDialog
    from gudazip.ui.extract_archive_dialog import ExtractArchiveDialog
    
    if action == '--add':
        # 添加到压缩包
        dialog = CreateArchiveDialog(window.archive_manager, "", window)
        dialog.selected_files.append(target_file)
        dialog.update_ui_state()
        dialog.exec()
        
    elif action == '--extract-here':
        # 解压到此处
        if window.archive_manager.is_archive_file(target_file):
            extract_path = os.path.dirname(target_file)
            try:
                success = window.archive_manager.extract_archive(target_file, extract_path)
                if success:
                    QMessageBox.information(window, "成功", f"文件已解压到：{extract_path}")
                else:
                    QMessageBox.warning(window, "失败", "解压操作失败")
            except Exception as e:
                QMessageBox.critical(window, "错误", f"解压失败：{str(e)}")
        else:
            QMessageBox.warning(window, "错误", "选择的文件不是有效的压缩包")
            
    elif action == '--open':
        # 用GudaZip打开
        if window.archive_manager.is_archive_file(target_file):
            window.open_archive_in_browser(target_file)
        else:
            QMessageBox.warning(window, "错误", "选择的文件不是有效的压缩包")
            
    elif action == '--compress-zip':
        # 压缩到.zip文件
        base_name = os.path.splitext(target_file)[0]
        output_path = f"{base_name}.zip"
        _create_archive(window, target_file, output_path, 'zip')
        
    elif action == '--compress-7z':
        # 压缩到.7z文件
        base_name = os.path.splitext(target_file)[0]
        output_path = f"{base_name}.7z"
        _create_archive(window, target_file, output_path, '7z')


def _create_archive(window, target_file, output_path, format_type):
    """创建压缩包的辅助函数"""
    try:
        success = window.archive_manager.create_archive(
            output_path,        # 第一个参数：输出文件路径
            [target_file],      # 第二个参数：要压缩的文件列表
            6,                  # 第三个参数：压缩级别（默认6）
            None                # 第四个参数：密码（默认None）
        )
        
        if success:
            # 显示成功消息，包含实际创建的文件名
            filename = os.path.basename(target_file)
            output_filename = os.path.basename(output_path)
            QMessageBox.information(window, "压缩成功", 
                                  f"已将 '{filename}' 压缩为 '{output_filename}'")
        else:
            QMessageBox.warning(window, "压缩失败", "创建压缩包失败")
            
    except Exception as e:
        QMessageBox.critical(window, "压缩错误", f"创建压缩包失败：{str(e)}")


if __name__ == "__main__":
    sys.exit(main()) 