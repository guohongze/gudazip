# -*- coding: utf-8 -*-
"""
文件浏览器组件
实现左侧的文件系统树状导航
"""

from PySide6.QtCore import Qt, QDir, Signal, QModelIndex, QStandardPaths, QSize
from PySide6.QtGui import QIcon, QAction, QKeyEvent, QStandardItemModel, QStandardItem
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeView, QHeaderView, 
    QFileSystemModel, QComboBox, QLabel, QPushButton, QLineEdit, QListView,
    QMenu, QMessageBox, QInputDialog, QApplication, QDialog, QDialogButtonBox,
    QFileIconProvider
)
import os
import shutil
import subprocess
import sys
import qtawesome as qta
from datetime import datetime
import ctypes
from pathlib import Path
import tempfile
import zipfile

# Windows API 相关导入
if sys.platform == "win32":
    try:
        import win32com.client
        from win32api import GetFileVersionInfo, LOWORD, HIWORD
        import win32con
        import win32gui
        import win32ui
        from PIL import Image
        import tempfile
        HAS_WIN32 = True
    except ImportError:
        HAS_WIN32 = False
else:
    HAS_WIN32 = False


class EnhancedIconProvider(QFileIconProvider):
    """增强的图标提供器，专门处理快捷方式和获取高质量图标"""
    
    def __init__(self):
        super().__init__()
        self._icon_cache = {}  # 图标缓存
        
    def _get_enhanced_icon(self, file_path):
        """获取增强的文件图标"""
        try:
            # 只对快捷方式文件进行特殊处理
            if file_path.lower().endswith('.lnk') and HAS_WIN32:
                return self._get_shortcut_target_icon(file_path)
            
            # 对于所有其他文件类型，完全不干预，让系统自己处理
            # 这里不应该调用 super().icon()，而是应该返回 None 让系统使用默认行为
            return None
            
        except Exception as e:
            print(f"获取文件图标时出错 {file_path}: {e}")
            return None
    
    def icon(self, type_or_info):
        """重写图标获取方法"""
        if hasattr(type_or_info, 'filePath'):
            # 处理 QFileInfo 对象
            file_path = type_or_info.filePath()
            
            # 检查缓存
            if file_path in self._icon_cache:
                return self._icon_cache[file_path]
            
            # 获取增强图标
            enhanced_icon = self._get_enhanced_icon(file_path)
            
            # 如果获取到了增强图标，使用它并缓存
            if enhanced_icon and not enhanced_icon.isNull():
                self._icon_cache[file_path] = enhanced_icon
                return enhanced_icon
            
            # 否则使用系统默认行为
            default_icon = super().icon(type_or_info)
            self._icon_cache[file_path] = default_icon
            return default_icon
        else:
            # 处理 QFileIconProvider.IconType
            return super().icon(type_or_info)
    
    def _get_shortcut_target_icon(self, lnk_path):
        """获取快捷方式目标程序的图标"""
        if not HAS_WIN32:
            return None
        
        try:
            # 创建 Shell 对象
            shell = win32com.client.Dispatch("WScript.Shell")
            shortcut = shell.CreateShortCut(lnk_path)
            target_path = shortcut.Targetpath
            
            # 如果目标路径存在，使用临时QFileSystemModel获取其图标
            if target_path and os.path.exists(target_path):
                from PySide6.QtWidgets import QFileSystemModel
                temp_model = QFileSystemModel()
                index = temp_model.index(target_path)
                if index.isValid():
                    icon = temp_model.fileIcon(index)
                    if not icon.isNull():
                        return icon
            
            # 如果无法获取目标，返回None让系统使用默认图标
            return None
            
        except Exception as e:
            print(f"获取快捷方式图标时出错 {lnk_path}: {e}")
            return None


