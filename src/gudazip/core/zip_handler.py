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

from .permission_manager import PermissionManager


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
            raise ValueError("无效的ZIP文件")
        except PermissionError:
            raise PermissionError(f"没有权限访问文件：{file_path}")
        except FileNotFoundError:
            raise FileNotFoundError(f"文件不存在：{file_path}")
        except Exception as e:
            raise Exception(f"读取ZIP文件失败: {e}")
            
        return archive_info
        
    def extract_archive(self, file_path: str, extract_to: str,
                       password: Optional[str] = None,
                       selected_files: Optional[List[str]] = None) -> bool:
        """解压ZIP文件"""
        try:
            # 验证输入参数
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"ZIP文件不存在：{file_path}")
                
            # 检查权限
            paths_to_check = [file_path, extract_to]
            if not PermissionManager.request_admin_if_needed(paths_to_check, "解压"):
                return False
                
            # 确保解压目录存在
            if not PermissionManager.ensure_directory_exists(extract_to):
                raise PermissionError(f"无法创建解压目录：{extract_to}")
            
            with zipfile.ZipFile(file_path, 'r') as zf:
                # 设置密码（如果需要）
                if password:
                    zf.setpassword(password.encode('utf-8'))
                
                # 解压指定文件或全部文件
                if selected_files:
                    for file_name in selected_files:
                        try:
                            # 安全检查：防止路径遍历攻击
                            if self._is_safe_path(file_name, extract_to):
                                zf.extract(file_name, extract_to)
                            else:
                                print(f"跳过不安全的路径: {file_name}")
                        except KeyError:
                            print(f"文件不存在: {file_name}")
                            continue
                        except Exception as e:
                            print(f"解压文件 {file_name} 失败: {e}")
                            continue
                else:
                    # 安全解压所有文件
                    for member in zf.infolist():
                        if self._is_safe_path(member.filename, extract_to):
                            zf.extract(member, extract_to)
                        else:
                            print(f"跳过不安全的路径: {member.filename}")
                    
            return True
            
        except zipfile.BadZipFile:
            raise ValueError("无效的ZIP文件")
        except RuntimeError as e:
            if "Bad password" in str(e):
                raise ValueError("密码错误")
            else:
                raise Exception(f"解压失败: {e}")
        except PermissionError as e:
            raise PermissionError(f"权限不足: {e}")
        except Exception as e:
            raise Exception(f"解压失败: {e}")
            
    def create_archive(self, file_path: str, files: List[str],
                      compression_level: int = 6,
                      password: Optional[str] = None) -> bool:
        """创建ZIP压缩包"""
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
                                # 计算相对路径
                                arcname = os.path.relpath(file_full_path, 
                                                         os.path.dirname(file_or_dir))
                                zf.write(file_full_path, arcname)
                                
            # 如果需要密码保护，需要使用第三方库如pyminizip
            if password:
                # TODO: 实现密码保护功能
                print("ZIP密码保护功能需要pyminizip库支持")
                
            return True
            
        except PermissionError as e:
            raise PermissionError(f"权限不足: {e}")
        except FileNotFoundError as e:
            raise FileNotFoundError(str(e))
        except Exception as e:
            raise Exception(f"创建ZIP文件失败: {e}")
            
    def _convert_time(self, date_time_tuple) -> str:
        """转换ZIP文件时间格式为字符串"""
        try:
            dt = datetime(*date_time_tuple)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            return "未知时间"
    
    def _is_safe_path(self, file_path: str, extract_to: str) -> bool:
        """检查解压路径是否安全，防止路径遍历攻击"""
        try:
            # 规范化路径
            extract_to = os.path.abspath(extract_to)
            target_path = os.path.abspath(os.path.join(extract_to, file_path))
            
            # 检查目标路径是否在解压目录内
            return target_path.startswith(extract_to)
        except Exception:
            return False
    
    def rename_file_in_archive(self, archive_path: str, old_name: str, new_name: str) -> bool:
        """重命名ZIP压缩包内的文件"""
        try:
            if not os.path.exists(archive_path):
                raise FileNotFoundError(f"压缩包不存在：{archive_path}")
            
            # 检查权限
            if not PermissionManager.request_admin_if_needed([archive_path], "修改压缩包"):
                return False
            
            # 创建临时文件
            temp_path = archive_path + '.tmp'
            
            with zipfile.ZipFile(archive_path, 'r') as old_zip:
                with zipfile.ZipFile(temp_path, 'w', zipfile.ZIP_DEFLATED) as new_zip:
                    # 遍历原压缩包中的所有文件
                    for item in old_zip.infolist():
                        # 读取文件数据
                        data = old_zip.read(item.filename)
                        
                        # 确定新的文件名
                        if item.filename == old_name:
                            # 这是要重命名的文件
                            new_info = zipfile.ZipInfo(new_name)
                            new_info.date_time = item.date_time
                            new_info.compress_type = item.compress_type
                            new_info.flag_bits = item.flag_bits
                            new_info.external_attr = item.external_attr
                            new_zip.writestr(new_info, data)
                        elif item.filename.startswith(old_name + '/'):
                            # 这是要重命名文件夹内的文件
                            new_filename = item.filename.replace(old_name + '/', new_name + '/', 1)
                            new_info = zipfile.ZipInfo(new_filename)
                            new_info.date_time = item.date_time
                            new_info.compress_type = item.compress_type
                            new_info.flag_bits = item.flag_bits
                            new_info.external_attr = item.external_attr
                            new_zip.writestr(new_info, data)
                        else:
                            # 其他文件保持不变
                            new_zip.writestr(item, data)
            
            # 替换原文件
            import shutil
            shutil.move(temp_path, archive_path)
            return True
            
        except Exception as e:
            # 清理临时文件
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
            raise Exception(f"重命名失败: {e}")
    
    def delete_file_from_archive(self, archive_path: str, file_name: str) -> bool:
        """从ZIP压缩包中删除文件"""
        try:
            if not os.path.exists(archive_path):
                raise FileNotFoundError(f"压缩包不存在：{archive_path}")
            
            # 检查权限
            if not PermissionManager.request_admin_if_needed([archive_path], "修改压缩包"):
                return False
            
            # 创建临时文件
            temp_path = archive_path + '.tmp'
            
            with zipfile.ZipFile(archive_path, 'r') as old_zip:
                with zipfile.ZipFile(temp_path, 'w', zipfile.ZIP_DEFLATED) as new_zip:
                    # 遍历原压缩包中的所有文件
                    for item in old_zip.infolist():
                        # 跳过要删除的文件
                        if item.filename == file_name:
                            continue
                        # 跳过要删除文件夹内的所有文件
                        if item.filename.startswith(file_name + '/'):
                            continue
                        
                        # 保留其他文件
                        data = old_zip.read(item.filename)
                        new_zip.writestr(item, data)
            
            # 替换原文件
            import shutil
            shutil.move(temp_path, archive_path)
            return True
            
        except Exception as e:
            # 清理临时文件
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
            raise Exception(f"删除失败: {e}")
    
    def list_archive_contents(self, archive_path: str) -> List[Dict[str, Any]]:
        """获取压缩包文件列表（用于刷新显示）"""
        try:
            if not os.path.exists(archive_path):
                raise FileNotFoundError(f"压缩包不存在：{archive_path}")
            
            files = []
            with zipfile.ZipFile(archive_path, 'r') as zf:
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
                        files.append(file_info)
            
            return files
            
        except Exception as e:
            raise Exception(f"读取压缩包内容失败: {e}") 