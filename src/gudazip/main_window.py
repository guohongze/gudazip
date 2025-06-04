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
from PySide6.QtCore import Qt, QDir, QUrl, QSize
from PySide6.QtGui import QAction, QIcon, QStandardItemModel, QStandardItem, QFont
import os
import qtawesome as qta
import subprocess
import sys

from .ui.file_browser import FileBrowser
from .ui.create_archive_dialog import CreateArchiveDialog
from .ui.extract_archive_dialog import ExtractArchiveDialog
from .core.archive_manager import ArchiveManager
from .core.error_manager import ErrorManager, ErrorCategory, ErrorSeverity, get_error_manager


class MainWindow(QMainWindow):
    """GudaZip主窗口"""
    
    def __init__(self):
        super().__init__()
        self.archive_manager = ArchiveManager(self)
        self.error_manager = get_error_manager(self)
        
        self.init_ui()
        self.setup_actions()
        self.setup_menus()
        self.setup_toolbar()
        self.setup_statusbar()
        
        # 添加刷新动作到主窗口，使F5快捷键在整个窗口中生效
        self.addAction(self.action_refresh)
        
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("GudaZip - Python桌面压缩管理器")
        self.setMinimumSize(1000, 700)
        
        # 设置窗口图标
        self.set_window_icon()
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 只使用左侧文件系统导航，占据整个空间
        self.file_browser = FileBrowser()
        main_layout.addWidget(self.file_browser)
        
        # 连接信号
        self.file_browser.fileSelected.connect(self.on_file_selected)
        # 连接多选信号
        self.file_browser.filesSelected.connect(self.on_files_selected)
        # 连接打开压缩包信号 - 在文件浏览器内查看
        self.file_browser.archiveOpenRequested.connect(self.open_archive_in_browser)
        
    def setup_actions(self):
        """设置动作"""
        # 新建压缩包
        self.action_new_archive = QAction("压缩", self)
        self.action_new_archive.setIcon(qta.icon('fa5s.file-archive', color='#2e7d32'))
        self.action_new_archive.setShortcut("Ctrl+N")
        self.action_new_archive.triggered.connect(self.new_archive)
        
        # 解压到文件夹
        self.action_extract = QAction("解压", self)
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
        self.action_about = QAction("关于", self)
        self.action_about.setIcon(qta.icon('fa5s.info-circle', color='#1976d2'))
        self.action_about.triggered.connect(self.show_about)
        
    def setup_menus(self):
        """设置菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        file_menu.addAction(self.action_open_archive)
        file_menu.addAction(self.action_back_to_filesystem)
        file_menu.addSeparator()
        file_menu.addAction(self.action_new_archive)
        file_menu.addAction(self.action_extract)
        file_menu.addSeparator()
        file_menu.addAction("退出", self.close)
        
        # 视图菜单
        view_menu = menubar.addMenu("视图")
        view_menu.addAction(self.action_refresh)
        
        # 工具菜单
        tools_menu = menubar.addMenu("工具")
        tools_menu.addAction(self.action_settings)
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助")
        help_menu.addAction(self.action_about)
        
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
                if os.path.isfile(file_path):
                    item_text = f"📄 {file_path}"
                else:
                    item_text = f"📁 {file_path}"
                
                from PySide6.QtWidgets import QListWidgetItem
                from PySide6.QtCore import Qt
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, file_path)
                dialog.files_list.addItem(item)
        
        # 更新对话框状态
        dialog.update_ui_state()
        
        # 显示对话框
        if dialog.exec() == QDialog.Accepted:
            # 对话框中已经处理了创建过程
            self.path_label.setText("压缩包创建完成")
            
    def extract_archive(self):
        """解压压缩包"""
        # 获取当前选择的压缩包路径
        current_path = self.file_browser.get_current_path()
        
        # 如果没有选择文件，或选择的不是压缩包，使用文件对话框选择
        if not current_path or not self.archive_manager.is_archive_file(current_path):
            current_path, _ = QFileDialog.getOpenFileName(
                self, "选择要解压的压缩包", "",
                "压缩包文件 (*.zip *.rar *.7z *.tar *.gz *.bz2);;所有文件 (*.*)"
            )
            
        if not current_path:
            return
            
        # 检查文件是否存在
        if not os.path.exists(current_path):
            QMessageBox.warning(self, "警告", f"文件不存在：{current_path}")
            return
            
        # 检查是否为支持的压缩包格式
        if not self.archive_manager.is_archive_file(current_path):
            QMessageBox.warning(self, "警告", f"不支持的文件格式：{current_path}")
            return
            
        try:
            # 创建并显示解压对话框
            dialog = ExtractArchiveDialog(self.archive_manager, current_path, self)
            
            # 显示对话框
            if dialog.exec() == QDialog.Accepted:
                # 解压完成，更新状态
                self.path_label.setText("解压完成")
                    
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法打开解压对话框：{str(e)}")
        
    def show_settings(self):
        """显示设置对话框"""
        # TODO: 实现设置对话框
        QMessageBox.information(self, "提示", "设置功能开发中...")
        
    def show_about(self):
        """显示关于对话框"""
        QMessageBox.about(self, "关于 GudaZip", 
                         "GudaZip v0.1.0\n"
                         "Python桌面压缩管理器\n"
                         "基于PySide6开发") 

    def set_window_icon(self):
        """设置窗口图标"""
        try:
            # 获取图标路径
            current_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            icon_path = os.path.join(current_dir, "resources", "icons", "app_icon.png")
            
            # 检查图标文件是否存在
            if os.path.exists(icon_path):
                icon = QIcon(icon_path)
                self.setWindowIcon(icon)
                
                # 同时设置应用程序图标（在任务栏中显示）
                from PySide6.QtWidgets import QApplication
                QApplication.instance().setWindowIcon(icon)
            else:
                # 如果图标文件不存在，使用FontAwesome图标作为备选
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
    