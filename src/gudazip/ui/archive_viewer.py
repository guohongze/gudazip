# -*- coding: utf-8 -*-
"""
压缩包查看器组件
用于显示压缩包内容
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTreeView, QListView, 
    QHeaderView, QAbstractItemView
)
from PySide6.QtCore import Qt, QModelIndex
from PySide6.QtGui import QStandardItemModel, QStandardItem, QIcon
import os
from datetime import datetime


class ArchiveViewer(QWidget):
    """压缩包查看器"""
    
    def __init__(self, archive_path=None, parent=None):
        super().__init__(parent)
        self.archive_path = archive_path
        self.archive_info = None
        self.init_ui()
        
    def init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建树视图来显示压缩包内容
        self.tree_view = QTreeView()
        self.tree_view.setAlternatingRowColors(True)
        self.tree_view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tree_view.setSortingEnabled(True)
        
        # 创建模型
        self.tree_model = QStandardItemModel()
        self.tree_model.setHorizontalHeaderLabels([
            "名称", "大小", "压缩后大小", "修改时间", "类型"
        ])
        
        self.tree_view.setModel(self.tree_model)
        
        # 设置列宽
        header = self.tree_view.header()
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # 名称列自适应
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # 大小列
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # 压缩后大小列
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # 修改时间列
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # 类型列
        
        layout.addWidget(self.tree_view)
        
        # 如果有压缩包路径，则加载内容
        if self.archive_path:
            self.load_archive_by_path(self.archive_path)
            
    def load_archive_by_path(self, archive_path):
        """根据文件路径加载压缩包"""
        self.archive_path = archive_path
        # TODO: 这里需要调用压缩包管理器来获取压缩包信息
        # 现在先显示一个示例结构
        self.load_sample_data()
        
    def load_archive(self, archive_info):
        """加载压缩包信息"""
        self.archive_info = archive_info
        self.tree_model.clear()
        self.tree_model.setHorizontalHeaderLabels([
            "名称", "大小", "压缩后大小", "修改时间", "类型"
        ])
        
        if not archive_info or not archive_info.get('files'):
            return
            
        # 构建文件树结构
        root_item = self.tree_model.invisibleRootItem()
        path_items = {}  # 路径到项目的映射
        
        for file_info in archive_info['files']:
            file_path = file_info['path']
            parts = file_path.split('/')
            
            current_item = root_item
            current_path = ""
            
            # 构建目录结构
            for i, part in enumerate(parts):
                if i < len(parts) - 1:  # 这是一个目录
                    current_path = current_path + part + "/" if current_path else part + "/"
                    
                    if current_path not in path_items:
                        dir_item = QStandardItem(part)
                        dir_item.setData("folder", Qt.UserRole)
                        size_item = QStandardItem("")
                        compressed_item = QStandardItem("")
                        time_item = QStandardItem("")
                        type_item = QStandardItem("文件夹")
                        
                        current_item.appendRow([
                            dir_item, size_item, compressed_item, 
                            time_item, type_item
                        ])
                        path_items[current_path] = dir_item
                        current_item = dir_item
                    else:
                        current_item = path_items[current_path]
                else:  # 这是文件
                    file_item = QStandardItem(part)
                    file_item.setData("file", Qt.UserRole)
                    
                    # 格式化文件大小
                    size = file_info.get('size', 0)
                    size_str = self.format_size(size)
                    size_item = QStandardItem(size_str)
                    
                    # 格式化压缩后大小
                    compressed_size = file_info.get('compressed_size', 0)
                    compressed_str = self.format_size(compressed_size)
                    compressed_item = QStandardItem(compressed_str)
                    
                    # 格式化时间
                    time_str = file_info.get('modified_time', '')
                    time_item = QStandardItem(time_str)
                    
                    # 文件类型
                    file_ext = os.path.splitext(part)[1].lower()
                    file_type = self.get_file_type(file_ext)
                    type_item = QStandardItem(file_type)
                    
                    current_item.appendRow([
                        file_item, size_item, compressed_item,
                        time_item, type_item
                    ])
                    
    def load_sample_data(self):
        """加载示例数据（用于测试）"""
        self.tree_model.clear()
        self.tree_model.setHorizontalHeaderLabels([
            "名称", "大小", "压缩后大小", "修改时间", "类型"
        ])
        
        root_item = self.tree_model.invisibleRootItem()
        
        # 添加示例文件和文件夹
        folder_item = QStandardItem("documents")
        folder_item.setData("folder", Qt.UserRole)
        
        size_item = QStandardItem("")
        compressed_item = QStandardItem("")
        time_item = QStandardItem("2024-01-15 10:30")
        type_item = QStandardItem("文件夹")
        
        root_item.appendRow([folder_item, size_item, compressed_item, time_item, type_item])
        
        # 在文件夹中添加文件
        file_item = QStandardItem("readme.txt")
        file_item.setData("file", Qt.UserRole)
        
        file_size_item = QStandardItem("1.2 KB")
        file_compressed_item = QStandardItem("0.8 KB")
        file_time_item = QStandardItem("2024-01-15 10:25")
        file_type_item = QStandardItem("文本文件")
        
        folder_item.appendRow([
            file_item, file_size_item, file_compressed_item,
            file_time_item, file_type_item
        ])
        
        # 添加根级别的文件
        root_file_item = QStandardItem("config.ini")
        root_file_item.setData("file", Qt.UserRole)
        
        root_size_item = QStandardItem("0.5 KB")
        root_compressed_item = QStandardItem("0.3 KB")
        root_time_item = QStandardItem("2024-01-15 09:15")
        root_type_item = QStandardItem("配置文件")
        
        root_item.appendRow([
            root_file_item, root_size_item, root_compressed_item,
            root_time_item, root_type_item
        ])
        
    def format_size(self, size_bytes):
        """格式化文件大小"""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
            
        return f"{size_bytes:.1f} {size_names[i]}"
        
    def get_file_type(self, extension):
        """根据文件扩展名获取文件类型"""
        type_mapping = {
            '.txt': '文本文件',
            '.doc': 'Word文档',
            '.docx': 'Word文档',
            '.pdf': 'PDF文档',
            '.jpg': '图片文件',
            '.jpeg': '图片文件',
            '.png': '图片文件',
            '.gif': '图片文件',
            '.mp3': '音频文件',
            '.mp4': '视频文件',
            '.avi': '视频文件',
            '.zip': '压缩文件',
            '.rar': '压缩文件',
            '.7z': '压缩文件',
            '.exe': '可执行文件',
            '.py': 'Python文件',
            '.cpp': 'C++文件',
            '.java': 'Java文件',
            '.html': 'HTML文件',
            '.css': 'CSS文件',
            '.js': 'JavaScript文件',
        }
        
        return type_mapping.get(extension, '未知文件')
        
    def get_selected_files(self):
        """获取选中的文件列表"""
        selected_files = []
        selection = self.tree_view.selectionModel().selectedRows()
        
        for index in selection:
            item = self.tree_model.itemFromIndex(index)
            if item and item.data(Qt.UserRole) == "file":
                # 构建完整路径
                path_parts = []
                current_item = item
                while current_item.parent():
                    path_parts.insert(0, current_item.text())
                    current_item = current_item.parent()
                path_parts.insert(0, current_item.text())
                
                file_path = "/".join(path_parts)
                selected_files.append(file_path)
                
        return selected_files 