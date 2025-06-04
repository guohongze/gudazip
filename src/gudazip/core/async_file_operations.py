# -*- coding: utf-8 -*-
"""
异步文件操作管理器
将耗时的文件操作移到后台线程执行，避免UI冻结
支持进度显示和操作取消
"""

import os
import shutil
import threading
import queue
import time
from typing import List, Optional, Dict, Any, Callable
from pathlib import Path
from PySide6.QtCore import QObject, Signal, QThread, QTimer
from PySide6.QtWidgets import QProgressDialog, QMessageBox, QApplication
import logging

logger = logging.getLogger(__name__)


class AsyncOperation:
    """异步操作基类"""
    
    def __init__(self, operation_id: str, operation_type: str, description: str):
        self.operation_id = operation_id
        self.operation_type = operation_type
        self.description = description
        self.progress = 0
        self.total = 100
        self.status = "pending"  # pending, running, completed, cancelled, error
        self.result = None
        self.error = None
        self.start_time = None
        self.end_time = None
        self.cancelled = False
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'operation_id': self.operation_id,
            'operation_type': self.operation_type,
            'description': self.description,
            'progress': self.progress,
            'total': self.total,
            'status': self.status,
            'start_time': self.start_time,
            'end_time': self.end_time
        }


class FileOperationWorker(QThread):
    """文件操作工作线程"""
    
    # 信号定义
    progress_updated = Signal(str, int, int)  # operation_id, current, total
    operation_completed = Signal(str, object)  # operation_id, result
    operation_failed = Signal(str, str)  # operation_id, error_message
    
    def __init__(self):
        super().__init__()
        self.operation_queue = queue.Queue()
        self.current_operation = None
        self.should_stop = False
        
    def add_operation(self, operation_func: Callable, operation_id: str, 
                     progress_callback: Optional[Callable] = None):
        """添加操作到队列"""
        self.operation_queue.put({
            'function': operation_func,
            'operation_id': operation_id,
            'progress_callback': progress_callback
        })
    
    def run(self):
        """主运行循环"""
        while not self.should_stop:
            try:
                # 从队列获取操作（阻塞等待）
                operation = self.operation_queue.get(timeout=1)
                self.current_operation = operation
                
                try:
                    # 执行操作
                    result = operation['function'](operation.get('progress_callback'))
                    self.operation_completed.emit(operation['operation_id'], result)
                except Exception as e:
                    logger.error(f"Operation {operation['operation_id']} failed: {e}")
                    self.operation_failed.emit(operation['operation_id'], str(e))
                finally:
                    self.current_operation = None
                    
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Worker thread error: {e}")
    
    def stop(self):
        """停止工作线程"""
        self.should_stop = True
        self.wait()


