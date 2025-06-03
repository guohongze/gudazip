# -*- coding: utf-8 -*-
"""
GudaZip主窗口
实现资源管理器风格的界面
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QSplitter, QTreeView, QListView, QToolBar, QMenuBar,
    QStatusBar, QLabel, QTabWidget, QPushButton, QFileDialog,
    QMessageBox, QFileSystemModel
)
from PySide6.QtCore import Qt, QDir, QUrl
from PySide6.QtGui import QAction, QIcon, QStandardItemModel, QStandardItem

from .ui.file_browser import FileBrowser
from .ui.archive_viewer import ArchiveViewer
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
        self.setMinimumSize(1000, 700)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QHBoxLayout(central_widget)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
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
        splitter.setSizes([300, 700])
        
        # 连接信号
        self.file_browser.fileSelected.connect(self.on_file_selected)
        
    def setup_actions(self):
        """设置动作"""
        # 新建压缩包
        self.action_new_archive = QAction("新建压缩包", self)
        self.action_new_archive.setShortcut("Ctrl+N")
        self.action_new_archive.triggered.connect(self.new_archive)
        
        # 打开压缩包
        self.action_open_archive = QAction("打开压缩包", self)
        self.action_open_archive.setShortcut("Ctrl+O")
        self.action_open_archive.triggered.connect(self.open_archive)
        
        # 解压到文件夹
        self.action_extract = QAction("解压到...", self)
        self.action_extract.setShortcut("Ctrl+E")
        self.action_extract.triggered.connect(self.extract_archive)
        
        # 添加文件
        self.action_add_files = QAction("添加文件", self)
        self.action_add_files.setShortcut("Ctrl+A")
        self.action_add_files.triggered.connect(self.add_files)
        
        # 测试压缩包
        self.action_test = QAction("测试压缩包", self)
        self.action_test.setShortcut("Ctrl+T")
        self.action_test.triggered.connect(self.test_archive)
        
        # 设置
        self.action_settings = QAction("设置", self)
        self.action_settings.triggered.connect(self.show_settings)
        
        # 关于
        self.action_about = QAction("关于", self)
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
                tab_name = file_path.split('/')[-1]  # 只显示文件名
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
        file_path, _ = QFileDialog.getSaveFileName(
            self, "新建压缩包", "", 
            "ZIP文件 (*.zip);;RAR文件 (*.rar);;7z文件 (*.7z);;所有文件 (*.*)"
        )
        if file_path:
            # TODO: 实现新建压缩包功能
            QMessageBox.information(self, "提示", f"将创建压缩包：{file_path}")
            
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
        # TODO: 实现解压功能
        QMessageBox.information(self, "提示", "解压功能开发中...")
        
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