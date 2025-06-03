# -*- coding: utf-8 -*-
"""
文件浏览器组件
实现左侧的文件系统树状导航
"""

from PySide6.QtCore import Qt, QDir, Signal, QModelIndex, QStandardPaths, QSize
from PySide6.QtGui import QIcon, QAction, QKeyEvent
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
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_view_mode = "详细信息"  # 当前视图模式
        # 剪贴板操作相关
        self.clipboard_items = []  # 剪贴板中的文件路径
        self.clipboard_operation = ""  # "copy" 或 "cut"
        
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
        
        # 设置上下文菜单
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
        
        # 设置列表视图的上下文菜单
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
            file_path = self.file_model.filePath(index)
            self.fileSelected.emit(file_path)
            
    def on_item_double_clicked(self, index: QModelIndex):
        """处理双击事件"""
        if index.isValid():
            file_path = self.file_model.filePath(index)
            if self.file_model.isDir(index):
                # 如果是文件夹，进入该文件夹
                self.set_root_path(file_path)
            else:
                # 如果是文件，发送选中信号
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
        index = self.tree_view.indexAt(position)
        self._show_context_menu(index, self.tree_view.mapToGlobal(position))
        
    def show_list_context_menu(self, position):
        """显示列表视图上下文菜单"""
        index = self.list_view.indexAt(position)
        self._show_context_menu(index, self.list_view.mapToGlobal(position))
        
    def _show_context_menu(self, index, global_position):
        """显示上下文菜单的通用方法"""
        menu = QMenu(self)
        
        # 获取当前所有选中的文件路径
        selected_paths = self.get_selected_paths()
        
        if index.isValid() and selected_paths:
            file_path = self.file_model.filePath(index)
            is_dir = self.file_model.isDir(index)
            
            # 如果右键的文件不在选中列表中，则只操作右键的文件
            if file_path not in selected_paths:
                selected_paths = [file_path]
            
            # 判断选中项目的类型
            is_multiple = len(selected_paths) > 1
            has_folders = any(os.path.isdir(path) for path in selected_paths)
            has_files = any(os.path.isfile(path) for path in selected_paths)
            
            # 打开菜单项（只在单选时显示）
            if not is_multiple:
                if is_dir:
                    open_action = QAction(qta.icon('fa5s.folder-open', color='#f57c00'), "打开", self)
                    open_action.triggered.connect(lambda: self.open_folder(file_path))
                else:
                    open_action = QAction(qta.icon('fa5s.file', color='#2196f3'), "打开", self)
                    open_action.triggered.connect(lambda: self.open_file(file_path))
                menu.addAction(open_action)
                menu.addSeparator()
            
            # 剪切、复制菜单项（支持多选）
            cut_action = QAction(qta.icon('fa5s.cut', color='#ff9800'), "剪切", self)
            copy_action = QAction(qta.icon('fa5s.copy', color='#2196f3'), "复制", self)
                
            cut_action.triggered.connect(lambda: self.cut_items(selected_paths))
            copy_action.triggered.connect(lambda: self.copy_items(selected_paths))
            menu.addAction(cut_action)
            menu.addAction(copy_action)
            
            # 粘贴菜单项（只在单选文件夹时显示）
            if not is_multiple and is_dir and self.clipboard_items:
                paste_action = QAction(qta.icon('fa5s.paste', color='#4caf50'), "粘贴", self)
                paste_action.triggered.connect(lambda: self.paste_items(file_path))
                menu.addAction(paste_action)
            
            menu.addSeparator()
            
            # 重命名菜单项（只在单选时显示）
            if not is_multiple:
                rename_action = QAction(qta.icon('fa5s.edit', color='#ff9800'), "重命名", self)
                rename_action.triggered.connect(lambda: self.rename_file(file_path))
                menu.addAction(rename_action)
            
            # 删除菜单项（支持多选）
            delete_action = QAction(qta.icon('fa5s.trash', color='#f44336'), "删除", self)
            delete_action.triggered.connect(lambda: self.delete_files(selected_paths))
            menu.addAction(delete_action)
            
            # 只在单选文件夹时显示新建选项
            if not is_multiple and is_dir:
                menu.addSeparator()
                new_folder_action = QAction(qta.icon('fa5s.folder', color='#4caf50'), "新建文件夹", self)
                new_folder_action.triggered.connect(lambda: self.create_folder(file_path))
                menu.addAction(new_folder_action)
                
                new_file_action = QAction(qta.icon('fa5s.file-alt', color='#4caf50'), "新建文件", self)
                new_file_action.triggered.connect(lambda: self.create_file(file_path))
                menu.addAction(new_file_action)
            
        else:
            # 在空白处右键，在当前目录操作
            current_dir = self.get_current_root_path()
            if current_dir and os.path.exists(current_dir):
                # 粘贴选项
                if self.clipboard_items:
                    paste_action = QAction(qta.icon('fa5s.paste', color='#4caf50'), "粘贴", self)
                    paste_action.triggered.connect(lambda: self.paste_items(current_dir))
                    menu.addAction(paste_action)
                    menu.addSeparator()
                
                # 新建选项
                new_folder_action = QAction(qta.icon('fa5s.folder', color='#4caf50'), "新建文件夹", self)
                new_folder_action.triggered.connect(lambda: self.create_folder(current_dir))
                menu.addAction(new_folder_action)
                
                new_file_action = QAction(qta.icon('fa5s.file-alt', color='#4caf50'), "新建文件", self)
                new_file_action.triggered.connect(lambda: self.create_file(current_dir))
                menu.addAction(new_file_action)
                
                menu.addSeparator()
                
                # 在资源管理器中打开当前目录
                open_explorer_action = QAction(qta.icon('fa5s.external-link-alt', color='#2196f3'), "在资源管理器中打开", self)
                open_explorer_action.triggered.connect(lambda: self.open_in_explorer(current_dir))
                menu.addAction(open_explorer_action)
                
                # 刷新选项
                refresh_action = QAction(qta.icon('fa5s.sync-alt', color='#2196f3'), "刷新", self)
                refresh_action.triggered.connect(self.refresh_view)
        
        if menu.actions():  # 只有在有菜单项时才显示
            menu.exec(global_position)

    def open_file(self, file_path):
        """打开文件"""
        if not os.path.exists(file_path):
            QMessageBox.warning(self, "错误", "文件不存在")
            return
            
        if os.path.isfile(file_path):
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

    def needs_admin_permission(self, file_path):
        """检查操作指定文件是否需要管理员权限"""
        if not file_path:
            return False
            
        # 规范化路径，统一使用反斜杠
        file_path = os.path.normpath(file_path)
            
        # 检查是否为系统保护目录
        protected_dirs = [
            "C:\\Windows",
            "C:\\Program Files", 
            "C:\\Program Files (x86)",
            "C:\\ProgramData",
            "C:\\System Volume Information"
        ]
        
        file_path_upper = file_path.upper()
        for protected_dir in protected_dirs:
            if file_path_upper.startswith(protected_dir.upper()):
                return True
                
        # 检查是否为系统根目录下的重要文件
        if file_path_upper.startswith("C:\\") and len(file_path.split("\\")) <= 2:
            return True
            
        return False
        
    def request_admin_if_needed(self, file_paths, operation="操作"):
        """如果需要管理员权限，则申请权限"""
        if isinstance(file_paths, str):
            file_paths = [file_paths]
            
        # 检查是否有文件需要管理员权限
        needs_admin = any(self.needs_admin_permission(path) for path in file_paths)
        
        if needs_admin and not self.is_admin():
            from main import request_admin_permission
            reason = f"{operation}系统文件"
            if request_admin_permission(reason):
                sys.exit(0)  # 重启为管理员模式
            return False  # 用户拒绝或申请失败
            
        return True  # 有权限或不需要权限
        
    def is_admin(self):
        """检查当前是否有管理员权限"""
        try:
            if os.name == 'nt':  # Windows
                return ctypes.windll.shell32.IsUserAnAdmin()
            else:
                return os.geteuid() == 0
        except:
            return False 