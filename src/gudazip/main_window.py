# -*- coding: utf-8 -*-
"""
GudaZip主窗口
实现资源管理器风格的界面
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QSplitter, QTreeView, QListView, QToolBar, QMenuBar,
    QStatusBar, QLabel, QTabWidget, QPushButton, QFileDialog,
    QMessageBox, QFileSystemModel, QDialog
)
from PySide6.QtCore import Qt, QDir, QUrl, QSize, QTimer
from PySide6.QtGui import QAction, QIcon, QStandardItemModel, QStandardItem, QFont
from PySide6.QtWidgets import QApplication
import os
import qtawesome as qta
import subprocess
import sys

from .ui.file_browser import FileBrowser
from .ui.create_archive_dialog import CreateArchiveDialog
from .ui.extract_archive_dialog import ExtractArchiveDialog
from .ui.settings_dialog import SettingsDialog
from .ui.help_dialog import HelpDialog
from .core.archive_manager import ArchiveManager
from .core.error_manager import ErrorManager, ErrorCategory, ErrorSeverity, get_error_manager
from .core.state_manager import StateManager, StateScope, StatePersistenceType, get_state_manager
from .core.config_manager import ConfigManager, get_config_manager


class MainWindow(QMainWindow):
    """GudaZip主窗口"""
    
    def __init__(self):
        super().__init__()
        self.archive_manager = ArchiveManager(self)
        self.error_manager = get_error_manager(self)
        self.state_manager = get_state_manager(self)
        self.config_manager = get_config_manager(self)
        
        # 初始化后台任务管理器
        from .ui.background_task_manager import get_background_task_manager
        self.background_task_manager = get_background_task_manager()
        print("后台任务管理器已初始化")
        
        self.init_ui()
        self.setup_actions()
        self.setup_menus()
        self.setup_toolbar()
        self.setup_statusbar()
        
        # 连接配置变更信号
        self.config_manager.config_changed.connect(self.on_config_changed)
        
        # 恢复窗口状态
        self.restore_window_state()
        
        # 添加刷新动作到主窗口，使F5快捷键在整个窗口中生效
        self.addAction(self.action_refresh)
        
    def showEvent(self, event):
        """窗口显示事件 - 强制刷新任务栏图标"""
        super().showEvent(event)
        # 延迟刷新图标，确保窗口完全显示后再设置
        QTimer.singleShot(100, self.force_refresh_taskbar_icon)
        
    def force_refresh_taskbar_icon(self):
        """强制刷新任务栏图标"""
        try:
            # 重新设置窗口图标
            current_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            icon_path = os.path.join(current_dir, "resources", "icons", "app.ico")
            
            if os.path.exists(icon_path):
                icon = QIcon(icon_path)
                # 设置窗口图标
                self.setWindowIcon(icon)
                # 设置应用程序图标（影响任务栏）
                QApplication.instance().setWindowIcon(icon)
                # 强制刷新窗口
                self.update()
        except Exception as e:
            print(f"强制刷新任务栏图标失败: {e}")
        
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("GudaZip - 压缩包管理工具")
        # 设置窗口图标
        self.set_window_icon()
        
        # 应用外观配置
        self.apply_appearance_config()
        
        # 创建中央窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 创建文件浏览器
        self.file_browser = FileBrowser(self)
        layout.addWidget(self.file_browser)
        
        # 连接信号
        self.file_browser.fileSelected.connect(self.on_file_selected)
        # 连接多选信号
        self.file_browser.filesSelected.connect(self.on_files_selected)
        # 连接打开压缩包信号 - 在文件浏览器内查看
        self.file_browser.archiveOpenRequested.connect(self.open_archive_in_browser)
        
    def apply_appearance_config(self):
        """应用外观配置"""
        try:
            appearance_config = self.config_manager.get_appearance_config()
            
            # 设置字体
            font = QFont(appearance_config['font_family'], appearance_config['font_size'])
            self.setFont(font)
            
            # 设置窗口透明度
            self.setWindowOpacity(appearance_config['window_opacity'])
                
        except Exception as e:
            self.error_manager.handle_exception(
                e,
                context={"operation": "apply_appearance_config"},
                category=ErrorCategory.APP_CONFIGURATION,
                show_dialog=False
            )
    
    def on_config_changed(self, key: str, old_value, new_value):
        """处理配置变更"""
        try:
            if key.startswith('appearance.'):
                # 外观相关配置变更，重新应用配置
                self.apply_appearance_config()
            elif key.startswith('window.'):
                # 窗口相关配置变更
                if key == 'window.center_on_startup':
                    # 居中设置变更时不需要立即处理，下次启动时生效
                    pass
            elif key.startswith('behavior.'):
                # 行为相关配置变更，通知文件浏览器
                if key == 'behavior.file_view_mode':
                    # 更新文件浏览器的视图模式
                    if hasattr(self.file_browser, 'set_view_mode'):
                        self.file_browser.set_view_mode(new_value)
                        
        except Exception as e:
            self.error_manager.handle_exception(
                e,
                context={"operation": "on_config_changed", "key": key},
                category=ErrorCategory.APP_CONFIGURATION,
                show_dialog=False
            )
    
    def setup_actions(self):
        """设置动作"""
        # 新建压缩包
        self.action_new_archive = QAction("添加", self)
        self.action_new_archive.setIcon(qta.icon('fa5s.file-archive', color='#2e7d32'))
        self.action_new_archive.setShortcut("Ctrl+N")
        self.action_new_archive.triggered.connect(self.new_archive)
        
        # 解压到文件夹
        self.action_extract = QAction("解压到", self)
        self.action_extract.setIcon(qta.icon('fa5s.file-export', color='#1976d2'))
        self.action_extract.setShortcut("Ctrl+E")
        self.action_extract.triggered.connect(self.extract_archive)
        
        # 打开压缩包 - 简单版本
        self.action_open_archive = QAction("打开", self)
        self.action_open_archive.setIcon(qta.icon('fa5s.folder-open', color='#ff9800'))
        self.action_open_archive.setShortcut("Ctrl+O")
        self.action_open_archive.triggered.connect(self.open_archive_simple)
        
        # 返回文件系统按钮 - 在setup_actions中创建，但初始禁用
        self.action_back_to_filesystem = QAction("返回文件系统", self)
        self.action_back_to_filesystem.setIcon(qta.icon('fa5s.arrow-left', color='#2196f3'))
        self.action_back_to_filesystem.setShortcut("Ctrl+B")
        self.action_back_to_filesystem.triggered.connect(self.exit_archive_mode)
        self.action_back_to_filesystem.setEnabled(False)  # 初始时禁用
        
        # 刷新动作 (F5快捷键)
        self.action_refresh = QAction("刷新", self)
        self.action_refresh.setIcon(qta.icon('fa5s.sync-alt', color='#2196f3'))
        self.action_refresh.setShortcut("F5")
        self.action_refresh.triggered.connect(self.refresh_view)
        
        # 设置
        self.action_settings = QAction("设置", self)
        self.action_settings.setIcon(qta.icon('fa5s.cog', color='#616161'))
        self.action_settings.triggered.connect(self.show_settings)
        
        # 关于
        self.action_about = QAction("帮助", self)
        self.action_about.setIcon(qta.icon('fa5s.question-circle', color='#1976d2'))
        self.action_about.triggered.connect(self.show_help)
        
    def setup_menus(self):
        """设置菜单栏"""
        # 隐藏菜单栏，不需要任何菜单
        self.menuBar().hide()
    
    def setup_toolbar(self):
        """设置工具栏"""
        toolbar = self.addToolBar("主工具栏")
        toolbar.setIconSize(QSize(24, 24))
        toolbar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        
        # 设置工具栏样式
        toolbar.setStyleSheet("""
        QToolBar {
            background-color: #f8f9fa;
            border: 1px solid #e0e0e0;
            border-radius: 4px;
            spacing: 3px;
            padding: 5px;
        }
        QToolButton {
            background-color: transparent;
            border: 1px solid transparent;
            border-radius: 4px;
            padding: 5px;
            margin: 2px;
            min-width: 60px;
        }
        QToolButton:hover {
            background-color: #e3f2fd;
            border-color: #90caf9;
        }
        QToolButton:pressed {
            background-color: #bbdefb;
            border-color: #64b5f6;
        }
        QToolBar::separator {
            background-color: #d0d0d0;
            width: 1px;
            margin: 5px;
        }
        """)
        
        # 添加动作到工具栏
        toolbar.addAction(self.action_new_archive)
        toolbar.addSeparator()
        toolbar.addAction(self.action_extract)
        toolbar.addSeparator()
        toolbar.addAction(self.action_open_archive)
        toolbar.addSeparator()
        toolbar.addAction(self.action_settings)
        toolbar.addSeparator()
        toolbar.addAction(self.action_about)
        toolbar.addSeparator()
        toolbar.addAction(self.action_back_to_filesystem)
        
    def setup_statusbar(self):
        """设置状态栏"""
        statusbar = self.statusBar()
        
        # 当前路径标签
        self.path_label = QLabel("就绪")
        statusbar.addWidget(self.path_label)
        
        # 文件统计标签
        self.stats_label = QLabel("")
        statusbar.addPermanentWidget(self.stats_label)
        
    def on_file_selected(self, file_path):
        """文件选择事件处理"""
        if self.archive_manager.is_archive_file(file_path):
            # 压缩包文件，显示信息
            self.path_label.setText(f"压缩包：{file_path}")
        else:
            self.path_label.setText(f"当前：{file_path}")
            
    def on_files_selected(self, files_path):
        """多文件选择事件处理"""
        if len(files_path) > 1:
            # 显示多选状态
            self.path_label.setText(f"已选择 {len(files_path)} 个项目")
        elif len(files_path) == 1:
            # 单选状态
            self.path_label.setText(f"当前：{files_path[0]}")
        else:
            self.path_label.setText("就绪")
        
    def new_archive(self):
        """新建压缩包"""
        # 检查是否处于压缩包查看模式
        if self.file_browser.archive_viewing_mode:
            # 在压缩包查看模式下，"添加"按钮应该用于向压缩包中添加文件
            self.add_files_to_archive()
            return
        
        # 获取当前选择的文件路径
        selected_paths = self.file_browser.get_selected_paths()
        current_path = self.file_browser.get_current_path()
        
        # 确定默认保存路径和文件名
        default_dir = ""
        default_name = "新建压缩包"
        
        if selected_paths:
            # 使用选中的文件列表
            target_files = selected_paths
            
            # 确定默认保存目录：使用第一个选中项目的父目录
            first_path = selected_paths[0]
            if os.path.isfile(first_path):
                default_dir = os.path.dirname(first_path)
            else:
                default_dir = os.path.dirname(first_path) if os.path.dirname(first_path) else first_path
            
            # 确定默认文件名逻辑
            directories = [p for p in selected_paths if os.path.isdir(p)]
            files = [p for p in selected_paths if os.path.isfile(p)]
            
            if directories:
                # 如果有目录，优先使用目录名（排序后的第一个）
                directories.sort()
                default_name = os.path.basename(directories[0])
            elif files:
                # 如果只有文件，使用排序后第一个文件的名称（不包含扩展名）
                files.sort()
                default_name = os.path.splitext(os.path.basename(files[0]))[0]
                
        elif current_path:
            # 使用当前路径
            target_files = [current_path]
            
            if os.path.isfile(current_path):
                default_dir = os.path.dirname(current_path)
                default_name = os.path.splitext(os.path.basename(current_path))[0]
            else:
                default_dir = os.path.dirname(current_path) if os.path.dirname(current_path) else current_path
                default_name = os.path.basename(current_path)
        else:
            # 没有选择任何文件
            target_files = []
            default_dir = os.path.expanduser("~")
            default_name = "新建压缩包"
        
        # 使用统一的路径格式（正斜杠）
        default_path = os.path.join(default_dir, f"{default_name}.zip").replace("\\", "/")
        
        # 创建并显示创建压缩包对话框
        dialog = CreateArchiveDialog(self.archive_manager, default_path, self)
        
        # 预先添加选中的文件到对话框中
        for file_path in target_files:
            if os.path.exists(file_path):
                dialog.selected_files.append(file_path)
        
        # 更新对话框状态
        dialog.update_ui_state()
        
        # 显示对话框
        if dialog.exec() == QDialog.Accepted:
            # 对话框中已经处理了创建过程
            self.path_label.setText("压缩包创建完成")
    
    def add_files_to_archive(self):
        """向压缩包中添加文件"""
        try:
            # 弹出文件选择对话框
            files, _ = QFileDialog.getOpenFileNames(
                self, 
                "选择要添加到压缩包的文件", 
                "",
                "所有文件 (*.*)"
            )
            
            if not files:
                return
            
            # 获取当前压缩包路径
            archive_path = self.file_browser.current_archive_path
            if not archive_path:
                QMessageBox.warning(self, "错误", "无法获取当前压缩包路径")
                return
            
            # 检查文件是否存在
            existing_files = [f for f in files if os.path.exists(f)]
            if not existing_files:
                QMessageBox.warning(self, "错误", "选择的文件不存在")
                return
            
            # 显示确认对话框
            reply = QMessageBox.question(
                self, 
                "确认添加", 
                f"确定要将 {len(existing_files)} 个文件添加到压缩包中吗？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                try:
                    # 调用压缩包管理器添加文件
                    success = self.archive_manager.add_files_to_archive(
                        archive_path, 
                        existing_files
                    )
                    
                    if success:
                        QMessageBox.information(self, "成功", f"成功添加了 {len(existing_files)} 个文件到压缩包")
                        
                        # 刷新压缩包视图
                        self.refresh_archive_view()
                    else:
                        QMessageBox.warning(self, "失败", "添加文件失败")
                        
                except Exception as e:
                    QMessageBox.critical(self, "错误", f"添加文件失败：{str(e)}")
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"添加文件时发生错误：{str(e)}")
            # 记录详细错误信息
            import traceback
            print(f"添加文件错误详情：{traceback.format_exc()}")
    
    def refresh_archive_view(self):
        """刷新压缩包视图"""
        try:
            if not self.file_browser.archive_viewing_mode:
                return
            
            # 重新获取压缩包信息
            archive_path = self.file_browser.current_archive_path
            if archive_path and os.path.exists(archive_path):
                archive_info = self.archive_manager.get_archive_info(archive_path)
                if archive_info:
                    # 更新文件浏览器的压缩包内容
                    archive_files = archive_info.get('files', [])
                    self.file_browser.archive_file_list = archive_files
                    
                    # 刷新显示
                    self.file_browser.display_archive_directory_content()
                    
                    # 更新状态栏
                    file_count = len(archive_files)
                    total_size = archive_info.get('total_size', 0)
                    compressed_size = archive_info.get('compressed_size', 0)
                    
                    def format_size(size_bytes):
                        for unit in ['B', 'KB', 'MB', 'GB']:
                            if size_bytes < 1024.0:
                                return f"{size_bytes:.1f} {unit}"
                            size_bytes /= 1024.0
                        return f"{size_bytes:.1f} TB"
                    
                    status_text = f"压缩包：{os.path.basename(archive_path)} ({file_count} 个文件, " \
                                 f"原始大小: {format_size(total_size)}, 压缩后: {format_size(compressed_size)})"
                    self.path_label.setText(status_text)
                    
        except Exception as e:
            print(f"刷新压缩包视图失败：{str(e)}")
            # 记录详细错误信息
            import traceback
            print(f"刷新压缩包视图错误详情：{traceback.format_exc()}")
            
    def extract_archive(self):
        """解压压缩包 - 使用独立的解压处理器"""
        from .core.extract_handler import ExtractHandler
        
        # 创建解压处理器
        extract_handler = ExtractHandler(self.archive_manager, self)
        
        try:
            # 获取当前选中的文件路径
            selected_paths = self.file_browser.get_selected_paths()
            current_path = self.file_browser.get_current_path()
            
            # 检查是否处于压缩包查看模式
            if self.file_browser.archive_viewing_mode:
                # 压缩包查看模式：解压选中的文件或整个压缩包
                archive_path = self.file_browser.current_archive_path
                current_view_path = getattr(self.file_browser, 'archive_current_dir', '')
                
                success = extract_handler.extract_from_archive_view(
                    archive_path, 
                    selected_paths or [], 
                    current_view_path
                )
                
                if success:
                    print(f"✅ 压缩包解压操作完成")
                
            else:
                # 文件系统模式：解压选中的压缩包文件
                success = extract_handler.extract_from_filesystem(selected_paths or [], current_path)
                
                if success:
                    print(f"✅ 文件系统解压操作完成")
                    
        except Exception as e:
            QMessageBox.critical(self, "错误", f"解压操作失败：{str(e)}")
        
    def show_settings(self):
        """显示设置对话框"""
        dialog = SettingsDialog(self)
        dialog.exec()
        
    def show_help(self):
        """显示帮助对话框"""
        dialog = HelpDialog(self)
        dialog.exec()

    def set_window_icon(self):
        """设置窗口图标"""
        try:
            # 获取图标路径
            current_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            icon_path = os.path.join(current_dir, "resources", "icons", "app.ico")
            
            print(f"主窗口图标路径: {icon_path}")
            print(f"主窗口图标文件存在: {os.path.exists(icon_path)}")
            
            # 检查图标文件是否存在
            if os.path.exists(icon_path):
                icon = QIcon(icon_path)
                print(f"主窗口图标对象创建成功: {not icon.isNull()}")
                
                # 设置窗口图标
                self.setWindowIcon(icon)
                
                # 同时设置应用程序图标（在任务栏中显示）
                from PySide6.QtWidgets import QApplication
                QApplication.instance().setWindowIcon(icon)
                
                print("✅ 主窗口图标设置完成")
            else:
                # 如果图标文件不存在，使用FontAwesome图标作为备选
                print("❌ 图标文件不存在，使用FontAwesome备选图标")
                icon = qta.icon('fa5s.file-archive', color='#2e7d32')
                self.setWindowIcon(icon)
                
        except Exception as e:
            print(f"设置图标失败: {e}")
            # 使用FontAwesome图标作为备选
            try:
                icon = qta.icon('fa5s.file-archive', color='#2e7d32')
                self.setWindowIcon(icon)
            except:
                pass  # 如果备选图标也失败，则使用系统默认图标 

    def refresh_view(self):
        """刷新视图"""
        # 调用文件浏览器的刷新功能
        if hasattr(self, 'file_browser'):
            self.file_browser.refresh_view()
        else:
            print("file_browser不存在")
            
    def open_archive_simple(self):
        """简单的打开压缩包功能 - 工具栏按钮"""
        # 选择压缩包文件
        file_path, _ = QFileDialog.getOpenFileName(
            self, "打开压缩包", "",
            "压缩包文件 (*.zip *.rar *.7z *.tar *.gz *.bz2);;所有文件 (*.*)"
        )
        
        if file_path and os.path.exists(file_path):
            self.open_archive_in_browser(file_path)
    
    def open_archive_with_system(self, file_path):
        """使用系统默认程序打开压缩包"""
        try:
            if sys.platform == "win32":
                # Windows: 使用explorer直接打开压缩包
                subprocess.run(['explorer', file_path], check=True)
            elif sys.platform == "darwin":  # macOS
                subprocess.run(['open', file_path], check=True)
            else:  # Linux
                subprocess.run(['xdg-open', file_path], check=True)
            
            self.path_label.setText(f"已打开压缩包：{os.path.basename(file_path)}")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法打开压缩包：{str(e)}")
    
    def load_archive_from_commandline(self, archive_path):
        """从命令行加载压缩包 - 在文件浏览器内查看"""
        # 在文件浏览器内查看
        self.open_archive_in_browser(archive_path)
    
    def open_archive_in_browser(self, file_path):
        """在文件浏览器内查看压缩包"""
        try:
            # 验证文件路径
            if not file_path or not os.path.exists(file_path):
                QMessageBox.warning(self, "错误", f"文件不存在：{file_path}")
                return
                
            # 检查是否为支持的压缩包
            if not self.archive_manager.is_archive_file(file_path):
                QMessageBox.warning(self, "错误", "不支持的压缩文件格式")
                return
            
            # 验证压缩包完整性
            if not self.archive_manager.validate_archive(file_path):
                QMessageBox.critical(self, "错误", "压缩包文件已损坏或无法读取")
                return
            
            # 获取压缩包信息
            archive_info = self.archive_manager.get_archive_info(file_path)
            if not archive_info:
                QMessageBox.critical(self, "错误", "无法读取压缩包信息")
                return
            
            # 进入压缩包查看模式
            archive_files = archive_info.get('files', [])
            self.file_browser.enter_archive_mode(file_path, archive_files)
            
            # 更新状态栏和窗口标题
            file_count = len(archive_files)
            total_size = archive_info.get('total_size', 0)
            compressed_size = archive_info.get('compressed_size', 0)
            
            # 格式化大小
            def format_size(size_bytes):
                for unit in ['B', 'KB', 'MB', 'GB']:
                    if size_bytes < 1024.0:
                        return f"{size_bytes:.1f} {unit}"
                    size_bytes /= 1024.0
                return f"{size_bytes:.1f} TB"
            
            status_text = f"压缩包：{os.path.basename(file_path)} ({file_count} 个文件, " \
                         f"原始大小: {format_size(total_size)}, 压缩后: {format_size(compressed_size)})"
            self.path_label.setText(status_text)
            
            # 启用返回按钮
            self.action_back_to_filesystem.setEnabled(True)
            
            # 在窗口标题中显示当前压缩包
            base_title = "GudaZip"
            import main
            if main.is_admin():
                base_title = "GudaZip - 管理员模式"
            self.setWindowTitle(f"{base_title} - {os.path.basename(file_path)}")
            
        except PermissionError as e:
            QMessageBox.critical(self, "权限错误", f"没有权限访问压缩包：{str(e)}")
        except FileNotFoundError as e:
            QMessageBox.critical(self, "文件错误", f"文件未找到：{str(e)}")
        except ValueError as e:
            QMessageBox.critical(self, "文件格式错误", str(e))
        except Exception as e:
            QMessageBox.critical(self, "错误", f"打开压缩包失败：{str(e)}")
            # 记录详细错误信息到控制台
            import traceback
            print(f"详细错误信息：{traceback.format_exc()}")
    
    def exit_archive_mode(self):
        """退出压缩包查看模式"""
        try:
            # 使用文件浏览器的退出方法
            self.file_browser.exit_archive_mode()
            
            # 禁用返回文件系统按钮
            self.action_back_to_filesystem.setEnabled(False)
            
            # 恢复窗口标题
            base_title = "GudaZip"
            import main
            if main.is_admin():
                base_title = "GudaZip - 管理员模式"
            self.setWindowTitle(base_title)
            
            # 更新状态栏
            self.path_label.setText("就绪")
            
        except Exception as e:
            QMessageBox.warning(self, "警告", f"退出压缩包查看模式时发生错误：{str(e)}")
            # 强制重置状态
            self.action_back_to_filesystem.setEnabled(False)
            self.path_label.setText("就绪")
    
    def restore_window_state(self):
        """恢复窗口状态"""
        try:
            # 获取窗口配置
            window_config = self.config_manager.get_window_config()
            
            # 获取保存的窗口几何信息
            saved_geometry = self.state_manager.get_state("window.geometry")
            saved_maximized = self.state_manager.get_state("window.maximized", False)
            
            # 如果记住窗口大小和位置，并且有保存的几何信息
            if (window_config['remember_size'] and window_config['remember_position'] 
                and saved_geometry):
                self.restoreGeometry(saved_geometry)
                
                # 恢复最大化状态
                if saved_maximized:
                    self.showMaximized()
            else:
                # 使用默认大小
                default_width = window_config['default_width']
                default_height = window_config['default_height']
                
                # 如果记住窗口大小但不记住位置，使用保存的大小但居中显示
                if window_config['remember_size'] and saved_geometry:
                    self.restoreGeometry(saved_geometry)
                    if window_config['center_on_startup']:
                        self.center_on_screen()
                else:
                    # 使用默认大小
                    self.resize(default_width, default_height)
                    
                    # 如果启用启动时居中，则居中显示
                    if window_config['center_on_startup']:
                        self.center_on_screen()
                    else:
                        # 默认位置
                        self.move(100, 100)
                
                # 如果保存了最大化状态且允许恢复
                if saved_maximized and window_config['remember_size']:
                    self.showMaximized()
            
            # 恢复分割器状态（如果有的话）
            splitter_state = self.state_manager.get_state("window.splitter_state")
            if splitter_state and hasattr(self, 'splitter'):
                self.splitter.restoreState(splitter_state)
                
        except Exception as e:
            self.error_manager.handle_exception(
                e,
                context={"operation": "restore_window_state"},
                category=ErrorCategory.APP_CONFIGURATION,
                show_dialog=False
            )
            # 如果恢复失败，使用默认设置
            self.resize(1200, 800)
            self.center_on_screen()
    
    def center_on_screen(self):
        """将窗口居中显示"""
        try:
            # 获取屏幕几何信息
            screen = self.screen()
            if screen:
                screen_geometry = screen.availableGeometry()
                window_geometry = self.frameGeometry()
                
                # 计算居中位置
                center_point = screen_geometry.center()
                window_geometry.moveCenter(center_point)
                
                # 移动到居中位置
                self.move(window_geometry.topLeft())
            else:
                # 如果无法获取屏幕信息，使用默认位置
                self.move(100, 100)
                
        except Exception as e:
            self.error_manager.handle_exception(
                e,
                context={"operation": "center_on_screen"},
                category=ErrorCategory.APP_INTERNAL,
                show_dialog=False
            )
            # 备用位置
            self.move(100, 100)
    
    def save_window_state(self):
        """保存窗口状态"""
        try:
            # 保存窗口几何信息
            self.state_manager.set_state(
                "window.geometry", 
                self.saveGeometry(),
                scope=StateScope.WINDOW,
                persistence_type=StatePersistenceType.QSETTINGS,
                description="窗口几何信息"
            )
            
            # 保存最大化状态
            self.state_manager.set_state(
                "window.maximized", 
                self.isMaximized(),
                scope=StateScope.WINDOW,
                persistence_type=StatePersistenceType.QSETTINGS,
                description="窗口是否最大化"
            )
            
            # 保存分割器状态（如果有的话）
            if hasattr(self, 'splitter'):
                self.state_manager.set_state(
                    "window.splitter_state", 
                    self.splitter.saveState(),
                    scope=StateScope.WINDOW,
                    persistence_type=StatePersistenceType.QSETTINGS,
                    description="分割器状态"
                )
            
            # 保存所有状态到文件
            self.state_manager.save_all_states()
            
        except Exception as e:
            self.error_manager.handle_exception(
                e,
                context={"operation": "save_window_state"},
                category=ErrorCategory.APP_CONFIGURATION,
                show_dialog=False
            )

    def closeEvent(self, event):
        """窗口关闭事件"""
        try:
            # 清理后台任务管理器
            from .ui.background_task_manager import get_background_task_manager
            task_manager = get_background_task_manager()
            if task_manager:
                print("正在清理后台任务管理器...")
                task_manager.cleanup()
            
            # 保存窗口状态
            self.save_window_state()
            
            # 保存文件浏览器状态
            if hasattr(self, 'file_browser'):
                self.file_browser.save_browser_state()
            
            # 保存配置文件
            self.config_manager.save_configs()
            
            # 记录程序退出时间
            from datetime import datetime
            self.state_manager.set_state(
                "app.last_close_time",
                datetime.now().isoformat(),
                scope=StateScope.SESSION,
                persistence_type=StatePersistenceType.JSON,
                description="程序最后关闭时间"
            )
            
            print("程序关闭，所有配置已保存")  # 调试信息
            
            # 接受关闭事件
            event.accept()
            
        except Exception as e:
            self.error_manager.handle_exception(
                e,
                context={"operation": "close_event"},
                category=ErrorCategory.APP_INTERNAL,
                show_dialog=False
            )
            event.accept()  # 即使出错也要关闭
    