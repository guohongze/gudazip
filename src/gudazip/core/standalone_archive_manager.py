# -*- coding: utf-8 -*-
"""
独立的压缩包管理器
专门用于独立任务管理器，避免Qt依赖
"""

import os
from typing import List, Dict, Any, Optional

from .zip_handler import ZipHandler
from .rar_handler import RarHandler
from .sevenzip_handler import SevenZipHandler
from .permission_manager import PermissionManager


class StandaloneArchiveManager:
    """独立的压缩包管理器，不依赖Qt"""
    
    def __init__(self):
        """初始化管理器"""
        self.handlers = {}
        self._register_handlers()
        
    def _register_handlers(self):
        """注册压缩格式处理器"""
        # ZIP处理器
        zip_handler = ZipHandler()
        for ext in zip_handler.supported_extensions:
            self.handlers[ext] = zip_handler
            
        # RAR处理器
        rar_handler = RarHandler()
        for ext in rar_handler.supported_extensions:
            self.handlers[ext] = rar_handler
        
        # 7Z处理器
        sevenzip_handler = SevenZipHandler()
        for ext in sevenzip_handler.supported_extensions:
            self.handlers[ext] = sevenzip_handler
            
    def is_archive_file(self, file_path: str) -> bool:
        """检查文件是否为支持的压缩包格式"""
        try:
            if not file_path or not os.path.isfile(file_path):
                return False
                
            _, ext = os.path.splitext(file_path.lower())
            return ext in self.handlers
        except Exception:
            return False
        
    def get_supported_extensions(self) -> List[str]:
        """获取支持的文件扩展名列表"""
        return list(self.handlers.keys())
        
    def extract_archive(self, file_path: str, extract_to: str, 
                       password: Optional[str] = None,
                       selected_files: Optional[List[str]] = None,
                       progress_callback=None) -> bool:
        """解压压缩包"""
        try:
            if not self.is_archive_file(file_path):
                print(f"不支持的压缩文件格式: {file_path}")
                return False
                
            # 检查权限（简化版本，不弹出对话框）
            if not PermissionManager.check_file_access(file_path, 'r'):
                print(f"无法读取文件：{file_path}")
                return False
                
            # 确保解压目录存在
            if not PermissionManager.ensure_directory_exists(extract_to):
                print(f"无法创建解压目录：{extract_to}")
                return False
                
            _, ext = os.path.splitext(file_path.lower())
            handler = self.handlers.get(ext)
            
            if handler:
                # 检查handler是否支持progress_callback
                import inspect
                sig = inspect.signature(handler.extract_archive)
                if 'progress_callback' in sig.parameters:
                    return handler.extract_archive(file_path, extract_to, password, selected_files, progress_callback)
                else:
                    return handler.extract_archive(file_path, extract_to, password, selected_files)
            return False
            
        except Exception as e:
            print(f"解压失败: {e}")
            return False
        
    def create_archive(self, file_path: str, files: List[str], 
                      compression_level: int = 6,
                      password: Optional[str] = None,
                      progress_callback=None) -> bool:
        """创建压缩包"""
        try:
            # 验证输入参数
            if not file_path:
                print("压缩包路径不能为空")
                return False
            if not files:
                print("待压缩文件列表不能为空")
                return False
                
            # 检查所有源文件是否存在
            missing_files = [f for f in files if not os.path.exists(f)]
            if missing_files:
                print(f"以下文件不存在：{', '.join(missing_files)}")
                return False
                
            # 检查权限（简化版本）
            for file_path_check in files:
                if not PermissionManager.check_file_access(file_path_check, 'r'):
                    print(f"无法读取文件：{file_path_check}")
                    return False
                    
            # 检查目标目录权限
            target_dir = os.path.dirname(file_path)
            if not PermissionManager.check_file_access(target_dir, 'w'):
                print(f"无法写入目标目录：{target_dir}")
                return False
                
            _, ext = os.path.splitext(file_path.lower())
            handler = self.handlers.get(ext)
            
            if handler and hasattr(handler, 'create_archive'):
                return handler.create_archive(file_path, files, compression_level, password, progress_callback)
            else:
                print(f"不支持创建 {ext} 格式的压缩包")
                return False
                
        except Exception as e:
            print(f"创建压缩包失败: {e}")
            return False
        
    def get_archive_handler(self, file_path: str):
        """获取指定文件的处理器"""
        try:
            if not self.is_archive_file(file_path):
                return None
                
            _, ext = os.path.splitext(file_path.lower())
            return self.handlers.get(ext)
        except Exception:
            return None
    
    def validate_archive(self, file_path: str) -> bool:
        """验证压缩包完整性"""
        try:
            if not self.is_archive_file(file_path):
                return False
                
            _, ext = os.path.splitext(file_path.lower())
            handler = self.handlers.get(ext)
            
            if handler:
                # 尝试获取压缩包信息来验证完整性
                info = handler.get_archive_info(file_path)
                return info is not None
            return False
            
        except Exception:
            return False