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
                       selected_files: Optional[List[str]] = None,
                       progress_callback=None) -> bool:
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
                
                # 获取要解压的文件列表和总大小
                if selected_files:
                    files_to_extract = []
                    total_size = 0
                    # 验证选中的文件是否存在于压缩包中
                    for file_name in selected_files:
                        try:
                            info = zf.getinfo(file_name)
                            files_to_extract.append(info)
                            total_size += info.file_size
                        except KeyError:
                            print(f"文件不存在于压缩包中: {file_name}")
                            continue
                else:
                    files_to_extract = [info for info in zf.infolist() if not info.filename.endswith('/')]
                    total_size = sum(info.file_size for info in files_to_extract)
                
                if progress_callback:
                    progress_callback(0, f"准备解压 {len(files_to_extract)} 个文件...")
                
                # 解压文件并跟踪进度
                extracted_size = 0
                extracted_count = 0
                
                for info in files_to_extract:
                    try:
                        # 安全检查：防止路径遍历攻击
                        if self._is_safe_path(info.filename, extract_to):
                            # 显示当前正在解压的文件
                            if progress_callback:
                                file_name = os.path.basename(info.filename)
                                progress_callback(
                                    int(5 + (extracted_size / total_size) * 85) if total_size > 0 else 5,
                                    f"正在解压: {file_name}"
                                )
                            
                            # 解压文件
                            zf.extract(info, extract_to)
                            
                            # 更新进度
                            extracted_size += info.file_size
                            extracted_count += 1
                            
                            # 更新进度条
                            if progress_callback and total_size > 0:
                                progress = int(5 + (extracted_size / total_size) * 85)  # 5-90%的范围
                                progress_callback(progress, f"已解压: {extracted_count}/{len(files_to_extract)} 个文件")
                        else:
                            print(f"跳过不安全的路径: {info.filename}")
                            extracted_count += 1
                            
                    except Exception as e:
                        print(f"解压文件 {info.filename} 失败: {e}")
                        extracted_count += 1
                        continue
                
                if progress_callback:
                    progress_callback(95, "正在完成解压...")
                    time.sleep(0.1)  # 短暂延迟让用户看到95%状态
                    progress_callback(100, "解压完成")
                    
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
                      password: Optional[str] = None,
                      progress_callback=None) -> bool:
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
            
            # 计算总文件大小和文件数量以跟踪进度
            total_size = 0
            total_files = []
            
            if progress_callback:
                progress_callback(0, "正在计算文件大小...")
            
            for file_or_dir in files:
                if os.path.isfile(file_or_dir):
                    total_size += os.path.getsize(file_or_dir)
                    total_files.append(file_or_dir)
                elif os.path.isdir(file_or_dir):
                    for root, dirs, file_list in os.walk(file_or_dir):
                        for file_name in file_list:
                            file_full_path = os.path.join(root, file_name)
                            if os.path.exists(file_full_path):
                                total_size += os.path.getsize(file_full_path)
                                total_files.append(file_full_path)
            
            if progress_callback:
                progress_callback(5, f"开始压缩 {len(total_files)} 个文件...")
                
            # 设置压缩级别
            compression = zipfile.ZIP_DEFLATED
            if compression_level == 0:
                compression = zipfile.ZIP_STORED
            
            processed_size = 0
            processed_files = 0
                
            with zipfile.ZipFile(file_path, 'w', compression) as zf:
                for file_or_dir in files:
                    if os.path.isfile(file_or_dir):
                        # 添加文件
                        arcname = os.path.basename(file_or_dir)
                        zf.write(file_or_dir, arcname)
                        
                        # 更新进度
                        if os.path.exists(file_or_dir):
                            processed_size += os.path.getsize(file_or_dir)
                            processed_files += 1
                            if progress_callback and total_size > 0:
                                progress = int(5 + (processed_size / total_size) * 85)  # 5-90%的范围
                                progress_callback(progress, f"正在压缩: {os.path.basename(file_or_dir)}")
                        
                    elif os.path.isdir(file_or_dir):
                        # 添加目录及其内容
                        for root, dirs, file_list in os.walk(file_or_dir):
                            for file_name in file_list:
                                file_full_path = os.path.join(root, file_name)
                                # 计算相对路径
                                arcname = os.path.relpath(file_full_path, 
                                                         os.path.dirname(file_or_dir))
                                zf.write(file_full_path, arcname)
                                
                                # 更新进度
                                if os.path.exists(file_full_path):
                                    processed_size += os.path.getsize(file_full_path)
                                    processed_files += 1
                                    if progress_callback and total_size > 0:
                                        progress = int(5 + (processed_size / total_size) * 85)  # 5-90%的范围
                                        progress_callback(progress, f"正在压缩: {os.path.basename(file_name)}")
            
            if progress_callback:
                progress_callback(95, "正在完成压缩...")
                                
            # 如果需要密码保护，需要使用第三方库如pyminizip
            if password:
                # TODO: 实现密码保护功能
                print("ZIP密码保护功能需要pyminizip库支持")
            
            if progress_callback:
                progress_callback(100, "压缩完成")
                
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
    
    def add_files_to_archive(self, archive_path: str, files_to_add: List[str], 
                            base_path: Optional[str] = None, 
                            progress_callback=None) -> bool:
        """向ZIP压缩包中添加文件"""
        try:
            # 验证输入参数
            if not files_to_add:
                raise ValueError("没有指定要添加的文件")
                
            # 检查压缩包是否存在
            if not os.path.exists(archive_path):
                raise FileNotFoundError(f"压缩包不存在：{archive_path}")
                
            # 检查所有要添加的文件是否存在
            missing_files = [f for f in files_to_add if not os.path.exists(f)]
            if missing_files:
                raise FileNotFoundError(f"以下文件不存在: {', '.join(missing_files)}")
            
            # 检查权限
            paths_to_check = files_to_add + [archive_path]
            if not PermissionManager.request_admin_if_needed(paths_to_check, "添加文件到压缩包"):
                return False
            
            if progress_callback:
                progress_callback(0, "正在准备添加文件...")
            
            # 创建临时压缩包
            temp_archive = archive_path + ".tmp"
            
            try:
                # 读取原压缩包，复制所有文件到新压缩包
                with zipfile.ZipFile(archive_path, 'r') as original_zf:
                    with zipfile.ZipFile(temp_archive, 'w', zipfile.ZIP_DEFLATED) as new_zf:
                        # 复制原有文件
                        if progress_callback:
                            progress_callback(10, "正在复制原有文件...")
                        
                        existing_files = original_zf.namelist()
                        total_existing = len(existing_files)
                        
                        for i, item in enumerate(existing_files):
                            # 读取原文件内容
                            data = original_zf.read(item)
                            # 写入到新压缩包
                            new_zf.writestr(item, data)
                            
                            if progress_callback and total_existing > 0:
                                progress = 10 + int((i / total_existing) * 30)  # 10-40%的范围
                                progress_callback(progress, f"复制文件: {os.path.basename(item)}")
                        
                        # 添加新文件
                        if progress_callback:
                            progress_callback(40, "正在添加新文件...")
                        
                        total_new_files = len(files_to_add)
                        for i, file_path in enumerate(files_to_add):
                            if os.path.isfile(file_path):
                                # 确定在压缩包中的路径
                                if base_path:
                                    # 使用相对于base_path的路径
                                    arcname = os.path.relpath(file_path, base_path)
                                else:
                                    # 只使用文件名
                                    arcname = os.path.basename(file_path)
                                
                                # 确保使用正斜杠作为分隔符
                                arcname = arcname.replace('\\', '/')
                                
                                # 检查文件是否已存在
                                if arcname in existing_files:
                                    # 生成唯一的文件名
                                    base_name, ext = os.path.splitext(arcname)
                                    counter = 1
                                    while f"{base_name}_{counter}{ext}" in existing_files:
                                        counter += 1
                                    arcname = f"{base_name}_{counter}{ext}"
                                
                                new_zf.write(file_path, arcname)
                                
                                if progress_callback:
                                    progress = 40 + int((i / total_new_files) * 50)  # 40-90%的范围
                                    progress_callback(progress, f"添加文件: {os.path.basename(file_path)}")
                            
                            elif os.path.isdir(file_path):
                                # 添加目录及其内容
                                for root, dirs, files in os.walk(file_path):
                                    for file in files:
                                        file_full_path = os.path.join(root, file)
                                        # 计算压缩包内的路径
                                        if base_path:
                                            arcname = os.path.relpath(file_full_path, base_path)
                                        else:
                                            arcname = os.path.relpath(file_full_path, os.path.dirname(file_path))
                                        
                                        # 确保使用正斜杠
                                        arcname = arcname.replace('\\', '/')
                                        
                                        new_zf.write(file_full_path, arcname)
                
                # 用新压缩包替换原压缩包
                if progress_callback:
                    progress_callback(95, "正在完成...")
                
                # 删除原文件，重命名临时文件
                os.remove(archive_path)
                os.rename(temp_archive, archive_path)
                
                if progress_callback:
                    progress_callback(100, "添加完成")
                
                return True
                
            except Exception as e:
                # 清理临时文件
                if os.path.exists(temp_archive):
                    try:
                        os.remove(temp_archive)
                    except:
                        pass
                raise e
                
        except zipfile.BadZipFile:
            raise ValueError("无效的ZIP文件")
        except PermissionError as e:
            raise PermissionError(f"权限不足: {e}")
        except Exception as e:
            raise Exception(f"添加文件失败: {e}") 