# -*- coding: utf-8 -*-
"""
文件浏览器组件
实现左侧的文件系统树状导航
重构版本：UI和业务逻辑分离，使用专门的操作管理器
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

# 导入管理器
from ..core.signal_manager import get_signal_manager
from ..core.file_operation_manager import FileOperationManager
from ..core.archive_operation_manager import ArchiveOperationManager
from .context_menu_manager import ContextMenuManager
from .toolbar_widget import ToolbarWidget


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
    """文件浏览器组件 - 重构版本"""
    
    # 信号：文件被选中
    fileSelected = Signal(str)
    # 信号：多个文件被选中
    filesSelected = Signal(list)
    # 信号：请求打开压缩包
    archiveOpenRequested = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_view_mode = "详细信息"  # 当前视图模式
        
        # 压缩包查看模式相关
        self.archive_viewing_mode = False  # 是否处于压缩包查看模式
        self.archive_model = None  # 压缩包内容模型
        self.archive_path = None  # 当前压缩包路径
        self.archive_current_dir = ""  # 压缩包内当前目录
        self.archive_file_list = []  # 压缩包文件列表
        
        # 初始化管理器
        self.signal_manager = get_signal_manager(debug_mode=True)
        self.file_operation_manager = FileOperationManager(self)
        self.archive_operation_manager = ArchiveOperationManager(self)
        self.context_menu_manager = ContextMenuManager(self)
        
        # 连接操作管理器的信号
        self._connect_operation_signals()
        
        # 设置焦点策略，使其能接收键盘事件
        self.setFocusPolicy(Qt.StrongFocus)
        
        self.init_ui()
        
    def _connect_operation_signals(self):
        """连接操作管理器的信号"""
        # 文件操作管理器信号
        self.file_operation_manager.operation_finished.connect(self._on_file_operation_finished)
        
        # 压缩包操作管理器信号
        self.archive_operation_manager.operation_finished.connect(self._on_archive_operation_finished)
        
    def _on_file_operation_finished(self, operation_type: str, result):
        """处理文件操作完成信号"""
        if not result.success and result.message:
            QMessageBox.warning(self, "操作失败", result.message)
        elif result.success and operation_type in ["delete", "rename", "create_folder", "create_file", "paste"]:
            # 对于修改文件系统的操作，刷新视图
            self.refresh_view()
    
    def _on_archive_operation_finished(self, operation_type: str, result):
        """处理压缩包操作完成信号"""
        if not result.success and result.message:
            QMessageBox.warning(self, "操作失败", result.message)
        elif result.success and operation_type in ["rename_file", "delete_file"]:
            # 对于修改压缩包的操作，刷新压缩包视图
            self.refresh_archive_view()
        
        # 显示成功消息
        if result.success and result.message:
            # 对于某些操作可以显示成功消息
            if operation_type in ["extract_file", "extract_archive"]:
                QMessageBox.information(self, "操作成功", result.message)
    
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
        
        # 创建工具栏组件
        self.toolbar = ToolbarWidget(self)
        
        # 连接工具栏信号到现有的处理方法
        self.toolbar.view_toggle_requested.connect(self.toggle_view_mode)
        self.toolbar.go_up_requested.connect(self.go_up_directory)
        self.toolbar.location_changed.connect(self.handle_location_selection)
        self.toolbar.manual_path_requested.connect(self.handle_manual_path_input)
        self.toolbar.search_text_changed.connect(self.on_search_text_changed)
        self.toolbar.refresh_requested.connect(self.refresh_view)
        
        layout.addWidget(self.toolbar)
        
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
        
        # 为视图添加样式
        self._apply_view_styles()
        
        # 设置默认路径为桌面
        desktop_path = QStandardPaths.writableLocation(QStandardPaths.DesktopLocation)
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
            # 更新工具栏按钮显示
            self.toolbar.update_view_mode("图标")
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
            # 更新工具栏按钮显示
            self.toolbar.update_view_mode("详细信息")
        
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
            
            # 更新下拉框显示 - 使用ToolbarWidget的接口
            # 首先检查是否在预设列表中
            path_found = False
            for i in range(self.toolbar.path_combo.count()):
                if self.toolbar.path_combo.itemData(i) == path:
                    # 使用信号管理器安全地设置，避免触发路径变化事件
                    self.toolbar.update_path_display(
                        path, 
                        use_signal_manager=self.signal_manager,
                        block_context="filesystem_path_update"
                    )
                    path_found = True
                    break
            
            if not path_found:
                # 如果路径不在预设列表中，直接设置文本
                # 使用信号管理器安全地设置文本，避免触发路径变化事件
                self.toolbar.update_path_display(
                    path,
                    use_signal_manager=self.signal_manager,
                    block_context="filesystem_path_update"
                )
            
            # 更新向上按钮状态
            self.update_up_button_state()
        
    def update_up_button_state(self):
        """更新向上按钮的启用状态"""
        if self.archive_viewing_mode:
            # 压缩包查看模式下的逻辑
            if self.archive_current_dir == "":
                # 在压缩包根目录，可以退出压缩包查看模式
                self.toolbar.update_up_button_state(True, "退出压缩包查看")
            else:
                # 在子目录，可以返回上一级
                parent_dir = os.path.dirname(self.archive_current_dir)
                if parent_dir == self.archive_current_dir:
                    parent_dir = ""
                if parent_dir:
                    tooltip = f"返回到: {os.path.basename(parent_dir)}"
                else:
                    tooltip = "返回到压缩包根目录"
                self.toolbar.update_up_button_state(True, tooltip)
            return
            
        # 文件系统模式下的原有逻辑
        current_path = self.get_current_root_path()
        
        # 如果当前在"此电脑"或者是根目录，禁用向上按钮
        if not current_path or current_path == "":
            self.toolbar.update_up_button_state(False, "已在最顶级目录")
        else:
            parent_path = os.path.dirname(current_path)
            # 检查是否已经到达根目录
            if parent_path == current_path:
                # 到达系统根目录，但还可以返回到"此电脑"
                self.toolbar.update_up_button_state(True, "返回到此电脑")
            else:
                tooltip = f"上一级目录: {os.path.basename(parent_path) if parent_path else '此电脑'}"
                self.toolbar.update_up_button_state(True, tooltip)
        
    def handle_location_selection(self, path_text):
        """处理位置下拉菜单选择 - 完全独立的位置切换处理"""
        # 强制退出压缩包模式（如果处于压缩包模式）
        if self.archive_viewing_mode:
            self.force_exit_archive_mode()
            
        # 从下拉框数据中提取真实路径
        current_data = self.toolbar.get_path_data()
        if current_data:
            target_path = current_data
        else:
            target_path = path_text
            
        # 直接切换到目标位置
        self.force_navigate_to_path(target_path)
    
    def handle_manual_path_input(self):
        """处理手动输入路径 - 完全独立的路径输入处理"""
        # 强制退出压缩包模式（如果处于压缩包模式）
        if self.archive_viewing_mode:
            self.force_exit_archive_mode()
            
        path_text = self.toolbar.get_path_text()
        if not path_text:
            return
            
        # 规范化路径
        path_text = os.path.normpath(path_text)
        
        # 直接切换到目标位置
        if path_text == "此电脑" or path_text.lower() == "thispc":
            self.force_navigate_to_path("ThisPC")
        elif os.path.exists(path_text) and os.path.isdir(path_text):
            self.force_navigate_to_path(path_text)
        else:
            QMessageBox.warning(self, "路径错误", f"路径不存在或不是文件夹: {path_text}")
            # 恢复为当前路径（使用ToolbarWidget的接口和信号管理器保护）
            current_path = self.get_current_root_path()
            if current_path:
                self.toolbar.update_path_display(
                    current_path,
                    use_signal_manager=self.signal_manager,
                    block_context="path_input_recovery"
                )
    
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
        """显示上下文菜单的通用方法 - 已被ContextMenuManager替代"""
        # 将调用委托给ContextMenuManager
        self.context_menu_manager.show_context_menu(index, global_position)

    def open_file(self, file_path):
        """打开文件"""
        if self.archive_operation_manager.is_supported_archive(file_path):
            # 压缩文件，发送打开压缩包信号
            self.archiveOpenRequested.emit(file_path)
        else:
            # 普通文件，使用文件操作管理器打开
            self.file_operation_manager.open_file(file_path)
            
    def open_folder(self, folder_path):
        """打开文件夹（进入该文件夹）"""
        if os.path.exists(folder_path) and os.path.isdir(folder_path):
            self.set_root_path(folder_path)
        else:
            QMessageBox.warning(self, "错误", "文件夹不存在或不是文件夹")

    def delete_files(self, file_paths):
        """删除多个文件或文件夹"""
        self.file_operation_manager.delete_files(file_paths, confirm=True)

    def rename_file(self, file_path):
        """重命名文件或文件夹"""
        self.file_operation_manager.rename_file(file_path)
        
    def create_folder(self, parent_path):
        """在指定路径创建新文件夹"""
        self.file_operation_manager.create_folder(parent_path)
                
    def create_file(self, parent_path):
        """在指定路径创建新文件"""
        self.file_operation_manager.create_file(parent_path)
                
    def copy_items(self, file_paths):
        """复制文件到剪贴板"""
        self.file_operation_manager.copy_to_clipboard(file_paths)
            
    def cut_items(self, file_paths):
        """剪切文件到剪贴板"""
        self.file_operation_manager.cut_to_clipboard(file_paths)
            
    def paste_items(self, target_dir):
        """粘贴剪贴板中的文件"""
        self.file_operation_manager.paste_from_clipboard(target_dir)
            
    def open_in_explorer(self, dir_path):
        """在Windows资源管理器中打开目录"""
        self.file_operation_manager.open_in_explorer(dir_path)

    def open_archive_file(self, file_path):
        """解压并打开压缩包中的文件"""
        if not self.archive_viewing_mode:
            return
        self.archive_operation_manager.open_archive_file(self.archive_path, file_path)
        
    def extract_archive_file(self, file_path):
        """解压压缩包中的单个文件到临时目录"""
        if not self.archive_viewing_mode:
            return
        self.archive_operation_manager.show_file_in_explorer(self.archive_path, file_path)

    def rename_archive_file(self, file_path, current_name):
        """重命名压缩包内的文件或文件夹"""
        if not self.archive_viewing_mode:
            return
        self.archive_operation_manager.rename_archive_file(self.archive_path, file_path)

    def delete_archive_file(self, file_path):
        """删除压缩包内的文件"""
        if not self.archive_viewing_mode:
            return
        self.archive_operation_manager.delete_archive_file(self.archive_path, file_path)

    def copy_archive_items(self, file_paths):
        """复制压缩包内的文件到剪贴板"""
        # 这里暂时保留简化的实现，因为压缩包内的复制粘贴比较复杂
        if not hasattr(self, 'archive_clipboard_items'):
            self.archive_clipboard_items = []
        self.archive_clipboard_items = file_paths.copy()
        print(f"📋 已复制压缩包内文件: {file_paths}")

    def open_archive_folder_in_explorer(self):
        """在资源管理器中打开当前压缩包所在文件夹"""
        if not self.archive_viewing_mode:
            return
        self.archive_operation_manager.open_archive_folder_in_explorer(self.archive_path)

    def refresh_archive_view(self):
        """刷新压缩包内容显示"""
        if not self.archive_viewing_mode or not self.archive_path:
            return
        
        # 使用压缩包操作管理器重新获取文件列表
        result = self.archive_operation_manager.list_archive_contents(self.archive_path)
        if result.success:
            # 转换回原来的格式以兼容现有代码
            self.archive_file_list = [file_info.to_dict() for file_info in result.data]
            # 重新显示当前目录内容
            self.display_archive_directory_content()

    def get_clipboard_info(self):
        """获取剪贴板信息"""
        return self.file_operation_manager.get_clipboard_info()

    @property 
    def clipboard_items(self):
        """兼容性属性：获取剪贴板项目"""
        info = self.file_operation_manager.get_clipboard_info()
        return info["items"]

    def is_archive_file(self, file_path):
        """检查文件是否为支持的压缩包格式"""
        return self.archive_operation_manager.is_supported_archive(file_path)

    def request_admin_if_needed(self, file_paths, operation="操作"):
        """如果需要管理员权限，则申请权限"""
        from ..core.permission_manager import PermissionManager
        return PermissionManager.request_admin_if_needed(file_paths, operation)
        
    def is_admin(self):
        """检查当前是否有管理员权限"""
        from ..core.permission_manager import PermissionManager
        return PermissionManager.is_admin()

    def enter_archive_mode(self, archive_path, archive_file_list):
        """进入压缩包查看模式"""
        try:
            self.archive_viewing_mode = True
            self.archive_path = archive_path
            self.archive_file_list = archive_file_list
            self.archive_current_dir = ""
            
            # 创建压缩包内容模型
            self.archive_model = QStandardItemModel()
            
            # 设置视图使用压缩包模型
            if hasattr(self, 'tree_view') and self.tree_view:
                self.tree_view.setModel(self.archive_model)
            if hasattr(self, 'list_view') and self.list_view:
                self.list_view.setModel(self.archive_model)
            
            # 显示压缩包根目录内容
            self.display_archive_directory_content()
            
            # 设置列宽
            if hasattr(self, 'setup_tree_columns'):
                self.setup_tree_columns()
            
            # 更新向上按钮状态
            if hasattr(self, 'update_up_button_state'):
                self.update_up_button_state()
            
            # 更新路径显示 - 使用ToolbarWidget的接口
            if hasattr(self, 'toolbar') and self.toolbar:
                # 使用信号管理器安全地更新路径，避免触发handle_location_selection
                self.toolbar.update_path_display(
                    os.path.basename(archive_path),
                    use_signal_manager=self.signal_manager,
                    block_context="archive_path_update"
                )
            
        except Exception as e:
            print(f"进入压缩包模式失败: {e}")
            import traceback
            print(f"详细错误: {traceback.format_exc()}")
    
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

    def force_exit_archive_mode(self):
        """强制退出压缩包模式 - 独立的退出逻辑"""
        # 重置所有压缩包相关状态
        self.archive_viewing_mode = False
        self.archive_path = None
        self.archive_file_list = []
        self.archive_current_dir = ""
        self.archive_model = None
        
        # 恢复文件系统模型
        self.tree_view.setModel(self.file_model)
        self.list_view.setModel(self.file_model)
        
        # 通知主窗口也退出压缩包模式
        parent_widget = self.parent()
        while parent_widget:
            if hasattr(parent_widget, 'exit_archive_mode'):
                parent_widget.exit_archive_mode()
                break
            parent_widget = parent_widget.parent()
    
    def force_navigate_to_path(self, target_path):
        """强制导航到指定路径 - 独立的导航逻辑"""
        if target_path == "ThisPC":
            # 处理"此电脑"
            self.file_model.setRootPath("")
            self.tree_view.setRootIndex(self.file_model.index(""))
            self.list_view.setRootIndex(self.file_model.index(""))
        elif os.path.exists(target_path):
            # 处理真实路径
            self.file_model.setRootPath(target_path)
            root_index = self.file_model.index(target_path)
            self.tree_view.setRootIndex(root_index)
            self.list_view.setRootIndex(root_index)
            
            # 更新下拉框显示（不触发信号）
            self.update_path_combo_display(target_path)
        
        # 更新向上按钮状态
        self.update_up_button_state()
    
    def update_path_combo_display(self, path):
        """更新路径下拉框显示 - 独立的显示更新逻辑"""
        # 使用ToolbarWidget的接口安全地更新显示，避免递归触发
        self.toolbar.update_path_display(
            path,
            use_signal_manager=self.signal_manager,
            block_context="combo_display_update"
        )

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

    def navigate_archive_directory(self, directory):
        """在压缩包中导航到指定目录"""
        if not self.archive_viewing_mode:
            return
            
        self.archive_current_dir = directory
        # 重新显示当前目录的内容
        self.display_archive_directory_content()
        # 更新向上按钮状态
        self.update_up_button_state()
        # 更新路径显示（使用ToolbarWidget的接口和信号管理器保护）
        if directory:
            display_path = f"{os.path.basename(self.archive_path)}/{directory}"
        else:
            display_path = os.path.basename(self.archive_path)
        
        # 使用ToolbarWidget的接口安全地更新路径显示，避免触发handle_location_selection
        self.toolbar.update_path_display(
            display_path,
            use_signal_manager=self.signal_manager,
            block_context="archive_navigation_update"
        )
    
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