class FileBrowser(QWidget):
    """文件浏览器组件"""
    
    # 信号：文件被选中
    fileSelected = Signal(str)
    # 信号：多个文件被选中
    filesSelected = Signal(list)
    # 信号：请求打开压缩包
    archiveOpenRequested = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_view_mode = "详细信息"  # 当前视图模式
        # 剪贴板操作相关
        self.clipboard_items = []  # 剪贴板中的文件路径
        self.clipboard_operation = ""  # "copy" 或 "cut"
        
        # 压缩包查看模式相关
        self.archive_viewing_mode = False  # 是否处于压缩包查看模式
        self.archive_model = None  # 压缩包内容模型
        self.archive_path = None  # 当前压缩包路径
        self.archive_current_dir = ""  # 压缩包内当前目录
        self.archive_file_list = []  # 压缩包文件列表
        
        # 设置焦点策略，使其能接收键盘事件
        self.setFocusPolicy(Qt.StrongFocus)
        
        self.init_ui()
        
    def init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 先创建文件系统模型
        self.file_model = QFileSystemModel()
        
        # 设置文件过滤器，显示所有文件和文件夹
        self.file_model.setFilter(
            QDir.AllDirs | QDir.Files | QDir.NoDotAndDotDot
        )
        
        # 设置增强的图标提供器，确保显示高质量图标
        enhanced_icon_provider = EnhancedIconProvider()
        self.file_model.setIconProvider(enhanced_icon_provider)
        
        # 创建顶部工具栏
        toolbar_layout = QHBoxLayout()
        
        # 视图切换按钮（最左侧）
        self.view_toggle_btn = QPushButton()
        self.view_toggle_btn.setIcon(qta.icon('fa5s.list', color='#333'))
        self.view_toggle_btn.setToolTip("切换到图标视图")
        self.view_toggle_btn.setFixedSize(40, 40)  # 从32x32增加到40x40 (25%增长)
        self.view_toggle_btn.setStyleSheet("""
            QPushButton {
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                background-color: #f8f9fa;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #e3f2fd;
                border-color: #90caf9;
            }
            QPushButton:pressed {
                background-color: #bbdefb;
                border-color: #64b5f6;
            }
        """)
        self.view_toggle_btn.clicked.connect(self.toggle_view_mode)
        toolbar_layout.addWidget(self.view_toggle_btn)
        
        # 向上一级目录按钮
        self.up_button = QPushButton()
        self.up_button.setIcon(qta.icon('fa5s.arrow-up', color='#333'))
        self.up_button.setToolTip("上一级目录")
        self.up_button.setFixedSize(40, 40)  # 从32x32增加到40x40 (25%增长)
        self.up_button.setStyleSheet("""
            QPushButton {
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                background-color: #f8f9fa;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #e3f2fd;
                border-color: #90caf9;
            }
            QPushButton:pressed {
                background-color: #bbdefb;
                border-color: #64b5f6;
            }
            QPushButton:disabled {
                background-color: #f5f5f5;
                color: #ccc;
                border-color: #e0e0e0;
            }
        """)
        self.up_button.clicked.connect(self.go_up_directory)
        toolbar_layout.addWidget(self.up_button)
        
        # 位置标签和下拉框
        location_label = QLabel("位置:")
        location_label.setStyleSheet("""
            QLabel {
                font-weight: bold;
                color: #333;
                margin-right: 5px;
                margin-left: 8px;
                border: none;
                background: transparent;
                font-size: 15px;
            }
        """)
        toolbar_layout.addWidget(location_label)
        
        # 路径下拉选择框
        self.path_combo = QComboBox()
        self.path_combo.setEditable(True)
        self.path_combo.setMinimumWidth(350)
        self.path_combo.setMaximumHeight(40)  # 从32增加到40 (25%增长)
        self.path_combo.setStyleSheet("""
            QComboBox {
                border: 1px solid #d0d0d0;
                padding: 6px 12px;
                background-color: white;
                font-size: 15px;
                min-height: 25px;
                border-radius: 4px;
            }
            QComboBox:hover {
                border-color: #90caf9;
            }
            QComboBox:focus {
                border-color: #1976d2;
                outline: none;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 25px;
                border-left-width: 1px;
                border-left-color: #d0d0d0;
                border-left-style: solid;
                border-top-right-radius: 4px;
                border-bottom-right-radius: 4px;
                background-color: #f8f9fa;
            }
            QComboBox::down-arrow {
                width: 0; 
                height: 0; 
                border-left: 6px solid transparent;
                border-right: 6px solid transparent; 
                border-top: 6px solid #666;
            }
            QComboBox::down-arrow:hover {
                border-top-color: #333;
            }
            QComboBox QAbstractItemView {
                border: 2px solid #ccc;
                border-radius: 6px;
                background-color: white;
                selection-background-color: #e3f2fd;
                outline: none;
                font-size: 23px;
                padding: 5px;
            }
            QComboBox QAbstractItemView::item {
                padding: 10px 15px;
                min-height: 35px;
            }
        """)
        
        # 获取Windows标准路径
        desktop_path = QStandardPaths.writableLocation(QStandardPaths.DesktopLocation)
        documents_path = QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation)
        downloads_path = QStandardPaths.writableLocation(QStandardPaths.DownloadLocation)
        pictures_path = QStandardPaths.writableLocation(QStandardPaths.PicturesLocation)
        videos_path = QStandardPaths.writableLocation(QStandardPaths.MoviesLocation)
        music_path = QStandardPaths.writableLocation(QStandardPaths.MusicLocation)
        home_path = QStandardPaths.writableLocation(QStandardPaths.HomeLocation)
        
        # 添加Windows11风格图标到下拉框 - 使用更大的emoji图标
        windows_paths = [
            ("🖥️  桌面", desktop_path),
            ("💻  此电脑", ""),  # 特殊处理
            ("📂  文档", documents_path),
            ("🖼️  图片", pictures_path),
            ("⬇️  下载", downloads_path),
            ("🎬  视频", videos_path),
            ("🎵  音乐", music_path),
            ("👤  用户", home_path),
        ]
        
        for name, path in windows_paths:
            if path == "" or os.path.exists(path):
                if path == "":
                    # 此电脑特殊处理
                    self.path_combo.addItem(name, "ThisPC")
                else:
                    self.path_combo.addItem(name, path)
        
        # 现在连接信号（在模型创建之后）
        self.path_combo.currentTextChanged.connect(self.on_path_changed)
        
        # 为路径输入框添加回车键事件处理
        self.path_combo.lineEdit().returnPressed.connect(self.on_path_entered)
        
        toolbar_layout.addWidget(self.path_combo)
        
        # 搜索框紧随位置框（不添加弹性空间）
        search_label = QLabel("搜索:")
        search_label.setStyleSheet("""
            QLabel {
                font-weight: bold;
                color: #333;
                margin-left: 15px;
                margin-right: 5px;
                border: none;
                background: transparent;
                font-size: 15px;
            }
        """)
        toolbar_layout.addWidget(search_label)
        
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("在当前位置中搜索...")
        self.search_box.textChanged.connect(self.on_search_text_changed)
        self.search_box.setMinimumWidth(280)
        self.search_box.setMaximumWidth(350)
        self.search_box.setMaximumHeight(40)  # 从32增加到40，与下拉框一致
        self.search_box.setStyleSheet("""
            QLineEdit {
                border: 1px solid #d0d0d0;
                padding: 6px 12px;
                background-color: white;
                font-size: 15px;
                min-height: 25px;
                border-radius: 4px;
            }
            QLineEdit:hover {
                border-color: #90caf9;
            }
            QLineEdit:focus {
                border-color: #1976d2;
                outline: none;
            }
            QLineEdit::placeholder {
                color: #999;
                font-style: italic;
                font-size: 14px;
            }
        """)
        toolbar_layout.addWidget(self.search_box)
        
        # 添加刷新按钮
        self.refresh_button = QPushButton()
        self.refresh_button.setIcon(qta.icon('fa5s.sync-alt', color='#333'))
        self.refresh_button.setToolTip("刷新 (F5)")
        self.refresh_button.setFixedSize(40, 40)  # 与其他按钮保持一致
        self.refresh_button.setStyleSheet("""
            QPushButton {
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                background-color: #f8f9fa;
                padding: 8px;
                margin-left: 8px;
            }
            QPushButton:hover {
                background-color: #e3f2fd;
                border-color: #90caf9;
            }
            QPushButton:pressed {
                background-color: #bbdefb;
                border-color: #64b5f6;
            }
        """)
        self.refresh_button.clicked.connect(self.refresh_view)
        toolbar_layout.addWidget(self.refresh_button)
        
        # 添加弹性空间到最右侧
        toolbar_layout.addStretch()
        
        # 为整个工具栏添加样式
        toolbar_widget = QWidget()
        toolbar_widget.setLayout(toolbar_layout)
        toolbar_widget.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 8px;
                margin: 2px;
            }
        """)
        
        layout.addWidget(toolbar_widget)
        
        # 创建树视图（详细信息视图）
        self.tree_view = QTreeView()
        self.tree_view.setModel(self.file_model)
        
        # 设置多选模式
        self.tree_view.setSelectionMode(QTreeView.ExtendedSelection)
        
        # 强制设置上下文菜单策略，确保使用我们的自定义菜单
        self.tree_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree_view.customContextMenuRequested.connect(self.show_context_menu)
        
        # 创建列表视图（图标视图）
        self.list_view = QListView()
        self.list_view.setModel(self.file_model)
        self.list_view.setViewMode(QListView.IconMode)
        self.list_view.setResizeMode(QListView.Adjust)
        self.list_view.setSelectionMode(QListView.ExtendedSelection)
        self.list_view.setUniformItemSizes(True)
        
        # 设置Windows风格的大图标模式
        self.list_view.setFlow(QListView.LeftToRight)  # 从左到右流式布局
        self.list_view.setWrapping(True)  # 启用换行
        self.list_view.setSpacing(8)  # 设置项目间距
        
        # 设置图标和网格大小 - 模仿Windows大图标模式
        icon_size = 48  # Windows大图标通常是48x48
        grid_size = 80  # 给图标和文字留足够空间
        
        self.list_view.setIconSize(QSize(icon_size, icon_size))
        self.list_view.setGridSize(QSize(grid_size, grid_size))
        
        # 设置移动和拖拽
        self.list_view.setMovement(QListView.Static)  # 静态排列，不允许拖拽重排
        
        # 强制设置列表视图的上下文菜单策略
        self.list_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_view.customContextMenuRequested.connect(self.show_list_context_menu)
        
        # 为树视图添加样式
        self.tree_view.setStyleSheet("""
            QTreeView {
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                background-color: white;
                selection-background-color: #e3f2fd;
                selection-color: #1976d2;
                outline: none;
                font-size: 12px;
                padding: 5px;
            }
            QTreeView::item {
                padding: 4px;
                border: none;
                min-height: 20px;
            }
            QTreeView::item:hover {
                background-color: #f5f5f5;
                border-radius: 4px;
            }
            QTreeView::item:selected {
                background-color: #e3f2fd;
                border-radius: 4px;
            }
            QTreeView::item:selected:active {
                background-color: #bbdefb;
            }
            QTreeView::branch {
                background-color: transparent;
            }
            QTreeView::branch:has-siblings:!adjoins-item {
                border-image: none;
                border: none;
            }
            QTreeView::branch:has-siblings:adjoins-item {
                border-image: none;
                border: none;
            }
            QTreeView::branch:!has-children:!has-siblings:adjoins-item {
                border-image: none;
                border: none;
            }
            QTreeView::branch:closed:has-children:has-siblings {
                border-image: none;
                border: none;
            }
            QTreeView::branch:has-children:!has-siblings:closed {
                border-image: none;
                border: none;
            }
            QTreeView::branch:open:has-children:has-siblings {
                border-image: none;
                border: none;
            }
            QTreeView::branch:open:has-children:!has-siblings {
                border-image: none;
                border: none;
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                padding: 8px;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                font-weight: bold;
                color: #333;
            }
        """)
        
        # 为列表视图添加样式
        self.list_view.setStyleSheet("""
            QListView {
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                background-color: white;
                selection-background-color: #e3f2fd;
                selection-color: #1976d2;
                outline: none;
                font-size: 11px;
                padding: 10px;
                show-decoration-selected: 1;
            }
            QListView::item {
                border: 1px solid transparent;
                border-radius: 6px;
                padding: 4px;
                margin: 2px;
                text-align: center;
                min-width: 70px;
                max-width: 70px;
            }
            QListView::item:hover {
                background-color: rgba(0, 120, 215, 0.1);
                border-color: rgba(0, 120, 215, 0.3);
            }
            QListView::item:selected {
                background-color: rgba(0, 120, 215, 0.15);
                border-color: #0078d4;
                color: black;
            }
            QListView::item:selected:active {
                background-color: rgba(0, 120, 215, 0.25);
                border-color: #005a9e;
            }
            QListView::item:focus {
                border-color: #0078d4;
                outline: none;
            }
        """)
        
        # 设置默认路径为桌面
        self.set_root_path(desktop_path)
        
        # 设置树视图的列显示
        self.setup_tree_columns()
        
        # 初始化向上按钮状态
        self.update_up_button_state()
        
        # 连接信号
        self.tree_view.clicked.connect(self.on_item_clicked)
        self.tree_view.doubleClicked.connect(self.on_item_double_clicked)
        self.tree_view.selectionModel().selectionChanged.connect(self.on_selection_changed)
        
        self.list_view.clicked.connect(self.on_item_clicked)
        self.list_view.doubleClicked.connect(self.on_item_double_clicked)
        self.list_view.selectionModel().selectionChanged.connect(self.on_selection_changed)
        
        # 默认显示详细信息视图
        layout.addWidget(self.tree_view)
        self.current_view = self.tree_view
        self.list_view.hide()
        
    def setup_tree_columns(self):
        """设置树视图的列"""
        # 显示所有列：名称、修改日期、类型、大小
        header = self.tree_view.header()
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # 名称列自适应
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # 大小列
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # 类型列  
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # 修改日期列
        
        # 设置列宽
        self.tree_view.setColumnWidth(1, 100)  # 大小
        self.tree_view.setColumnWidth(2, 100)  # 类型
        self.tree_view.setColumnWidth(3, 150)  # 修改日期
        
    def toggle_view_mode(self):
        """切换视图模式"""
        if self.current_view_mode == "详细信息":
            # 切换到图标视图
            self.tree_view.hide()
            
            # 移除树视图，添加列表视图
            layout = self.layout()
            layout.removeWidget(self.tree_view)
            layout.addWidget(self.list_view)
            self.list_view.show()
            
            self.current_view = self.list_view
            self.current_view_mode = "图标"
            self.view_toggle_btn.setIcon(qta.icon('fa5s.th', color='#333'))
            self.view_toggle_btn.setToolTip("切换到详细信息视图")
        else:
            # 切换到详细信息视图
            self.list_view.hide()
            
            # 移除列表视图，添加树视图
            layout = self.layout()
            layout.removeWidget(self.list_view)
            layout.addWidget(self.tree_view)
            self.tree_view.show()
            
            self.current_view = self.tree_view
            self.current_view_mode = "详细信息"
            self.view_toggle_btn.setIcon(qta.icon('fa5s.list', color='#333'))
            self.view_toggle_btn.setToolTip("切换到图标视图")
        
        # 设置图标视图显示
        self.setup_icon_view()
        
    def setup_icon_view(self):
        """设置图标视图的显示参数"""
        # 根据当前视图调整显示
        if self.current_view == self.list_view:
            # 确保列表视图显示图标
            self.list_view.setModelColumn(0)  # 显示第一列（文件名+图标）
            
            # 刷新视图
            current_index = self.list_view.rootIndex()
            if current_index.isValid():
                self.list_view.setRootIndex(current_index)
            
            # 强制更新视图
            self.list_view.viewport().update()
            
            # 确保项目正确对齐
            self.list_view.setLayoutMode(QListView.Batched)
            self.list_view.setBatchSize(100)
        
    def set_root_path(self, path):
        """设置根路径"""
        # 如果处于压缩包查看模式，不允许设置文件系统路径
        if self.archive_viewing_mode:
            return
            
        if path == "ThisPC":
            # 处理"此电脑"
            self.file_model.setRootPath("")
            self.tree_view.setRootIndex(self.file_model.index(""))
            self.list_view.setRootIndex(self.file_model.index(""))
            # 更新向上按钮状态
            self.update_up_button_state()
            return
            
        if os.path.exists(path):
            self.file_model.setRootPath(path)
            root_index = self.file_model.index(path)
            self.tree_view.setRootIndex(root_index)
            self.list_view.setRootIndex(root_index)
            
            # 更新下拉框显示
            # 首先检查是否在预设列表中
            path_found = False
            for i in range(self.path_combo.count()):
                if self.path_combo.itemData(i) == path:
                    self.path_combo.setCurrentIndex(i)
                    path_found = True
                    break
            
            if not path_found:
                # 如果路径不在预设列表中，直接设置文本
                # 临时断开信号连接，避免触发路径变化事件
                self.path_combo.currentTextChanged.disconnect(self.on_path_changed)
                self.path_combo.setCurrentText(path)
                self.path_combo.currentTextChanged.connect(self.on_path_changed)
                
            # 更新向上按钮状态
            self.update_up_button_state()
            
    def update_up_button_state(self):
        """更新向上按钮的启用状态"""
        if self.archive_viewing_mode:
            # 压缩包查看模式下的逻辑
            if self.archive_current_dir == "":
                # 在压缩包根目录，可以退出压缩包查看模式
                self.up_button.setEnabled(True)
                self.up_button.setToolTip("退出压缩包查看")
            else:
                # 在子目录，可以返回上一级
                self.up_button.setEnabled(True)
                parent_dir = os.path.dirname(self.archive_current_dir)
                if parent_dir == self.archive_current_dir:
                    parent_dir = ""
                if parent_dir:
                    self.up_button.setToolTip(f"返回到: {os.path.basename(parent_dir)}")
                else:
                    self.up_button.setToolTip("返回到压缩包根目录")
            return
            
        # 文件系统模式下的原有逻辑
        current_path = self.get_current_root_path()
        
        # 如果当前在"此电脑"或者是根目录，禁用向上按钮
        if not current_path or current_path == "":
            self.up_button.setEnabled(False)
            self.up_button.setToolTip("已在最顶级目录")
        else:
            parent_path = os.path.dirname(current_path)
            # 检查是否已经到达根目录
            if parent_path == current_path:
                # 到达系统根目录，但还可以返回到"此电脑"
                self.up_button.setEnabled(True)
                self.up_button.setToolTip("返回到此电脑")
            else:
                self.up_button.setEnabled(True)
                self.up_button.setToolTip(f"上一级目录: {os.path.basename(parent_path) if parent_path else '此电脑'}")
        
    def on_path_changed(self, path_text):
        """路径改变事件"""
        # 从下拉框文本中提取路径
        current_data = self.path_combo.currentData()
        if current_data:
            # 使用存储的路径数据
            path = current_data
        else:
            # 手动输入的路径
            path = path_text
            
        if path == "ThisPC":
            self.set_root_path("ThisPC")
        elif os.path.exists(path):
            self.set_root_path(path)
            
    def on_path_entered(self):
        """用户在路径输入框中按回车键"""
        path_text = self.path_combo.lineEdit().text().strip()
        if not path_text:
            return
            
        # 规范化路径
        path_text = os.path.normpath(path_text)
        
        if path_text == "此电脑" or path_text.lower() == "thispc":
            self.set_root_path("ThisPC")
        elif os.path.exists(path_text) and os.path.isdir(path_text):
            self.set_root_path(path_text)
        else:
            QMessageBox.warning(self, "路径错误", f"路径不存在或不是文件夹: {path_text}")
            # 恢复为当前路径
            current_path = self.get_current_root_path()
            if current_path:
                self.path_combo.lineEdit().setText(current_path)
            
    def go_up_directory(self):
        """返回上一级目录"""
        if self.archive_viewing_mode:
            # 压缩包查看模式下的逻辑
            if self.archive_current_dir == "":
                # 在压缩包根目录，退出压缩包查看模式
                # 查找主窗口并调用退出方法
                parent_widget = self.parent()
                while parent_widget:
                    if hasattr(parent_widget, 'exit_archive_mode'):
                        parent_widget.exit_archive_mode()
                        return
                    parent_widget = parent_widget.parent()
                # 如果找不到主窗口，直接退出压缩包模式
                self.exit_archive_mode()
                return
            else:
                # 返回上一级目录
                parent_dir = os.path.dirname(self.archive_current_dir)
                if parent_dir == self.archive_current_dir:
                    parent_dir = ""
                self.navigate_archive_directory(parent_dir)
            return
            
        # 文件系统模式下的原有逻辑
        current_path = self.get_current_root_path()
        if not current_path or current_path == "":
            # 当前在"此电脑"，无法再向上
            return
            
        parent_path = os.path.dirname(current_path)
        
        # 如果已经到根目录，切换到"此电脑"
        if parent_path == current_path or not parent_path:
            self.set_root_path("ThisPC")
        else:
            self.set_root_path(parent_path)
            
        # 更新向上按钮状态
        self.update_up_button_state()
        
    def on_search_text_changed(self, text):
        """搜索文本改变事件"""
        # 在压缩包查看模式下禁用搜索
        if self.archive_viewing_mode:
            return
            
        if not text.strip():
            # 清空搜索，显示所有文件
            self.file_model.setNameFilters([])
            self.file_model.setNameFilterDisables(False)
        else:
            # 设置文件名过滤器
            filters = [f"*{text}*"]
            self.file_model.setNameFilters(filters)
            self.file_model.setNameFilterDisables(False)
            
    def get_current_root_path(self):
        """获取当前根路径"""
        return self.file_model.rootPath()
        
    def on_item_clicked(self, index: QModelIndex):
        """处理单击事件"""
        if index.isValid():
            if self.archive_viewing_mode:
                # 压缩包查看模式下，发送压缩包中的文件路径
                file_path = index.data(Qt.UserRole + 1)
                if file_path:
                    self.fileSelected.emit(file_path)
            else:
                # 文件系统模式
                file_path = self.file_model.filePath(index)
                self.fileSelected.emit(file_path)
            
    def on_item_double_clicked(self, index: QModelIndex):
        """处理双击事件"""
        if not index.isValid():
            return
            
        if self.archive_viewing_mode:
            # 压缩包查看模式下的双击处理
            item_type = index.data(Qt.UserRole)
            if item_type == 'folder':
                # 双击文件夹，进入该文件夹
                folder_path = index.data(Qt.UserRole + 1)
                self.navigate_archive_directory(folder_path)
            elif item_type == 'file':
                # 双击文件，解压到临时目录并打开
                file_path = index.data(Qt.UserRole + 1)
                self.open_archive_file(file_path)
        else:
            # 文件系统模式下的原有逻辑
            file_path = self.file_model.filePath(index)
            if self.file_model.isDir(index):
                # 如果是文件夹，进入该文件夹
                self.set_root_path(file_path)
            else:
                # 如果是文件，检查是否为压缩文件
                if self.is_archive_file(file_path):
                    # 压缩文件，发送打开压缩包信号
                    self.archiveOpenRequested.emit(file_path)
                else:
                    # 普通文件，发送选中信号
                    self.fileSelected.emit(file_path)
                
    def on_selection_changed(self):
        """处理选择变化事件"""
        selected_paths = self.get_selected_paths()
        if selected_paths:
            self.filesSelected.emit(selected_paths)
            
    def get_current_path(self):
        """获取当前选中的路径"""
        current_index = self.current_view.currentIndex()
        if current_index.isValid():
            return self.file_model.filePath(current_index)
        return ""
        
    def get_selected_paths(self):
        """获取所有选中的路径"""
        selected_indexes = self.current_view.selectionModel().selectedIndexes()
        paths = []
        for index in selected_indexes:
            if index.column() == 0:  # 只处理第一列（文件名列）
                path = self.file_model.filePath(index)
                if path not in paths:
                    paths.append(path)
        return sorted(paths)  # 按字母顺序排序
        
    def set_current_path(self, path):
        """设置当前选中的路径"""
        index = self.file_model.index(path)
        if index.isValid():
            self.current_view.setCurrentIndex(index)
            self.current_view.scrollTo(index) 

    def show_context_menu(self, position):
        """显示树视图上下文菜单"""
        print(f"🖱️ 树视图右键菜单触发 - 位置: {position}")
        index = self.tree_view.indexAt(position)
        self._show_context_menu(index, self.tree_view.mapToGlobal(position))
        
    def show_list_context_menu(self, position):
        """显示列表视图上下文菜单"""
        print(f"🖱️ 列表视图右键菜单触发 - 位置: {position}")
        index = self.list_view.indexAt(position)
        self._show_context_menu(index, self.list_view.mapToGlobal(position))
        
    def _show_context_menu(self, index, global_position):
        """显示上下文菜单的通用方法"""
        print(f"🔧 右键菜单触发 - 位置: {global_position}, 索引有效: {index.isValid()}")
        
        menu = QMenu(self)
        
        if self.archive_viewing_mode:
            # 压缩包查看模式下的专用右键菜单
            self._show_archive_context_menu(index, menu)
        else:
            # 普通文件系统模式下的右键菜单
            self._show_filesystem_context_menu(index, menu)
        
        print(f"📋 菜单项数量: {len(menu.actions())}")
        if menu.actions():  # 只有在有菜单项时才显示
            print("🎯 显示菜单...")
            menu.exec(global_position)
        else:
            print("❌ 没有菜单项，不显示菜单")
    
    def _show_archive_context_menu(self, index, menu):
        """显示压缩包模式的上下文菜单"""
        if index.isValid():
            # 压缩包内文件/文件夹的右键菜单
            item_type = index.data(Qt.UserRole)
            file_path = index.data(Qt.UserRole + 1)
            item_name = index.data(Qt.DisplayRole)
            
            if item_type == 'file':
                # 文件右键菜单
                open_action = QAction("打开", self)
                open_action.setIcon(qta.icon('fa5s.file', color='#2196f3'))
                open_action.triggered.connect(lambda: self.open_archive_file(file_path))
                menu.addAction(open_action)
                
                menu.addSeparator()
                
                # 复制
                copy_action = QAction("复制", self)
                copy_action.setIcon(qta.icon('fa5s.copy', color='#2196f3'))
                copy_action.triggered.connect(lambda: self.copy_archive_items([file_path]))
                menu.addAction(copy_action)
                
                # 重命名
                rename_action = QAction("重命名", self)
                rename_action.setIcon(qta.icon('fa5s.edit', color='#ff9800'))
                rename_action.triggered.connect(lambda: self.rename_archive_file(file_path, item_name))
                menu.addAction(rename_action)
                
                # 删除
                delete_action = QAction("删除", self)
                delete_action.setIcon(qta.icon('fa5s.trash', color='#f44336'))
                delete_action.triggered.connect(lambda: self.delete_archive_file(file_path))
                menu.addAction(delete_action)
                
                menu.addSeparator()
                
                # 解压到临时目录
                extract_action = QAction("解压到临时目录", self)
                extract_action.setIcon(qta.icon('fa5s.download', color='#4caf50'))
                extract_action.triggered.connect(lambda: self.extract_archive_file(file_path))
                menu.addAction(extract_action)
                
                # 打开当前文件夹
                open_folder_action = QAction("打开当前文件夹", self)
                open_folder_action.setIcon(qta.icon('fa5s.external-link-alt', color='#2196f3'))
                open_folder_action.triggered.connect(self.open_archive_folder_in_explorer)
                menu.addAction(open_folder_action)
                
            elif item_type == 'folder':
                # 文件夹右键菜单
                open_action = QAction("打开", self)
                open_action.setIcon(qta.icon('fa5s.folder-open', color='#f57c00'))
                open_action.triggered.connect(lambda: self.navigate_archive_directory(file_path))
                menu.addAction(open_action)
                
                menu.addSeparator()
                
                # 复制
                copy_action = QAction("复制", self)
                copy_action.setIcon(qta.icon('fa5s.copy', color='#2196f3'))
                copy_action.triggered.connect(lambda: self.copy_archive_items([file_path]))
                menu.addAction(copy_action)
                
                # 重命名
                rename_action = QAction("重命名", self)
                rename_action.setIcon(qta.icon('fa5s.edit', color='#ff9800'))
                rename_action.triggered.connect(lambda: self.rename_archive_file(file_path, item_name))
                menu.addAction(rename_action)
                
                # 删除
                delete_action = QAction("删除", self)
                delete_action.setIcon(qta.icon('fa5s.trash', color='#f44336'))
                delete_action.triggered.connect(lambda: self.delete_archive_file(file_path))
                menu.addAction(delete_action)
                
                menu.addSeparator()
                
                # 新建文件夹
                new_folder_action = QAction("新建文件夹", self)
                new_folder_action.setIcon(qta.icon('fa5s.folder', color='#4caf50'))
                new_folder_action.triggered.connect(lambda: self.create_archive_folder(file_path))
                menu.addAction(new_folder_action)
                
                # 打开当前文件夹
                open_folder_action = QAction("打开当前文件夹", self)
                open_folder_action.setIcon(qta.icon('fa5s.external-link-alt', color='#2196f3'))
                open_folder_action.triggered.connect(self.open_archive_folder_in_explorer)
                menu.addAction(open_folder_action)
        else:
            # 压缩包内空白处右键菜单
            # 粘贴（如果有剪贴板内容）
            if hasattr(self, 'archive_clipboard_items') and self.archive_clipboard_items:
                paste_action = QAction("粘贴", self)
                paste_action.setIcon(qta.icon('fa5s.paste', color='#4caf50'))
                paste_action.triggered.connect(self.paste_to_archive)
                menu.addAction(paste_action)
                menu.addSeparator()
            
            # 如果有系统剪贴板文件，可以粘贴到压缩包
            if self.clipboard_items:
                paste_files_action = QAction("粘贴文件到压缩包", self)
                paste_files_action.setIcon(qta.icon('fa5s.file-import', color='#4caf50'))
                paste_files_action.triggered.connect(self.paste_files_to_archive)
                menu.addAction(paste_files_action)
                menu.addSeparator()
            
            # 创建文件夹
            new_folder_action = QAction("新建文件夹", self)
            new_folder_action.setIcon(qta.icon('fa5s.folder', color='#4caf50'))
            new_folder_action.triggered.connect(lambda: self.create_archive_folder())
            menu.addAction(new_folder_action)
            
            # 打开当前文件夹
            open_folder_action = QAction("打开当前文件夹", self)
            open_folder_action.setIcon(qta.icon('fa5s.external-link-alt', color='#2196f3'))
            open_folder_action.triggered.connect(self.open_archive_folder_in_explorer)
            menu.addAction(open_folder_action)
            
            menu.addSeparator()
            
            # 返回上级目录或退出压缩包
            if self.archive_current_dir:
                up_action = QAction("返回上级目录", self)
                up_action.setIcon(qta.icon('fa5s.arrow-up', color='#2196f3'))
                up_action.triggered.connect(self.go_up_directory)
                menu.addAction(up_action)
            
            exit_action = QAction("退出压缩包查看", self)
            exit_action.setIcon(qta.icon('fa5s.times', color='#f44336'))
            exit_action.triggered.connect(self._exit_archive_mode)
            menu.addAction(exit_action)

    def _show_filesystem_context_menu(self, index, menu):
        """显示文件系统模式的上下文菜单"""
        # 获取当前所有选中的文件路径
        selected_paths = self.get_selected_paths()
        print(f"📂 已选中路径: {selected_paths}")
        
        if index.isValid():
            file_path = self.file_model.filePath(index)
            is_dir = self.file_model.isDir(index)
            print(f"📁 右键文件: {file_path}, 是文件夹: {is_dir}")
            
            # 如果右键的文件不在选中列表中，则只操作右键的文件
            if file_path not in selected_paths:
                selected_paths = [file_path]
                print(f"📝 更新选中列表为右键文件: {selected_paths}")
            
            # 判断选中项目的类型
            is_multiple = len(selected_paths) > 1
            has_folders = any(os.path.isdir(path) for path in selected_paths)
            has_files = any(os.path.isfile(path) for path in selected_paths)
            
            # 打开菜单项（只在单选时显示）
            if not is_multiple:
                if is_dir:
                    open_action = QAction("打开", self)
                    open_action.setIcon(qta.icon('fa5s.folder-open', color='#f57c00'))
                    open_action.triggered.connect(lambda: self.open_folder(file_path))
                else:
                    open_action = QAction("打开", self)
                    open_action.setIcon(qta.icon('fa5s.file', color='#2196f3'))
                    open_action.triggered.connect(lambda: self.open_file(file_path))
                menu.addAction(open_action)
                menu.addSeparator()
            
            # 剪切、复制菜单项（支持多选）
            cut_action = QAction("剪切", self)
            cut_action.setIcon(qta.icon('fa5s.cut', color='#ff9800'))
            copy_action = QAction("复制", self)
            copy_action.setIcon(qta.icon('fa5s.copy', color='#2196f3'))
                
            cut_action.triggered.connect(lambda: self.cut_items(selected_paths))
            copy_action.triggered.connect(lambda: self.copy_items(selected_paths))
            menu.addAction(cut_action)
            menu.addAction(copy_action)
            
            # 粘贴菜单项（只在单选文件夹时显示）
            if not is_multiple and is_dir and self.clipboard_items:
                paste_action = QAction("粘贴", self)
                paste_action.setIcon(qta.icon('fa5s.paste', color='#4caf50'))
                paste_action.triggered.connect(lambda: self.paste_items(file_path))
                menu.addAction(paste_action)
            
            menu.addSeparator()
            
            # 重命名菜单项（只在单选时显示）
            if not is_multiple:
                rename_action = QAction("重命名", self)
                rename_action.setIcon(qta.icon('fa5s.edit', color='#ff9800'))
                rename_action.triggered.connect(lambda: self.rename_file(file_path))
                menu.addAction(rename_action)
            
            # 删除菜单项（支持多选）
            delete_action = QAction("删除", self)
            delete_action.setIcon(qta.icon('fa5s.trash', color='#f44336'))
            delete_action.triggered.connect(lambda: self.delete_files(selected_paths))
            menu.addAction(delete_action)
            
            # 只在单选文件夹时显示新建选项
            if not is_multiple and is_dir:
                menu.addSeparator()
                new_folder_action = QAction("新建文件夹", self)
                new_folder_action.setIcon(qta.icon('fa5s.folder', color='#4caf50'))
                new_folder_action.triggered.connect(lambda: self.create_folder(file_path))
                menu.addAction(new_folder_action)
                
                new_file_action = QAction("新建文件", self)
                new_file_action.setIcon(qta.icon('fa5s.file-alt', color='#4caf50'))
                new_file_action.triggered.connect(lambda: self.create_file(file_path))
                menu.addAction(new_file_action)
            
            # 刷新选项
            refresh_action = QAction("刷新", self)
            refresh_action.setIcon(qta.icon('fa5s.sync-alt', color='#2196f3'))
            refresh_action.triggered.connect(self.refresh_view)
            menu.addAction(refresh_action)
            
        else:
            # 在空白处右键，在当前目录操作
            current_dir = self.get_current_root_path()
            print(f"📂 空白处右键，当前目录: {current_dir}")
            if current_dir and os.path.exists(current_dir):
                # 粘贴选项
                if self.clipboard_items:
                    paste_action = QAction("粘贴", self)
                    paste_action.setIcon(qta.icon('fa5s.paste', color='#4caf50'))
                    paste_action.triggered.connect(lambda: self.paste_items(current_dir))
                    menu.addAction(paste_action)
                    menu.addSeparator()
                
                # 新建选项
                new_folder_action = QAction("新建文件夹", self)
                new_folder_action.setIcon(qta.icon('fa5s.folder', color='#4caf50'))
                new_folder_action.triggered.connect(lambda: self.create_folder(current_dir))
                menu.addAction(new_folder_action)
                
                new_file_action = QAction("新建文件", self)
                new_file_action.setIcon(qta.icon('fa5s.file-alt', color='#4caf50'))
                new_file_action.triggered.connect(lambda: self.create_file(current_dir))
                menu.addAction(new_file_action)
                
                menu.addSeparator()
                
                # 在资源管理器中打开当前目录
                open_explorer_action = QAction("在资源管理器中打开", self)
                open_explorer_action.setIcon(qta.icon('fa5s.external-link-alt', color='#2196f3'))
                open_explorer_action.triggered.connect(lambda: self.open_in_explorer(current_dir))
                menu.addAction(open_explorer_action)
                
                # 刷新选项
                refresh_action = QAction("刷新", self)
                refresh_action.setIcon(qta.icon('fa5s.sync-alt', color='#2196f3'))
                refresh_action.triggered.connect(self.refresh_view)
                menu.addAction(refresh_action)

    def open_file(self, file_path):
        """打开文件"""
        if not os.path.exists(file_path):
            QMessageBox.warning(self, "错误", "文件不存在")
            return
            
        if os.path.isfile(file_path):
            # 检查是否为压缩文件
            if self.is_archive_file(file_path):
                # 压缩文件，发送打开压缩包信号
                self.archiveOpenRequested.emit(file_path)
                return
                
            try:
                if sys.platform == "win32":
                    os.startfile(file_path)
                elif sys.platform == "darwin":  # macOS
                    subprocess.call(["open", file_path])
                else:  # Linux
                    subprocess.call(["xdg-open", file_path])
            except Exception as e:
                QMessageBox.warning(self, "打开文件失败", f"无法打开文件: {str(e)}")
        else:
            QMessageBox.warning(self, "错误", "这不是一个文件")
            
    def open_folder(self, folder_path):
        """打开文件夹（进入该文件夹）"""
        if not os.path.exists(folder_path):
            QMessageBox.warning(self, "错误", "文件夹不存在")
            return
            
        if os.path.isdir(folder_path):
            self.set_root_path(folder_path)
        else:
            QMessageBox.warning(self, "错误", "这不是一个文件夹")

    def delete_file(self, file_path):
        """删除单个文件或文件夹（兼容方法）"""
        self.delete_files([file_path])

    def delete_files(self, file_paths):
        """删除多个文件或文件夹"""
        if not file_paths:
            return
            
        # 过滤出存在的文件
        existing_paths = [path for path in file_paths if os.path.exists(path)]
        if not existing_paths:
            QMessageBox.warning(self, "错误", "选中的文件或文件夹都不存在")
            return
            
        # 检查是否需要管理员权限
        if not self.request_admin_if_needed(existing_paths, "删除"):
            return
            
        # 统计文件和文件夹数量
        folders = [path for path in existing_paths if os.path.isdir(path)]
        files = [path for path in existing_paths if os.path.isfile(path)]
        
        # 构建确认消息
        if len(existing_paths) == 1:
            file_name = os.path.basename(existing_paths[0])
            if os.path.isdir(existing_paths[0]):
                message = f"确定要删除文件夹 '{file_name}' 及其所有内容吗？\n这个操作不可撤销。"
            else:
                message = f"确定要删除文件 '{file_name}' 吗？\n这个操作不可撤销。"
        else:
            items = []
            if folders:
                items.append(f"{len(folders)} 个文件夹")
            if files:
                items.append(f"{len(files)} 个文件")
            items_text = "和".join(items)
            message = f"确定要删除 {items_text} 吗？\n"
            if folders:
                message += "文件夹及其所有内容将被删除。\n"
            message += "这个操作不可撤销。"
            
        reply = QMessageBox.question(
            self, "确认删除", 
            message,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            success_count = 0
            failed_items = []
            
            for file_path in existing_paths:
                try:
                    if os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                    else:
                        os.remove(file_path)
                    success_count += 1
                except Exception as e:
                    failed_items.append(f"{os.path.basename(file_path)}: {str(e)}")
            
            # 刷新视图
            self.refresh_view()
            
            # 显示结果（只显示失败信息，不显示成功信息）
            if failed_items:
                error_message = "以下项目删除失败：\n" + "\n".join(failed_items)
                QMessageBox.critical(self, "删除失败", error_message)

    def rename_file(self, file_path):
        """重命名文件或文件夹"""
        if not os.path.exists(file_path):
            QMessageBox.warning(self, "错误", "文件或文件夹不存在")
            return
            
        # 检查是否需要管理员权限
        if not self.request_admin_if_needed(file_path, "重命名"):
            return
            
        old_name = os.path.basename(file_path)
        new_name, ok = QInputDialog.getText(
            self, "重命名", 
            f"请输入新名称:", 
            text=old_name
        )
        
        if ok and new_name and new_name != old_name:
            if not new_name.strip():
                QMessageBox.warning(self, "错误", "名称不能为空")
                return
                
            new_path = os.path.join(os.path.dirname(file_path), new_name)
            
            if os.path.exists(new_path):
                QMessageBox.warning(self, "错误", f"名称 '{new_name}' 已经存在")
                return
                
            try:
                os.rename(file_path, new_path)
                self.refresh_view()
            except Exception as e:
                QMessageBox.critical(self, "重命名失败", f"无法重命名: {str(e)}")

    def create_folder(self, parent_path):
        """在指定路径创建新文件夹"""
        if not os.path.exists(parent_path) or not os.path.isdir(parent_path):
            QMessageBox.warning(self, "错误", "目标路径不存在或不是文件夹")
            return
            
        folder_name, ok = QInputDialog.getText(
            self, "新建文件夹", 
            "请输入文件夹名称:",
            text="新建文件夹"
        )
        
        if ok and folder_name:
            if not folder_name.strip():
                QMessageBox.warning(self, "错误", "文件夹名称不能为空")
                return
                
            new_folder_path = os.path.join(parent_path, folder_name)
            
            if os.path.exists(new_folder_path):
                QMessageBox.warning(self, "错误", f"文件夹 '{folder_name}' 已经存在")
                return
                
            try:
                os.makedirs(new_folder_path)
                self.refresh_view()
            except Exception as e:
                QMessageBox.critical(self, "创建失败", f"无法创建文件夹: {str(e)}")
                
    def create_file(self, parent_path):
        """在指定路径创建新文件"""
        if not os.path.exists(parent_path) or not os.path.isdir(parent_path):
            QMessageBox.warning(self, "错误", "目标路径不存在或不是文件夹")
            return
            
        file_name, ok = QInputDialog.getText(
            self, "新建文件", 
            "请输入文件名称:",
            text="新建文件.txt"
        )
        
        if ok and file_name:
            if not file_name.strip():
                QMessageBox.warning(self, "错误", "文件名称不能为空")
                return
                
            new_file_path = os.path.join(parent_path, file_name)
            
            if os.path.exists(new_file_path):
                QMessageBox.warning(self, "错误", f"文件 '{file_name}' 已经存在")
                return
                
            try:
                with open(new_file_path, 'w', encoding='utf-8') as f:
                    f.write("")  # 创建空文件
                self.refresh_view()
            except Exception as e:
                QMessageBox.critical(self, "创建失败", f"无法创建文件: {str(e)}")
                
    def refresh_view(self):
        """刷新视图"""
        current_path = self.get_current_root_path()
        if current_path:
            # 强制刷新文件系统模型
            self.file_model.setRootPath("")  # 先清空
            self.file_model.setRootPath(current_path)  # 重新设置
            
            # 刷新根索引
            root_index = self.file_model.index(current_path)
            self.tree_view.setRootIndex(root_index)
            self.list_view.setRootIndex(root_index)
            
            # 强制更新视图
            self.tree_view.viewport().update()
            self.list_view.viewport().update()
            
            # 重置排序以触发刷新
            self.tree_view.header().setSortIndicator(0, Qt.AscendingOrder)
            
            print(f"已刷新视图: {current_path}")  # 调试信息

    def keyPressEvent(self, event: QKeyEvent):
        """处理键盘事件"""
        if event.key() == Qt.Key_F5:
            # F5键刷新
            self.refresh_view()
            event.accept()
        else:
            # 传递其他键盘事件给父类处理
            super().keyPressEvent(event)
            
    def copy_items(self, file_paths):
        """复制文件到剪贴板"""
        # 检查是否需要管理员权限
        if not self.request_admin_if_needed(file_paths, "复制"):
            return
            
        self.clipboard_items = file_paths.copy()
        self.clipboard_operation = "copy"
            
    def cut_items(self, file_paths):
        """剪切文件到剪贴板"""
        # 检查是否需要管理员权限
        if not self.request_admin_if_needed(file_paths, "剪切"):
            return
            
        self.clipboard_items = file_paths.copy()
        self.clipboard_operation = "cut"
            
    def paste_items(self, target_dir):
        """粘贴剪贴板中的文件"""
        if not self.clipboard_items:
            QMessageBox.warning(self, "错误", "剪贴板为空")
            return
            
        if not os.path.exists(target_dir) or not os.path.isdir(target_dir):
            QMessageBox.warning(self, "错误", "目标路径不存在或不是文件夹")
            return
            
        success_count = 0
        error_count = 0
        
        for source_path in self.clipboard_items:
            if not os.path.exists(source_path):
                error_count += 1
                continue
                
            file_name = os.path.basename(source_path)
            target_path = os.path.join(target_dir, file_name)
            
            # 如果目标文件已存在，添加数字后缀
            counter = 1
            original_target = target_path
            while os.path.exists(target_path):
                name, ext = os.path.splitext(os.path.basename(original_target))
                target_path = os.path.join(target_dir, f"{name}_{counter}{ext}")
                counter += 1
            
            try:
                if self.clipboard_operation == "copy":
                    if os.path.isdir(source_path):
                        shutil.copytree(source_path, target_path)
                    else:
                        shutil.copy2(source_path, target_path)
                elif self.clipboard_operation == "cut":
                    shutil.move(source_path, target_path)
                success_count += 1
            except Exception as e:
                error_count += 1
                QMessageBox.warning(self, "操作失败", f"无法处理 '{file_name}': {str(e)}")
        
        # 如果是剪切操作，清空剪贴板
        if self.clipboard_operation == "cut":
            self.clipboard_items = []
            self.clipboard_operation = ""
            
        # 刷新视图
        self.refresh_view()
        
        # 显示结果 - 只显示错误信息
        if error_count > 0:
            QMessageBox.warning(self, "部分失败", f"有 {error_count} 个项目操作失败")
            
    def open_in_explorer(self, dir_path):
        """在Windows资源管理器中打开目录"""
        if not os.path.exists(dir_path):
            QMessageBox.warning(self, "错误", "目录不存在")
            return
            
        try:
            if sys.platform == "win32":
                # Windows: 使用explorer打开目录
                os.startfile(dir_path)
            elif sys.platform == "darwin":  # macOS
                subprocess.call(["open", dir_path])
            else:  # Linux
                subprocess.call(["xdg-open", dir_path])
        except Exception as e:
            QMessageBox.warning(self, "打开失败", f"无法打开目录: {str(e)}")

    def request_admin_if_needed(self, file_paths, operation="操作"):
        """如果需要管理员权限，则申请权限"""
        from ..core.permission_manager import PermissionManager
        return PermissionManager.request_admin_if_needed(file_paths, operation)
        
    def is_admin(self):
        """检查当前是否有管理员权限"""
        from ..core.permission_manager import PermissionManager
        return PermissionManager.is_admin()

    def is_archive_file(self, file_path):
        """检查文件是否为支持的压缩包格式"""
        if not os.path.isfile(file_path):
            return False
            
        # 支持的压缩文件扩展名
        archive_extensions = ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz']
        _, ext = os.path.splitext(file_path.lower())
        return ext in archive_extensions 

    def navigate_archive_directory(self, directory):
        """在压缩包中导航到指定目录"""
        if not self.archive_viewing_mode:
            return
            
        self.archive_current_dir = directory
        # 重新显示当前目录的内容
        self.display_archive_directory_content()
        # 更新向上按钮状态
        self.update_up_button_state()
        # 更新路径显示
        if directory:
            display_path = f"{os.path.basename(self.archive_path)}/{directory}"
        else:
            display_path = os.path.basename(self.archive_path)
        self.path_combo.lineEdit().setText(display_path)
    
    def display_archive_directory_content(self):
        """显示压缩包当前目录的内容"""
        if not self.archive_viewing_mode or not self.archive_model:
            return
            
        # 清空模型
        self.archive_model.clear()
        self.archive_model.setHorizontalHeaderLabels(["名称", "大小", "类型", "修改时间"])
        
        # 获取当前目录下的文件和文件夹
        current_items = {}  # 文件夹和文件的字典
        
        # 遍历压缩包中的所有文件
        for file_info in getattr(self, 'archive_file_list', []):
            file_path = file_info.get('path', '').replace('\\', '/')
            
            # 检查文件是否在当前目录下
            if self.archive_current_dir:
                if not file_path.startswith(self.archive_current_dir + '/'):
                    continue
                # 获取相对于当前目录的路径
                relative_path = file_path[len(self.archive_current_dir) + 1:]
            else:
                relative_path = file_path
            
            # 检查是否为直接子项（不包含更深层的路径分隔符）
            path_parts = relative_path.split('/')
            
            if len(path_parts) == 1:
                # 直接文件
                item_name = path_parts[0]
                if item_name and item_name not in current_items:
                    current_items[item_name] = {
                        'type': 'file',
                        'info': file_info,
                        'name': item_name
                    }
            elif len(path_parts) > 1:
                # 文件夹中的文件，需要创建文件夹项
                folder_name = path_parts[0]
                if folder_name and folder_name not in current_items:
                    current_items[folder_name] = {
                        'type': 'folder',
                        'name': folder_name,
                        'path': f"{self.archive_current_dir}/{folder_name}" if self.archive_current_dir else folder_name
                    }
        
        # 添加项目到模型
        for item_name, item_data in sorted(current_items.items()):
            if item_data['type'] == 'folder':
                # 文件夹
                name_item = QStandardItem(item_name)
                name_item.setIcon(qta.icon('fa5s.folder', color='#ffc107'))
                name_item.setData('folder', Qt.UserRole)
                name_item.setData(item_data['path'], Qt.UserRole + 1)
                
                size_item = QStandardItem("")
                type_item = QStandardItem("文件夹")
                time_item = QStandardItem("")
                
            else:
                # 文件
                file_info = item_data['info']
                name_item = QStandardItem(item_name)
                
                # 根据文件扩展名设置图标
                ext = os.path.splitext(item_name)[1].lower()
                if ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']:
                    name_item.setIcon(qta.icon('fa5s.image', color='#4caf50'))
                elif ext in ['.txt', '.md', '.log']:
                    name_item.setIcon(qta.icon('fa5s.file-alt', color='#ff9800'))
                elif ext in ['.zip', '.rar', '.7z']:
                    name_item.setIcon(qta.icon('fa5s.file-archive', color='#9c27b0'))
                else:
                    name_item.setIcon(qta.icon('fa5s.file', color='#2196f3'))
                
                name_item.setData('file', Qt.UserRole)
                name_item.setData(file_info.get('path', ''), Qt.UserRole + 1)
                
                size_item = QStandardItem(self.format_file_size(file_info.get('size', 0)))
                type_item = QStandardItem(self.get_file_type(item_name))
                time_item = QStandardItem(file_info.get('modified_time', ''))
            
            self.archive_model.appendRow([name_item, size_item, type_item, time_item])
    
    def format_file_size(self, size_bytes):
        """格式化文件大小"""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        
        return f"{size_bytes:.1f} {size_names[i]}"
    
    def get_file_type(self, file_path):
        """获取文件类型描述"""
        if not file_path:
            return "文件"
        
        ext = os.path.splitext(file_path)[1].lower()
        type_map = {
            '.txt': '文本文件',
            '.doc': 'Word文档',
            '.docx': 'Word文档',
            '.pdf': 'PDF文档',
            '.jpg': 'JPEG图像',
            '.jpeg': 'JPEG图像',
            '.png': 'PNG图像',
            '.gif': 'GIF图像',
            '.bmp': 'BMP图像',
            '.mp3': 'MP3音频',
            '.mp4': 'MP4视频',
            '.avi': 'AVI视频',
            '.zip': 'ZIP压缩包',
            '.rar': 'RAR压缩包',
            '.7z': '7-Zip压缩包',
        }
        
        return type_map.get(ext, '文件') 

    def enter_archive_mode(self, archive_path, archive_file_list):
        """进入压缩包查看模式"""
        self.archive_viewing_mode = True
        self.archive_path = archive_path
        self.archive_file_list = archive_file_list
        self.archive_current_dir = ""
        
        # 创建压缩包内容模型
        self.archive_model = QStandardItemModel()
        
        # 设置视图使用压缩包模型
        self.tree_view.setModel(self.archive_model)
        self.list_view.setModel(self.archive_model)
        
        # 显示压缩包根目录内容
        self.display_archive_directory_content()
        
        # 设置列宽
        self.setup_tree_columns()
        
        # 更新向上按钮状态
        self.update_up_button_state()
        
        # 更新路径显示
        self.path_combo.lineEdit().setText(os.path.basename(archive_path))
    
    def exit_archive_mode(self):
        """退出压缩包查看模式"""
        self.archive_viewing_mode = False
        self.archive_path = None
        self.archive_file_list = []
        self.archive_current_dir = ""
        self.archive_model = None
        
        # 恢复文件系统模型
        self.tree_view.setModel(self.file_model)
        self.list_view.setModel(self.file_model)
        
        # 更新向上按钮状态
        self.update_up_button_state() 

    def open_archive_file(self, file_path):
        """解压并打开压缩包中的文件"""
        try:
            # 创建临时目录
            temp_dir = tempfile.mkdtemp(prefix="gudazip_")
            
            # 从压缩包中解压指定文件
            from ..core.archive_manager import ArchiveManager
            archive_manager = ArchiveManager()
            
            success = archive_manager.extract_archive(
                self.archive_path, 
                temp_dir, 
                selected_files=[file_path]
            )
            
            if success:
                # 构建临时文件的完整路径
                temp_file_path = os.path.join(temp_dir, file_path)
                
                # 使用系统默认程序打开文件
                if os.path.exists(temp_file_path):
                    if sys.platform == "win32":
                        os.startfile(temp_file_path)
                    elif sys.platform == "darwin":  # macOS
                        subprocess.call(["open", temp_file_path])
                    else:  # Linux
                        subprocess.call(["xdg-open", temp_file_path])
                else:
                    QMessageBox.warning(self, "错误", "无法找到解压后的文件")
            else:
                QMessageBox.warning(self, "错误", "无法解压文件")
                # 清理临时目录
                shutil.rmtree(temp_dir, ignore_errors=True)
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"打开文件失败：{str(e)}")
        
    def open_archive_folder(self, folder_path):
        """打开压缩包中的文件夹"""
        if not self.archive_viewing_mode:
            QMessageBox.warning(self, "错误", "当前不是压缩包查看模式")
            return
            
        if not os.path.exists(folder_path):
            QMessageBox.warning(self, "错误", "文件夹不存在")
            return
            
        try:
            # 打开文件夹
            if sys.platform == "win32":
                os.startfile(folder_path)
            elif sys.platform == "darwin":  # macOS
                subprocess.call(["open", folder_path])
            else:  # Linux
                subprocess.call(["xdg-open", folder_path])
        except Exception as e:
            QMessageBox.critical(self, "打开文件夹失败", f"无法打开文件夹: {str(e)}") 

    def extract_archive_file(self, file_path):
        """解压压缩包中的单个文件到临时目录"""
        try:
            # 创建临时目录
            temp_dir = tempfile.mkdtemp(prefix="gudazip_extract_")
            
            # 从压缩包中解压指定文件
            from ..core.archive_manager import ArchiveManager
            archive_manager = ArchiveManager()
            
            success = archive_manager.extract_archive(
                self.archive_path, 
                temp_dir, 
                selected_files=[file_path]
            )
            
            if success:
                # 构建解压后文件的完整路径
                extracted_file_path = os.path.join(temp_dir, file_path)
                
                if os.path.exists(extracted_file_path):
                    # 在资源管理器中显示文件
                    if sys.platform == "win32":
                        # Windows: 选中文件并打开资源管理器
                        subprocess.run(['explorer', '/select,', extracted_file_path])
                    else:
                        # 其他系统：打开包含文件夹
                        parent_dir = os.path.dirname(extracted_file_path)
                        if sys.platform == "darwin":  # macOS
                            subprocess.call(["open", parent_dir])
                        else:  # Linux
                            subprocess.call(["xdg-open", parent_dir])
                    
                    QMessageBox.information(self, "解压成功", f"文件已解压到临时目录：\n{extracted_file_path}")
                else:
                    QMessageBox.warning(self, "错误", "无法找到解压后的文件")
            else:
                QMessageBox.warning(self, "错误", "解压文件失败")
                # 清理临时目录
                shutil.rmtree(temp_dir, ignore_errors=True)
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"解压文件失败：{str(e)}")
    
    def _exit_archive_mode(self):
        """退出压缩包查看模式"""
        # 查找主窗口并调用退出方法
        parent_widget = self.parent()
        while parent_widget:
            if hasattr(parent_widget, 'exit_archive_mode'):
                parent_widget.exit_archive_mode()
                return
            parent_widget = parent_widget.parent()
        # 如果找不到主窗口，直接退出压缩包模式
        self.exit_archive_mode() 

    def copy_archive_items(self, file_paths):
        """复制压缩包内的文件到剪贴板"""
        if not hasattr(self, 'archive_clipboard_items'):
            self.archive_clipboard_items = []
        self.archive_clipboard_items = file_paths.copy()
        print(f"📋 已复制压缩包内文件: {file_paths}")
    
    def rename_archive_file(self, file_path, current_name):
        """重命名压缩包内的文件或文件夹"""
        new_name, ok = QInputDialog.getText(
            self, "重命名", 
            f"请输入新名称:", 
            text=current_name
        )
        
        if ok and new_name and new_name != current_name:
            if not new_name.strip():
                QMessageBox.warning(self, "错误", "名称不能为空")
                return
            
            # 计算新的文件路径
            if self.archive_current_dir:
                new_file_path = f"{self.archive_current_dir}/{new_name}"
            else:
                new_file_path = new_name
            
            try:
                # 使用ArchiveManager重命名文件
                from ..core.archive_manager import ArchiveManager
                archive_manager = ArchiveManager()
                
                success = archive_manager.rename_file_in_archive(
                    self.archive_path, 
                    file_path, 
                    new_file_path
                )
                
                if success:
                    # 重新刷新压缩包内容显示
                    self.refresh_archive_view()
                    QMessageBox.information(self, "成功", f"文件已重命名为: {new_name}")
                else:
                    QMessageBox.warning(self, "重命名失败", "无法重命名该文件")
                    
            except Exception as e:
                QMessageBox.critical(self, "重命名失败", f"重命名操作失败：{str(e)}")
    
    def refresh_archive_view(self):
        """刷新压缩包内容显示"""
        if not self.archive_viewing_mode or not self.archive_path:
            return
        
        try:
            # 重新读取压缩包文件列表
            from ..core.archive_manager import ArchiveManager
            archive_manager = ArchiveManager()
            
            file_list = archive_manager.list_archive_contents(self.archive_path)
            if file_list:
                self.archive_file_list = file_list
                # 重新显示当前目录内容
                self.display_archive_directory_content()
            
        except Exception as e:
            print(f"刷新压缩包视图失败: {e}")
    
    def create_archive_folder(self, parent_path=None):
        """在压缩包中创建新文件夹"""
        folder_name, ok = QInputDialog.getText(
            self, "新建文件夹", 
            "请输入文件夹名称:",
            text="新建文件夹"
        )
        
        if ok and folder_name:
            if not folder_name.strip():
                QMessageBox.warning(self, "错误", "文件夹名称不能为空")
                return
            
            # 显示提示信息（压缩包修改需要重新创建）
            QMessageBox.information(
                self, "功能提示", 
                "在压缩包中创建文件夹需要重新创建压缩包。\n此功能暂未实现，敬请期待。"
            )
    
    def open_archive_folder_in_explorer(self):
        """在资源管理器中打开当前压缩包所在文件夹"""
        if not self.archive_path or not os.path.exists(self.archive_path):
            QMessageBox.warning(self, "错误", "压缩包路径无效")
            return
        
        # 获取压缩包所在的文件夹
        archive_dir = os.path.dirname(self.archive_path)
        
        try:
            if sys.platform == "win32":
                # Windows: 直接打开文件夹（与普通模式保持一致）
                os.startfile(archive_dir)
            elif sys.platform == "darwin":  # macOS
                subprocess.call(["open", archive_dir])
            else:  # Linux
                subprocess.call(["xdg-open", archive_dir])
        except Exception as e:
            QMessageBox.warning(self, "打开失败", f"无法打开文件夹: {str(e)}")
    
    def paste_to_archive(self):
        """粘贴压缩包内复制的文件到当前位置"""
        if not hasattr(self, 'archive_clipboard_items') or not self.archive_clipboard_items:
            QMessageBox.warning(self, "错误", "没有可粘贴的压缩包内容")
            return
        
        QMessageBox.information(
            self, "功能提示", 
            "在压缩包内移动/复制文件需要重新创建压缩包。\n此功能暂未实现，敬请期待。"
        )
    
    def paste_files_to_archive(self):
        """将系统剪贴板中的文件粘贴到压缩包中"""
        if not self.clipboard_items:
            QMessageBox.warning(self, "错误", "没有可粘贴的文件")
            return
        
        # 检查文件是否存在
        existing_files = [f for f in self.clipboard_items if os.path.exists(f)]
        if not existing_files:
            QMessageBox.warning(self, "错误", "剪贴板中的文件不存在")
            return
        
        reply = QMessageBox.question(
            self, "确认粘贴", 
            f"确定要将 {len(existing_files)} 个文件添加到压缩包中吗？\n注意：这需要重新创建压缩包。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            QMessageBox.information(
                self, "功能提示", 
                "向压缩包中添加文件需要重新创建压缩包。\n此功能暂未实现，敬请期待。"
            )

    def delete_archive_file(self, file_path):
        """删除压缩包内的文件"""
        reply = QMessageBox.question(
            self, "确认删除", 
            f"确定要从压缩包中删除 '{os.path.basename(file_path)}' 吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # 使用ArchiveManager删除文件
                from ..core.archive_manager import ArchiveManager
                archive_manager = ArchiveManager()
                
                success = archive_manager.delete_file_from_archive(
                    self.archive_path, 
                    file_path
                )
                
                if success:
                    # 重新刷新压缩包内容显示
                    self.refresh_archive_view()
                    QMessageBox.information(self, "成功", f"文件已删除: {os.path.basename(file_path)}")
                else:
                    QMessageBox.warning(self, "删除失败", "无法删除该文件")
                    
            except Exception as e:
                QMessageBox.critical(self, "删除失败", f"删除操作失败：{str(e)}")