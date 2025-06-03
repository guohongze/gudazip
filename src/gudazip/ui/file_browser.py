# -*- coding: utf-8 -*-
"""
文件浏览器组件
实现左侧的文件系统树状导航
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QTreeView, QHeaderView, QFileSystemModel
from PySide6.QtCore import Qt, QDir, Signal, QModelIndex


class FileBrowser(QWidget):
    """文件浏览器组件"""
    
    # 信号：文件被选中
    fileSelected = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建文件系统模型
        self.file_model = QFileSystemModel()
        self.file_model.setRootPath(QDir.rootPath())
        
        # 设置文件过滤器，显示所有文件和文件夹
        self.file_model.setFilter(
            QDir.AllDirs | QDir.Files | QDir.NoDotAndDotDot
        )
        
        # 创建树视图
        self.tree_view = QTreeView()
        self.tree_view.setModel(self.file_model)
        
        # 设置根路径
        root_index = self.file_model.index(QDir.rootPath())
        self.tree_view.setRootIndex(root_index)
        
        # 隐藏除名称外的其他列
        for i in range(1, self.file_model.columnCount()):
            self.tree_view.hideColumn(i)
            
        # 设置头部
        header = self.tree_view.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        
        # 连接信号
        self.tree_view.clicked.connect(self.on_item_clicked)
        self.tree_view.doubleClicked.connect(self.on_item_double_clicked)
        
        layout.addWidget(self.tree_view)
        
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
                
    def get_current_path(self):
        """获取当前选中的路径"""
        current_index = self.tree_view.currentIndex()
        if current_index.isValid():
            return self.file_model.filePath(current_index)
        return ""
        
    def set_current_path(self, path):
        """设置当前选中的路径"""
        index = self.file_model.index(path)
        if index.isValid():
            self.tree_view.setCurrentIndex(index)
            self.tree_view.scrollTo(index) 