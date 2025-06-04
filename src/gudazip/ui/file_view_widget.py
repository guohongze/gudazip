# -*- coding: utf-8 -*-
"""
文件视图组件
独立的文件视图Widget，包含双视图模式（树视图和列表视图）、图标管理等功能
"""

from PySide6.QtCore import Qt, QDir, Signal, QModelIndex, QSize
from PySide6.QtGui import QIcon, QKeyEvent, QStandardItemModel, QStandardItem
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTreeView, QHeaderView, 
    QFileSystemModel, QListView, QFileIconProvider
)
import os
import sys
import qtawesome as qta

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


class FileViewWidget(QWidget):
    """文件视图组件 - 负责双视图模式管理和文件显示"""
    
    # 信号定义 - 向FileBrowser发送用户交互
    item_clicked = Signal(QModelIndex)  # 项目被点击
    item_double_clicked = Signal(QModelIndex)  # 项目被双击
    selection_changed = Signal()  # 选择变更
    context_menu_requested = Signal(QModelIndex, object)  # 右键菜单请求 (index, global_position)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_view_mode = "详细信息"  # 当前视图模式
        self.file_model = None  # 文件系统模型
        self.archive_model = None  # 压缩包内容模型
        self.enhanced_icon_provider = None  # 增强图标提供器
        self.init_ui()
        
    def init_ui(self):
        """初始化用户界面"""
        # 创建布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建增强的图标提供器
        self.enhanced_icon_provider = EnhancedIconProvider()
        
        # 创建树视图（详细信息视图）
        self.tree_view = QTreeView()
        self.tree_view.setSelectionMode(QTreeView.ExtendedSelection)
        self.tree_view.setContextMenuPolicy(Qt.CustomContextMenu)
        
        # 创建列表视图（图标视图）
        self.list_view = QListView()
        self.list_view.setViewMode(QListView.IconMode)
        self.list_view.setResizeMode(QListView.Adjust)
        self.list_view.setSelectionMode(QListView.ExtendedSelection)
        self.list_view.setUniformItemSizes(True)
        self.list_view.setContextMenuPolicy(Qt.CustomContextMenu)
        
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
        
        # 应用视图样式
        self._apply_view_styles()
        
        # 连接信号
        self._connect_signals()
        
        # 默认显示详细信息视图
        layout.addWidget(self.tree_view)
        self.current_view = self.tree_view
        self.list_view.hide()
        
    def _apply_view_styles(self):
        """应用视图样式"""
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
    
    def _connect_signals(self):
        """连接视图信号"""
        # 树视图信号
        self.tree_view.clicked.connect(self.item_clicked.emit)
        self.tree_view.doubleClicked.connect(self.item_double_clicked.emit)
        self.tree_view.customContextMenuRequested.connect(self._on_tree_context_menu)
        
        # 列表视图信号
        self.list_view.clicked.connect(self.item_clicked.emit)
        self.list_view.doubleClicked.connect(self.item_double_clicked.emit)
        self.list_view.customContextMenuRequested.connect(self._on_list_context_menu)
    
    def _on_tree_context_menu(self, position):
        """处理树视图右键菜单"""
        index = self.tree_view.indexAt(position)
        global_position = self.tree_view.mapToGlobal(position)
        self.context_menu_requested.emit(index, global_position)
    
    def _on_list_context_menu(self, position):
        """处理列表视图右键菜单"""
        index = self.list_view.indexAt(position)
        global_position = self.list_view.mapToGlobal(position)
        self.context_menu_requested.emit(index, global_position)
    
    def set_file_model(self, model):
        """设置文件系统模型"""
        self.file_model = model
        
        # 设置增强的图标提供器
        if self.enhanced_icon_provider:
            model.setIconProvider(self.enhanced_icon_provider)
        
        # 为视图设置模型
        self.tree_view.setModel(model)
        self.list_view.setModel(model)
        
        # 设置树视图的列显示
        self.setup_tree_columns()
        
        # 连接选择变更信号 - 使用lambda避免参数传递问题
        self.tree_view.selectionModel().selectionChanged.connect(lambda: self.selection_changed.emit())
        self.list_view.selectionModel().selectionChanged.connect(lambda: self.selection_changed.emit())
    
    def set_archive_model(self, model):
        """设置压缩包模型"""
        self.archive_model = model
        self.tree_view.setModel(model)
        self.list_view.setModel(model)
        
        # 重新设置树视图的列显示
        self.setup_tree_columns()
        
        # 连接选择变更信号 - 使用lambda避免参数传递问题
        if model and model.rowCount() > 0:
            self.tree_view.selectionModel().selectionChanged.connect(lambda: self.selection_changed.emit())
            self.list_view.selectionModel().selectionChanged.connect(lambda: self.selection_changed.emit())
    
    def setup_tree_columns(self):
        """设置树视图的列"""
        if not self.tree_view.model():
            return
            
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
        
        # 设置图标视图显示
        self.setup_icon_view()
        
        return self.current_view_mode
    
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
    
    def set_root_index(self, index):
        """设置根索引"""
        self.tree_view.setRootIndex(index)
        self.list_view.setRootIndex(index)
    
    def get_current_view(self):
        """获取当前活动视图"""
        return self.current_view
    
    def get_current_index(self):
        """获取当前选中的索引"""
        return self.current_view.currentIndex()
    
    def get_selected_indexes(self):
        """获取所有选中的索引"""
        if not self.current_view.selectionModel():
            return []
        return self.current_view.selectionModel().selectedIndexes()
    
    def set_current_index(self, index):
        """设置当前选中的索引"""
        self.current_view.setCurrentIndex(index)
        self.current_view.scrollTo(index)
    
    def refresh_view(self):
        """刷新当前视图"""
        # 强制更新视图
        self.tree_view.viewport().update()
        self.list_view.viewport().update()
        
        # 重置排序以触发刷新
        if self.tree_view.model():
            self.tree_view.header().setSortIndicator(0, Qt.AscendingOrder)
    
    def get_model(self):
        """获取当前模型"""
        return self.tree_view.model()
    
    def clear_selection(self):
        """清除选择"""
        if self.current_view.selectionModel():
            self.current_view.selectionModel().clearSelection() 