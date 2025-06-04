# -*- coding: utf-8 -*-
"""
压缩包操作管理器
负责所有压缩包相关的操作，包括解压、查看、修改等
将压缩包业务逻辑从UI层完全分离
"""

import os
import tempfile
import shutil
import sys
import subprocess
from typing import List, Optional, Dict, Any, Tuple
from PySide6.QtWidgets import QMessageBox, QInputDialog, QWidget
from PySide6.QtCore import QObject, Signal
import logging

logger = logging.getLogger(__name__)


class ArchiveOperationResult:
    """压缩包操作结果封装"""
    
    def __init__(self, success: bool = True, message: str = "", 
                 data: Any = None, error_details: str = ""):
        self.success = success
        self.message = message
        self.data = data
        self.error_details = error_details
    
    def __bool__(self):
        return self.success
    
    def __str__(self):
        return f"ArchiveOperationResult(success={self.success}, message='{self.message}')"


class ArchiveFileInfo:
    """压缩包文件信息"""
    
    def __init__(self, path: str, size: int = 0, modified_time: str = "", 
                 is_directory: bool = False, original_info: Any = None):
        self.path = path.replace('\\', '/')  # 统一使用正斜杠
        self.size = size
        self.modified_time = modified_time
        self.is_directory = is_directory
        self.original_info = original_info
        self.name = os.path.basename(self.path)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'path': self.path,
            'name': self.name,
            'size': self.size,
            'modified_time': self.modified_time,
            'is_directory': self.is_directory
        }


