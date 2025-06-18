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
from ..core.error_manager import ErrorManager, ErrorCategory, ErrorSeverity, get_error_manager
from ..core.state_manager import StateManager, StateScope, StatePersistenceType, get_state_manager
from ..core.config_manager import ConfigManager, get_config_manager
from .context_menu_manager import ContextMenuManager
from .toolbar_widget import ToolbarWidget
from .file_view_widget import FileViewWidget


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
        
        # 初始化管理器
        self.signal_manager = get_signal_manager(self)
        self.file_operation_manager = FileOperationManager(self)
        self.archive_operation_manager = ArchiveOperationManager(self)
        self.error_manager = get_error_manager(self)
        self.state_manager = get_state_manager(self)
        self.config_manager = get_config_manager(self)
        
        # 压缩包查看模式相关
        self.archive_viewing_mode = False  # 是否处于压缩包查看模式
        self.current_archive_path = ""  # 当前查看的压缩包路径
        self.archive_current_dir = ""   # 压缩包内当前目录
        
        # 从配置中获取当前视图模式
        self.current_view_mode = self.config_manager.get_config('behavior.file_view_mode', '详细信息')
        
        # 初始化UI组件
        self.init_ui()
        
        # 连接组件间的信号
        self.connect_signals()
        
        # 恢复浏览器状态
        self.restore_browser_state()
        
    def connect_signals(self):
        """连接组件间的信号"""
        # 连接操作管理器的信号
        self._connect_operation_signals()
        
        # 初始化右键菜单管理器
        self.context_menu_manager = ContextMenuManager(self)
        
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
        
        # 创建文件视图组件
        self.file_view = FileViewWidget(self)
        
        # 设置文件系统模型到视图组件
        self.file_view.set_file_model(self.file_model)
        
        # 连接文件视图信号到现有的处理方法
        self.file_view.item_clicked.connect(self.on_item_clicked)
        self.file_view.item_double_clicked.connect(self.on_item_double_clicked)
        self.file_view.selection_changed.connect(self.on_selection_changed)
        self.file_view.context_menu_requested.connect(self._on_view_context_menu)
        
        layout.addWidget(self.file_view)
        
        # 设置默认路径为桌面
        desktop_path = QStandardPaths.writableLocation(QStandardPaths.DesktopLocation)
        self.set_root_path(desktop_path)
        
        # 初始化向上按钮状态
        self.update_up_button_state()
        
    def _on_view_context_menu(self, index, global_position):
        """处理文件视图的右键菜单请求"""
        self.context_menu_manager.show_context_menu(index, global_position)
        
    def toggle_view_mode(self):
        """切换视图模式"""
        # 委托给FileViewWidget处理视图切换
        new_mode = self.file_view.toggle_view_mode()
        
        # 更新当前视图模式记录
        self.current_view_mode = new_mode
        
        # 保存到配置管理器
        self.config_manager.set_config('behavior.file_view_mode', new_mode)
        
        # 立即保存配置到文件
        self.config_manager.save_configs()
        
        # 更新工具栏按钮显示
        self.toolbar.update_view_mode(new_mode)
        
        print(f"视图模式已切换为: {new_mode} 并保存到配置文件")  # 调试信息
        
    def set_view_mode(self, mode):
        """设置视图模式"""
        if mode != self.current_view_mode:
            # 如果当前模式与目标模式不同，则切换
            self.file_view.set_view_mode(mode)
            self.current_view_mode = mode
            
            # 更新工具栏按钮显示
            self.toolbar.update_view_mode(mode)
            
            print(f"视图模式已设置为: {mode}")  # 调试信息
        
    def set_root_path(self, path):
        """设置根路径"""
        # 如果处于压缩包查看模式，不允许设置文件系统路径
        if self.archive_viewing_mode:
            return
            
        if path == "ThisPC":
            # 处理"此电脑"
            self.file_model.setRootPath("")
            self.file_view.set_root_index(self.file_model.index(""))
            # 更新向上按钮状态
            self.update_up_button_state()
            return
            
        if os.path.exists(path):
            self.file_model.setRootPath(path)
            root_index = self.file_model.index(path)
            self.file_view.set_root_index(root_index)
            
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
            # 文件系统模式下的双击处理
            file_path = self.file_model.filePath(index)
            if self.file_model.isDir(index):
                # 如果是文件夹，进入该文件夹
                self.set_root_path(file_path)
            else:
                # 如果是文件，直接打开文件
                self.open_file(file_path)
                
    def on_selection_changed(self):
        """处理选择变化事件"""
        selected_paths = self.get_selected_paths()
        if selected_paths:
            self.filesSelected.emit(selected_paths)
            
    def get_current_path(self):
        """获取当前选中的路径"""
        current_index = self.file_view.get_current_index()
        if current_index.isValid():
            return self.file_model.filePath(current_index)
        return ""
        
    def get_selected_paths(self):
        """获取所有选中的路径"""
        if self.archive_viewing_mode:
            # 压缩包模式：获取选中的文件在压缩包中的路径
            selected_indexes = self.file_view.get_selected_indexes()
            paths = []
            for index in selected_indexes:
                if index.column() == 0:  # 只处理第一列（文件名列）
                    # 在压缩包模式下，从UserRole+1获取文件路径
                    item = self.archive_model.itemFromIndex(index)
                    if item:
                        file_path = item.data(Qt.UserRole + 1)
                        if file_path and file_path not in paths:
                            paths.append(file_path)
            return sorted(paths)
        else:
            # 文件系统模式：获取文件系统路径
            selected_indexes = self.file_view.get_selected_indexes()
            paths = []
            for index in selected_indexes:
                if index.column() == 0:  # 只处理第一列（文件名列）
                    path = self.file_model.filePath(index)
                    if path not in paths:
                        paths.append(path)
            return sorted(paths)  # 按字母顺序排序
        
    def get_archive_relative_path(self, display_path):
        """获取文件在压缩包中的相对路径"""
        if not self.archive_viewing_mode:
            return None
        
        # 如果是显示路径，直接返回（因为在压缩包模式下，get_selected_paths已经返回了正确的路径）
        return display_path
        
    def set_current_path(self, path):
        """设置当前选中的路径"""
        index = self.file_model.index(path)
        if index.isValid():
            self.file_view.set_current_index(index)

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
        self.archive_operation_manager.open_archive_file(self.current_archive_path, file_path)
        
    def extract_archive_file(self, file_path):
        """解压压缩包中的单个文件到临时目录"""
        if not self.archive_viewing_mode:
            return
        self.archive_operation_manager.show_file_in_explorer(self.current_archive_path, file_path)

    def rename_archive_file(self, file_path, current_name):
        """重命名压缩包内的文件或文件夹"""
        if not self.archive_viewing_mode:
            return
        self.archive_operation_manager.rename_archive_file(self.current_archive_path, file_path)

    def delete_archive_file(self, file_path):
        """删除压缩包内的文件"""
        if not self.archive_viewing_mode:
            return
        self.archive_operation_manager.delete_archive_file(self.current_archive_path, file_path)

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
        self.archive_operation_manager.open_archive_folder_in_explorer(self.current_archive_path)

    def refresh_archive_view(self):
        """刷新压缩包内容显示"""
        if not self.archive_viewing_mode or not self.current_archive_path:
            return
        
        # 使用压缩包操作管理器重新获取文件列表
        result = self.archive_operation_manager.list_archive_contents(self.current_archive_path)
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
            self.current_archive_path = archive_path
            self.archive_file_list = archive_file_list
            self.archive_current_dir = ""
            
            # 创建压缩包内容模型
            self.archive_model = QStandardItemModel()
            
            # 设置视图使用压缩包模型
            self.file_view.set_archive_model(self.archive_model)
            
            # 显示压缩包根目录内容
            self.display_archive_directory_content()
            
            # 更新向上按钮状态
            self.update_up_button_state()
            
            # 更新路径显示 - 使用ToolbarWidget的接口
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
        self.current_archive_path = ""
        self.archive_file_list = []
        self.archive_current_dir = ""
        self.archive_model = None
        
        # 恢复文件系统模型
        self.file_view.set_file_model(self.file_model)
        
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
        self.current_archive_path = ""
        self.archive_file_list = []
        self.archive_current_dir = ""
        self.archive_model = None
        
        # 恢复文件系统模型
        self.file_view.set_file_model(self.file_model)
        
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
            self.file_view.set_root_index(self.file_model.index(""))
        elif os.path.exists(target_path):
            # 处理真实路径
            self.file_model.setRootPath(target_path)
            root_index = self.file_model.index(target_path)
            self.file_view.set_root_index(root_index)
            
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
            self.file_view.set_root_index(root_index)
            
            # 强制更新视图
            self.file_view.refresh_view()
            
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
            display_path = f"{os.path.basename(self.current_archive_path)}/{directory}"
        else:
            display_path = os.path.basename(self.current_archive_path)
        
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

    def restore_browser_state(self):
        """恢复文件浏览器状态"""
        try:
            # 从配置管理器获取行为设置
            behavior_config = self.config_manager.get_behavior_config()
            
            # 恢复视图模式
            saved_view_mode = behavior_config['file_view_mode']
            self.current_view_mode = saved_view_mode
            
            # 实际设置FileViewWidget的视图模式
            self.file_view.set_view_mode(saved_view_mode)
            
            # 更新工具栏显示  
            self.toolbar.update_view_mode(saved_view_mode)
            
            print(f"恢复视图模式: {saved_view_mode}")  # 调试信息
            
            # 恢复显示隐藏文件设置
            show_hidden = behavior_config['show_hidden_files']
            if hasattr(self.file_view, 'set_show_hidden_files'):
                self.file_view.set_show_hidden_files(show_hidden)
            
            # 恢复排序设置
            sort_column = behavior_config['sort_column']
            sort_order = behavior_config['sort_order']
            if hasattr(self.file_view, 'set_sort_settings'):
                self.file_view.set_sort_settings(sort_column, sort_order)
            
            # 恢复当前路径（从状态管理器）
            saved_path = self.state_manager.get_state("browser.current_path", "")
            if saved_path and os.path.exists(saved_path):
                self.set_root_path(saved_path)
            else:
                # 根据配置决定启动路径
                startup_path = self.config_manager.get_config('general.startup_path', 'desktop')
                if startup_path == 'desktop':
                    desktop_path = QStandardPaths.writableLocation(QStandardPaths.DesktopLocation)
                    self.set_root_path(desktop_path)
                elif startup_path == 'home':
                    home_path = QStandardPaths.writableLocation(QStandardPaths.HomeLocation)
                    self.set_root_path(home_path)
                elif startup_path == 'documents':
                    documents_path = QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation)
                    self.set_root_path(documents_path)
                elif startup_path == 'last_location' and saved_path:
                    self.set_root_path(saved_path)
                else:
                    # 默认到桌面
                    desktop_path = QStandardPaths.writableLocation(QStandardPaths.DesktopLocation)
                    self.set_root_path(desktop_path)
            
            # 恢复压缩包状态
            archive_mode = self.state_manager.get_state("archive.viewing_mode", False)
            if archive_mode:
                archive_path = self.state_manager.get_state("archive.current_path", "")
                archive_dir = self.state_manager.get_state("archive.current_dir", "")
                if archive_path and os.path.exists(archive_path):
                    self.archive_viewing_mode = archive_mode
                    self.current_archive_path = archive_path
                    self.archive_current_dir = archive_dir
                    if hasattr(self.file_view, 'set_archive_mode'):
                        self.file_view.set_archive_mode(True, archive_path, archive_dir)
            
        except Exception as e:
            self.error_manager.handle_exception(
                e,
                context={"operation": "restore_browser_state"},
                category=ErrorCategory.APP_CONFIGURATION,
                show_dialog=False
            )
    
    def save_browser_state(self):
        """保存文件浏览器状态"""
        try:
            # 保存视图模式
            self.state_manager.set_state(
                "browser.view_mode",
                self.current_view_mode,
                scope=StateScope.USER,
                persistence_type=StatePersistenceType.JSON,
                description="文件视图模式"
            )
            
            # 保存当前路径
            current_path = self.file_view.get_current_path()
            self.state_manager.set_state(
                "browser.current_path",
                current_path,
                scope=StateScope.SESSION,
                persistence_type=StatePersistenceType.JSON,
                description="当前浏览路径"
            )
            
            # 保存显示隐藏文件设置
            show_hidden = self.file_view.get_show_hidden_files()
            self.state_manager.set_state(
                "browser.show_hidden_files",
                show_hidden,
                scope=StateScope.USER,
                persistence_type=StatePersistenceType.JSON,
                description="显示隐藏文件"
            )
            
            # 保存排序设置
            sort_column, sort_order = self.file_view.get_sort_settings()
            self.state_manager.set_state(
                "browser.sort_column",
                sort_column,
                scope=StateScope.USER,
                persistence_type=StatePersistenceType.JSON,
                description="排序列"
            )
            self.state_manager.set_state(
                "browser.sort_order",
                sort_order,
                scope=StateScope.USER,
                persistence_type=StatePersistenceType.JSON,
                description="排序顺序"
            )
            
            # 保存压缩包状态
            self.state_manager.set_state(
                "archive.viewing_mode",
                self.archive_viewing_mode,
                scope=StateScope.SESSION,
                persistence_type=StatePersistenceType.MEMORY,
                description="压缩包查看模式"
            )
            self.state_manager.set_state(
                "archive.current_path",
                self.current_archive_path,
                scope=StateScope.SESSION,
                persistence_type=StatePersistenceType.MEMORY,
                description="当前压缩包路径"
            )
            self.state_manager.set_state(
                "archive.current_dir",
                self.archive_current_dir,
                scope=StateScope.SESSION,
                persistence_type=StatePersistenceType.MEMORY,
                description="压缩包内当前目录"
            )
            
        except Exception as e:
            self.error_manager.handle_exception(
                e,
                context={"operation": "save_browser_state"},
                category=ErrorCategory.APP_CONFIGURATION,
                show_dialog=False
            )

    def handle_path_changed(self, path):
        """处理路径变更"""
        try:
            # 保存当前路径到状态管理器
            self.state_manager.set_state(
                "browser.current_path",
                path,
                scope=StateScope.SESSION,
                persistence_type=StatePersistenceType.JSON,
                notify=False  # 不发送信号避免循环
            )
            
            # 更新导航历史
            nav_history = self.state_manager.get_state("history.navigation", [])
            if not nav_history or nav_history[-1] != path:
                nav_history.append(path)
                # 限制历史记录数量
                if len(nav_history) > 50:
                    nav_history = nav_history[-50:]
                self.state_manager.set_state(
                    "history.navigation",
                    nav_history,
                    scope=StateScope.SESSION,
                    persistence_type=StatePersistenceType.MEMORY,
                    notify=False
                )
            
        except Exception as e:
            self.error_manager.handle_exception(
                e,
                context={"operation": "handle_path_changed", "path": path},
                category=ErrorCategory.APP_INTERNAL,
                show_dialog=False
            )

    def enter_archive_viewing_mode(self, archive_path):
        """进入压缩包查看模式"""
        try:
            self.archive_viewing_mode = True
            self.current_archive_path = archive_path
            self.archive_current_dir = ""
            
            # 更新状态管理器
            self.state_manager.set_state(
                "archive.viewing_mode",
                True,
                scope=StateScope.SESSION,
                persistence_type=StatePersistenceType.MEMORY
            )
            self.state_manager.set_state(
                "archive.current_path",
                archive_path,
                scope=StateScope.SESSION,
                persistence_type=StatePersistenceType.MEMORY
            )
            self.state_manager.set_state(
                "archive.current_dir",
                "",
                scope=StateScope.SESSION,
                persistence_type=StatePersistenceType.MEMORY
            )
            
            # 更新最近打开的压缩包列表
            recent_archives = self.state_manager.get_state("recent.archives", [])
            if archive_path in recent_archives:
                recent_archives.remove(archive_path)
            recent_archives.insert(0, archive_path)
            # 限制列表长度
            if len(recent_archives) > 10:
                recent_archives = recent_archives[:10]
            self.state_manager.set_state(
                "recent.archives",
                recent_archives,
                scope=StateScope.USER,
                persistence_type=StatePersistenceType.JSON
            )
            
            # 启用压缩包模式
            self.file_view.set_archive_mode(True, archive_path, "")
            
        except Exception as e:
            self.error_manager.handle_exception(
                e,
                context={"operation": "enter_archive_viewing_mode", "archive_path": archive_path},
                category=ErrorCategory.APP_INTERNAL
            )
    
    def exit_archive_viewing_mode(self):
        """退出压缩包查看模式"""
        try:
            self.archive_viewing_mode = False
            self.current_archive_path = ""
            self.archive_current_dir = ""
            
            # 更新状态管理器
            self.state_manager.set_state(
                "archive.viewing_mode",
                False,
                scope=StateScope.SESSION,
                persistence_type=StatePersistenceType.MEMORY
            )
            self.state_manager.set_state(
                "archive.current_path",
                "",
                scope=StateScope.SESSION,
                persistence_type=StatePersistenceType.MEMORY
            )
            self.state_manager.set_state(
                "archive.current_dir",
                "",
                scope=StateScope.SESSION,
                persistence_type=StatePersistenceType.MEMORY
            )
            
            # 禁用压缩包模式
            self.file_view.set_archive_mode(False, "", "")
            
        except Exception as e:
            self.error_manager.handle_exception(
                e,
                context={"operation": "exit_archive_viewing_mode"},
                category=ErrorCategory.APP_INTERNAL,
                show_dialog=False
            )

    def show_properties(self, file_path):
        """显示文件属性"""
        if not file_path or not os.path.exists(file_path):
            QMessageBox.warning(self, "错误", "文件不存在或路径无效")
            return
            
        if sys.platform == "win32":
            # 转换为Windows格式路径
            win_path = os.path.normpath(file_path)
            
            # 方法1: 使用win32com.client模块打开文件属性对话框
            if HAS_WIN32:
                try:
                    shell = win32com.client.Dispatch("Shell.Application")
                    folder = shell.NameSpace(os.path.dirname(win_path))
                    item = folder.ParseName(os.path.basename(win_path))
                    if item:
                        item.InvokeVerb("properties")
                        return  # 成功后直接返回
                except Exception as e:
                    print(f"win32com方法失败: {e}")
            
            # 方法2: 使用ctypes调用Shell32.dll
            try:
                if self._show_properties_fallback(win_path):
                    return  # 成功后直接返回
            except Exception as e:
                print(f"ctypes方法失败: {e}")
            
            # 方法3: 最后的备用方案 - 打开文件位置
            try:
                self._open_file_location(win_path)
            except Exception as e:
                QMessageBox.critical(self, "错误", f"无法显示文件属性或打开文件位置：{str(e)}")
        else:
            QMessageBox.information(self, "提示", f"当前系统 ({sys.platform}) 不支持显示Windows文件属性")
    
    def _show_properties_fallback(self, file_path):
        """显示文件属性的备用方法"""
        try:
            # 使用shell32.dll的SHObjectProperties函数
            shell32 = ctypes.windll.shell32
            SHObjectProperties = shell32.SHObjectProperties
            
            # 定义函数原型
            SHObjectProperties.argtypes = [ctypes.wintypes.HWND, ctypes.wintypes.DWORD, ctypes.wintypes.LPCWSTR, ctypes.wintypes.LPCWSTR]
            SHObjectProperties.restype = ctypes.wintypes.BOOL
            
            # 调用函数显示属性对话框
            # SHOP_FILEPATH = 0x2  # 表示路径是文件路径
            result = SHObjectProperties(0, 0x2, file_path, None)
            return bool(result)
                
        except Exception as e:
            print(f"备用方法失败: {e}")
            return False
    
    def _open_file_location(self, file_path):
        """在资源管理器中打开文件位置"""
        try:
            # 确保路径使用反斜杠
            win_path = os.path.normpath(file_path)
            
            # 方法1: 尝试使用shell=True的explorer命令
            try:
                subprocess.run(f'explorer /select,"{win_path}"', shell=True, check=True, timeout=5)
                return
            except Exception:
                pass  # 继续尝试下一种方法
            
            # 方法2: 使用os.startfile打开文件所在文件夹
            folder_path = os.path.dirname(win_path)
            os.startfile(folder_path)
            
        except Exception as e:
            raise Exception(f"无法打开文件位置: {e}")

    def show_archive_file_properties(self, file_path, file_name):
        """显示压缩包内文件的属性信息"""
        try:
            # 获取压缩包管理器
            from ..core.archive_manager import get_archive_manager
            archive_manager = get_archive_manager()
            
            # 获取文件信息
            file_info = None
            if hasattr(self, 'archive_file_list') and self.archive_file_list:
                for item in self.archive_file_list:
                    if item.get('path') == file_path or item.get('name') == file_name:
                        file_info = item
                        break
            
            if not file_info:
                QMessageBox.information(self, "属性", f"文件名: {file_name}\n路径: {file_path}\n\n无法获取详细信息")
                return
            
            # 构建属性信息
            info_text = f"文件名: {file_name}\n"
            info_text += f"路径: {file_path}\n"
            info_text += f"类型: {'文件夹' if file_info.get('is_dir', False) else '文件'}\n"
            
            if not file_info.get('is_dir', False):
                # 文件信息
                size = file_info.get('size', 0)
                compressed_size = file_info.get('compressed_size', 0)
                info_text += f"大小: {self.format_file_size(size)}\n"
                info_text += f"压缩后大小: {self.format_file_size(compressed_size)}\n"
                
                if size > 0 and compressed_size > 0:
                    compression_ratio = (1 - compressed_size / size) * 100
                    info_text += f"压缩率: {compression_ratio:.1f}%\n"
            
            modified_time = file_info.get('modified_time', '')
            if modified_time:
                info_text += f"修改时间: {modified_time}\n"
            
            # 压缩包信息
            info_text += f"\n压缩包: {os.path.basename(self.current_archive_path)}"
            
            QMessageBox.information(self, "文件属性", info_text)
            
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法获取文件属性信息：{str(e)}")