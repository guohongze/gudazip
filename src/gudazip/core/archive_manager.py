# -*- coding: utf-8 -*-
"""
压缩包管理器
统一处理各种压缩格式的接口
"""

import os
import ctypes
import sys
from typing import Dict, List, Optional, Any
from .zip_handler import ZipHandler
from .rar_handler import RarHandler


class ArchiveManager:
    """压缩包管理器"""
    
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
            
    def needs_admin_permission(self, file_path):
        """检查操作指定文件是否需要管理员权限"""
        if not file_path:
            return False
            
        # 规范化路径，统一使用反斜杠
        file_path = os.path.normpath(file_path)
            
        # 检查是否为系统保护目录
        protected_dirs = [
            "C:\\Windows",
            "C:\\Program Files", 
            "C:\\Program Files (x86)",
            "C:\\ProgramData",
            "C:\\System Volume Information"
        ]
        
        file_path_upper = file_path.upper()
        for protected_dir in protected_dirs:
            if file_path_upper.startswith(protected_dir.upper()):
                return True
                
        # 检查是否为系统根目录下的重要文件
        if file_path_upper.startswith("C:\\") and len(file_path.split("\\")) <= 2:
            return True
            
        return False
        
    def is_admin(self):
        """检查当前是否有管理员权限"""
        try:
            if os.name == 'nt':  # Windows
                return ctypes.windll.shell32.IsUserAnAdmin()
            else:
                return os.geteuid() == 0
        except:
            return False
            
    def request_admin_if_needed(self, file_paths, operation="操作"):
        """如果需要管理员权限，则申请权限"""
        if isinstance(file_paths, str):
            file_paths = [file_paths]
            
        # 检查是否有文件需要管理员权限
        needs_admin = any(self.needs_admin_permission(path) for path in file_paths)
        
        if needs_admin and not self.is_admin():
            # 动态导入以避免循环导入
            try:
                from main import request_admin_permission
                reason = f"{operation}系统文件"
                if request_admin_permission(reason):
                    sys.exit(0)  # 重启为管理员模式
                return False  # 用户拒绝或申请失败
            except ImportError:
                # 如果无法导入main模块，抛出权限错误
                raise Exception(f"需要管理员权限才能{operation}系统文件。请以管理员身份运行程序。")
            
        return True  # 有权限或不需要权限
        
    def is_archive_file(self, file_path: str) -> bool:
        """检查文件是否为支持的压缩包格式"""
        if not os.path.isfile(file_path):
            return False
            
        _, ext = os.path.splitext(file_path.lower())
        return ext in self.handlers
        
    def get_supported_extensions(self) -> List[str]:
        """获取支持的文件扩展名列表"""
        return list(self.handlers.keys())
        
    def get_archive_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """获取压缩包信息"""
        if not self.is_archive_file(file_path):
            return None
            
        _, ext = os.path.splitext(file_path.lower())
        handler = self.handlers.get(ext)
        
        if handler:
            try:
                return handler.get_archive_info(file_path)
            except Exception as e:
                print(f"获取压缩包信息失败: {e}")
                return None
        return None
        
    def extract_archive(self, file_path: str, extract_to: str, 
                       password: Optional[str] = None,
                       selected_files: Optional[List[str]] = None) -> bool:
        """解压压缩包"""
        if not self.is_archive_file(file_path):
            return False
            
        _, ext = os.path.splitext(file_path.lower())
        handler = self.handlers.get(ext)
        
        if handler:
            try:
                return handler.extract_archive(file_path, extract_to, password, selected_files)
            except Exception as e:
                print(f"解压失败: {e}")
                return False
        return False
        
    def create_archive(self, file_path: str, files: List[str], 
                      compression_level: int = 6,
                      password: Optional[str] = None) -> bool:
        """创建压缩包"""
        _, ext = os.path.splitext(file_path.lower())
        handler = self.handlers.get(ext)
        
        if handler and hasattr(handler, 'create_archive'):
            try:
                return handler.create_archive(file_path, files, compression_level, password)
            except Exception as e:
                print(f"创建压缩包失败: {e}")
                return False
        return False
        
    def add_files_to_archive(self, archive_path: str, files: List[str]) -> bool:
        """向压缩包添加文件"""
        if not self.is_archive_file(archive_path):
            return False
            
        _, ext = os.path.splitext(archive_path.lower())
        handler = self.handlers.get(ext)
        
        if handler and hasattr(handler, 'add_files'):
            try:
                return handler.add_files(archive_path, files)
            except Exception as e:
                print(f"添加文件失败: {e}")
                return False
        return False
        
    def remove_files_from_archive(self, archive_path: str, files: List[str]) -> bool:
        """从压缩包删除文件"""
        if not self.is_archive_file(archive_path):
            return False
            
        _, ext = os.path.splitext(archive_path.lower())
        handler = self.handlers.get(ext)
        
        if handler and hasattr(handler, 'remove_files'):
            try:
                return handler.remove_files(archive_path, files)
            except Exception as e:
                print(f"删除文件失败: {e}")
                return False
        return False
        
    def test_archive(self, file_path: str, password: Optional[str] = None) -> bool:
        """测试压缩包完整性"""
        if not self.is_archive_file(file_path):
            return False
            
        _, ext = os.path.splitext(file_path.lower())
        handler = self.handlers.get(ext)
        
        if handler and hasattr(handler, 'test_archive'):
            try:
                return handler.test_archive(file_path, password)
            except Exception as e:
                print(f"测试压缩包失败: {e}")
                return False
        return False
        
    def get_archive_handler(self, file_path: str):
        """获取指定文件的处理器"""
        if not self.is_archive_file(file_path):
            return None
            
        _, ext = os.path.splitext(file_path.lower())
        return self.handlers.get(ext) 