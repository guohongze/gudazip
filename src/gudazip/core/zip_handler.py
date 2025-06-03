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


class ZipHandler:
    """ZIP格式处理器"""
    
    def __init__(self):
        """初始化处理器"""
        self.supported_extensions = ['.zip']
        
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
            
    def add_files(self, archive_path: str, files: List[str]) -> bool:
        """向ZIP文件添加文件"""
        try:
            # 创建临时文件
            temp_path = archive_path + '.tmp'
            
            with zipfile.ZipFile(archive_path, 'r') as original_zf:
                with zipfile.ZipFile(temp_path, 'w') as new_zf:
                    # 复制原有文件
                    for item in original_zf.infolist():
                        data = original_zf.read(item.filename)
                        new_zf.writestr(item, data)
                    
                    # 添加新文件
                    for file_path in files:
                        if os.path.isfile(file_path):
                            arcname = os.path.basename(file_path)
                            new_zf.write(file_path, arcname)
                            
            # 替换原文件
            os.replace(temp_path, archive_path)
            return True
            
        except Exception as e:
            # 清理临时文件
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise Exception(f"添加文件失败: {e}")
            
    def remove_files(self, archive_path: str, files: List[str]) -> bool:
        """从ZIP文件删除文件"""
        try:
            # 创建临时文件
            temp_path = archive_path + '.tmp'
            
            with zipfile.ZipFile(archive_path, 'r') as original_zf:
                with zipfile.ZipFile(temp_path, 'w') as new_zf:
                    # 复制除了要删除的文件之外的所有文件
                    for item in original_zf.infolist():
                        if item.filename not in files:
                            data = original_zf.read(item.filename)
                            new_zf.writestr(item, data)
                            
            # 替换原文件
            os.replace(temp_path, archive_path)
            return True
            
        except Exception as e:
            # 清理临时文件
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise Exception(f"删除文件失败: {e}")
            
    def test_archive(self, file_path: str, password: Optional[str] = None) -> bool:
        """测试ZIP文件完整性"""
        try:
            with zipfile.ZipFile(file_path, 'r') as zf:
                if password:
                    zf.setpassword(password.encode('utf-8'))
                
                # 测试所有文件
                result = zf.testzip()
                return result is None  # 如果返回None，表示测试通过
                
        except zipfile.BadZipFile:
            return False
        except RuntimeError as e:
            if "Bad password" in str(e):
                raise Exception("密码错误")
            return False
        except Exception:
            return False
            
    def _convert_time(self, date_time_tuple) -> str:
        """转换时间格式"""
        try:
            dt = datetime(*date_time_tuple)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            return "" 