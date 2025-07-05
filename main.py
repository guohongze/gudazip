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

# 添加模块路径到Python路径
# 在开发环境中使用src目录，在打包后的exe中直接使用当前目录
if getattr(sys, 'frozen', False):
    # 打包后的exe环境
    sys.path.insert(0, os.path.dirname(sys.executable))
else:
    # 开发环境
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from gudazip.main_window import MainWindow
from gudazip.core.environment_manager import get_environment_manager


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
        
        # 设置应用程序图标（使用环境变量）
        try:
            env_manager = get_environment_manager()
            icon_path = env_manager.get_app_icon_path()
            print(f"图标路径: {icon_path}")
            print(f"图标文件存在: {os.path.exists(icon_path) if icon_path else False}")
            
            if icon_path and os.path.exists(icon_path):
                icon = QIcon(icon_path)
                print(f"图标对象创建成功: {not icon.isNull()}")
                
                # 设置应用程序图标（影响所有窗口的默认图标）
                app.setWindowIcon(icon)
                
                # 在Windows上，还需要设置应用程序ID来确保任务栏图标正确显示
                if os.name == 'nt':
                    try:
                        import ctypes
                        # 设置应用程序用户模型ID，这有助于Windows正确识别应用程序
                        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('GudaZip.DesktopApp.1.0')
                        print("已设置Windows应用程序ID")
                    except Exception as e:
                        print(f"设置Windows应用程序ID失败: {e}")
                
                print("✅ 应用程序图标设置完成")
            else:
                print("❌ 图标文件不存在，使用默认图标")
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
                # 处理右键菜单命令 - 简化后的参数
                if arg in ['--add', '--extract-dialog']:
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
        
        # 处理右键菜单命令 - 不显示主窗口
        if context_menu_action and target_file:
            try:
                result = handle_context_menu_action(window, context_menu_action, target_file)
                # 如果启动了独立任务，等待一段时间确保任务进程正常启动
                if result == 'background_task_started':
                    import time
                    time.sleep(2)  # 等待2秒确保独立任务进程启动
                # 右键菜单操作完成后，如果没有其他需要，直接退出
                return 0
            except Exception as e:
                QMessageBox.warning(None, "操作失败", f"执行右键菜单操作失败：{str(e)}")
                return 1
        
        # 显示主窗口（只在非右键菜单模式下）
        window.show()
        
        # 检查是否需要提示设置为默认压缩软件
        try:
            check_default_app_setting(window)
        except Exception as e:
            print(f"检查默认压缩软件设置时出错: {e}")
        
        # 如果有压缩文件参数，在窗口显示后打开它
        if archive_file:
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


def check_default_app_setting(window):
    """检查是否需要提示设置为默认压缩软件"""
    try:
        from gudazip.ui.default_app_dialog import DefaultAppDialog
        
        # 获取配置管理器和文件关联管理器
        config_manager = window.config_manager
        file_association_manager = window.file_association_manager
        
        # 检查是否设置了不再提示
        never_ask = config_manager.get_config('startup.never_ask_default_app', False)
        if never_ask:
            return
        
        # 检查当前是否已经是默认压缩软件
        associated_extensions = file_association_manager.get_associated_extensions()
        all_extensions = file_association_manager.supported_extensions
        
        # 如果已经关联了大部分文件类型，认为已经是默认压缩软件
        if len(associated_extensions) >= len(all_extensions) * 0.8:  # 80%以上
            return
        
        # 显示默认压缩软件设置对话框
        dialog = DefaultAppDialog(
            parent=window,
            file_association_manager=file_association_manager,
            config_manager=config_manager
        )
        
        dialog.exec()
        
    except ImportError as e:
        print(f"无法导入默认应用设置对话框: {e}")
    except Exception as e:
        print(f"检查默认压缩软件设置时出错: {e}")


def handle_context_menu_action(window, action, target_file):
    """处理右键菜单操作"""
    from PySide6.QtWidgets import QDialog
    from gudazip.ui.create_archive_dialog import CreateArchiveDialog
    from gudazip.ui.extract_archive_dialog import ExtractArchiveDialog
    
    if action == '--add':
        # 弹出创建压缩包对话框
        try:
            dialog = CreateArchiveDialog(window.archive_manager)
            
            # 设置源文件/文件夹
            dialog.selected_files = [target_file]
            
            # 设置默认输出路径
            file_dir = os.path.dirname(target_file)
            file_base = os.path.splitext(os.path.basename(target_file))[0]
            if os.path.isdir(target_file):
                file_base = os.path.basename(target_file)
            default_archive_path = os.path.join(file_dir, f"{file_base}.zip")
            dialog.path_edit.setText(default_archive_path)
            
            # 更新UI状态以启用创建按钮
            dialog.update_ui_state()
            
            # 显示对话框
            result = dialog.exec()
            
            if result == QDialog.Accepted:
                # 检查是否启动了后台任务
                if hasattr(dialog, '_background_task_started') and dialog._background_task_started:
                    print(f"✅ 已启动后台压缩任务")
                    return 'background_task_started'
                else:
                    print(f"✅ 压缩任务已完成")
                    return 'completed'
            else:
                print("用户取消了压缩操作")
                return 'cancelled'
                
        except Exception as e:
            print(f"❌ 处理压缩对话框异常: {e}")
            return 'failed'
        
    elif action == '--extract-dialog':
        # 弹出解压对话框
        try:
            if window.archive_manager.is_archive_file(target_file):
                dialog = ExtractArchiveDialog(window.archive_manager, target_file)
                
                # 设置默认解压目录
                file_dir = os.path.dirname(target_file)
                file_base = os.path.splitext(os.path.basename(target_file))[0]
                extract_dir = os.path.join(file_dir, file_base)
                dialog.target_edit.setText(extract_dir)
                
                # 显示对话框
                result = dialog.exec()
                
                if result == QDialog.Accepted:
                    # 检查是否启动了后台任务
                    if hasattr(dialog, '_background_task_started') and dialog._background_task_started:
                        print(f"✅ 已启动后台解压任务")
                        return 'background_task_started'
                    else:
                        print(f"✅ 解压任务已完成")
                        return 'completed'
                else:
                    print("用户取消了解压操作")
                    return 'cancelled'
            else:
                print(f"❌ 选择的文件不是有效的压缩包: {target_file}")
                return 'failed'
                
        except Exception as e:
            print(f"❌ 处理解压对话框异常: {e}")
            return 'failed'
    
    return 'completed'





if __name__ == "__main__":
    sys.exit(main())