class AsyncFileOperationManager(QObject):
    """异步文件操作管理器"""
    
    # 信号定义
    operation_started = Signal(str, str)  # operation_id, description
    operation_progress = Signal(str, int, int)  # operation_id, current, total
    operation_completed = Signal(str, object)  # operation_id, result
    operation_failed = Signal(str, str)  # operation_id, error_message
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.operations: Dict[str, AsyncOperation] = {}
        self.worker = FileOperationWorker()
        self.progress_dialogs: Dict[str, QProgressDialog] = {}
        
        # 连接信号
        self.worker.progress_updated.connect(self._on_progress_updated)
        self.worker.operation_completed.connect(self._on_operation_completed)
        self.worker.operation_failed.connect(self._on_operation_failed)
        
        # 启动工作线程
        self.worker.start()
        
        # 生成唯一ID的计数器
        self._operation_counter = 0
    
    def _generate_operation_id(self) -> str:
        """生成唯一的操作ID"""
        self._operation_counter += 1
        return f"op_{int(time.time())}_{self._operation_counter}"
    
    def _on_progress_updated(self, operation_id: str, current: int, total: int):
        """处理进度更新"""
        if operation_id in self.operations:
            operation = self.operations[operation_id]
            operation.progress = current
            operation.total = total
            
            # 更新进度对话框
            if operation_id in self.progress_dialogs:
                dialog = self.progress_dialogs[operation_id]
                dialog.setValue(current)
                dialog.setMaximum(total)
                
                # 检查是否被取消
                if dialog.wasCanceled():
                    operation.cancelled = True
        
        self.operation_progress.emit(operation_id, current, total)
    
    def _on_operation_completed(self, operation_id: str, result):
        """处理操作完成"""
        if operation_id in self.operations:
            operation = self.operations[operation_id]
            operation.status = "completed"
            operation.result = result
            operation.end_time = time.time()
            
            # 关闭进度对话框
            if operation_id in self.progress_dialogs:
                dialog = self.progress_dialogs[operation_id]
                dialog.close()
                del self.progress_dialogs[operation_id]
        
        self.operation_completed.emit(operation_id, result)
    
    def _on_operation_failed(self, operation_id: str, error_message: str):
        """处理操作失败"""
        if operation_id in self.operations:
            operation = self.operations[operation_id]
            operation.status = "error"
            operation.error = error_message
            operation.end_time = time.time()
            
            # 关闭进度对话框
            if operation_id in self.progress_dialogs:
                dialog = self.progress_dialogs[operation_id]
                dialog.close()
                del self.progress_dialogs[operation_id]
        
        self.operation_failed.emit(operation_id, error_message)
    
    def copy_files_async(self, source_paths: List[str], target_dir: str, 
                        show_progress: bool = True) -> str:
        """异步复制文件"""
        operation_id = self._generate_operation_id()
        description = f"复制 {len(source_paths)} 个项目到 {os.path.basename(target_dir)}"
        
        # 创建操作记录
        operation = AsyncOperation(operation_id, "copy", description)
        operation.status = "running"
        operation.start_time = time.time()
        self.operations[operation_id] = operation
        
        # 显示进度对话框
        if show_progress:
            self._create_progress_dialog(operation_id, description)
        
        # 定义操作函数
        def copy_operation(progress_callback):
            return self._copy_files_sync(source_paths, target_dir, progress_callback)
        
        # 添加到工作队列
        self.worker.add_operation(copy_operation, operation_id, self._create_progress_callback(operation_id))
        
        self.operation_started.emit(operation_id, description)
        return operation_id
    
    def move_files_async(self, source_paths: List[str], target_dir: str, 
                        show_progress: bool = True) -> str:
        """异步移动文件"""
        operation_id = self._generate_operation_id()
        description = f"移动 {len(source_paths)} 个项目到 {os.path.basename(target_dir)}"
        
        # 创建操作记录
        operation = AsyncOperation(operation_id, "move", description)
        operation.status = "running"
        operation.start_time = time.time()
        self.operations[operation_id] = operation
        
        # 显示进度对话框
        if show_progress:
            self._create_progress_dialog(operation_id, description)
        
        # 定义操作函数
        def move_operation(progress_callback):
            return self._move_files_sync(source_paths, target_dir, progress_callback)
        
        # 添加到工作队列
        self.worker.add_operation(move_operation, operation_id, self._create_progress_callback(operation_id))
        
        self.operation_started.emit(operation_id, description)
        return operation_id
    
    def delete_files_async(self, file_paths: List[str], 
                          show_progress: bool = True) -> str:
        """异步删除文件"""
        operation_id = self._generate_operation_id()
        description = f"删除 {len(file_paths)} 个项目"
        
        # 创建操作记录
        operation = AsyncOperation(operation_id, "delete", description)
        operation.status = "running"
        operation.start_time = time.time()
        self.operations[operation_id] = operation
        
        # 显示进度对话框
        if show_progress:
            self._create_progress_dialog(operation_id, description)
        
        # 定义操作函数
        def delete_operation(progress_callback):
            return self._delete_files_sync(file_paths, progress_callback)
        
        # 添加到工作队列
        self.worker.add_operation(delete_operation, operation_id, self._create_progress_callback(operation_id))
        
        self.operation_started.emit(operation_id, description)
        return operation_id
    
    def extract_archive_async(self, archive_path: str, target_dir: str, 
                             selected_files: Optional[List[str]] = None,
                             show_progress: bool = True) -> str:
        """异步解压压缩包"""
        operation_id = self._generate_operation_id()
        if selected_files:
            description = f"解压 {len(selected_files)} 个文件到 {os.path.basename(target_dir)}"
        else:
            description = f"解压 {os.path.basename(archive_path)} 到 {os.path.basename(target_dir)}"
        
        # 创建操作记录
        operation = AsyncOperation(operation_id, "extract", description)
        operation.status = "running"
        operation.start_time = time.time()
        self.operations[operation_id] = operation
        
        # 显示进度对话框
        if show_progress:
            self._create_progress_dialog(operation_id, description)
        
        # 定义操作函数
        def extract_operation(progress_callback):
            return self._extract_archive_sync(archive_path, target_dir, selected_files, progress_callback)
        
        # 添加到工作队列
        self.worker.add_operation(extract_operation, operation_id, self._create_progress_callback(operation_id))
        
        self.operation_started.emit(operation_id, description)
        return operation_id
    
    def _create_progress_dialog(self, operation_id: str, description: str):
        """创建进度对话框"""
        dialog = QProgressDialog(description, "取消", 0, 100)
        dialog.setWindowTitle("正在处理...")
        dialog.setMinimumDuration(500)  # 500ms后显示
        dialog.setModal(True)
        dialog.setAutoClose(True)
        dialog.setAutoReset(True)
        
        self.progress_dialogs[operation_id] = dialog
    
    def _create_progress_callback(self, operation_id: str):
        """创建进度回调函数"""
        def progress_callback(current: int, total: int):
            if operation_id in self.operations:
                operation = self.operations[operation_id]
                if operation.cancelled:
                    return False  # 返回False表示取消操作
            
            self.worker.progress_updated.emit(operation_id, current, total)
            
            # 让Qt处理事件，保持UI响应
            QApplication.processEvents()
            return True
        
        return progress_callback
    
    def _copy_files_sync(self, source_paths: List[str], target_dir: str, 
                        progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """同步复制文件（在后台线程执行）"""
        results = {
            'success': True,
            'copied_files': [],
            'failed_files': [],
            'total_size': 0
        }
        
        total_files = len(source_paths)
        
        for i, source_path in enumerate(source_paths):
            try:
                if not os.path.exists(source_path):
                    results['failed_files'].append(f"{source_path}: 文件不存在")
                    continue
                
                # 计算目标路径
                file_name = os.path.basename(source_path)
                target_path = os.path.join(target_dir, file_name)
                
                # 如果目标已存在，生成新名称
                if os.path.exists(target_path):
                    target_path = self._get_unique_path(target_path)
                
                # 执行复制
                if os.path.isdir(source_path):
                    shutil.copytree(source_path, target_path)
                    # 计算文件夹大小（简化版）
                    size = sum(os.path.getsize(os.path.join(root, file)) 
                              for root, dirs, files in os.walk(target_path) 
                              for file in files)
                else:
                    shutil.copy2(source_path, target_path)
                    size = os.path.getsize(target_path)
                
                results['copied_files'].append(target_path)
                results['total_size'] += size
                
                # 更新进度
                if progress_callback:
                    if not progress_callback(i + 1, total_files):
                        # 操作被取消
                        results['success'] = False
                        results['cancelled'] = True
                        break
                
            except Exception as e:
                results['failed_files'].append(f"{source_path}: {str(e)}")
                logger.error(f"Failed to copy {source_path}: {e}")
        
        if results['failed_files']:
            results['success'] = len(results['copied_files']) > 0
        
        return results
    
    def _move_files_sync(self, source_paths: List[str], target_dir: str, 
                        progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """同步移动文件（在后台线程执行）"""
        results = {
            'success': True,
            'moved_files': [],
            'failed_files': []
        }
        
        total_files = len(source_paths)
        
        for i, source_path in enumerate(source_paths):
            try:
                if not os.path.exists(source_path):
                    results['failed_files'].append(f"{source_path}: 文件不存在")
                    continue
                
                # 计算目标路径
                file_name = os.path.basename(source_path)
                target_path = os.path.join(target_dir, file_name)
                
                # 如果目标已存在，生成新名称
                if os.path.exists(target_path):
                    target_path = self._get_unique_path(target_path)
                
                # 执行移动
                shutil.move(source_path, target_path)
                results['moved_files'].append(target_path)
                
                # 更新进度
                if progress_callback:
                    if not progress_callback(i + 1, total_files):
                        # 操作被取消
                        results['success'] = False
                        results['cancelled'] = True
                        break
                
            except Exception as e:
                results['failed_files'].append(f"{source_path}: {str(e)}")
                logger.error(f"Failed to move {source_path}: {e}")
        
        if results['failed_files']:
            results['success'] = len(results['moved_files']) > 0
        
        return results
    
    def _delete_files_sync(self, file_paths: List[str], 
                          progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """同步删除文件（在后台线程执行）"""
        results = {
            'success': True,
            'deleted_files': [],
            'failed_files': []
        }
        
        total_files = len(file_paths)
        
        for i, file_path in enumerate(file_paths):
            try:
                if not os.path.exists(file_path):
                    results['failed_files'].append(f"{file_path}: 文件不存在")
                    continue
                
                # 执行删除
                if os.path.isdir(file_path):
                    shutil.rmtree(file_path)
                else:
                    os.remove(file_path)
                
                results['deleted_files'].append(file_path)
                
                # 更新进度
                if progress_callback:
                    if not progress_callback(i + 1, total_files):
                        # 操作被取消
                        results['success'] = False
                        results['cancelled'] = True
                        break
                
            except Exception as e:
                results['failed_files'].append(f"{file_path}: {str(e)}")
                logger.error(f"Failed to delete {file_path}: {e}")
        
        if results['failed_files']:
            results['success'] = len(results['deleted_files']) > 0
        
        return results
    
    def _extract_archive_sync(self, archive_path: str, target_dir: str, 
                             selected_files: Optional[List[str]] = None,
                             progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """同步解压压缩包（在后台线程执行）"""
        results = {
            'success': False,
            'extracted_files': [],
            'failed_files': [],
            'target_dir': target_dir
        }
        
        try:
            # 确保目标目录存在
            os.makedirs(target_dir, exist_ok=True)
            
            # 目前只支持ZIP格式
            if not archive_path.lower().endswith('.zip'):
                results['failed_files'].append("目前只支持ZIP格式")
                return results
            
            import zipfile
            with zipfile.ZipFile(archive_path, 'r') as zf:
                # 获取要解压的文件列表
                if selected_files:
                    files_to_extract = selected_files
                else:
                    files_to_extract = zf.namelist()
                
                total_files = len(files_to_extract)
                
                for i, file_name in enumerate(files_to_extract):
                    try:
                        # 解压文件
                        zf.extract(file_name, target_dir)
                        extracted_path = os.path.join(target_dir, file_name)
                        results['extracted_files'].append(extracted_path)
                        
                        # 更新进度
                        if progress_callback:
                            if not progress_callback(i + 1, total_files):
                                # 操作被取消
                                results['cancelled'] = True
                                break
                        
                    except Exception as e:
                        results['failed_files'].append(f"{file_name}: {str(e)}")
                        logger.error(f"Failed to extract {file_name}: {e}")
            
            results['success'] = len(results['extracted_files']) > 0
            
        except Exception as e:
            results['failed_files'].append(f"解压失败: {str(e)}")
            logger.error(f"Failed to extract archive {archive_path}: {e}")
        
        return results
    
    def _get_unique_path(self, path: str) -> str:
        """获取唯一的文件路径（避免覆盖）"""
        if not os.path.exists(path):
            return path
        
        base_path = Path(path)
        stem = base_path.stem
        suffix = base_path.suffix
        parent = base_path.parent
        
        counter = 1
        while True:
            new_name = f"{stem} ({counter}){suffix}"
            new_path = parent / new_name
            if not os.path.exists(new_path):
                return str(new_path)
            counter += 1
    
    def get_operation_status(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """获取操作状态"""
        if operation_id in self.operations:
            return self.operations[operation_id].to_dict()
        return None
    
    def cancel_operation(self, operation_id: str) -> bool:
        """取消操作"""
        if operation_id in self.operations:
            operation = self.operations[operation_id]
            operation.cancelled = True
            operation.status = "cancelled"
            
            # 关闭进度对话框
            if operation_id in self.progress_dialogs:
                dialog = self.progress_dialogs[operation_id]
                dialog.close()
                del self.progress_dialogs[operation_id]
            
            return True
        return False
    
    def get_active_operations(self) -> List[Dict[str, Any]]:
        """获取所有活动操作"""
        return [op.to_dict() for op in self.operations.values() 
                if op.status in ["pending", "running"]]
    
    def cleanup_completed_operations(self):
        """清理已完成的操作记录"""
        completed_ops = [op_id for op_id, op in self.operations.items() 
                        if op.status in ["completed", "cancelled", "error"]]
        
        for op_id in completed_ops:
            del self.operations[op_id]
    
    def __del__(self):
        """析构函数，确保工作线程正确停止"""
        try:
            self.worker.stop()
        except:
            pass 