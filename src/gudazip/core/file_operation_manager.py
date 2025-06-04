# -*- coding: utf-8 -*-
"""
文件操作管理器
负责所有文件系统相关的操作，包括创建、删除、重命名、复制、移动等
将业务逻辑从UI层完全分离
"""

import os
import shutil
import sys
import subprocess
from typing import List, Optional, Tuple, Dict, Any
from pathlib import Path
from PySide6.QtWidgets import QMessageBox, QInputDialog, QWidget
from PySide6.QtCore import QObject, Signal
import logging

logger = logging.getLogger(__name__)


class FileOperationResult:
    """文件操作结果封装"""
    
    def __init__(self, success: bool = True, message: str = "", 
                 affected_files: List[str] = None, error_details: str = ""):
        self.success = success
        self.message = message
        self.affected_files = affected_files or []
        self.error_details = error_details
        self.operation_count = len(self.affected_files)
    
    def __bool__(self):
        return self.success
    
    def __str__(self):
        return f"FileOperationResult(success={self.success}, message='{self.message}', files={self.operation_count})"


class ClipboardManager:
    """剪贴板管理器"""
    
    def __init__(self):
        self.items: List[str] = []
        self.operation: str = ""  # "copy" 或 "cut"
    
    def copy(self, file_paths: List[str]) -> bool:
        """复制文件到剪贴板"""
        if not file_paths:
            return False
        
        self.items = [path for path in file_paths if os.path.exists(path)]
        self.operation = "copy"
        return len(self.items) > 0
    
    def cut(self, file_paths: List[str]) -> bool:
        """剪切文件到剪贴板"""
        if not file_paths:
            return False
        
        self.items = [path for path in file_paths if os.path.exists(path)]
        self.operation = "cut"
        return len(self.items) > 0
    
    def clear(self):
        """清空剪贴板"""
        self.items.clear()
        self.operation = ""
    
    def is_empty(self) -> bool:
        """检查剪贴板是否为空"""
        return len(self.items) == 0
    
    def get_operation_type(self) -> str:
        """获取操作类型"""
        return self.operation


