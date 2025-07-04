# -*- coding: utf-8 -*-
"""
通用压缩文件处理器
支持多种压缩格式的统一接口
"""

import os
import tarfile
import gzip
import bz2
import lzma
import shutil
import tempfile
from typing import Dict, List, Optional, Any
from datetime import datetime
import time

from .permission_manager import PermissionManager


class UniversalHandler:
    """通用压缩文件处理器"""
    
    def __init__(self):
        """初始化处理器"""
        # 按处理方式分组的支持格式
        self.tar_extensions = ['.tar', '.tgz', '.tar.gz', '.tbz', '.tbz2', '.tar.bz2', '.txz', '.tar.xz', '.taz']
        self.gzip_extensions = ['.gz', '.gzip']
        self.bzip2_extensions = ['.bz2', '.bzip2']
        self.xz_extensions = ['.xz']
        self.lzma_extensions = ['.lzma']
        
        self.supported_extensions = (
            self.tar_extensions + 
            self.gzip_extensions + 
            self.bzip2_extensions + 
            self.xz_extensions + 
            self.lzma_extensions
        )
        
    def get_archive_type(self, file_path: str) -> str:
        """确定压缩文件类型"""
        ext = os.path.splitext(file_path)[1].lower()
        
        # 处理复合扩展名
        if file_path.lower().endswith('.tar.gz'):
            return 'tar.gz'
        elif file_path.lower().endswith('.tar.bz2'):
            return 'tar.bz2'
        elif file_path.lower().endswith('.tar.xz'):
            return 'tar.xz'
        elif ext in self.tar_extensions:
            return 'tar'
        elif ext in self.gzip_extensions:
            return 'gzip'
        elif ext in self.bzip2_extensions:
            return 'bzip2'
        elif ext in self.xz_extensions:
            return 'xz'
        elif ext in self.lzma_extensions:
            return 'lzma'
        else:
            return 'unknown'
    
    def get_archive_info(self, file_path: str) -> Dict[str, Any]:
        """获取压缩文件信息"""
        archive_info = {
            'path': file_path,
            'format': 'Unknown',
            'files': [],
            'total_size': 0,
            'compressed_size': 0,
            'file_count': 0,
            'has_password': False
        }
        
        try:
            archive_type = self.get_archive_type(file_path)
            archive_info['format'] = archive_type.upper()
            
            if archive_type.startswith('tar'):
                return self._get_tar_info(file_path, archive_info)
            elif archive_type in ['gzip', 'bzip2', 'xz', 'lzma']:
                return self._get_single_file_info(file_path, archive_info, archive_type)
            else:
                raise ValueError(f"不支持的文件格式: {archive_type}")
                
        except Exception as e:
            raise Exception(f"读取压缩文件失败: {e}")
            
        return archive_info
    
    def _get_tar_info(self, file_path: str, archive_info: Dict[str, Any]) -> Dict[str, Any]:
        """获取tar类型文件信息"""
        try:
            with tarfile.open(file_path, 'r:*') as tar:
                for member in tar.getmembers():
                    if member.isfile():
                        file_info = {
                            'path': member.name,
                            'size': member.size,
                            'compressed_size': 0,  # tar不提供压缩大小
                            'modified_time': datetime.fromtimestamp(member.mtime).strftime('%Y-%m-%d %H:%M:%S'),
                            'crc': 0,
                            'is_encrypted': False
                        }
                        archive_info['files'].append(file_info)
                        archive_info['total_size'] += member.size
                        archive_info['file_count'] += 1
            
            archive_info['compressed_size'] = os.path.getsize(file_path)
            
        except tarfile.ReadError:
            raise ValueError("无效的tar文件")
        except Exception as e:
            raise Exception(f"读取tar文件失败: {e}")
            
        return archive_info
    
    def _get_single_file_info(self, file_path: str, archive_info: Dict[str, Any], format_type: str) -> Dict[str, Any]:
        """获取单文件压缩格式信息"""
        try:
            # 对于单文件压缩，通常包含一个同名文件（去掉压缩扩展名）
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            if format_type == 'gzip' and base_name.endswith('.tar'):
                base_name = os.path.splitext(base_name)[0]
            
            file_info = {
                'path': base_name,
                'size': 0,  # 需要解压才能获得真实大小
                'compressed_size': os.path.getsize(file_path),
                'modified_time': datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M:%S'),
                'crc': 0,
                'is_encrypted': False
            }
            
            archive_info['files'].append(file_info)
            archive_info['file_count'] = 1
            archive_info['compressed_size'] = os.path.getsize(file_path)
            
        except Exception as e:
            raise Exception(f"读取{format_type}文件失败: {e}")
            
        return archive_info
    
    def extract_archive(self, file_path: str, extract_to: str,
                       password: Optional[str] = None,
                       selected_files: Optional[List[str]] = None,
                       progress_callback=None) -> bool:
        """解压压缩文件"""
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"压缩文件不存在：{file_path}")
                
            # 检查权限
            paths_to_check = [file_path, extract_to]
            if not PermissionManager.request_admin_if_needed(paths_to_check, "解压"):
                return False
                
            # 确保解压目录存在
            if not PermissionManager.ensure_directory_exists(extract_to):
                raise PermissionError(f"无法创建解压目录：{extract_to}")
            
            archive_type = self.get_archive_type(file_path)
            
            if progress_callback:
                progress_callback(0, f"开始解压 {archive_type.upper()} 文件...")
            
            if archive_type.startswith('tar'):
                return self._extract_tar(file_path, extract_to, selected_files, progress_callback)
            elif archive_type in ['gzip', 'bzip2', 'xz', 'lzma']:
                return self._extract_single_file(file_path, extract_to, archive_type, progress_callback)
            else:
                raise ValueError(f"不支持的文件格式: {archive_type}")
                
        except Exception as e:
            raise Exception(f"解压失败: {e}")
    
    def _extract_tar(self, file_path: str, extract_to: str, selected_files: Optional[List[str]], progress_callback) -> bool:
        """解压tar类型文件"""
        try:
            with tarfile.open(file_path, 'r:*') as tar:
                if selected_files:
                    # 解压选定文件
                    members = [member for member in tar.getmembers() if member.name in selected_files]
                else:
                    # 解压所有文件
                    members = tar.getmembers()
                
                total_files = len([m for m in members if m.isfile()])
                extracted_files = 0
                
                for member in members:
                    if member.isfile():
                        tar.extract(member, extract_to)
                        extracted_files += 1
                        
                        if progress_callback:
                            progress = int((extracted_files / total_files) * 90)
                            progress_callback(progress, f"已解压 {extracted_files}/{total_files} 文件")
                
                if progress_callback:
                    progress_callback(100, "解压完成")
                    
            return True
            
        except Exception as e:
            raise Exception(f"解压tar文件失败: {e}")
    
    def _extract_single_file(self, file_path: str, extract_to: str, format_type: str, progress_callback) -> bool:
        """解压单文件压缩格式"""
        try:
            # 确定输出文件名
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            output_path = os.path.join(extract_to, base_name)
            
            if progress_callback:
                progress_callback(10, f"正在解压 {format_type.upper()} 文件...")
            
            # 根据格式选择解压方法
            if format_type == 'gzip':
                with gzip.open(file_path, 'rb') as f_in:
                    with open(output_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
            elif format_type == 'bzip2':
                with bz2.BZ2File(file_path, 'rb') as f_in:
                    with open(output_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
            elif format_type in ['xz', 'lzma']:
                with lzma.LZMAFile(file_path, 'rb') as f_in:
                    with open(output_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
            
            if progress_callback:
                progress_callback(100, "解压完成")
                
            return True
            
        except Exception as e:
            raise Exception(f"解压{format_type}文件失败: {e}")
    
    def create_archive(self, file_path: str, files: List[str],
                      compression_level: int = 6,
                      password: Optional[str] = None,
                      progress_callback=None) -> bool:
        """创建压缩文件"""
        try:
            if not files:
                raise ValueError("没有指定要压缩的文件")
            
            # 根据文件扩展名确定压缩类型
            archive_type = self.get_archive_type(file_path)
            
            if archive_type.startswith('tar'):
                return self._create_tar(file_path, files, archive_type, compression_level, progress_callback)
            elif archive_type in ['gzip', 'bzip2', 'xz', 'lzma']:
                return self._create_single_file(file_path, files, archive_type, compression_level, progress_callback)
            else:
                raise ValueError(f"不支持创建 {archive_type} 格式")
                
        except Exception as e:
            raise Exception(f"创建压缩文件失败: {e}")
    
    def _create_tar(self, file_path: str, files: List[str], archive_type: str, compression_level: int, progress_callback) -> bool:
        """创建tar类型压缩文件"""
        try:
            # 确定tar模式
            if archive_type == 'tar.gz' or archive_type == 'tgz':
                mode = 'w:gz'
            elif archive_type == 'tar.bz2' or archive_type == 'tbz2':
                mode = 'w:bz2'
            elif archive_type == 'tar.xz':
                mode = 'w:xz'
            else:
                mode = 'w'
            
            if progress_callback:
                progress_callback(0, f"开始创建 {archive_type.upper()} 压缩包...")
            
            with tarfile.open(file_path, mode, compresslevel=compression_level) as tar:
                total_files = len(files)
                added_files = 0
                
                for file_item in files:
                    if os.path.exists(file_item):
                        arcname = os.path.basename(file_item)
                        tar.add(file_item, arcname=arcname)
                        added_files += 1
                        
                        if progress_callback:
                            progress = int((added_files / total_files) * 90)
                            progress_callback(progress, f"已添加 {added_files}/{total_files} 文件")
            
            if progress_callback:
                progress_callback(100, "压缩完成")
                
            return True
            
        except Exception as e:
            raise Exception(f"创建tar压缩文件失败: {e}")
    
    def _create_single_file(self, file_path: str, files: List[str], format_type: str, compression_level: int, progress_callback) -> bool:
        """创建单文件压缩格式"""
        try:
            if len(files) != 1:
                raise ValueError(f"{format_type.upper()} 格式只能压缩单个文件")
            
            source_file = files[0]
            if not os.path.isfile(source_file):
                raise ValueError("只能压缩文件，不支持目录")
            
            if progress_callback:
                progress_callback(10, f"正在创建 {format_type.upper()} 压缩文件...")
            
            # 根据格式选择压缩方法
            if format_type == 'gzip':
                with open(source_file, 'rb') as f_in:
                    with gzip.open(file_path, 'wb', compresslevel=compression_level) as f_out:
                        shutil.copyfileobj(f_in, f_out)
            elif format_type == 'bzip2':
                with open(source_file, 'rb') as f_in:
                    with bz2.BZ2File(file_path, 'wb', compresslevel=compression_level) as f_out:
                        shutil.copyfileobj(f_in, f_out)
            elif format_type in ['xz', 'lzma']:
                preset = min(compression_level, 6)  # lzma压缩级别最高为6
                with open(source_file, 'rb') as f_in:
                    with lzma.LZMAFile(file_path, 'wb', preset=preset) as f_out:
                        shutil.copyfileobj(f_in, f_out)
            
            if progress_callback:
                progress_callback(100, "压缩完成")
                
            return True
            
        except Exception as e:
            raise Exception(f"创建{format_type}压缩文件失败: {e}") 