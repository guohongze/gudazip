# -*- coding: utf-8 -*-
"""
权限管理器
统一处理系统权限相关操作
"""

import os
import sys
import ctypes
from typing import List, Union
import importlib.util


class PermissionManager:
    """权限管理器"""
    
    # 系统保护目录列表
    PROTECTED_DIRS = [
        "C:\\Windows",
        "C:\\Program Files", 
        "C:\\Program Files (x86)",
        "C:\\ProgramData",
        "C:\\System Volume Information"
    ]
    
    @staticmethod
    def is_admin() -> bool:
        """检查当前是否有管理员权限"""
        try:
            if os.name == 'nt':  # Windows
                return ctypes.windll.shell32.IsUserAnAdmin()
            else:
                return os.geteuid() == 0
        except Exception:
            return False
    
    @staticmethod
    def needs_admin_permission(file_path: str) -> bool:
        """检查操作指定文件是否需要管理员权限"""
        if not file_path:
            return False
        
        # 检查是否为注册表操作
        if file_path.startswith("HKEY_"):
            return True
            
        # 规范化路径，统一使用反斜杠
        file_path = os.path.normpath(file_path)
        file_path_upper = file_path.upper()
        
        # 检查是否为系统保护目录
        for protected_dir in PermissionManager.PROTECTED_DIRS:
            if file_path_upper.startswith(protected_dir.upper()):
                return True
                
        # 检查是否为系统根目录下的重要文件
        if file_path_upper.startswith("C:\\") and len(file_path.split("\\")) <= 2:
            return True
            
        return False
    
    @staticmethod
    def request_admin_if_needed(file_paths: Union[str, List[str]], operation: str = "操作") -> bool:
        """如果需要管理员权限，则申请权限"""
        if isinstance(file_paths, str):
            file_paths = [file_paths]
            
        # 检查是否有文件需要管理员权限
        needs_admin = any(PermissionManager.needs_admin_permission(path) for path in file_paths)
        
        if needs_admin and not PermissionManager.is_admin():
            # 动态导入以避免循环导入
            try:
                # 尝试多种导入路径
                try:
                    # 首先尝试从根目录导入
                    import sys
                    import os
                    main_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'main.py')
                    if os.path.exists(main_path):
                        spec = importlib.util.spec_from_file_location("main", main_path)
                        main_module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(main_module)
                        request_admin_permission = main_module.request_admin_permission
                    else:
                        # 备用：尝试直接导入
                        from main import request_admin_permission
                except ImportError:
                    # 再次备用：尝试从上级目录导入
                    import importlib.util
                    main_py_paths = [
                        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'main.py'),
                        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'main.py'),
                        'main.py'
                    ]
                    
                    request_admin_permission = None
                    for path in main_py_paths:
                        if os.path.exists(path):
                            spec = importlib.util.spec_from_file_location("main", path)
                            main_module = importlib.util.module_from_spec(spec)
                            spec.loader.exec_module(main_module)
                            request_admin_permission = main_module.request_admin_permission
                            break
                    
                    if request_admin_permission is None:
                        raise ImportError("无法找到main模块")
                
                reason = f"{operation}系统文件"
                if request_admin_permission(reason):
                    sys.exit(0)  # 重启为管理员模式
                return False  # 用户拒绝或申请失败
            except ImportError:
                # 如果无法导入main模块，抛出权限错误
                raise PermissionError(f"需要管理员权限才能{operation}系统文件。请以管理员身份运行程序。")
            
        return True  # 有权限或不需要权限
    
    @staticmethod
    def check_file_access(file_path: str, mode: str = 'r') -> bool:
        """检查文件访问权限"""
        try:
            if mode == 'r':
                return os.access(file_path, os.R_OK)
            elif mode == 'w':
                if os.path.exists(file_path):
                    return os.access(file_path, os.W_OK)
                else:
                    # 检查父目录的写权限
                    parent_dir = os.path.dirname(file_path)
                    return os.access(parent_dir, os.W_OK)
            elif mode == 'rw':
                return PermissionManager.check_file_access(file_path, 'r') and \
                       PermissionManager.check_file_access(file_path, 'w')
            else:
                return False
        except Exception:
            return False
    
    @staticmethod
    def ensure_directory_exists(dir_path: str) -> bool:
        """确保目录存在，如果不存在则创建"""
        try:
            os.makedirs(dir_path, exist_ok=True)
            return True
        except PermissionError:
            if PermissionManager.request_admin_if_needed(dir_path, "创建目录"):
                try:
                    os.makedirs(dir_path, exist_ok=True)
                    return True
                except Exception:
                    return False
            return False
        except Exception:
            return False 