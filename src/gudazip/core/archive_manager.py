# -*- coding: utf-8 -*-
"""
压缩包管理器
统一管理各种压缩格式的处理
"""

import os
from typing import List, Dict, Any, Optional

from .zip_handler import ZipHandler
from .rar_handler import RarHandler
from .permission_manager import PermissionManager


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
        
    def get_archive_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """获取压缩包信息"""
        try:
            if not self.is_archive_file(file_path):
                return None
                
            # 检查文件访问权限
            if not PermissionManager.check_file_access(file_path, 'r'):
                raise PermissionError(f"无法读取文件：{file_path}")
                
            _, ext = os.path.splitext(file_path.lower())
            handler = self.handlers.get(ext)
            
            if handler:
                return handler.get_archive_info(file_path)
            return None
            
        except Exception as e:
            raise Exception(f"获取压缩包信息失败: {e}")
        
    def extract_archive(self, file_path: str, extract_to: str, 
                       password: Optional[str] = None,
                       selected_files: Optional[List[str]] = None) -> bool:
        """解压压缩包"""
        try:
            if not self.is_archive_file(file_path):
                raise ValueError("不支持的压缩文件格式")
                
            # 检查权限
            if not PermissionManager.request_admin_if_needed([file_path, extract_to], "解压"):
                return False
                
            # 确保解压目录存在
            if not PermissionManager.ensure_directory_exists(extract_to):
                raise PermissionError(f"无法创建解压目录：{extract_to}")
                
            _, ext = os.path.splitext(file_path.lower())
            handler = self.handlers.get(ext)
            
            if handler:
                return handler.extract_archive(file_path, extract_to, password, selected_files)
            return False
            
        except Exception as e:
            raise Exception(f"解压失败: {e}")
        
    def create_archive(self, file_path: str, files: List[str], 
                      compression_level: int = 6,
                      password: Optional[str] = None) -> bool:
        """创建压缩包"""
        try:
            # 验证输入参数
            if not file_path:
                raise ValueError("压缩包路径不能为空")
            if not files:
                raise ValueError("待压缩文件列表不能为空")
                
            # 检查所有源文件是否存在
            missing_files = [f for f in files if not os.path.exists(f)]
            if missing_files:
                raise FileNotFoundError(f"以下文件不存在：{', '.join(missing_files)}")
                
            # 检查权限
            paths_to_check = files + [os.path.dirname(file_path)]
            if not PermissionManager.request_admin_if_needed(paths_to_check, "创建压缩包"):
                return False
                
            _, ext = os.path.splitext(file_path.lower())
            handler = self.handlers.get(ext)
            
            if handler and hasattr(handler, 'create_archive'):
                return handler.create_archive(file_path, files, compression_level, password)
            else:
                raise ValueError(f"不支持创建 {ext} 格式的压缩包")
                
        except Exception as e:
            raise Exception(f"创建压缩包失败: {e}")
        
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
                
            # 尝试获取压缩包信息来验证完整性
            info = self.get_archive_info(file_path)
            return info is not None
            
        except Exception:
            return False
    
    def rename_file_in_archive(self, archive_path: str, old_name: str, new_name: str) -> bool:
        """重命名压缩包内的文件"""
        try:
            if not self.is_archive_file(archive_path):
                raise ValueError("不支持的压缩文件格式")
            
            _, ext = os.path.splitext(archive_path.lower())
            handler = self.handlers.get(ext)
            
            if handler and hasattr(handler, 'rename_file_in_archive'):
                return handler.rename_file_in_archive(archive_path, old_name, new_name)
            else:
                raise ValueError(f"不支持在 {ext} 格式中重命名文件")
                
        except Exception as e:
            raise Exception(f"重命名失败: {e}")
    
    def delete_file_from_archive(self, archive_path: str, file_name: str) -> bool:
        """从压缩包中删除文件"""
        try:
            if not self.is_archive_file(archive_path):
                raise ValueError("不支持的压缩文件格式")
            
            _, ext = os.path.splitext(archive_path.lower())
            handler = self.handlers.get(ext)
            
            if handler and hasattr(handler, 'delete_file_from_archive'):
                return handler.delete_file_from_archive(archive_path, file_name)
            else:
                raise ValueError(f"不支持在 {ext} 格式中删除文件")
                
        except Exception as e:
            raise Exception(f"删除失败: {e}")
    
    def list_archive_contents(self, archive_path: str) -> List[Dict[str, Any]]:
        """获取压缩包文件列表"""
        try:
            if not self.is_archive_file(archive_path):
                raise ValueError("不支持的压缩文件格式")
            
            _, ext = os.path.splitext(archive_path.lower())
            handler = self.handlers.get(ext)
            
            if handler and hasattr(handler, 'list_archive_contents'):
                return handler.list_archive_contents(archive_path)
            else:
                # 如果没有专门的方法，使用get_archive_info
                info = handler.get_archive_info(archive_path)
                return info.get('files', [])
                
        except Exception as e:
            raise Exception(f"获取文件列表失败: {e}") 