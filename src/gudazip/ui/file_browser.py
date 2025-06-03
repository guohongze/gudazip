# -*- coding: utf-8 -*-
"""
文件浏览器组件
实现左侧的文件系统树状导航
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeView, QHeaderView, 
    QFileSystemModel, QComboBox, QLabel, QPushButton, QLineEdit, QListView
)
from PySide6.QtCore import Qt, QDir, Signal, QModelIndex, QStandardPaths
from PySide6.QtGui import QIcon
import os
import qtawesome as qta


class FileBrowser(QWidget):
    """文件浏览器组件"""
    
    # 信号：文件被选中
    fileSelected = Signal(str)
    # 信号：多个文件被选中
    filesSelected = Signal(list)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_view_mode = "详细信息"  # 当前视图模式
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
        
        # 创建顶部工具栏
        toolbar_layout = QHBoxLayout()
        
        # 视图切换按钮（最左侧）
        self.view_toggle_btn = QPushButton()
        self.view_toggle_btn.setIcon(qta.icon('fa5s.list', color='#333'))
        self.view_toggle_btn.setToolTip("切换到图标视图")
        self.view_toggle_btn.setFixedSize(32, 32)
        self.view_toggle_btn.setStyleSheet("""
            QPushButton {
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                background-color: #f8f9fa;
                padding: 6px;
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
            }
        """)
        toolbar_layout.addWidget(location_label)
        
        # 路径下拉选择框
        self.path_combo = QComboBox()
        self.path_combo.setEditable(True)
        self.path_combo.setMinimumWidth(350)
        self.path_combo.setMaximumHeight(32)
        self.path_combo.setStyleSheet("""
            QComboBox {
                border: 1px solid #d0d0d0;
                padding: 5px 10px;
                background-color: white;
                font-size: 12px;
                min-height: 20px;
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
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border: none;
                width: 0px;
                height: 0px;
                border-left: 6px solid transparent;
                border-right: 6px solid transparent;
                border-top: 6px solid #666;
                margin-right: 5px;
            }
            QComboBox QAbstractItemView {
                border: 2px solid #ccc;
                border-radius: 6px;
                background-color: white;
                selection-background-color: #e3f2fd;
                outline: none;
                font-size: 18px;
                padding: 4px;
            }
            QComboBox QAbstractItemView::item {
                padding: 8px 12px;
                min-height: 28px;
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
        
        # 添加Windows标准路径到下拉框，使用更大的图标
        windows_paths = [
            ("📥 桌面", desktop_path),
            ("💻 此电脑", ""),  # 特殊处理
            ("📁 文档", documents_path),
            ("🖼️ 图片", pictures_path),
            ("📥 下载", downloads_path),
            ("🎬 视频", videos_path),
            ("🎵 音乐", music_path),
            ("🏠 用户目录", home_path),
            ("💾 C盘", "C:\\"),
            ("💾 D盘", "D:\\"),
            ("💾 E盘", "E:\\"),
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
            }
        """)
        toolbar_layout.addWidget(search_label)
        
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("在当前位置中搜索...")
        self.search_box.textChanged.connect(self.on_search_text_changed)
        self.search_box.setMinimumWidth(280)
        self.search_box.setMaximumWidth(350)
        self.search_box.setMaximumHeight(32)
        self.search_box.setStyleSheet("""
            QLineEdit {
                border: 1px solid #d0d0d0;
                padding: 5px 12px;
                background-color: white;
                font-size: 12px;
                min-height: 20px;
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
            }
        """)
        toolbar_layout.addWidget(self.search_box)
        
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
        
        # 创建列表视图（图标视图）
        self.list_view = QListView()
        self.list_view.setModel(self.file_model)
        self.list_view.setViewMode(QListView.IconMode)
        self.list_view.setResizeMode(QListView.Adjust)
        self.list_view.setSelectionMode(QListView.ExtendedSelection)
        self.list_view.setUniformItemSizes(True)
        self.list_view.setGridSize(self.list_view.gridSize() * 1.2)  # 稍微增大网格
        
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
                font-size: 12px;
                padding: 5px;
            }
            QListView::item {
                padding: 8px;
                border: none;
                border-radius: 4px;
                margin: 2px;
            }
            QListView::item:hover {
                background-color: #f5f5f5;
            }
            QListView::item:selected {
                background-color: #e3f2fd;
            }
            QListView::item:selected:active {
                background-color: #bbdefb;
            }
        """)
        
        # 设置默认路径为桌面
        self.set_root_path(desktop_path)
        
        # 设置树视图的列显示
        self.setup_tree_columns()
        
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
        
    def set_root_path(self, path):
        """设置根路径"""
        if path == "ThisPC":
            # 处理"此电脑"
            self.file_model.setRootPath("")
            self.tree_view.setRootIndex(self.file_model.index(""))
            self.list_view.setRootIndex(self.file_model.index(""))
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