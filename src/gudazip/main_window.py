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

from .ui.file_browser import FileBrowser
from .ui.archive_viewer import ArchiveViewer
from .ui.create_archive_dialog import CreateArchiveDialog
from .ui.extract_archive_dialog import ExtractArchiveDialog
from .core.archive_manager import ArchiveManager


class MainWindow(QMainWindow):
    """GudaZip主窗口"""
    
    def __init__(self):
        super().__init__()
        self.archive_manager = ArchiveManager()
        self.init_ui()
        self.setup_actions()
        self.setup_menus()
        self.setup_toolbar()
        self.setup_statusbar()
        
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("GudaZip - Python桌面压缩管理器")
        self.setMinimumSize(1200, 700)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QHBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧文件系统导航
        self.file_browser = FileBrowser()
        splitter.addWidget(self.file_browser)
        
        # 右侧文件列表/压缩包内容查看器
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        
        # 添加默认的文件浏览标签
        self.archive_viewer = ArchiveViewer()
        self.tab_widget.addTab(self.archive_viewer, "文件浏览")
        
        splitter.addWidget(self.tab_widget)
        
        # 设置分割器比例
        splitter.setSizes([300, 900])
        
        main_layout.addWidget(splitter)
        
        # 连接信号
        self.file_browser.fileSelected.connect(self.on_file_selected)
        # 连接多选信号
        self.file_browser.filesSelected.connect(self.on_files_selected)
        
    def setup_actions(self):
        """设置动作"""
        # 新建压缩包
        self.action_new_archive = QAction("新建压缩包", self)
        self.action_new_archive.setIcon(qta.icon('fa5s.file-archive', color='#2e7d32'))
        self.action_new_archive.setShortcut("Ctrl+N")
        self.action_new_archive.triggered.connect(self.new_archive)
        
        # 打开压缩包
        self.action_open_archive = QAction("打开压缩包", self)
        self.action_open_archive.setIcon(qta.icon('fa5s.folder-open', color='#f57c00'))
        self.action_open_archive.setShortcut("Ctrl+O")
        self.action_open_archive.triggered.connect(self.open_archive)
        
        # 解压到文件夹
        self.action_extract = QAction("解压到...", self)
        self.action_extract.setIcon(qta.icon('fa5s.file-export', color='#1976d2'))
        self.action_extract.setShortcut("Ctrl+E")
        self.action_extract.triggered.connect(self.extract_archive)
        
        # 添加文件
        self.action_add_files = QAction("添加文件", self)
        self.action_add_files.setIcon(qta.icon('fa5s.plus-circle', color='#388e3c'))
        self.action_add_files.setShortcut("Ctrl+A")
        self.action_add_files.triggered.connect(self.add_files)
        
        # 测试压缩包
        self.action_test = QAction("测试压缩包", self)
        self.action_test.setIcon(qta.icon('fa5s.check-circle', color='#7b1fa2'))
        self.action_test.setShortcut("Ctrl+T")
        self.action_test.triggered.connect(self.test_archive)
        
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
        file_menu.addAction(self.action_new_archive)
        file_menu.addAction(self.action_open_archive)
        file_menu.addSeparator()
        file_menu.addAction(self.action_extract)
        file_menu.addAction(self.action_add_files)
        file_menu.addSeparator()
        file_menu.addAction("退出", self.close)
        
        # 工具菜单
        tools_menu = menubar.addMenu("工具")
        tools_menu.addAction(self.action_test)
        tools_menu.addSeparator()
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
        toolbar.addAction(self.action_open_archive)
        toolbar.addSeparator()
        toolbar.addAction(self.action_extract)
        toolbar.addAction(self.action_add_files)
        toolbar.addSeparator()
        toolbar.addAction(self.action_test)
        
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
            self.open_archive_file(file_path)
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
        
    def open_archive_file(self, file_path):
        """打开压缩包文件"""
        try:
            # 检查是否已经打开
            for i in range(self.tab_widget.count()):
                if self.tab_widget.tabText(i) == file_path:
                    self.tab_widget.setCurrentIndex(i)
                    return
                    
            # 创建新的压缩包查看器
            archive_viewer = ArchiveViewer(file_path)
            archive_info = self.archive_manager.get_archive_info(file_path)
            
            if archive_info:
                archive_viewer.load_archive(archive_info)
                tab_name = os.path.basename(file_path)  # 只显示文件名
                self.tab_widget.addTab(archive_viewer, tab_name)
                self.tab_widget.setCurrentWidget(archive_viewer)
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法打开压缩包：{str(e)}")
            
    def close_tab(self, index):
        """关闭标签页"""
        if index > 0:  # 不允许关闭第一个标签（文件浏览）
            self.tab_widget.removeTab(index)
            
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
        
        # 使用Windows标准路径格式
        default_path = os.path.join(default_dir, f"{default_name}.zip")
        
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
            # 这里可以添加后续处理，比如刷新界面等
            self.path_label.setText("压缩包创建完成")
            
            # 可选：打开刚创建的压缩包
            archive_path = dialog.path_edit.text()
            if os.path.exists(archive_path):
                self.open_archive_file(archive_path)
            
    def open_archive(self):
        """打开压缩包"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "打开压缩包", "",
            "压缩包文件 (*.zip *.rar *.7z *.tar *.gz *.bz2);;所有文件 (*.*)"
        )
        if file_path:
            self.open_archive_file(file_path)
            
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
                
                # 可选：在文件浏览器中显示解压后的文件夹
                extract_path = dialog.target_edit.text()
                if os.path.exists(extract_path):
                    # 可以在这里添加打开文件夹的功能
                    pass
                    
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法打开解压对话框：{str(e)}")
        
    def add_files(self):
        """添加文件到压缩包"""
        # TODO: 实现添加文件功能
        QMessageBox.information(self, "提示", "添加文件功能开发中...")
        
    def test_archive(self):
        """测试压缩包"""
        # TODO: 实现测试功能
        QMessageBox.information(self, "提示", "测试功能开发中...")
        
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