class FileOperationManager(QObject):
    """
    文件操作管理器
    
    负责所有文件系统操作，包括：
    - 文件/文件夹的创建、删除、重命名、复制、移动
    - 权限检查和管理
    - 剪贴板操作
    - 错误处理和用户交互
    """
    
    # 信号定义
    operation_started = Signal(str, list)  # 操作开始 (操作类型, 文件列表)
    operation_finished = Signal(str, object)  # 操作完成 (操作类型, FileOperationResult)
    progress_updated = Signal(int, int)  # 进度更新 (当前, 总数)
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__()
        self.parent_widget = parent
        self.clipboard = ClipboardManager()
        
    def set_parent_widget(self, parent: QWidget):
        """设置父窗口，用于显示对话框"""
        self.parent_widget = parent
    
    # ========== 文件基础操作 ==========
    
    def create_folder(self, parent_path: str, folder_name: str = None) -> FileOperationResult:
        """
        创建新文件夹
        
        Args:
            parent_path: 父目录路径
            folder_name: 文件夹名称，如果为None则弹出输入框
            
        Returns:
            FileOperationResult: 操作结果
        """
        if not os.path.exists(parent_path) or not os.path.isdir(parent_path):
            return FileOperationResult(False, "目标路径不存在或不是文件夹", error_details=f"Invalid parent path: {parent_path}")
        
        # 如果没有提供文件夹名称，弹出输入框
        if folder_name is None:
            if not self.parent_widget:
                return FileOperationResult(False, "无法获取文件夹名称：缺少父窗口")
            
            folder_name, ok = QInputDialog.getText(
                self.parent_widget, "新建文件夹", 
                "请输入文件夹名称:", text="新建文件夹"
            )
            
            if not ok or not folder_name.strip():
                return FileOperationResult(False, "操作已取消")
            
            folder_name = folder_name.strip()
        
        new_folder_path = os.path.join(parent_path, folder_name)
        
        if os.path.exists(new_folder_path):
            return FileOperationResult(False, f"文件夹 '{folder_name}' 已经存在")
        
        try:
            self.operation_started.emit("create_folder", [new_folder_path])
            os.makedirs(new_folder_path)
            result = FileOperationResult(True, f"成功创建文件夹: {folder_name}", [new_folder_path])
            self.operation_finished.emit("create_folder", result)
            return result
        except Exception as e:
            error_msg = f"无法创建文件夹: {str(e)}"
            result = FileOperationResult(False, error_msg, error_details=str(e))
            self.operation_finished.emit("create_folder", result)
            return result
    
    def create_file(self, parent_path: str, file_name: str = None) -> FileOperationResult:
        """
        创建新文件
        
        Args:
            parent_path: 父目录路径
            file_name: 文件名称，如果为None则弹出输入框
            
        Returns:
            FileOperationResult: 操作结果
        """
        if not os.path.exists(parent_path) or not os.path.isdir(parent_path):
            return FileOperationResult(False, "目标路径不存在或不是文件夹", error_details=f"Invalid parent path: {parent_path}")
        
        # 如果没有提供文件名称，弹出输入框
        if file_name is None:
            if not self.parent_widget:
                return FileOperationResult(False, "无法获取文件名称：缺少父窗口")
            
            file_name, ok = QInputDialog.getText(
                self.parent_widget, "新建文件", 
                "请输入文件名称:", text="新建文件.txt"
            )
            
            if not ok or not file_name.strip():
                return FileOperationResult(False, "操作已取消")
            
            file_name = file_name.strip()
        
        new_file_path = os.path.join(parent_path, file_name)
        
        if os.path.exists(new_file_path):
            return FileOperationResult(False, f"文件 '{file_name}' 已经存在")
        
        try:
            self.operation_started.emit("create_file", [new_file_path])
            with open(new_file_path, 'w', encoding='utf-8') as f:
                f.write("")  # 创建空文件
            result = FileOperationResult(True, f"成功创建文件: {file_name}", [new_file_path])
            self.operation_finished.emit("create_file", result)
            return result
        except Exception as e:
            error_msg = f"无法创建文件: {str(e)}"
            result = FileOperationResult(False, error_msg, error_details=str(e))
            self.operation_finished.emit("create_file", result)
            return result
    
    def delete_files(self, file_paths: List[str], confirm: bool = True) -> FileOperationResult:
        """
        删除多个文件或文件夹
        
        Args:
            file_paths: 要删除的文件路径列表
            confirm: 是否需要用户确认
            
        Returns:
            FileOperationResult: 操作结果
        """
        if not file_paths:
            return FileOperationResult(False, "没有选择要删除的文件")
        
        # 过滤出存在的文件
        existing_paths = [path for path in file_paths if os.path.exists(path)]
        if not existing_paths:
            return FileOperationResult(False, "选中的文件或文件夹都不存在")
        
        # 检查权限
        permission_result = self._check_operation_permission(existing_paths, "删除")
        if not permission_result.success:
            return permission_result
        
        # 用户确认
        if confirm and self.parent_widget:
            if not self._confirm_delete_operation(existing_paths):
                return FileOperationResult(False, "用户取消了删除操作")
        
        # 执行删除
        self.operation_started.emit("delete", existing_paths)
        success_count = 0
        failed_items = []
        
        for i, file_path in enumerate(existing_paths):
            self.progress_updated.emit(i + 1, len(existing_paths))
            try:
                if os.path.isdir(file_path):
                    shutil.rmtree(file_path)
                else:
                    os.remove(file_path)
                success_count += 1
            except Exception as e:
                failed_items.append(f"{os.path.basename(file_path)}: {str(e)}")
        
        # 构建结果
        if failed_items:
            error_message = "以下项目删除失败：\n" + "\n".join(failed_items)
            result = FileOperationResult(False, error_message, 
                                       existing_paths[:success_count], 
                                       error_details=str(failed_items))
        else:
            result = FileOperationResult(True, f"成功删除 {success_count} 个项目", existing_paths)
        
        self.operation_finished.emit("delete", result)
        return result
    
    def rename_file(self, file_path: str, new_name: str = None) -> FileOperationResult:
        """
        重命名文件或文件夹
        
        Args:
            file_path: 要重命名的文件路径
            new_name: 新名称，如果为None则弹出输入框
            
        Returns:
            FileOperationResult: 操作结果
        """
        if not os.path.exists(file_path):
            return FileOperationResult(False, "文件或文件夹不存在")
        
        # 检查权限
        permission_result = self._check_operation_permission([file_path], "重命名")
        if not permission_result.success:
            return permission_result
        
        old_name = os.path.basename(file_path)
        
        # 如果没有提供新名称，弹出输入框
        if new_name is None:
            if not self.parent_widget:
                return FileOperationResult(False, "无法获取新名称：缺少父窗口")
            
            new_name, ok = QInputDialog.getText(
                self.parent_widget, "重命名", 
                f"请输入新名称:", text=old_name
            )
            
            if not ok or not new_name.strip():
                return FileOperationResult(False, "操作已取消")
            
            new_name = new_name.strip()
        
        if new_name == old_name:
            return FileOperationResult(False, "新名称与原名称相同")
        
        new_path = os.path.join(os.path.dirname(file_path), new_name)
        
        if os.path.exists(new_path):
            return FileOperationResult(False, f"名称 '{new_name}' 已经存在")
        
        try:
            self.operation_started.emit("rename", [file_path])
            os.rename(file_path, new_path)
            result = FileOperationResult(True, f"成功重命名为: {new_name}", [new_path])
            self.operation_finished.emit("rename", result)
            return result
        except Exception as e:
            error_msg = f"无法重命名: {str(e)}"
            result = FileOperationResult(False, error_msg, error_details=str(e))
            self.operation_finished.emit("rename", result)
            return result
    
    # ========== 剪贴板操作 ==========
    
    def copy_to_clipboard(self, file_paths: List[str]) -> FileOperationResult:
        """复制文件到剪贴板"""
        if not file_paths:
            return FileOperationResult(False, "没有选择要复制的文件")
        
        # 检查权限
        permission_result = self._check_operation_permission(file_paths, "复制")
        if not permission_result.success:
            return permission_result
        
        success = self.clipboard.copy(file_paths)
        if success:
            return FileOperationResult(True, f"已复制 {len(self.clipboard.items)} 个项目到剪贴板", 
                                     self.clipboard.items)
        else:
            return FileOperationResult(False, "复制失败：没有有效的文件")
    
    def cut_to_clipboard(self, file_paths: List[str]) -> FileOperationResult:
        """剪切文件到剪贴板"""
        if not file_paths:
            return FileOperationResult(False, "没有选择要剪切的文件")
        
        # 检查权限
        permission_result = self._check_operation_permission(file_paths, "剪切")
        if not permission_result.success:
            return permission_result
        
        success = self.clipboard.cut(file_paths)
        if success:
            return FileOperationResult(True, f"已剪切 {len(self.clipboard.items)} 个项目到剪贴板", 
                                     self.clipboard.items)
        else:
            return FileOperationResult(False, "剪切失败：没有有效的文件")
    
    def paste_from_clipboard(self, target_dir: str) -> FileOperationResult:
        """从剪贴板粘贴文件"""
        if self.clipboard.is_empty():
            return FileOperationResult(False, "剪贴板为空")
        
        if not os.path.exists(target_dir) or not os.path.isdir(target_dir):
            return FileOperationResult(False, "目标路径不存在或不是文件夹")
        
        self.operation_started.emit("paste", self.clipboard.items)
        success_count = 0
        error_count = 0
        processed_files = []
        
        for i, source_path in enumerate(self.clipboard.items):
            self.progress_updated.emit(i + 1, len(self.clipboard.items))
            
            if not os.path.exists(source_path):
                error_count += 1
                continue
            
            file_name = os.path.basename(source_path)
            target_path = self._get_unique_target_path(target_dir, file_name)
            
            try:
                if self.clipboard.operation == "copy":
                    if os.path.isdir(source_path):
                        shutil.copytree(source_path, target_path)
                    else:
                        shutil.copy2(source_path, target_path)
                elif self.clipboard.operation == "cut":
                    shutil.move(source_path, target_path)
                
                processed_files.append(target_path)
                success_count += 1
            except Exception as e:
                logger.error(f"粘贴文件失败 {source_path}: {e}")
                error_count += 1
        
        # 如果是剪切操作，清空剪贴板
        if self.clipboard.operation == "cut":
            self.clipboard.clear()
        
        # 构建结果
        if error_count > 0:
            message = f"粘贴完成：成功 {success_count} 个，失败 {error_count} 个"
            result = FileOperationResult(success_count > 0, message, processed_files)
        else:
            result = FileOperationResult(True, f"成功粘贴 {success_count} 个项目", processed_files)
        
        self.operation_finished.emit("paste", result)
        return result
    
    def clear_clipboard(self):
        """清空剪贴板"""
        self.clipboard.clear()
    
    def get_clipboard_info(self) -> Dict[str, Any]:
        """获取剪贴板信息"""
        return {
            "items": self.clipboard.items.copy(),
            "operation": self.clipboard.operation,
            "count": len(self.clipboard.items),
            "is_empty": self.clipboard.is_empty()
        }
    
    # ========== 文件系统操作 ==========
    
    def open_file(self, file_path: str) -> FileOperationResult:
        """使用系统默认程序打开文件"""
        if not os.path.exists(file_path):
            return FileOperationResult(False, "文件不存在")
        
        if not os.path.isfile(file_path):
            return FileOperationResult(False, "这不是一个文件")
        
        try:
            if sys.platform == "win32":
                os.startfile(file_path)
            elif sys.platform == "darwin":  # macOS
                subprocess.call(["open", file_path])
            else:  # Linux
                subprocess.call(["xdg-open", file_path])
            
            return FileOperationResult(True, f"已打开文件: {os.path.basename(file_path)}", [file_path])
        except Exception as e:
            return FileOperationResult(False, f"无法打开文件: {str(e)}", error_details=str(e))
    
    def open_in_explorer(self, dir_path: str) -> FileOperationResult:
        """在文件管理器中打开目录"""
        if not os.path.exists(dir_path):
            return FileOperationResult(False, "目录不存在")
        
        try:
            if sys.platform == "win32":
                os.startfile(dir_path)
            elif sys.platform == "darwin":  # macOS
                subprocess.call(["open", dir_path])
            else:  # Linux
                subprocess.call(["xdg-open", dir_path])
            
            return FileOperationResult(True, f"已在文件管理器中打开: {os.path.basename(dir_path)}", [dir_path])
        except Exception as e:
            return FileOperationResult(False, f"无法打开目录: {str(e)}", error_details=str(e))
    
    # ========== 私有辅助方法 ==========
    
    def _check_operation_permission(self, file_paths: List[str], operation: str) -> FileOperationResult:
        """检查操作权限"""
        try:
            from .permission_manager import PermissionManager
            if not PermissionManager.request_admin_if_needed(file_paths, operation):
                return FileOperationResult(False, f"没有执行{operation}操作的权限")
            return FileOperationResult(True)
        except ImportError:
            # 如果权限管理器不可用，跳过权限检查
            logger.warning("PermissionManager not available, skipping permission check")
            return FileOperationResult(True)
    
    def _confirm_delete_operation(self, file_paths: List[str]) -> bool:
        """确认删除操作"""
        if not self.parent_widget:
            return True  # 如果没有父窗口，默认确认
        
        # 统计文件和文件夹数量
        folders = [path for path in file_paths if os.path.isdir(path)]
        files = [path for path in file_paths if os.path.isfile(path)]
        
        # 构建确认消息
        if len(file_paths) == 1:
            file_name = os.path.basename(file_paths[0])
            if os.path.isdir(file_paths[0]):
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
            self.parent_widget, "确认删除", 
            message,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        return reply == QMessageBox.Yes
    
    def _get_unique_target_path(self, target_dir: str, file_name: str) -> str:
        """获取唯一的目标路径（如果文件已存在，添加数字后缀）"""
        target_path = os.path.join(target_dir, file_name)
        
        if not os.path.exists(target_path):
            return target_path
        
        # 如果文件已存在，添加数字后缀
        counter = 1
        name, ext = os.path.splitext(file_name)
        while os.path.exists(target_path):
            new_name = f"{name}_{counter}{ext}"
            target_path = os.path.join(target_dir, new_name)
            counter += 1
        
        return target_path 