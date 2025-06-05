# -*- coding: utf-8 -*-
"""
文件操作管理器
负责所有文件系统相关的操作，包括创建、删除、重命名、复制、移动等
将业务逻辑从UI层完全分离
支持异步文件操作以避免UI冻结
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

# 导入错误管理器
from .error_manager import ErrorManager, ErrorCategory, ErrorSeverity, get_error_manager

logger = logging.getLogger(__name__)

# 异步操作支持
try:
    from .async_file_operations import AsyncFileOperationManager
    ASYNC_OPERATIONS_AVAILABLE = True
except ImportError:
    AsyncFileOperationManager = None
    ASYNC_OPERATIONS_AVAILABLE = False
    logger.warning("AsyncFileOperationManager not available, using synchronous operations only")


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
    
    负责所有文件系统相关的操作：
    1. 文件/文件夹的创建、删除、重命名、复制、移动
    2. 剪贴板操作（复制、剪切、粘贴）
    3. 文件/文件夹的打开、在资源管理器中显示
    4. 异步文件操作支持
    5. 统一的错误处理
    
    通过信号与UI层通信，完全分离业务逻辑
    """
    
    # 信号定义
    operation_finished = Signal(str, object)  # operation_type, FileOperationResult
    
    # 异步操作信号
    async_operation_started = Signal(str, str, str)    # operation_id, operation_type, description
    async_operation_completed = Signal(str, str, object)  # operation_id, operation_type, result
    async_operation_failed = Signal(str, str, str)     # operation_id, operation_type, error_message
    
    def __init__(self, parent: Optional[QWidget] = None, enable_async: bool = True):
        super().__init__()
        self.parent_widget = parent
        
        # 初始化错误管理器
        self.error_manager = get_error_manager(parent)
        
        # 剪贴板操作状态
        self.clipboard_operation = None  # "copy" 或 "cut"
        self.clipboard_items = []
        
        # 异步操作配置
        self.enable_async = enable_async and ASYNC_OPERATIONS_AVAILABLE
        self.async_manager = None
        
        if self.enable_async:
            try:
                self.async_manager = AsyncFileOperationManager(self)
                # 连接异步操作信号
                self.async_manager.operation_started.connect(self._on_async_operation_started)
                self.async_manager.operation_completed.connect(self._on_async_operation_completed)
                self.async_manager.operation_failed.connect(self._on_async_operation_failed)
                logger.info("Async file operations enabled")
            except Exception as e:
                # 使用错误管理器处理异步初始化失败
                self.error_manager.handle_exception(
                    e, 
                    context={"operation": "initialize_async_operations"},
                    show_dialog=False,  # 不显示对话框，只记录日志
                    category=ErrorCategory.APP_DEPENDENCY
                )
                self.enable_async = False
                self.async_manager = None
        
        # 异步操作阈值（文件数量超过此值时使用异步操作）
        self.async_copy_threshold = 5    # 复制超过5个文件时使用异步
        self.async_move_threshold = 3    # 移动超过3个文件时使用异步
        self.async_delete_threshold = 10 # 删除超过10个文件时使用异步
        self.async_paste_threshold = 5   # 粘贴超过5个文件时使用异步
        
    def _on_async_operation_started(self, operation_id: str, description: str):
        """处理异步操作开始信号"""
        # 提取操作类型
        operation_type = "async_operation"
        if "复制" in description:
            operation_type = "copy"
        elif "移动" in description:
            operation_type = "move"
        elif "删除" in description:
            operation_type = "delete"
        elif "解压" in description:
            operation_type = "extract"
        
        self.async_operation_started.emit(operation_id, operation_type, description)
    
    def _on_async_operation_completed(self, operation_id: str, result):
        """处理异步操作完成信号"""
        # 转换为FileOperationResult格式
        if isinstance(result, dict):
            if result.get('success', False):
                affected_files = []
                if 'copied_files' in result:
                    affected_files = result['copied_files']
                elif 'moved_files' in result:
                    affected_files = result['moved_files']
                elif 'deleted_files' in result:
                    affected_files = result['deleted_files']
                elif 'extracted_files' in result:
                    affected_files = result['extracted_files']
                
                # 构建成功消息
                if 'copied_files' in result:
                    message = f"成功复制 {len(affected_files)} 个项目"
                    if result.get('total_size', 0) > 0:
                        size_mb = result['total_size'] / (1024 * 1024)
                        message += f"，总大小: {size_mb:.1f} MB"
                elif 'moved_files' in result:
                    message = f"成功移动 {len(affected_files)} 个项目"
                elif 'deleted_files' in result:
                    message = f"成功删除 {len(affected_files)} 个项目"
                elif 'extracted_files' in result:
                    message = f"成功解压 {len(affected_files)} 个文件到 {os.path.basename(result.get('target_dir', ''))}"
                else:
                    message = "操作完成"
                
                # 添加失败信息
                if result.get('failed_files'):
                    failed_count = len(result['failed_files'])
                    message += f"，{failed_count} 个项目失败"
                
                file_result = FileOperationResult(True, message, affected_files)
            else:
                message = "操作失败"
                if result.get('failed_files'):
                    message = "操作部分失败：\n" + "\n".join(result['failed_files'][:5])  # 只显示前5个错误
                    if len(result['failed_files']) > 5:
                        message += f"\n还有 {len(result['failed_files']) - 5} 个错误..."
                
                file_result = FileOperationResult(False, message, result.get('copied_files', []) or result.get('moved_files', []) or result.get('deleted_files', []))
        else:
            file_result = FileOperationResult(True, "异步操作完成", [])
        
        # 发送操作完成信号（保持与同步操作的一致性）
        operation_type = "async_operation"
        self.operation_finished.emit(operation_type, file_result)
        self.async_operation_completed.emit(operation_id, operation_type, file_result)
    
    def _on_async_operation_failed(self, operation_id: str, error_message: str):
        """处理异步操作失败信号"""
        file_result = FileOperationResult(False, f"异步操作失败: {error_message}", error_details=error_message)
        operation_type = "async_operation"
        self.operation_finished.emit(operation_type, file_result)
        self.async_operation_failed.emit(operation_id, operation_type, error_message)
    
    def set_parent_widget(self, parent: QWidget):
        """设置父窗口，用于显示对话框"""
        self.parent_widget = parent
    
    # ========== 文件基础操作 ==========
    
    def create_folder(self, parent_path: str, folder_name: str = None) -> FileOperationResult:
        """
        在指定目录下创建新文件夹
        
        Args:
            parent_path: 父目录路径
            folder_name: 文件夹名称（可选，如果不提供会弹出对话框）
            
        Returns:
            FileOperationResult: 操作结果
        """
        if not os.path.exists(parent_path):
            return FileOperationResult(False, "父目录不存在")
        
        if not os.path.isdir(parent_path):
            return FileOperationResult(False, "指定路径不是目录")
        
        # 检查权限 - 如果需要管理员权限则提示用户
        try:
            from .permission_manager import PermissionManager
            if not PermissionManager.request_admin_if_needed([parent_path], "创建文件夹"):
                return FileOperationResult(False, "需要管理员权限才能在此位置创建文件夹")
        except ImportError:
            logger.warning("PermissionManager not available, proceeding without permission check")
        except Exception as e:
            logger.error(f"Permission check failed: {e}")
        
        try:
            # 如果没有提供文件夹名称，弹出对话框询问
            if folder_name is None:
                if self.parent_widget:
                    text, ok = QInputDialog.getText(
                        self.parent_widget, "创建文件夹", 
                        "请输入文件夹名称:",
                        text="新建文件夹"
                    )
                    if not ok or not text:
                        return FileOperationResult(False, "用户取消创建文件夹操作")
                    folder_name = text.strip()
                else:
                    return FileOperationResult(False, "未提供文件夹名称且无法显示对话框")
            
            # 验证文件夹名称
            if not folder_name:
                return FileOperationResult(False, "文件夹名称不能为空")
            
            # 检查名称是否包含非法字符
            illegal_chars = ['<', '>', ':', '"', '|', '?', '*']
            if any(char in folder_name for char in illegal_chars):
                return FileOperationResult(False, f"文件夹名称不能包含以下字符: {' '.join(illegal_chars)}")
            
            # 构建完整路径
            folder_path = os.path.join(parent_path, folder_name)
            
            # 检查文件夹是否已存在
            if os.path.exists(folder_path):
                return FileOperationResult(False, f"文件夹 '{folder_name}' 已存在")
            
            # 创建文件夹
            os.makedirs(folder_path, exist_ok=False)
            
            result = FileOperationResult(
                True, 
                f"成功创建文件夹: {folder_name}",
                [folder_path]
            )
            
            self.operation_finished.emit("create_folder", result)
            return result
            
        except PermissionError as e:
            error_msg = f"权限不足，无法在此位置创建文件夹"
            self.error_manager.handle_exception(
                e,
                context={"parent_path": parent_path, "folder_name": folder_name, "operation": "create_folder"},
                category=ErrorCategory.FILE_PERMISSION
            )
            return FileOperationResult(False, error_msg)
        except OSError as e:
            error_msg = f"创建文件夹失败: {str(e)}"
            self.error_manager.handle_exception(
                e,
                context={"parent_path": parent_path, "folder_name": folder_name, "operation": "create_folder"},
                category=ErrorCategory.FILE_OPERATION
            )
            return FileOperationResult(False, error_msg)
        except Exception as e:
            self.error_manager.handle_exception(
                e,
                context={"parent_path": parent_path, "folder_name": folder_name, "operation": "create_folder"},
                category=ErrorCategory.FILE_OPERATION
            )
            return FileOperationResult(False, f"创建文件夹操作失败：{str(e)}")
    
    def create_file(self, parent_path: str, file_name: str = None) -> FileOperationResult:
        """
        在指定目录下创建新文件
        
        Args:
            parent_path: 父目录路径
            file_name: 文件名称（可选，如果不提供会弹出对话框）
            
        Returns:
            FileOperationResult: 操作结果
        """
        if not os.path.exists(parent_path):
            return FileOperationResult(False, "父目录不存在")
        
        if not os.path.isdir(parent_path):
            return FileOperationResult(False, "指定路径不是目录")
        
        # 检查权限 - 如果需要管理员权限则提示用户
        try:
            from .permission_manager import PermissionManager
            if not PermissionManager.request_admin_if_needed([parent_path], "创建文件"):
                return FileOperationResult(False, "需要管理员权限才能在此位置创建文件")
        except ImportError:
            logger.warning("PermissionManager not available, proceeding without permission check")
        except Exception as e:
            logger.error(f"Permission check failed: {e}")
        
        try:
            # 如果没有提供文件名称，弹出对话框询问
            if file_name is None:
                if self.parent_widget:
                    text, ok = QInputDialog.getText(
                        self.parent_widget, "创建文件", 
                        "请输入文件名称:",
                        text="新建文件.txt"
                    )
                    if not ok or not text:
                        return FileOperationResult(False, "用户取消创建文件操作")
                    file_name = text.strip()
                else:
                    return FileOperationResult(False, "未提供文件名称且无法显示对话框")
            
            # 验证文件名称
            if not file_name:
                return FileOperationResult(False, "文件名称不能为空")
            
            # 检查名称是否包含非法字符
            illegal_chars = ['<', '>', ':', '"', '|', '?', '*']
            if any(char in file_name for char in illegal_chars):
                return FileOperationResult(False, f"文件名称不能包含以下字符: {' '.join(illegal_chars)}")
            
            # 构建完整路径
            file_path = os.path.join(parent_path, file_name)
            
            # 检查文件是否已存在
            if os.path.exists(file_path):
                return FileOperationResult(False, f"文件 '{file_name}' 已存在")
            
            # 创建文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("")  # 创建空文件
            
            result = FileOperationResult(
                True, 
                f"成功创建文件: {file_name}",
                [file_path]
            )
            
            self.operation_finished.emit("create_file", result)
            return result
            
        except PermissionError as e:
            error_msg = f"权限不足，无法在此位置创建文件"
            self.error_manager.handle_exception(
                e,
                context={"parent_path": parent_path, "file_name": file_name, "operation": "create_file"},
                category=ErrorCategory.FILE_PERMISSION
            )
            return FileOperationResult(False, error_msg)
        except OSError as e:
            error_msg = f"创建文件失败: {str(e)}"
            self.error_manager.handle_exception(
                e,
                context={"parent_path": parent_path, "file_name": file_name, "operation": "create_file"},
                category=ErrorCategory.FILE_OPERATION
            )
            return FileOperationResult(False, error_msg)
        except Exception as e:
            self.error_manager.handle_exception(
                e,
                context={"parent_path": parent_path, "file_name": file_name, "operation": "create_file"},
                category=ErrorCategory.FILE_OPERATION
            )
            return FileOperationResult(False, f"创建文件操作失败：{str(e)}")
    
    def delete_files(self, file_paths: List[str], confirm: bool = True) -> FileOperationResult:
        """
        删除多个文件或文件夹（支持异步操作）
        
        Args:
            file_paths: 要删除的文件路径列表
            confirm: 是否需要确认
            
        Returns:
            FileOperationResult: 操作结果
        """
        if not file_paths:
            return FileOperationResult(False, "没有选择要删除的文件")
        
        # 检查权限 - 如果需要管理员权限则提示用户
        try:
            from .permission_manager import PermissionManager
            if not PermissionManager.request_admin_if_needed(file_paths, "删除"):
                return FileOperationResult(False, "需要管理员权限才能删除这些文件")
        except ImportError:
            # 权限管理器不可用时的警告
            logger.warning("PermissionManager not available, proceeding without permission check")
        except Exception as e:
            # 权限请求过程中的错误
            logger.error(f"Permission check failed: {e}")
            # 继续执行，但记录错误
        
        # 检查异步操作条件
        if self.enable_async and len(file_paths) >= self.async_delete_threshold:
            try:
                operation_id = self.async_manager.async_delete_files(file_paths, confirm)
                return FileOperationResult(True, f"开始异步删除 {len(file_paths)} 个文件", file_paths)
            except Exception as e:
                self.error_manager.handle_exception(
                    e,
                    context={"operation": "async_delete", "file_count": len(file_paths)},
                    category=ErrorCategory.FILE_OPERATION
                )
                # 异步失败时回退到同步操作
        
        # 同步删除操作
        try:
            if confirm:
                reply = QMessageBox.question(
                    self.parent_widget, "确认删除",
                    f"确定要删除选中的 {len(file_paths)} 个项目吗？\n\n注意：此操作不可撤销！",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if reply != QMessageBox.Yes:
                    return FileOperationResult(False, "用户取消删除操作")
            
            deleted_files = []
            failed_files = []
            
            for file_path in file_paths:
                try:
                    if os.path.exists(file_path):
                        if os.path.isdir(file_path):
                            shutil.rmtree(file_path)
                        else:
                            os.remove(file_path)
                        deleted_files.append(file_path)
                    else:
                        failed_files.append(f"{file_path} (文件不存在)")
                except PermissionError as e:
                    failed_files.append(f"{file_path} (权限不足)")
                    self.error_manager.handle_exception(
                        e,
                        context={"path": file_path, "operation": "delete"},
                        show_dialog=False,  # 不单独显示，在结果中统一处理
                        category=ErrorCategory.FILE_PERMISSION
                    )
                except Exception as e:
                    failed_files.append(f"{file_path} (删除失败: {str(e)})")
                    self.error_manager.handle_exception(
                        e,
                        context={"path": file_path, "operation": "delete"},
                        show_dialog=False,
                        category=ErrorCategory.FILE_OPERATION
                    )
            
            # 生成结果
            if failed_files:
                if deleted_files:
                    message = f"部分删除成功：成功删除 {len(deleted_files)} 个文件，{len(failed_files)} 个失败"
                    details = "失败的文件：\n" + "\n".join(failed_files[:10])  # 限制显示数量
                    if len(failed_files) > 10:
                        details += f"\n还有 {len(failed_files) - 10} 个失败..."
                else:
                    message = f"删除全部失败：{len(failed_files)} 个文件删除失败"
                    details = "失败的文件：\n" + "\n".join(failed_files[:10])
                    if len(failed_files) > 10:
                        details += f"\n还有 {len(failed_files) - 10} 个失败..."
                
                # 显示部分失败的错误信息
                self.error_manager.handle_error(
                    ErrorCategory.FILE_OPERATION,
                    ErrorSeverity.WARNING if deleted_files else ErrorSeverity.ERROR,
                    message,
                    details=details,
                    context={"deleted_count": len(deleted_files), "failed_count": len(failed_files)}
                )
                
                return FileOperationResult(bool(deleted_files), message, deleted_files, details)
            else:
                message = f"成功删除 {len(deleted_files)} 个文件"
                return FileOperationResult(True, message, deleted_files)
                
        except Exception as e:
            self.error_manager.handle_exception(
                e,
                context={"operation": "delete_files", "file_count": len(file_paths)},
                category=ErrorCategory.FILE_OPERATION
            )
            return FileOperationResult(False, f"删除操作失败：{str(e)}")
    
    def rename_file(self, file_path: str, new_name: str = None) -> FileOperationResult:
        """
        重命名文件或文件夹
        
        Args:
            file_path: 要重命名的文件路径
            new_name: 新的文件名（可选，如果不提供会弹出对话框）
            
        Returns:
            FileOperationResult: 操作结果
        """
        if not os.path.exists(file_path):
            return FileOperationResult(False, "要重命名的文件不存在")
        
        # 检查权限 - 如果需要管理员权限则提示用户
        try:
            from .permission_manager import PermissionManager
            if not PermissionManager.request_admin_if_needed([file_path], "重命名"):
                return FileOperationResult(False, "需要管理员权限才能重命名此文件")
        except ImportError:
            logger.warning("PermissionManager not available, proceeding without permission check")
        except Exception as e:
            logger.error(f"Permission check failed: {e}")
        
        try:
            current_name = os.path.basename(file_path)
            parent_dir = os.path.dirname(file_path)
            
            # 如果没有提供新名称，弹出对话框询问
            if new_name is None:
                if self.parent_widget:
                    text, ok = QInputDialog.getText(
                        self.parent_widget, "重命名", 
                        f"请输入新的名称:", 
                        text=current_name
                    )
                    if not ok or not text:
                        return FileOperationResult(False, "用户取消重命名操作")
                    new_name = text.strip()
                else:
                    return FileOperationResult(False, "未提供新名称且无法显示对话框")
            
            # 验证新名称
            if not new_name or new_name == current_name:
                return FileOperationResult(False, "新名称不能为空或与原名称相同")
            
            # 检查新名称是否包含非法字符
            illegal_chars = ['<', '>', ':', '"', '|', '?', '*']
            if any(char in new_name for char in illegal_chars):
                return FileOperationResult(False, f"文件名不能包含以下字符: {' '.join(illegal_chars)}")
            
            # 构建新的完整路径
            new_path = os.path.join(parent_dir, new_name)
            
            # 检查目标是否已存在
            if os.path.exists(new_path):
                return FileOperationResult(False, f"名称 '{new_name}' 已存在")
            
            # 执行重命名
            os.rename(file_path, new_path)
            
            result = FileOperationResult(
                True, 
                f"已将 '{current_name}' 重命名为 '{new_name}'",
                [new_path]
            )
            
            self.operation_finished.emit("rename", result)
            return result
            
        except PermissionError as e:
            error_msg = f"权限不足，无法重命名 '{current_name}'"
            self.error_manager.handle_exception(
                e,
                context={"path": file_path, "new_name": new_name, "operation": "rename"},
                category=ErrorCategory.FILE_PERMISSION
            )
            return FileOperationResult(False, error_msg)
        except OSError as e:
            error_msg = f"重命名失败: {str(e)}"
            self.error_manager.handle_exception(
                e,
                context={"path": file_path, "new_name": new_name, "operation": "rename"},
                category=ErrorCategory.FILE_OPERATION
            )
            return FileOperationResult(False, error_msg)
        except Exception as e:
            self.error_manager.handle_exception(
                e,
                context={"path": file_path, "new_name": new_name, "operation": "rename"},
                category=ErrorCategory.FILE_OPERATION
            )
            return FileOperationResult(False, f"重命名操作失败：{str(e)}")
    
    # ========== 剪贴板操作 ==========
    
    def copy_to_clipboard(self, file_paths: List[str]) -> FileOperationResult:
        """
        复制文件到剪贴板
        
        Args:
            file_paths: 要复制的文件路径列表
            
        Returns:
            FileOperationResult: 操作结果
        """
        try:
            if not file_paths:
                return FileOperationResult(False, "没有选择要复制的文件")
            
            # 检查文件是否存在
            existing_files = []
            missing_files = []
            
            for file_path in file_paths:
                if os.path.exists(file_path):
                    existing_files.append(file_path)
                else:
                    missing_files.append(file_path)
            
            if missing_files:
                if existing_files:
                    # 部分文件不存在
                    self.error_manager.handle_error(
                        ErrorCategory.FILE_NOT_FOUND,
                        ErrorSeverity.WARNING,
                        f"部分文件不存在，已忽略 {len(missing_files)} 个文件",
                        details="不存在的文件：\n" + "\n".join(missing_files[:5]),
                        context={"missing_count": len(missing_files), "existing_count": len(existing_files)}
                    )
                else:
                    # 全部文件不存在
                    self.error_manager.handle_error(
                        ErrorCategory.FILE_NOT_FOUND,
                        ErrorSeverity.ERROR,
                        "所选文件都不存在",
                        details="不存在的文件：\n" + "\n".join(missing_files[:5]),
                        context={"missing_files": missing_files}
                    )
                    return FileOperationResult(False, "所选文件都不存在")
            
            # 设置剪贴板状态
            self.clipboard_operation = "copy"
            self.clipboard_items = existing_files
            
            return FileOperationResult(True, f"已复制 {len(existing_files)} 个项目到剪贴板", existing_files)
            
        except Exception as e:
            self.error_manager.handle_exception(
                e,
                context={"operation": "copy_to_clipboard", "file_count": len(file_paths)},
                category=ErrorCategory.FILE_OPERATION
            )
            return FileOperationResult(False, f"复制到剪贴板失败：{str(e)}")
    
    def cut_to_clipboard(self, file_paths: List[str]) -> FileOperationResult:
        """
        剪切文件到剪贴板
        
        Args:
            file_paths: 要剪切的文件路径列表
            
        Returns:
            FileOperationResult: 操作结果
        """
        try:
            if not file_paths:
                return FileOperationResult(False, "没有选择要剪切的文件")
            
            # 检查文件是否存在
            existing_files = []
            missing_files = []
            
            for file_path in file_paths:
                if os.path.exists(file_path):
                    existing_files.append(file_path)
                else:
                    missing_files.append(file_path)
            
            if missing_files:
                if existing_files:
                    # 部分文件不存在
                    self.error_manager.handle_error(
                        ErrorCategory.FILE_NOT_FOUND,
                        ErrorSeverity.WARNING,
                        f"部分文件不存在，已忽略 {len(missing_files)} 个文件",
                        details="不存在的文件：\n" + "\n".join(missing_files[:5]),
                        context={"missing_count": len(missing_files), "existing_count": len(existing_files)}
                    )
                else:
                    # 全部文件不存在
                    self.error_manager.handle_error(
                        ErrorCategory.FILE_NOT_FOUND,
                        ErrorSeverity.ERROR,
                        "所选文件都不存在",
                        details="不存在的文件：\n" + "\n".join(missing_files[:5]),
                        context={"missing_files": missing_files}
                    )
                    return FileOperationResult(False, "所选文件都不存在")
            
            # 设置剪贴板状态
            self.clipboard_operation = "cut"
            self.clipboard_items = existing_files
            
            return FileOperationResult(True, f"已剪切 {len(existing_files)} 个项目到剪贴板", existing_files)
            
        except Exception as e:
            self.error_manager.handle_exception(
                e,
                context={"operation": "cut_to_clipboard", "file_count": len(file_paths)},
                category=ErrorCategory.FILE_OPERATION
            )
            return FileOperationResult(False, f"剪切到剪贴板失败：{str(e)}")

    def paste_from_clipboard(self, target_dir: str) -> FileOperationResult:
        """
        从剪贴板粘贴文件（支持异步操作）
        
        Args:
            target_dir: 目标目录
            
        Returns:
            FileOperationResult: 操作结果
        """
        try:
            if not self.clipboard_items:
                return FileOperationResult(False, "剪贴板为空")
            
            if not os.path.exists(target_dir):
                return FileOperationResult(False, "目标目录不存在")
            
            if not os.path.isdir(target_dir):
                return FileOperationResult(False, "目标路径不是目录")
            
            # 检查权限 - 如果需要管理员权限则提示用户
            try:
                from .permission_manager import PermissionManager
                operation_name = "移动" if self.clipboard_operation == "cut" else "复制"
                if not PermissionManager.request_admin_if_needed([target_dir], f"{operation_name}文件"):
                    return FileOperationResult(False, f"需要管理员权限才能在此位置{operation_name}文件")
            except ImportError:
                logger.warning("PermissionManager not available, proceeding without permission check")
            except Exception as e:
                logger.error(f"Permission check failed: {e}")
            
            # 检查异步操作条件
            if self.enable_async and len(self.clipboard_items) >= self.async_paste_threshold:
                try:
                    operation_id = self.async_manager.async_paste_files(
                        self.clipboard_items, 
                        target_dir, 
                        self.clipboard_operation == "cut"
                    )
                    return FileOperationResult(True, f"开始异步粘贴 {len(self.clipboard_items)} 个文件", self.clipboard_items)
                except Exception as e:
                    self.error_manager.handle_exception(
                        e,
                        context={"operation": "async_paste", "file_count": len(self.clipboard_items)},
                        category=ErrorCategory.FILE_OPERATION
                    )
                    # 异步失败时回退到同步操作
            
            # 同步粘贴操作
            success_count = 0
            failed_files = []
            successful_files = []
            
            for file_path in self.clipboard_items:
                try:
                    if not os.path.exists(file_path):
                        failed_files.append(f"{file_path} (源文件不存在)")
                        continue
                    
                    file_name = os.path.basename(file_path)
                    target_path = os.path.join(target_dir, file_name)
                    
                    # 检查目标是否已存在
                    if os.path.exists(target_path):
                        # 生成新名称
                        base, ext = os.path.splitext(file_name)
                        counter = 1
                        while os.path.exists(target_path):
                            new_name = f"{base} - 副本 ({counter}){ext}"
                            target_path = os.path.join(target_dir, new_name)
                            counter += 1
                    
                    if self.clipboard_operation == "cut":
                        # 移动文件
                        shutil.move(file_path, target_path)
                    else:
                        # 复制文件
                        if os.path.isdir(file_path):
                            shutil.copytree(file_path, target_path)
                        else:
                            shutil.copy2(file_path, target_path)
                    
                    successful_files.append(target_path)
                    success_count += 1
                    
                except PermissionError as e:
                    failed_files.append(f"{file_path} (权限不足)")
                    self.error_manager.handle_exception(
                        e,
                        context={"source": file_path, "target": target_dir, "operation": "paste"},
                        show_dialog=False,
                        category=ErrorCategory.FILE_PERMISSION
                    )
                except Exception as e:
                    failed_files.append(f"{file_path} (操作失败: {str(e)})")
                    self.error_manager.handle_exception(
                        e,
                        context={"source": file_path, "target": target_dir, "operation": "paste"},
                        show_dialog=False,
                        category=ErrorCategory.FILE_OPERATION
                    )
            
            # 如果是剪切操作且成功，清空剪贴板
            if self.clipboard_operation == "cut" and success_count > 0:
                self.clipboard_items = []
                self.clipboard_operation = None
            
            # 生成结果
            if failed_files:
                if successful_files:
                    message = f"部分粘贴成功：成功粘贴 {len(successful_files)} 个文件，{len(failed_files)} 个失败"
                    details = "失败的文件：\n" + "\n".join(failed_files[:10])
                    if len(failed_files) > 10:
                        details += f"\n还有 {len(failed_files) - 10} 个失败..."
                else:
                    message = f"粘贴全部失败：{len(failed_files)} 个文件粘贴失败"
                    details = "失败的文件：\n" + "\n".join(failed_files[:10])
                    if len(failed_files) > 10:
                        details += f"\n还有 {len(failed_files) - 10} 个失败..."
                
                # 显示部分失败的错误信息
                self.error_manager.handle_error(
                    ErrorCategory.FILE_OPERATION,
                    ErrorSeverity.WARNING if successful_files else ErrorSeverity.ERROR,
                    message,
                    details=details,
                    context={"success_count": len(successful_files), "failed_count": len(failed_files)}
                )
                
                return FileOperationResult(bool(successful_files), message, successful_files, details)
            else:
                operation_name = "移动" if self.clipboard_operation == "cut" else "复制"
                message = f"成功{operation_name} {len(successful_files)} 个文件"
                result = FileOperationResult(True, message, successful_files)
                
                self.operation_finished.emit("paste", result)
                return result
                
        except Exception as e:
            self.error_manager.handle_exception(
                e,
                context={"operation": "paste_from_clipboard", "target_dir": target_dir},
                category=ErrorCategory.FILE_OPERATION
            )
            return FileOperationResult(False, f"粘贴操作失败：{str(e)}")

    def get_clipboard_info(self) -> Dict[str, Any]:
        """
        获取剪贴板信息
        
        Returns:
            dict: 剪贴板信息
        """
        return {
            "operation": self.clipboard_operation,
            "items": self.clipboard_items.copy(),
            "count": len(self.clipboard_items)
        }

    # ========== 文件系统操作 ==========

    def open_file(self, file_path: str) -> FileOperationResult:
        """
        用系统默认程序打开文件
        
        Args:
            file_path: 要打开的文件路径
            
        Returns:
            FileOperationResult: 操作结果
        """
        try:
            if not os.path.exists(file_path):
                self.error_manager.handle_error(
                    ErrorCategory.FILE_NOT_FOUND,
                    ErrorSeverity.ERROR,
                    f"文件不存在：{file_path}",
                    context={"path": file_path, "operation": "open_file"}
                )
                return FileOperationResult(False, "文件不存在")
            
            if not os.path.isfile(file_path):
                self.error_manager.handle_error(
                    ErrorCategory.FILE_OPERATION,
                    ErrorSeverity.ERROR,
                    f"指定路径不是文件：{file_path}",
                    context={"path": file_path, "operation": "open_file"}
                )
                return FileOperationResult(False, "指定路径不是文件")
            
            # 根据操作系统使用不同的命令打开文件
            if sys.platform == "win32":
                # Windows使用start命令
                subprocess.run(["start", "", file_path], shell=True, check=True)
            elif sys.platform == "darwin":
                # macOS使用open命令
                subprocess.run(["open", file_path], check=True)
            else:
                # Linux使用xdg-open命令
                subprocess.run(["xdg-open", file_path], check=True)
            
            return FileOperationResult(True, f"已打开文件：{os.path.basename(file_path)}", [file_path])
            
        except subprocess.CalledProcessError as e:
            error_msg = f"无法打开文件，可能没有关联的程序：{os.path.basename(file_path)}"
            self.error_manager.handle_exception(
                e,
                context={"path": file_path, "operation": "open_file"},
                category=ErrorCategory.FILE_OPERATION
            )
            return FileOperationResult(False, error_msg)
        except Exception as e:
            self.error_manager.handle_exception(
                e,
                context={"path": file_path, "operation": "open_file"},
                category=ErrorCategory.FILE_OPERATION
            )
            return FileOperationResult(False, f"打开文件失败：{str(e)}")

    def open_in_explorer(self, dir_path: str) -> FileOperationResult:
        """在Windows资源管理器中打开目录"""
        try:
            if not os.path.exists(dir_path):
                self.error_manager.handle_error(
                    ErrorCategory.FILE_NOT_FOUND,
                    ErrorSeverity.ERROR,
                    f"目录不存在：{dir_path}",
                    context={"path": dir_path, "operation": "open_in_explorer"}
                )
                return FileOperationResult(False, "目录不存在")
            
            if sys.platform == "win32":
                subprocess.call(["explorer", dir_path])
            elif sys.platform == "darwin":
                subprocess.call(["open", "-R", dir_path])
            else:
                subprocess.call(["xdg-open", dir_path])
            
            return FileOperationResult(True, f"已在资源管理器中打开：{dir_path}", [dir_path])
            
        except Exception as e:
            self.error_manager.handle_exception(
                e,
                context={"path": dir_path, "operation": "open_in_explorer"},
                category=ErrorCategory.FILE_OPERATION
            )
            return FileOperationResult(False, f"无法打开资源管理器：{str(e)}")

    # ========== 异步操作控制 ==========
    
    def set_async_enabled(self, enabled: bool):
        """启用或禁用异步操作"""
        if enabled and not ASYNC_OPERATIONS_AVAILABLE:
            logger.warning("Cannot enable async operations: AsyncFileOperationManager not available")
            return False
        
        self.enable_async = enabled
        if enabled and not self.async_manager:
            try:
                self.async_manager = AsyncFileOperationManager(self)
                # 连接异步操作信号
                self.async_manager.operation_started.connect(self._on_async_operation_started)
                self.async_manager.operation_completed.connect(self._on_async_operation_completed)
                self.async_manager.operation_failed.connect(self._on_async_operation_failed)
                logger.info("Async file operations enabled")
            except Exception as e:
                logger.error(f"Failed to initialize async operations: {e}")
                self.enable_async = False
                self.async_manager = None
        
        return True
    
    def is_async_enabled(self) -> bool:
        """检查异步操作是否启用"""
        return self.enable_async and self.async_manager is not None
    
    def set_async_threshold(self, operation: str, threshold: int):
        """设置异步操作阈值"""
        if operation in self.async_threshold:
            self.async_threshold[operation] = threshold
            logger.info(f"Set async threshold for {operation} to {threshold}")
        else:
            logger.warning(f"Unknown operation type for async threshold: {operation}")
    
    def get_async_threshold(self, operation: str) -> int:
        """获取异步操作阈值"""
        return self.async_threshold.get(operation, 0)
    
    def get_active_async_operations(self) -> List[Dict[str, Any]]:
        """获取当前活动的异步操作"""
        if self.async_manager:
            return self.async_manager.get_active_operations()
        return []
    
    def cancel_async_operation(self, operation_id: str) -> bool:
        """取消异步操作"""
        if self.async_manager:
            return self.async_manager.cancel_operation(operation_id)
        return False
    
    def cleanup_async_operations(self):
        """清理已完成的异步操作记录"""
        if self.async_manager:
            self.async_manager.cleanup_completed_operations()
    
    def get_async_operation_status(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """获取异步操作状态"""
        if self.async_manager:
            return self.async_manager.get_operation_status(operation_id)
        return None
    
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