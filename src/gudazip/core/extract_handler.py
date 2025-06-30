# -*- coding: utf-8 -*-
"""
解压处理器
专门处理压缩包解压相关的逻辑，简化main_window中的复杂逻辑
"""

import os
from typing import List, Optional, Dict, Any
from PySide6.QtWidgets import QMessageBox, QDialog


class ExtractRequest:
    """解压请求数据类"""
    
    def __init__(self, archive_path: str, selected_files: Optional[List[str]] = None):
        """
        初始化解压请求
        
        Args:
            archive_path: 压缩包路径
            selected_files: 要解压的文件列表（None表示解压全部）
        """
        self.archive_path = archive_path
        self.selected_files = selected_files or []
        self.is_partial_extract = bool(selected_files)
    
    def __str__(self):
        if self.is_partial_extract:
            return f"解压 {len(self.selected_files)} 个选中文件从 {os.path.basename(self.archive_path)}"
        else:
            return f"解压整个压缩包 {os.path.basename(self.archive_path)}"


class ExtractHandler:
    """解压处理器"""
    
    def __init__(self, archive_manager, parent_window=None):
        """
        初始化解压处理器
        
        Args:
            archive_manager: 压缩包管理器
            parent_window: 父窗口（用于显示对话框）
        """
        self.archive_manager = archive_manager
        self.parent_window = parent_window
    
    def extract_from_archive_view(self, archive_path: str, selected_display_paths: List[str], 
                                 current_view_path: str) -> bool:
        """
        从压缩包查看模式中解压文件
        
        Args:
            archive_path: 压缩包路径
            selected_display_paths: 选中的显示路径（可能包含前缀）
            current_view_path: 当前查看的路径
            
        Returns:
            bool: 是否成功处理解压请求
        """
        try:
            # 验证压缩包路径
            if not archive_path or not os.path.exists(archive_path):
                QMessageBox.critical(self.parent_window, "错误", "压缩包文件不存在")
                return False
            
            # 处理选中文件的路径
            selected_files = []
            if selected_display_paths:
                # 清理路径，移除可能的显示前缀
                for display_path in selected_display_paths:
                    clean_path = self._clean_archive_path(display_path, current_view_path)
                    if clean_path:
                        selected_files.append(clean_path)
                
                if not selected_files:
                    QMessageBox.warning(self.parent_window, "警告", "未能识别选中的文件路径")
                    return False
            
            # 创建解压请求
            extract_request = ExtractRequest(archive_path, selected_files if selected_files else None)
            
            # 执行解压
            return self._execute_extract_request(extract_request)
            
        except Exception as e:
            QMessageBox.critical(self.parent_window, "错误", f"解压处理失败：{str(e)}")
            return False
    
    def extract_from_filesystem(self, file_paths: List[str], current_path: str) -> bool:
        """
        从文件系统模式中解压压缩包
        
        Args:
            file_paths: 选中的文件路径列表
            current_path: 当前路径
            
        Returns:
            bool: 是否成功处理解压请求
        """
        try:
            # 寻找有效的压缩包文件
            archive_path = self._find_valid_archive(file_paths, current_path)
            
            if not archive_path:
                # 让用户手动选择压缩包
                from PySide6.QtWidgets import QFileDialog
                archive_path, _ = QFileDialog.getOpenFileName(
                    self.parent_window, "选择要解压的压缩包", "",
                    "压缩包文件 (*.zip *.rar *.7z *.tar *.gz *.bz2);;所有文件 (*.*)"
                )
                
                if not archive_path:
                    return False
            
            # 验证压缩包
            if not self.archive_manager.is_archive_file(archive_path):
                QMessageBox.warning(self.parent_window, "警告", "选择的文件不是有效的压缩包")
                return False
            
            # 创建解压请求（文件系统模式总是解压整个压缩包）
            extract_request = ExtractRequest(archive_path, None)
            
            # 执行解压
            return self._execute_extract_request(extract_request)
            
        except Exception as e:
            QMessageBox.critical(self.parent_window, "错误", f"解压处理失败：{str(e)}")
            return False
    
    def _clean_archive_path(self, display_path: str, current_view_path: str) -> str:
        """
        清理压缩包内的文件路径，移除显示前缀
        
        Args:
            display_path: 显示的路径
            current_view_path: 当前查看的路径
            
        Returns:
            str: 清理后的路径
        """
        try:
            # 移除可能的前缀标识
            clean_path = display_path
            
            # 如果路径以文件名开头（可能是选中的文件名），直接返回
            if os.path.basename(display_path) == display_path:
                # 这是一个文件名，需要加上当前目录路径
                if current_view_path and current_view_path != "/":
                    clean_path = current_view_path.rstrip("/") + "/" + display_path
                else:
                    clean_path = display_path
            
            # 确保使用正确的分隔符（压缩包内通常使用正斜杠）
            clean_path = clean_path.replace("\\", "/")
            
            # 移除开头的斜杠（如果有）
            clean_path = clean_path.lstrip("/")
            
            return clean_path
            
        except Exception:
            # 如果清理失败，返回原始路径
            return display_path
    
    def _find_valid_archive(self, file_paths: List[str], current_path: str) -> Optional[str]:
        """
        从文件路径列表中找到有效的压缩包
        
        Args:
            file_paths: 文件路径列表
            current_path: 当前路径
            
        Returns:
            Optional[str]: 找到的压缩包路径，如果没有找到则返回None
        """
        # 首先检查选中的文件
        if file_paths:
            for path in file_paths:
                if os.path.isfile(path) and self.archive_manager.is_archive_file(path):
                    return path
        
        # 检查当前路径
        if current_path and os.path.isfile(current_path):
            if self.archive_manager.is_archive_file(current_path):
                return current_path
        
        return None
    
    def _execute_extract_request(self, extract_request: ExtractRequest) -> bool:
        """
        执行解压请求
        
        Args:
            extract_request: 解压请求
            
        Returns:
            bool: 是否成功打开解压对话框
        """
        try:
            # 验证archive_path
            if not os.path.exists(extract_request.archive_path):
                QMessageBox.critical(
                    self.parent_window, 
                    "错误", 
                    f"压缩包文件不存在：{extract_request.archive_path}"
                )
                return False
            
            from ..ui.extract_archive_dialog import ExtractArchiveDialog
            
            # 创建解压对话框
            dialog = ExtractArchiveDialog(
                self.archive_manager, 
                extract_request.archive_path, 
                extract_request.selected_files,
                self.parent_window
            )
            
            # 显示对话框
            result = dialog.exec()
            
            if result == QDialog.Accepted:
                # 更新父窗口状态
                if self.parent_window and hasattr(self.parent_window, 'path_label'):
                    if extract_request.is_partial_extract:
                        self.parent_window.path_label.setText(
                            f"解压完成：{len(extract_request.selected_files)} 个文件"
                        )
                    else:
                        self.parent_window.path_label.setText("解压完成：整个压缩包")
                
                return True
            else:
                return False
                
        except Exception as e:
            QMessageBox.critical(
                self.parent_window, 
                "错误", 
                f"无法打开解压对话框：{str(e)}"
            )
            return False
    
    def get_archive_info(self, archive_path: str) -> Optional[Dict[str, Any]]:
        """
        获取压缩包信息
        
        Args:
            archive_path: 压缩包路径
            
        Returns:
            Optional[Dict[str, Any]]: 压缩包信息，失败时返回None
        """
        try:
            return self.archive_manager.get_archive_info(archive_path)
        except Exception:
            return None 