class ArchiveOperationManager(QObject):
    """
    压缩包操作管理器
    
    负责所有压缩包操作，包括：
    - 压缩包内容列出和导航
    - 文件解压和临时文件管理
    - 压缩包文件的修改（重命名、删除等）
    - 压缩包内文件的打开和预览
    """
    
    # 信号定义
    operation_started = Signal(str, str)  # 操作开始 (操作类型, 压缩包路径)
    operation_finished = Signal(str, object)  # 操作完成 (操作类型, ArchiveOperationResult)
    extraction_progress = Signal(int, int)  # 解压进度 (当前, 总数)
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__()
        self.parent_widget = parent
        self.archive_manager = None
        self.temp_directories = []  # 记录创建的临时目录，用于清理
        
        # 初始化ArchiveManager
        self._init_archive_manager()
    
    def _init_archive_manager(self):
        """初始化压缩包管理器"""
        try:
            from .archive_manager import ArchiveManager
            self.archive_manager = ArchiveManager()
        except ImportError as e:
            logger.error(f"Failed to import ArchiveManager: {e}")
            self.archive_manager = None
    
    def set_parent_widget(self, parent: QWidget):
        """设置父窗口，用于显示对话框"""
        self.parent_widget = parent
    
    # ========== 支持的压缩格式检查 ==========
    
    def is_supported_archive(self, file_path: str) -> bool:
        """检查文件是否为支持的压缩包格式"""
        if not os.path.isfile(file_path):
            return False
        
        # 支持的压缩文件扩展名
        archive_extensions = ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz']
        _, ext = os.path.splitext(file_path.lower())
        return ext in archive_extensions
    
    # ========== 压缩包内容操作 ==========
    
    def list_archive_contents(self, archive_path: str) -> ArchiveOperationResult:
        """
        列出压缩包内容
        
        Args:
            archive_path: 压缩包文件路径
            
        Returns:
            ArchiveOperationResult: 包含文件列表的操作结果
        """
        if not os.path.exists(archive_path):
            return ArchiveOperationResult(False, "压缩包文件不存在")
        
        if not self.is_supported_archive(archive_path):
            return ArchiveOperationResult(False, "不支持的压缩包格式")
        
        if not self.archive_manager:
            return ArchiveOperationResult(False, "压缩包管理器不可用")
        
        try:
            self.operation_started.emit("list_contents", archive_path)
            
            # 获取文件列表
            file_list = self.archive_manager.list_archive_contents(archive_path)
            
            if file_list is None:
                result = ArchiveOperationResult(False, "无法读取压缩包内容")
            else:
                # 转换为ArchiveFileInfo对象
                archive_files = []
                for file_info in file_list:
                    archive_file = ArchiveFileInfo(
                        path=file_info.get('path', ''),
                        size=file_info.get('size', 0),
                        modified_time=file_info.get('modified_time', ''),
                        is_directory=file_info.get('is_directory', False),
                        original_info=file_info
                    )
                    archive_files.append(archive_file)
                
                result = ArchiveOperationResult(
                    True, 
                    f"成功读取压缩包内容，共 {len(archive_files)} 个项目",
                    archive_files
                )
            
            self.operation_finished.emit("list_contents", result)
            return result
            
        except Exception as e:
            error_msg = f"读取压缩包内容失败: {str(e)}"
            result = ArchiveOperationResult(False, error_msg, error_details=str(e))
            self.operation_finished.emit("list_contents", result)
            return result
    
    def get_directory_contents(self, archive_files: List[ArchiveFileInfo], 
                             current_dir: str = "") -> List[ArchiveFileInfo]:
        """
        获取压缩包中指定目录的直接内容
        
        Args:
            archive_files: 压缩包所有文件列表
            current_dir: 当前目录路径（空字符串表示根目录）
            
        Returns:
            List[ArchiveFileInfo]: 当前目录的直接子项
        """
        current_items = {}  # 用字典避免重复
        
        for file_info in archive_files:
            file_path = file_info.path
            
            # 检查文件是否在当前目录下
            if current_dir:
                if not file_path.startswith(current_dir + '/'):
                    continue
                # 获取相对于当前目录的路径
                relative_path = file_path[len(current_dir) + 1:]
            else:
                relative_path = file_path
            
            # 检查是否为直接子项
            path_parts = relative_path.split('/')
            
            if len(path_parts) == 1:
                # 直接文件
                item_name = path_parts[0]
                if item_name and item_name not in current_items:
                    current_items[item_name] = file_info
            elif len(path_parts) > 1:
                # 文件夹中的文件，需要创建文件夹项
                folder_name = path_parts[0]
                if folder_name and folder_name not in current_items:
                    folder_path = f"{current_dir}/{folder_name}" if current_dir else folder_name
                    current_items[folder_name] = ArchiveFileInfo(
                        path=folder_path,
                        is_directory=True
                    )
        
        return list(current_items.values())
    
    # ========== 文件解压操作 ==========
    
    def extract_file_to_temp(self, archive_path: str, file_path: str) -> ArchiveOperationResult:
        """
        解压单个文件到临时目录
        
        Args:
            archive_path: 压缩包路径
            file_path: 要解压的文件在压缩包中的路径
            
        Returns:
            ArchiveOperationResult: 包含临时文件路径的操作结果
        """
        if not self.archive_manager:
            return ArchiveOperationResult(False, "压缩包管理器不可用")
        
        try:
            # 创建临时目录
            temp_dir = tempfile.mkdtemp(prefix="gudazip_")
            self.temp_directories.append(temp_dir)
            
            self.operation_started.emit("extract_file", archive_path)
            
            # 解压文件
            success = self.archive_manager.extract_archive(
                archive_path, 
                temp_dir, 
                selected_files=[file_path]
            )
            
            if success:
                # 构建临时文件的完整路径
                temp_file_path = os.path.join(temp_dir, file_path)
                
                if os.path.exists(temp_file_path):
                    result = ArchiveOperationResult(
                        True,
                        f"文件已解压到临时目录",
                        {"temp_path": temp_file_path, "temp_dir": temp_dir}
                    )
                else:
                    result = ArchiveOperationResult(False, "解压后找不到文件")
            else:
                result = ArchiveOperationResult(False, "解压文件失败")
                # 清理失败的临时目录
                shutil.rmtree(temp_dir, ignore_errors=True)
                if temp_dir in self.temp_directories:
                    self.temp_directories.remove(temp_dir)
            
            self.operation_finished.emit("extract_file", result)
            return result
            
        except Exception as e:
            error_msg = f"解压文件失败: {str(e)}"
            result = ArchiveOperationResult(False, error_msg, error_details=str(e))
            self.operation_finished.emit("extract_file", result)
            return result
    
    def extract_archive_to_directory(self, archive_path: str, target_dir: str, 
                                   selected_files: Optional[List[str]] = None) -> ArchiveOperationResult:
        """
        解压压缩包到指定目录
        
        Args:
            archive_path: 压缩包路径
            target_dir: 目标目录
            selected_files: 要解压的文件列表（None表示解压全部）
            
        Returns:
            ArchiveOperationResult: 操作结果
        """
        if not self.archive_manager:
            return ArchiveOperationResult(False, "压缩包管理器不可用")
        
        if not os.path.exists(target_dir) or not os.path.isdir(target_dir):
            return ArchiveOperationResult(False, "目标目录不存在或不是文件夹")
        
        try:
            self.operation_started.emit("extract_archive", archive_path)
            
            success = self.archive_manager.extract_archive(
                archive_path, 
                target_dir, 
                selected_files=selected_files
            )
            
            if success:
                file_count = len(selected_files) if selected_files else "所有"
                result = ArchiveOperationResult(
                    True,
                    f"成功解压 {file_count} 个文件到 {target_dir}",
                    {"target_dir": target_dir, "extracted_files": selected_files}
                )
            else:
                result = ArchiveOperationResult(False, "解压失败")
            
            self.operation_finished.emit("extract_archive", result)
            return result
            
        except Exception as e:
            error_msg = f"解压失败: {str(e)}"
            result = ArchiveOperationResult(False, error_msg, error_details=str(e))
            self.operation_finished.emit("extract_archive", result)
            return result
    
    # ========== 文件打开操作 ==========
    
    def open_archive_file(self, archive_path: str, file_path: str) -> ArchiveOperationResult:
        """
        打开压缩包中的文件
        
        Args:
            archive_path: 压缩包路径
            file_path: 文件在压缩包中的路径
            
        Returns:
            ArchiveOperationResult: 操作结果
        """
        # 先解压到临时目录
        extract_result = self.extract_file_to_temp(archive_path, file_path)
        
        if not extract_result.success:
            return extract_result
        
        temp_file_path = extract_result.data["temp_path"]
        
        # 使用系统默认程序打开文件
        try:
            if sys.platform == "win32":
                os.startfile(temp_file_path)
            elif sys.platform == "darwin":  # macOS
                subprocess.call(["open", temp_file_path])
            else:  # Linux
                subprocess.call(["xdg-open", temp_file_path])
            
            return ArchiveOperationResult(
                True,
                f"已打开文件: {os.path.basename(file_path)}",
                {"temp_path": temp_file_path}
            )
        except Exception as e:
            return ArchiveOperationResult(False, f"无法打开文件: {str(e)}", error_details=str(e))
    
    def show_file_in_explorer(self, archive_path: str, file_path: str) -> ArchiveOperationResult:
        """
        在文件管理器中显示解压后的文件
        
        Args:
            archive_path: 压缩包路径
            file_path: 文件在压缩包中的路径
            
        Returns:
            ArchiveOperationResult: 操作结果
        """
        # 先解压到临时目录
        extract_result = self.extract_file_to_temp(archive_path, file_path)
        
        if not extract_result.success:
            return extract_result
        
        temp_file_path = extract_result.data["temp_path"]
        
        try:
            if sys.platform == "win32":
                # Windows: 选中文件并打开资源管理器
                subprocess.run(['explorer', '/select,', temp_file_path])
            else:
                # 其他系统：打开包含文件夹
                parent_dir = os.path.dirname(temp_file_path)
                if sys.platform == "darwin":  # macOS
                    subprocess.call(["open", parent_dir])
                else:  # Linux
                    subprocess.call(["xdg-open", parent_dir])
            
            return ArchiveOperationResult(
                True,
                f"已在文件管理器中显示: {os.path.basename(file_path)}",
                {"temp_path": temp_file_path}
            )
        except Exception as e:
            return ArchiveOperationResult(False, f"无法在文件管理器中显示: {str(e)}", error_details=str(e))
    
    # ========== 压缩包修改操作 ==========
    
    def rename_archive_file(self, archive_path: str, old_path: str, 
                           new_name: str = None) -> ArchiveOperationResult:
        """
        重命名压缩包中的文件
        
        Args:
            archive_path: 压缩包路径
            old_path: 原文件路径
            new_name: 新名称，如果为None则弹出输入框
            
        Returns:
            ArchiveOperationResult: 操作结果
        """
        if not self.archive_manager:
            return ArchiveOperationResult(False, "压缩包管理器不可用")
        
        old_name = os.path.basename(old_path)
        
        # 如果没有提供新名称，弹出输入框
        if new_name is None:
            if not self.parent_widget:
                return ArchiveOperationResult(False, "无法获取新名称：缺少父窗口")
            
            new_name, ok = QInputDialog.getText(
                self.parent_widget, "重命名", 
                f"请输入新名称:", text=old_name
            )
            
            if not ok or not new_name.strip():
                return ArchiveOperationResult(False, "操作已取消")
            
            new_name = new_name.strip()
        
        if new_name == old_name:
            return ArchiveOperationResult(False, "新名称与原名称相同")
        
        # 计算新的文件路径
        parent_dir = os.path.dirname(old_path)
        new_path = os.path.join(parent_dir, new_name).replace('\\', '/')
        
        try:
            self.operation_started.emit("rename_file", archive_path)
            
            success = self.archive_manager.rename_file_in_archive(
                archive_path, old_path, new_path
            )
            
            if success:
                result = ArchiveOperationResult(
                    True,
                    f"成功重命名为: {new_name}",
                    {"old_path": old_path, "new_path": new_path}
                )
            else:
                result = ArchiveOperationResult(False, "重命名失败")
            
            self.operation_finished.emit("rename_file", result)
            return result
            
        except Exception as e:
            error_msg = f"重命名失败: {str(e)}"
            result = ArchiveOperationResult(False, error_msg, error_details=str(e))
            self.operation_finished.emit("rename_file", result)
            return result
    
    def delete_archive_file(self, archive_path: str, file_path: str, 
                           confirm: bool = True) -> ArchiveOperationResult:
        """
        删除压缩包中的文件
        
        Args:
            archive_path: 压缩包路径
            file_path: 要删除的文件路径
            confirm: 是否需要用户确认
            
        Returns:
            ArchiveOperationResult: 操作结果
        """
        if not self.archive_manager:
            return ArchiveOperationResult(False, "压缩包管理器不可用")
        
        # 用户确认
        if confirm and self.parent_widget:
            file_name = os.path.basename(file_path)
            reply = QMessageBox.question(
                self.parent_widget, "确认删除", 
                f"确定要从压缩包中删除 '{file_name}' 吗？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply != QMessageBox.Yes:
                return ArchiveOperationResult(False, "用户取消了删除操作")
        
        try:
            self.operation_started.emit("delete_file", archive_path)
            
            success = self.archive_manager.delete_file_from_archive(
                archive_path, file_path
            )
            
            if success:
                result = ArchiveOperationResult(
                    True,
                    f"成功删除文件: {os.path.basename(file_path)}",
                    {"deleted_file": file_path}
                )
            else:
                result = ArchiveOperationResult(False, "删除失败")
            
            self.operation_finished.emit("delete_file", result)
            return result
            
        except Exception as e:
            error_msg = f"删除失败: {str(e)}"
            result = ArchiveOperationResult(False, error_msg, error_details=str(e))
            self.operation_finished.emit("delete_file", result)
            return result
    
    # ========== 压缩包导航操作 ==========
    
    def get_parent_directory(self, current_dir: str) -> str:
        """获取父目录路径"""
        if not current_dir:
            return ""  # 已在根目录
        
        parent_dir = os.path.dirname(current_dir)
        if parent_dir == current_dir:
            return ""  # 到达根目录
        
        return parent_dir
    
    def open_archive_folder_in_explorer(self, archive_path: str) -> ArchiveOperationResult:
        """在文件管理器中打开压缩包所在文件夹"""
        if not os.path.exists(archive_path):
            return ArchiveOperationResult(False, "压缩包文件不存在")
        
        archive_dir = os.path.dirname(archive_path)
        
        try:
            if sys.platform == "win32":
                os.startfile(archive_dir)
            elif sys.platform == "darwin":  # macOS
                subprocess.call(["open", archive_dir])
            else:  # Linux
                subprocess.call(["xdg-open", archive_dir])
            
            return ArchiveOperationResult(
                True,
                f"已在文件管理器中打开压缩包所在文件夹",
                {"archive_dir": archive_dir}
            )
        except Exception as e:
            return ArchiveOperationResult(False, f"无法打开文件夹: {str(e)}", error_details=str(e))
    
    # ========== 临时文件管理 ==========
    
    def cleanup_temp_files(self):
        """清理所有临时文件"""
        for temp_dir in self.temp_directories:
            try:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
            except Exception as e:
                logger.warning(f"Failed to cleanup temp directory {temp_dir}: {e}")
        
        self.temp_directories.clear()
    
    def __del__(self):
        """析构函数，自动清理临时文件"""
        self.cleanup_temp_files() 