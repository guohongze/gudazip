# -*- coding: utf-8 -*-
"""
ZIP格式处理器
实现ZIP文件的读写操作
"""

import os
import zipfile
from typing import Dict, List, Optional, Any
from datetime import datetime
import time
import ctypes
import sys


class ZipHandler:
    """ZIP格式处理器"""
    
    def __init__(self):
        """初始化处理器"""
        self.supported_extensions = ['.zip']
        
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
        
    def get_archive_info(self, file_path: str) -> Dict[str, Any]:
        """获取ZIP压缩包信息"""
        archive_info = {
            'path': file_path,
            'format': 'ZIP',
            'files': [],
            'total_size': 0,
            'compressed_size': 0,
            'file_count': 0,
            'has_password': False
        }
        
        try:
            with zipfile.ZipFile(file_path, 'r') as zf:
                # 检查是否有密码保护
                for info in zf.infolist():
                    if info.flag_bits & 0x1:  # 检查加密标志
                        archive_info['has_password'] = True
                        break
                
                # 获取文件列表
                for info in zf.infolist():
                    if not info.filename.endswith('/'):  # 不是目录
                        file_info = {
                            'path': info.filename,
                            'size': info.file_size,
                            'compressed_size': info.compress_size,
                            'modified_time': self._convert_time(info.date_time),
                            'crc': info.CRC,
                            'is_encrypted': bool(info.flag_bits & 0x1)
                        }
                        archive_info['files'].append(file_info)
                        archive_info['total_size'] += info.file_size
                        archive_info['compressed_size'] += info.compress_size
                        archive_info['file_count'] += 1
                        
        except zipfile.BadZipFile:
            raise Exception("无效的ZIP文件")
        except Exception as e:
            raise Exception(f"读取ZIP文件失败: {e}")
            
        return archive_info
        
    def extract_archive(self, file_path: str, extract_to: str,
                       password: Optional[str] = None,
                       selected_files: Optional[List[str]] = None) -> bool:
        """解压ZIP文件"""
        try:
            # 检查源文件和目标目录的权限
            paths_to_check = [file_path, extract_to]
            if not self.request_admin_if_needed(paths_to_check, "解压"):
                return False
                
            # 确保解压目录存在
            os.makedirs(extract_to, exist_ok=True)
            
            with zipfile.ZipFile(file_path, 'r') as zf:
                # 设置密码（如果需要）
                if password:
                    zf.setpassword(password.encode('utf-8'))
                
                # 解压指定文件或全部文件
                if selected_files:
                    for file_name in selected_files:
                        try:
                            zf.extract(file_name, extract_to)
                        except KeyError:
                            print(f"文件不存在: {file_name}")
                            continue
                else:
                    zf.extractall(extract_to)
                    
            return True
            
        except zipfile.BadZipFile:
            raise Exception("无效的ZIP文件")
        except RuntimeError as e:
            if "Bad password" in str(e):
                raise Exception("密码错误")
            else:
                raise Exception(f"解压失败: {e}")
        except Exception as e:
            raise Exception(f"解压失败: {e}")
            
    def create_archive(self, file_path: str, files: List[str],
                      compression_level: int = 6,
                      password: Optional[str] = None) -> bool:
        """创建ZIP压缩包"""
        try:
            # 设置压缩级别
            compression = zipfile.ZIP_DEFLATED
            if compression_level == 0:
                compression = zipfile.ZIP_STORED
                
            with zipfile.ZipFile(file_path, 'w', compression) as zf:
                for file_or_dir in files:
                    if os.path.isfile(file_or_dir):
                        # 添加文件
                        arcname = os.path.basename(file_or_dir)
                        zf.write(file_or_dir, arcname)
                    elif os.path.isdir(file_or_dir):
                        # 添加目录及其内容
                        for root, dirs, file_list in os.walk(file_or_dir):
                            for file_name in file_list:
                                file_full_path = os.path.join(root, file_name)
                                arcname = os.path.relpath(file_full_path, 
                                                         os.path.dirname(file_or_dir))
                                zf.write(file_full_path, arcname)
                                
            # 如果需要密码保护，需要使用第三方库如pyminizip
            if password:
                # TODO: 实现密码保护功能
                print("ZIP密码保护功能需要pyminizip库支持")
                
            return True
            
        except Exception as e:
            raise Exception(f"创建ZIP文件失败: {e}")
            
    def _convert_time(self, date_time_tuple) -> str:
        """转换时间格式"""
        try:
            dt = datetime(*date_time_tuple)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            return "" 