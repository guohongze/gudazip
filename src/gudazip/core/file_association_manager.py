#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件关联管理器
使用安全的PyWin32接口进行文件关联管理，避免直接操作注册表
"""

import sys
import os
import subprocess
from typing import List, Dict
from PySide6.QtWidgets import QMessageBox

# 导入安全的PyWin32注册表封装
from .pywin32_registry import PyWin32Registry
from .permission_manager import PermissionManager
from .environment_manager import get_environment_manager

class FileAssociationManager:
    """安全的文件关联管理器，使用PyWin32接口"""
    
    def __init__(self):
        self.prog_id = "GudaZip.Archive"
        self.app_description = "GudaZip压缩文件"
        self.registry = PyWin32Registry()
        
        # 支持的压缩文件扩展名
        self.supported_extensions = [
            # 基础格式
            '.zip', '.rar', '.7z', 
            # tar系列
            '.tar', '.tgz', '.tar.gz', '.tbz', '.tbz2', '.tar.bz2', '.txz', '.tar.xz', '.taz',
            # 压缩格式
            '.gz', '.gzip', '.bz2', '.bzip2', '.xz', '.lzma', '.z',
            # 其他常见格式
            '.cab', '.arj', '.lzh', '.cpio',
            # ISO镜像（如果需要）
            '.iso'
        ]
    
    @staticmethod
    def get_app_path() -> str:
        """获取应用程序的实际路径（使用环境变量）"""
        env_manager = get_environment_manager()
        return env_manager.get_app_executable_path()
    
    def is_admin(self) -> bool:
        """检查是否有管理员权限"""
        return PermissionManager.is_admin()
    
    def register_file_association(self, extensions: List[str], set_as_default: bool = False) -> Dict[str, any]:
        """
        安全地注册文件关联
        只针对特定的压缩文件格式，使用用户级别注册表
        """
        result = {
            "success": False,
            "message": "",
            "details": {},
            "success_count": 0,
            "total_operations": len(extensions)
        }
        
        # 注：使用HKEY_CURRENT_USER，不需要管理员权限
        
        if not self.registry.is_available():
            status = self.registry.get_module_status()
            missing_modules = status.get('missing_modules', [])
            result["message"] = f"PyWin32基础模块不可用。缺失模块: {missing_modules}"
            result["details"] = status
            return result
        
        try:
            # 获取应用程序路径和图标（使用环境变量）
            env_manager = get_environment_manager()
            app_path = env_manager.get_app_executable_path()
            icon_path = env_manager.get_app_icon_path()
            
            success_count = 0
            details = {}
            
            for ext in extensions:
                try:
                    # 确保是支持的扩展名
                    if not ext.startswith('.'):
                        ext = '.' + ext
                    
                    if ext not in self.supported_extensions:
                        details[ext] = {"success": False, "error": "不支持的文件格式"}
                        continue
                    
                    # 使用安全的文件关联方法
                    if self.registry.register_file_association_safe(
                        ext, self.prog_id, self.app_description, icon_path, app_path
                    ):
                        success_count += 1
                        details[ext] = {"success": True, "as_default": set_as_default}
                        print(f"✅ 文件关联成功: {ext}")
                    else:
                        details[ext] = {"success": False, "error": "注册失败"}
                        print(f"❌ 文件关联失败: {ext}")
                        
                except Exception as e:
                    details[ext] = {"success": False, "error": str(e)}
                    print(f"❌ 文件关联异常: {ext} -> {e}")
            
            # 刷新Shell关联
            self.registry.refresh_shell()
            
            result.update({
                "success": success_count > 0,
                "message": f"文件关联完成！成功关联 {success_count}/{len(extensions)} 个格式",
                "details": details,
                "success_count": success_count
            })
            
            return result
            
        except Exception as e:
            result.update({
                "success": False,
                "message": f"文件关联失败：{str(e)}",
                "error": str(e)
            })
            return result
    
    def unregister_file_association(self, extensions: List[str]) -> Dict[str, any]:
        """
        安全地取消文件关联
        """
        result = {
            "success": False,
            "message": "",
            "details": {},
            "success_count": 0,
            "total_operations": len(extensions)
        }
        
        # 注：使用HKEY_CURRENT_USER，不需要管理员权限
        
        if not self.registry.is_available():
            status = self.registry.get_module_status()
            missing_modules = status.get('missing_modules', [])
            result["message"] = f"PyWin32基础模块不可用。缺失模块: {missing_modules}"
            result["details"] = status
            return result
        
        try:
            success_count = 0
            details = {}
            
            for ext in extensions:
                try:
                    if not ext.startswith('.'):
                        ext = '.' + ext
                    
                    # 使用安全的取消关联方法
                    if self.registry.unregister_file_association_safe(ext, self.prog_id):
                        success_count += 1
                        details[ext] = {"success": True}
                        print(f"✅ 取消关联成功: {ext}")
                    else:
                        details[ext] = {"success": False, "error": "取消关联失败"}
                        print(f"❌ 取消关联失败: {ext}")
                        
                except Exception as e:
                    details[ext] = {"success": False, "error": str(e)}
                    print(f"❌ 取消关联异常: {ext} -> {e}")
            
            # 刷新Shell关联
            self.registry.refresh_shell()
            
            result.update({
                "success": success_count > 0,
                "message": f"取消文件关联完成！成功取消 {success_count}/{len(extensions)} 个格式",
                "details": details,
                "success_count": success_count
            })
            
            return result
            
        except Exception as e:
            result.update({
                "success": False,
                "message": f"取消文件关联失败：{str(e)}",
                "error": str(e)
            })
            return result
    
    def check_association_status(self, extensions: List[str]) -> Dict[str, bool]:
        """检查文件关联状态"""
        status = {}
        
        if not self.registry.is_available():
            for ext in extensions:
                status[ext] = False
            return status
        
        for ext in extensions:
            if not ext.startswith('.'):
                ext = '.' + ext
            try:
                status[ext] = self.registry.check_file_association(ext, self.prog_id)
            except Exception:
                status[ext] = False
        
        return status
    
    def get_associated_extensions(self) -> List[str]:
        """获取当前已关联的扩展名列表"""
        associated = []
        
        if not self.registry.is_available():
            return associated
        
        for ext in self.supported_extensions:
            try:
                if self.registry.check_file_association(ext, self.prog_id):
                    associated.append(ext)
            except Exception:
                continue
        
        return associated
    
    def install_context_menu(self, menu_options: Dict[str, bool]) -> Dict[str, any]:
        """
        安全地安装右键菜单
        为普通文件/文件夹添加压缩功能，为压缩文件添加解压功能
        不包含桌面空白处等系统对象
        """
        result = {
            "success": False,
            "message": "",
            "details": {},
            "success_count": 0,
            "total_operations": 0
        }
        
        if not self.registry.is_available():
            status = self.registry.get_module_status()
            missing_modules = status.get('missing_modules', [])
            result["message"] = f"PyWin32基础模块不可用。缺失模块: {missing_modules}"
            result["details"] = status
            return result
        
        try:
            # 获取应用程序路径和图标（使用环境变量）
            env_manager = get_environment_manager()
            app_path = env_manager.get_app_executable_path()
            icon_path = env_manager.get_app_icon_path()
            
            success_count = 0
            total_operations = 0
            
            # 1. 为普通文件和文件夹添加压缩菜单
            compression_targets = []
            compression_menu_items = {}
            
            # 为所有文件和文件夹添加压缩选项，但不包括桌面空白处
            if menu_options.get("add", False) or menu_options.get("zip", False) or menu_options.get("7z", False):
                # 只针对文件和文件夹，不包括Directory\\Background（桌面空白处）
                compression_targets.extend(["*", "Directory"])
                
                # 统一的压缩菜单
                compression_menu_items["compress"] = {
                    "display_name": "使用Gudazip压缩",
                    "command": f'{app_path} --add "%1"',
                    "icon_path": icon_path
                }
                
                total_operations += len(compression_targets) * len(compression_menu_items)
                
                # 为普通文件和文件夹创建压缩菜单
                if self.registry.create_context_menu_for_files_and_folders(
                    compression_targets, compression_menu_items
                ):
                    success_count += len(compression_targets) * len(compression_menu_items)
                    print("✅ 为普通文件和文件夹添加压缩菜单成功")
                else:
                    print("❌ 为普通文件和文件夹添加压缩菜单失败")
            
            # 2. 为压缩文件添加解压菜单（但首先需要移除可能存在的压缩菜单）
            extraction_menu_items = {}
            
            if menu_options.get("extract", False) or menu_options.get("open", False):
                # 先移除压缩文件上的压缩菜单
                compression_menu_ids_to_remove = ["compress"]
                self.registry.remove_context_menu_safe(
                    self.supported_extensions, compression_menu_ids_to_remove
                )
                
                # 简化的解压菜单 - 只保留两个选项
                if menu_options.get("open", False):
                    extraction_menu_items["open"] = {
                        "display_name": "打开压缩包",
                        "command": f'{app_path} "%1"',  # 直接打开，不使用--open参数
                        "icon_path": icon_path
                    }
                
                if menu_options.get("extract", False):
                    extraction_menu_items["extract"] = {
                        "display_name": "使用Gudazip解压", 
                        "command": f'{app_path} --extract-dialog "%1"',  # 新的解压对话框参数
                        "icon_path": icon_path
                    }
                
                total_operations += len(self.supported_extensions) * len(extraction_menu_items)
                
                # 为压缩文件创建解压菜单
                if self.registry.create_context_menu_safe(
                    self.supported_extensions, extraction_menu_items
                ):
                    success_count += len(self.supported_extensions) * len(extraction_menu_items)
                    print("✅ 为压缩文件添加解压菜单成功")
                else:
                    print("❌ 为压缩文件添加解压菜单失败")
            
            if success_count > 0:
                # 刷新Shell关联
                self.registry.refresh_shell()
                
                result.update({
                    "success": True,
                    "message": f"右键菜单安装成功！共创建 {success_count} 个菜单项",
                    "success_count": success_count,
                    "total_operations": total_operations
                })
            else:
                result.update({
                    "success": False,
                    "message": "右键菜单安装失败",
                    "success_count": 0,
                    "total_operations": total_operations
                })
            
            return result
            
        except Exception as e:
            result.update({
                "success": False,
                "message": f"安装右键菜单失败：{str(e)}",
                "error": str(e)
            })
            return result
    
    def uninstall_context_menu(self) -> Dict[str, any]:
        """安全地卸载右键菜单"""
        result = {
            "success": False,
            "message": "",
            "details": {},
            "success_count": 0,
            "total_operations": 0
        }
        
        if not self.registry.is_available():
            status = self.registry.get_module_status()
            missing_modules = status.get('missing_modules', [])
            result["message"] = f"PyWin32基础模块不可用。缺失模块: {missing_modules}"
            result["details"] = status
            return result
        
        try:
            success_count = 0
            total_operations = 0
            
            # 1. 移除普通文件和文件夹的压缩菜单
            compression_targets = ["*", "Directory"]
            compression_menu_ids = ["compress"]
            
            total_operations += len(compression_targets) * len(compression_menu_ids)
            
            if self.registry.remove_context_menu_for_files_and_folders(
                compression_targets, compression_menu_ids
            ):
                success_count += len(compression_targets) * len(compression_menu_ids)
                print("✅ 移除普通文件和文件夹的压缩菜单成功")
            else:
                print("❌ 移除普通文件和文件夹的压缩菜单失败")
            
            # 2. 移除压缩文件的解压菜单
            extraction_menu_ids = ["extract", "open"]
            
            total_operations += len(self.supported_extensions) * len(extraction_menu_ids)
            
            if self.registry.remove_context_menu_safe(
                self.supported_extensions, extraction_menu_ids
            ):
                success_count += len(self.supported_extensions) * len(extraction_menu_ids)
                print("✅ 移除压缩文件的解压菜单成功")
            else:
                print("❌ 移除压缩文件的解压菜单失败")
            
            if success_count > 0:
                # 刷新Shell关联
                self.registry.refresh_shell()
                
                result.update({
                    "success": True,
                    "message": f"右键菜单卸载成功！共移除 {success_count} 个菜单项",
                    "success_count": success_count,
                    "total_operations": total_operations
                })
            else:
                result.update({
                    "success": False,
                    "message": "右键菜单卸载失败",
                    "success_count": 0,
                    "total_operations": total_operations
                })
            
            return result
            
        except Exception as e:
            result.update({
                "success": False,
                "message": f"卸载右键菜单失败：{str(e)}",
                "error": str(e)
            })
            return result
    
    def check_context_menu_status(self) -> Dict[str, Dict[str, bool]]:
        """检查右键菜单状态"""
        status = {
            "files_and_folders": {},  # 普通文件和文件夹的压缩菜单
            "archives": {}            # 压缩文件的解压菜单
        }
        
        if not self.registry.is_available():
            return status
        
        try:
            # 1. 检查普通文件和文件夹的压缩菜单
            compression_targets = ["*", "Directory"]
            compression_menu_ids = ["compress"]
            
            for target in compression_targets:
                target_status = {}
                for menu_id in compression_menu_ids:
                    target_status[menu_id] = self.registry.check_general_context_menu(target, menu_id)
                status["files_and_folders"][target] = target_status
            
            # 2. 检查压缩文件的解压菜单
            extraction_menu_ids = ["extract", "open"]
            
            for ext in self.supported_extensions:
                ext_status = {}
                for menu_id in extraction_menu_ids:
                    menus = self.registry.list_context_menus(ext)
                    ext_status[menu_id] = menu_id in menus
                status["archives"][ext] = ext_status
                
        except Exception as e:
            print(f"检查右键菜单状态失败: {e}")
        
        return status

    # 兼容旧接口的方法（返回简化结果）
    def register_file_association_simple(self, extensions: List[str], set_as_default: bool = False) -> bool:
        """简化的文件关联注册接口（向后兼容）"""
        result = self.register_file_association(extensions, set_as_default)
        return result.get("success", False)
    
    def unregister_file_association_simple(self, extensions: List[str]) -> bool:
        """简化的文件关联取消接口（向后兼容）"""
        result = self.unregister_file_association(extensions)
        return result.get("success", False)
    
    def install_context_menu_simple(self, menu_options: Dict[str, bool]) -> bool:
        """简化的右键菜单安装接口（向后兼容）"""
        result = self.install_context_menu(menu_options)
        return result.get("success", False)
    
    def uninstall_context_menu_simple(self) -> bool:
        """简化的右键菜单卸载接口（向后兼容）"""
        result = self.uninstall_context_menu()
        return result.get("success", False)
    
    def check_context_menu_status_simple(self) -> bool:
        """简化的右键菜单状态检查接口（向后兼容）"""
        status = self.check_context_menu_status()
        # 如果任何文件类型有任何菜单项，就认为已安装
        for ext_status in status.values():
            if any(ext_status.values()):
                return True
        return False
    
    def clean_desktop_background_menu(self) -> Dict[str, any]:
        """
        清理桌面空白处的右键菜单
        专门用于移除之前错误注册的Directory\\Background菜单
        """
        result = {
            "success": False,
            "message": "",
            "details": {},
            "success_count": 0,
            "total_operations": 0
        }
        
        if not self.registry.is_available():
            status = self.registry.get_module_status()
            missing_modules = status.get('missing_modules', [])
            result["message"] = f"PyWin32基础模块不可用。缺失模块: {missing_modules}"
            result["details"] = status
            return result
        
        try:
            success_count = 0
            total_operations = 0
            
            # 清理Directory\\Background中的gudazip菜单
            desktop_background_targets = ["Directory\\Background"]
            menu_ids_to_remove = ["compress", "extract", "open"]
            
            total_operations += len(desktop_background_targets) * len(menu_ids_to_remove)
            
            if self.registry.remove_context_menu_for_files_and_folders(
                desktop_background_targets, menu_ids_to_remove
            ):
                success_count += len(desktop_background_targets) * len(menu_ids_to_remove)
                print("✅ 清理桌面空白处的右键菜单成功")
            else:
                print("❌ 清理桌面空白处的右键菜单失败")
            
            # 刷新Shell关联
            self.registry.refresh_shell()
            
            result.update({
                "success": True,
                "message": f"桌面空白处右键菜单清理完成！共移除 {success_count} 个菜单项",
                "success_count": success_count,
                "total_operations": total_operations
            })
            
            return result
            
        except Exception as e:
            result.update({
                "success": False,
                "message": f"清理桌面空白处右键菜单失败：{str(e)}",
                "error": str(e)
            })
            return result