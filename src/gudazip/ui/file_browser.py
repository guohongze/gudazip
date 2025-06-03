# -*- coding: utf-8 -*-
"""
文件浏览器组件
实现左侧的文件系统树状导航
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeView, QHeaderView, 
    QFileSystemModel, QComboBox, QLabel, QPushButton
)
from PySide6.QtCore import Qt, QDir, Signal, QModelIndex, QStandardPaths
import os


class FileBrowser(QWidget):
    """文件浏览器组件"""
    
    # 信号：文件被选中
    fileSelected = Signal(str)
    # 信号：多个文件被选中
    filesSelected = Signal(list)
    
    def __init__(self, parent=None):
        super().__init__(parent)
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
        
        # 创建路径选择区域
        path_layout = QHBoxLayout()
        
        # 路径标签
        path_label = QLabel("位置:")
        path_layout.addWidget(path_label)
        
        # 路径下拉选择框
        self.path_combo = QComboBox()
        self.path_combo.setEditable(True)
        
        # 添加常用路径
        desktop_path = QStandardPaths.writableLocation(QStandardPaths.DesktopLocation)
        documents_path = QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation)
        downloads_path = QStandardPaths.writableLocation(QStandardPaths.DownloadLocation)
        home_path = QStandardPaths.writableLocation(QStandardPaths.HomeLocation)
        
        # 添加路径到下拉框
        common_paths = [
            ("桌面", desktop_path),
            ("我的文档", documents_path),
            ("下载", downloads_path),
            ("用户目录", home_path),
            ("C盘", "C:\\"),
            ("D盘", "D:\\"),
            ("E盘", "E:\\"),
        ]
        
        for name, path in common_paths:
            if os.path.exists(path):
                self.path_combo.addItem(f"{name} ({path})", path)
        
        # 现在连接信号（在模型创建之后）
        self.path_combo.currentTextChanged.connect(self.on_path_changed)
        
        path_layout.addWidget(self.path_combo)
        
        # 刷新按钮
        refresh_button = QPushButton("刷新")
        refresh_button.clicked.connect(self.refresh_view)
        path_layout.addWidget(refresh_button)
        
        layout.addLayout(path_layout)
        
        # 创建树视图
        self.tree_view = QTreeView()
        self.tree_view.setModel(self.file_model)
        
        # 设置多选模式
        self.tree_view.setSelectionMode(QTreeView.ExtendedSelection)
        
        # 设置默认路径为桌面
        self.set_root_path(desktop_path)
        
        # 隐藏除名称外的其他列
        for i in range(1, self.file_model.columnCount()):
            self.tree_view.hideColumn(i)
            
        # 设置头部
        header = self.tree_view.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        
        # 连接信号
        self.tree_view.clicked.connect(self.on_item_clicked)
        self.tree_view.doubleClicked.connect(self.on_item_double_clicked)
        # 添加选择变化信号
        self.tree_view.selectionModel().selectionChanged.connect(self.on_selection_changed)
        
        layout.addWidget(self.tree_view)
        
    def set_root_path(self, path):
        """设置根路径"""
        if os.path.exists(path):
            self.file_model.setRootPath(path)
            root_index = self.file_model.index(path)
            self.tree_view.setRootIndex(root_index)
            
            # 更新下拉框显示
            for i in range(self.path_combo.count()):
                if self.path_combo.itemData(i) == path:
                    self.path_combo.setCurrentIndex(i)
                    break
            else:
                # 如果路径不在预设列表中，添加到下拉框
                self.path_combo.setCurrentText(path)
                
    def on_path_changed(self, path_text):
        """路径改变事件"""
        # 从下拉框文本中提取路径
        if "(" in path_text and ")" in path_text:
            # 格式：名称 (路径)
            start = path_text.find("(") + 1
            end = path_text.find(")")
            path = path_text[start:end]
        else:
            # 直接输入的路径
            path = path_text
            
        if os.path.exists(path):
            self.set_root_path(path)
            
    def refresh_view(self):
        """刷新视图"""
        current_path = self.file_model.rootPath()
        self.file_model.setRootPath("")
        self.file_model.setRootPath(current_path)
        
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
                # 如果是文件夹，展开/折叠
                if self.tree_view.isExpanded(index):
                    self.tree_view.collapse(index)
                else:
                    self.tree_view.expand(index)
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
        current_index = self.tree_view.currentIndex()
        if current_index.isValid():
            return self.file_model.filePath(current_index)
        return ""
        
    def get_selected_paths(self):
        """获取所有选中的路径"""
        selected_indexes = self.tree_view.selectionModel().selectedIndexes()
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
            self.tree_view.setCurrentIndex(index)
            self.tree_view.scrollTo(index) 