# -*- coding: utf-8 -*-
"""
7Z格式处理器
实现7Z文件的读写操作
"""

import os
import py7zr
from typing import Dict, List, Optional, Any
from datetime import datetime
import time

from .permission_manager import PermissionManager


class SevenZipHandler:
    """7Z格式处理器"""
    
    def __init__(self):
        """初始化处理器"""
        self.supported_extensions = ['.7z']
        
    def get_archive_info(self, file_path: str) -> Dict[str, Any]:
        """获取7Z压缩包信息"""
        archive_info = {
            'path': file_path,
            'format': '7Z',
            'files': [],
            'total_size': 0,
            'compressed_size': 0,
            'file_count': 0,
            'has_password': False
        }
        
        try:
            with py7zr.SevenZipFile(file_path, mode='r') as sz:
                # 检查是否有密码保护
                try:
                    sz.testarchive()
                except py7zr.PasswordRequired:
                    archive_info['has_password'] = True
                except Exception:
                    pass
                
                # 获取文件列表
                for info in sz.list():
                    if not info.filename.endswith('/'):  # 不是目录
                        file_info = {
                            'path': info.filename,
                            'size': info.uncompressed,
                            'compressed_size': info.compressed if hasattr(info, 'compressed') else 0,
                            'modified_time': info.creationtime.strftime('%Y-%m-%d %H:%M:%S') if info.creationtime else '',
                            'crc': info.crc32 if hasattr(info, 'crc32') else 0,
                            'is_encrypted': archive_info['has_password']
                        }
                        archive_info['files'].append(file_info)
                        archive_info['total_size'] += info.uncompressed
                        if hasattr(info, 'compressed') and info.compressed is not None:
                            archive_info['compressed_size'] += info.compressed
                        archive_info['file_count'] += 1
                        
        except py7zr.Bad7zFile:
            raise ValueError("无效的7Z文件")
        except py7zr.PasswordRequired:
            archive_info['has_password'] = True
        except PermissionError:
            raise PermissionError(f"没有权限访问文件：{file_path}")
        except FileNotFoundError:
            raise FileNotFoundError(f"文件不存在：{file_path}")
        except Exception as e:
            raise Exception(f"读取7Z文件失败: {e}")
            
        return archive_info
        
    def extract_archive(self, file_path: str, extract_to: str,
                       password: Optional[str] = None,
                       selected_files: Optional[List[str]] = None,
                       progress_callback=None) -> bool:
        """解压7Z文件"""
        try:
            # 验证输入参数
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"7Z文件不存在：{file_path}")
                
            # 检查权限
            paths_to_check = [file_path, extract_to]
            if not PermissionManager.request_admin_if_needed(paths_to_check, "解压"):
                return False
                
            # 确保解压目录存在
            if not PermissionManager.ensure_directory_exists(extract_to):
                raise PermissionError(f"无法创建解压目录：{extract_to}")
            
            with py7zr.SevenZipFile(file_path, mode='r', password=password) as sz:
                # 获取要解压的文件列表
                all_files = sz.list()
                
                if selected_files:
                    files_to_extract = []
                    total_size = 0
                    for info in all_files:
                        if info.filename in selected_files and not info.filename.endswith('/'):
                            files_to_extract.append(info)
                            total_size += info.uncompressed
                else:
                    files_to_extract = [info for info in all_files if not info.filename.endswith('/')]
                    total_size = sum(info.uncompressed for info in files_to_extract)
                
                if progress_callback:
                    progress_callback(0, f"准备解压 {len(files_to_extract)} 个文件...")
                
                # 解压文件
                if selected_files:
                    # 解压选定的文件
                    sz.extract(path=extract_to, targets=selected_files)
                else:
                    # 解压全部文件
                    sz.extractall(path=extract_to)
                
                if progress_callback:
                    progress_callback(95, "正在完成解压...")
                    time.sleep(0.1)
                    progress_callback(100, "解压完成")
                    
            return True
            
        except py7zr.Bad7zFile:
            raise ValueError("无效的7Z文件")
        except py7zr.PasswordRequired:
            raise ValueError("需要密码")
        except py7zr.WrongPassword:
            raise ValueError("密码错误")
        except PermissionError as e:
            raise PermissionError(f"权限不足: {e}")
        except Exception as e:
            raise Exception(f"解压失败: {e}")
            
    def create_archive(self, file_path: str, files: List[str],
                      compression_level: int = 6,
                      password: Optional[str] = None,
                      progress_callback=None) -> bool:
        """创建7Z压缩包"""
        try:
            # 验证输入
            if not files:
                raise ValueError("没有指定要压缩的文件")
                
            # 检查所有源文件是否存在
            missing_files = []
            for file_or_dir in files:
                if not os.path.exists(file_or_dir):
                    missing_files.append(file_or_dir)
            
            if missing_files:
                raise FileNotFoundError(f"以下文件不存在: {', '.join(missing_files)}")
            
            # 检查权限
            paths_to_check = files + [os.path.dirname(file_path)]
            if not PermissionManager.request_admin_if_needed(paths_to_check, "创建压缩包"):
                return False
            
            # 映射压缩级别 (0-9 映射到 py7zr 的压缩级别)
            compression_map = {
                0: 0,  # 存储
                1: 1,  # 最快
                2: 3,
                3: 5,
                4: 7,
                5: 9,  # 默认
                6: 9,  # 默认
                7: 9,
                8: 9,
                9: 9   # 最高
            }
            
            py7zr_compression = compression_map.get(compression_level, 9)
            
            if progress_callback:
                progress_callback(0, "正在计算文件大小...")
            
            # 计算总文件大小以跟踪进度
            total_size = 0
            total_files = []
            
            for file_or_dir in files:
                if os.path.isfile(file_or_dir):
                    total_files.append(file_or_dir)
                    total_size += os.path.getsize(file_or_dir)
                elif os.path.isdir(file_or_dir):
                    for root, dirs, filenames in os.walk(file_or_dir):
                        for filename in filenames:
                            full_path = os.path.join(root, filename)
                            total_files.append(full_path)
                            try:
                                total_size += os.path.getsize(full_path)
                            except:
                                pass  # 忽略无法访问的文件
            
            if progress_callback:
                progress_callback(5, f"开始压缩 {len(total_files)} 个文件...")
            
            # 创建7Z压缩包
            with py7zr.SevenZipFile(file_path, 'w', password=password) as sz:
                processed_size = 0
                
                for file_or_dir in files:
                    if os.path.isfile(file_or_dir):
                        # 添加单个文件
                        arcname = os.path.basename(file_or_dir)
                        sz.write(file_or_dir, arcname)
                        processed_size += os.path.getsize(file_or_dir)
                        
                        if progress_callback and total_size > 0:
                            progress = int(5 + (processed_size / total_size) * 85)
                            progress_callback(progress, f"正在压缩: {arcname}")
                            
                    elif os.path.isdir(file_or_dir):
                        # 添加目录
                        dir_name = os.path.basename(file_or_dir)
                        for root, dirs, filenames in os.walk(file_or_dir):
                            for filename in filenames:
                                full_path = os.path.join(root, filename)
                                # 计算相对路径
                                rel_path = os.path.relpath(full_path, os.path.dirname(file_or_dir))
                                sz.write(full_path, rel_path)
                                
                                try:
                                    processed_size += os.path.getsize(full_path)
                                except:
                                    pass
                                
                                if progress_callback and total_size > 0:
                                    progress = int(5 + (processed_size / total_size) * 85)
                                    progress_callback(progress, f"正在压缩: {filename}")
                
                if progress_callback:
                    progress_callback(95, "正在完成压缩...")
                    time.sleep(0.1)
                    progress_callback(100, "压缩完成")
                    
            return True
            
        except PermissionError as e:
            raise PermissionError(f"权限不足: {e}")
        except Exception as e:
            raise Exception(f"创建7Z压缩包失败: {e}")
            
    def list_archive_contents(self, archive_path: str) -> List[Dict[str, Any]]:
        """列出7Z压缩包内容"""
        try:
            contents = []
            with py7zr.SevenZipFile(archive_path, mode='r') as sz:
                for info in sz.list():
                    if not info.filename.endswith('/'):
                        file_info = {
                            'name': info.filename,
                            'size': info.uncompressed,
                            'compressed_size': info.compressed if hasattr(info, 'compressed') else 0,
                            'modified_time': info.creationtime.strftime('%Y-%m-%d %H:%M:%S') if info.creationtime else '',
                            'is_dir': False
                        }
                        contents.append(file_info)
            return contents
        except Exception as e:
            raise Exception(f"列出7Z内容失败: {e}") 