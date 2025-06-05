# -*- coding: utf-8 -*-
"""
RAR格式处理器
实现RAR文件的只读操作（需要rarfile库）
"""

import os
from typing import Dict, List, Optional, Any
from datetime import datetime

try:
    import rarfile
    RARFILE_AVAILABLE = True
except ImportError:
    RARFILE_AVAILABLE = False


class RarHandler:
    """RAR格式处理器"""
    
    def __init__(self):
        """初始化处理器"""
        self.supported_extensions = ['.rar']
        
        # 检查rarfile库是否可用
        if not RARFILE_AVAILABLE:
            print("警告: rarfile库未安装，RAR支持将受限")
            
        # 尝试设置unrar工具路径（Windows）
        if RARFILE_AVAILABLE:
            try:
                # 在Windows上尝试常用的unrar路径
                possible_paths = [
                    r"C:\Program Files\WinRAR\UnRAR.exe",
                    r"C:\Program Files (x86)\WinRAR\UnRAR.exe",
                    "unrar.exe"  # 假设在PATH中
                ]
                
                for path in possible_paths:
                    if os.path.exists(path) or path == "unrar.exe":
                        rarfile.UNRAR_TOOL = path
                        break
            except:
                pass
        
    def get_archive_info(self, file_path: str) -> Dict[str, Any]:
        """获取RAR压缩包信息"""
        if not RARFILE_AVAILABLE:
            raise Exception("rarfile库未安装，无法处理RAR文件")
            
        archive_info = {
            'path': file_path,
            'format': 'RAR',
            'files': [],
            'total_size': 0,
            'compressed_size': 0,
            'file_count': 0,
            'has_password': False
        }
        
        try:
            with rarfile.RarFile(file_path, 'r') as rf:
                # 检查是否需要密码
                try:
                    file_list = rf.infolist()
                except rarfile.NeedFirstVolume:
                    raise Exception("需要RAR文件的第一卷")
                except rarfile.BadRarFile:
                    raise Exception("无效的RAR文件")
                except:
                    # 可能需要密码
                    archive_info['has_password'] = True
                    # 尝试获取文件列表（可能失败）
                    try:
                        file_list = rf.infolist()
                    except:
                        file_list = []
                
                # 获取文件信息
                for info in file_list:
                    if not info.is_dir():  # 不是目录
                        file_info = {
                            'path': info.filename,
                            'size': info.file_size,
                            'compressed_size': info.compress_size,
                            'modified_time': self._convert_time(info.date_time),
                            'crc': info.CRC,
                            'is_encrypted': info.needs_password()
                        }
                        archive_info['files'].append(file_info)
                        archive_info['total_size'] += info.file_size
                        archive_info['compressed_size'] += info.compress_size
                        archive_info['file_count'] += 1
                        
                        # 如果任何文件需要密码，标记整个包需要密码
                        if info.needs_password():
                            archive_info['has_password'] = True
                            
        except rarfile.RarCannotExec:
            raise Exception("无法执行unrar工具，请安装WinRAR或unrar命令行工具")
        except Exception as e:
            raise Exception(f"读取RAR文件失败: {e}")
            
        return archive_info
        
    def extract_archive(self, file_path: str, extract_to: str,
                       password: Optional[str] = None,
                       selected_files: Optional[List[str]] = None) -> bool:
        """解压RAR文件"""
        if not RARFILE_AVAILABLE:
            raise Exception("rarfile库未安装，无法处理RAR文件")
            
        try:
            # 确保解压目录存在
            os.makedirs(extract_to, exist_ok=True)
            
            with rarfile.RarFile(file_path, 'r') as rf:
                # 设置密码（如果需要）
                if password:
                    rf.setpassword(password)
                
                # 解压指定文件或全部文件
                if selected_files:
                    for file_name in selected_files:
                        try:
                            rf.extract(file_name, extract_to)
                        except KeyError:
                            print(f"文件不存在: {file_name}")
                            continue
                else:
                    rf.extractall(extract_to)
                    
            return True
            
        except rarfile.BadRarFile:
            raise Exception("无效的RAR文件")
        except rarfile.RarWrongPassword:
            raise Exception("密码错误")
        except rarfile.RarCannotExec:
            raise Exception("无法执行unrar工具")
        except Exception as e:
            raise Exception(f"解压失败: {e}")
            
    def _convert_time(self, date_time_tuple) -> str:
        """转换时间格式"""
        try:
            if len(date_time_tuple) >= 6:
                dt = datetime(*date_time_tuple[:6])
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            else:
                return ""
        except:
            return ""
            
    # RAR格式只支持读取，不支持创建和修改
    def create_archive(self, file_path: str, files: List[str],
                      compression_level: int = 6,
                      password: Optional[str] = None,
                      progress_callback=None) -> bool:
        """RAR格式不支持创建"""
        raise Exception("RAR格式不支持创建新的压缩包")