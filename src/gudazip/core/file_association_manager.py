# -*- coding: utf-8 -*-
"""
文件关联管理器
处理Windows系统的文件关联设置
"""

import os
import sys
import subprocess
from typing import List, Dict, Optional
from PySide6.QtWidgets import QMessageBox

# Windows注册表模块，仅在Windows系统上可用
try:
    import winreg
except ImportError:
    winreg = None

# 导入权限管理器
from .permission_manager import PermissionManager


class FileAssociationManager:
    """文件关联管理器"""
    
    def __init__(self):
        self.app_name = "GudaZip"
        self.app_description = "GudaZip 压缩管理器"
        self.prog_id = "GudaZip.Archive"
        
    @staticmethod
    def get_app_path() -> str:
        """获取应用程序路径"""
        if getattr(sys, 'frozen', False):
            # 如果是打包的exe
            return sys.executable
        else:
            # 如果是直接运行的Python脚本
            # 当前文件: src/gudazip/core/file_association_manager.py
            # 项目根目录需要上4级: core -> gudazip -> src -> 根目录
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            main_py = os.path.join(project_root, 'main.py')
            if os.path.exists(main_py):
                return f'"{sys.executable}" "{main_py}"'
            return f'"{sys.executable}" "{__file__}"'
    
    def is_admin(self) -> bool:
        """检查是否有管理员权限"""
        return PermissionManager.is_admin()
    

    
    def register_file_association(self, extensions: List[str], set_as_default: bool = False) -> bool:
        """注册文件关联"""
        if sys.platform != "win32" or winreg is None:
            QMessageBox.warning(None, "不支持", "文件关联功能仅在Windows系统上可用")
            return False
        
        # 使用统一的权限管理系统
        # 注册表操作需要管理员权限，检查 HKEY_CLASSES_ROOT 访问权限
        registry_paths = ["HKEY_CLASSES_ROOT"]  # 模拟需要权限的路径
        if not PermissionManager.request_admin_if_needed(registry_paths, "设置文件关联"):
            return False
        
        try:
            app_path = self.get_app_path()
            app_dir = os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else __file__)
            icon_path = os.path.join(app_dir, "resources", "icons", "app_icon.ico")
            
            # 注册程序ID
            self._register_prog_id(app_path, icon_path)
            
            # 注册文件扩展名
            for ext in extensions:
                self._register_extension(ext, set_as_default)
            
            # 刷新Shell关联
            self._refresh_shell_associations()
            
            return True
            
        except PermissionError:
            QMessageBox.warning(None, "权限不足", 
                              "修改文件关联需要管理员权限。\n"
                              "请以管理员身份运行程序，或手动设置文件关联。")
            return False
        except Exception as e:
            QMessageBox.critical(None, "错误", f"设置文件关联失败：{str(e)}")
            return False
    
    def _register_prog_id(self, app_path: str, icon_path: str):
        """注册程序ID"""
        try:
            # 创建程序ID键
            with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, self.prog_id) as key:
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, self.app_description)
            
            # 设置图标
            if os.path.exists(icon_path):
                with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, f"{self.prog_id}\\DefaultIcon") as key:
                    winreg.SetValueEx(key, "", 0, winreg.REG_SZ, f'"{icon_path}",0')
            
            # 设置打开命令
            with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, f"{self.prog_id}\\shell\\open\\command") as key:
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, f'{app_path} "%1"')
                
        except Exception as e:
            raise Exception(f"注册程序ID失败: {e}")
    
    def _register_extension(self, extension: str, set_as_default: bool):
        """注册文件扩展名"""
        try:
            # 确保扩展名以点开头
            if not extension.startswith('.'):
                extension = '.' + extension
            
            if set_as_default:
                # 设置为默认程序（系统级别）
                with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, extension) as key:
                    winreg.SetValueEx(key, "", 0, winreg.REG_SZ, self.prog_id)
            
            # 添加到用户选择列表
            with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, f"{extension}\\OpenWithProgids") as key:
                winreg.SetValueEx(key, self.prog_id, 0, winreg.REG_NONE, b"")
                
        except Exception as e:
            raise Exception(f"注册扩展名 {extension} 失败: {e}")
    
    def _refresh_shell_associations(self):
        """刷新Shell文件关联"""
        try:
            # 通知系统文件关联已更改
            import ctypes
            from ctypes import wintypes
            
            SHCNE_ASSOCCHANGED = 0x08000000
            SHCNF_IDLIST = 0x0000
            
            ctypes.windll.shell32.SHChangeNotify(
                SHCNE_ASSOCCHANGED, SHCNF_IDLIST, None, None
            )
            
        except Exception as e:
            print(f"刷新Shell关联失败: {e}")
    
    def unregister_file_association(self, extensions: List[str]) -> bool:
        """取消文件关联"""
        if sys.platform != "win32" or winreg is None:
            return False
        
        # 使用统一的权限管理系统
        # 注册表操作需要管理员权限，检查 HKEY_CLASSES_ROOT 访问权限
        registry_paths = ["HKEY_CLASSES_ROOT"]  # 模拟需要权限的路径
        if not PermissionManager.request_admin_if_needed(registry_paths, "取消文件关联"):
            return False
        
        try:
            for ext in extensions:
                if not ext.startswith('.'):
                    ext = '.' + ext
                
                # 从OpenWithProgids中移除
                try:
                    with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, f"{ext}\\OpenWithProgids", 0, winreg.KEY_SET_VALUE) as key:
                        winreg.DeleteValue(key, self.prog_id)
                except FileNotFoundError:
                    pass  # 键不存在，忽略
                except OSError:
                    pass  # 值不存在，忽略
            
            # 刷新Shell关联
            self._refresh_shell_associations()
            return True
            
        except Exception as e:
            QMessageBox.critical(None, "错误", f"取消文件关联失败：{str(e)}")
            return False
    
    def check_association_status(self, extensions: List[str]) -> Dict[str, bool]:
        """检查文件关联状态"""
        status = {}
        
        if sys.platform != "win32" or winreg is None:
            for ext in extensions:
                status[ext] = False
            return status
        
        for ext in extensions:
            if not ext.startswith('.'):
                ext = '.' + ext
            
            try:
                # 检查是否在OpenWithProgids中
                with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, f"{ext}\\OpenWithProgids") as key:
                    try:
                        winreg.QueryValueEx(key, self.prog_id)
                        status[ext] = True
                    except FileNotFoundError:
                        status[ext] = False
            except FileNotFoundError:
                status[ext] = False
        
        return status
        
    def install_context_menu(self, menu_options: Dict[str, bool]) -> bool:
        """安装右键菜单"""
        if sys.platform != "win32" or winreg is None:
            QMessageBox.warning(None, "不支持", "右键菜单功能仅在Windows系统上可用")
            return False
        
        # 使用统一的权限管理系统
        # 注册表操作需要管理员权限，检查 HKEY_CLASSES_ROOT 访问权限
        registry_paths = ["HKEY_CLASSES_ROOT"]  # 模拟需要权限的路径
        if not PermissionManager.request_admin_if_needed(registry_paths, "安装右键菜单"):
            return False
        
        try:
            app_path = self.get_app_path()
            
            # 安装到所有文件的右键菜单
            self._install_shell_menu("*", menu_options, app_path)
            
            # 安装到文件夹的右键菜单
            self._install_shell_menu("Folder", menu_options, app_path)
            
            # 安装到文件夹背景的右键菜单
            self._install_shell_menu("Directory\\Background", menu_options, app_path)
            
            # 刷新Shell关联
            self._refresh_shell_associations()
            
            return True
            
        except PermissionError:
            QMessageBox.warning(None, "权限不足", 
                              "安装右键菜单需要管理员权限。\n"
                              "请以管理员身份运行程序。")
            return False
        except Exception as e:
            QMessageBox.critical(None, "错误", f"安装右键菜单失败：{str(e)}")
            return False
    
    def _install_shell_menu(self, target: str, menu_options: Dict[str, bool], app_path: str):
        """为指定目标安装Shell菜单"""
        try:
            # 检查是否有任何菜单项被启用
            enabled_items = [k for k, v in menu_options.items() if v]
            if not enabled_items:
                return
            
            # 创建主菜单项"GudaZip"，包含子菜单
            main_menu_key = f"{target}\\shell\\GudaZip"
            
            # 创建主菜单项
            with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, main_menu_key) as key:
                winreg.SetValueEx(key, "MUIVerb", 0, winreg.REG_SZ, "GudaZip")
                winreg.SetValueEx(key, "subcommands", 0, winreg.REG_SZ, "")  # 小写的subcommands，设置为空字符串启用shell子菜单
                
                # 设置图标
                app_exe = app_path.split('"')[1] if '"' in app_path else app_path.split()[0]
                winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, f'"{app_exe}",0')
            
            # 创建子菜单容器
            submenu_shell_key = f"{main_menu_key}\\shell"
            
            # 创建各个子菜单项
            if menu_options.get('add', False):
                self._create_submenu_item(submenu_shell_key, "add", "添加到压缩包", app_path, "--add")
            
            if menu_options.get('extract', False):
                self._create_submenu_item(submenu_shell_key, "extract", "解压到此处", app_path, "--extract-here")
            
            if menu_options.get('open', False):
                self._create_submenu_item(submenu_shell_key, "open", "用GudaZip打开", app_path, "--open")
            
            if menu_options.get('zip', False):
                self._create_submenu_item(submenu_shell_key, "zip", "压缩到.zip", app_path, "--compress-zip")
            
            if menu_options.get('7z', False):
                self._create_submenu_item(submenu_shell_key, "7z", "压缩到.7z", app_path, "--compress-7z")
                
        except Exception as e:
            raise Exception(f"为 {target} 安装Shell菜单失败: {e}")
    
    def _create_submenu_item(self, parent_key: str, item_id: str, display_name: str, app_path: str, command_arg: str):
        """在子菜单中创建菜单项"""
        try:
            item_key = f"{parent_key}\\{item_id}"
            with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, item_key) as key:
                # 设置默认值（这是菜单显示的文字）
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, display_name)
                
                # 设置图标
                app_exe = app_path.split('"')[1] if '"' in app_path else app_path.split()[0]
                winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, f'"{app_exe}",0')
            
            # 创建命令
            command_key = f"{item_key}\\command"
            with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, command_key) as key:
                command = f'{app_path} {command_arg} "%1"'
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, command)
                
        except Exception as e:
            raise Exception(f"创建子菜单项 {item_id} 失败: {e}")
    

    
    def uninstall_context_menu(self) -> bool:
        """卸载右键菜单"""
        if sys.platform != "win32" or winreg is None:
            return False
        
        # 使用统一的权限管理系统
        # 注册表操作需要管理员权限，检查 HKEY_CLASSES_ROOT 访问权限
        registry_paths = ["HKEY_CLASSES_ROOT"]  # 模拟需要权限的路径
        if not PermissionManager.request_admin_if_needed(registry_paths, "卸载右键菜单"):
            return False
        
        try:
            # 从各个位置删除菜单
            targets = ["*", "Folder", "Directory\\Background"]
            
            for target in targets:
                try:
                    # 删除主菜单项（可能包含子菜单）
                    menu_key = f"{target}\\shell\\GudaZip"
                    self._delete_registry_key_recursive(winreg.HKEY_CLASSES_ROOT, menu_key)
                except FileNotFoundError:
                    pass  # 键不存在，忽略
                except Exception as e:
                    print(f"删除 {target} 的GudaZip菜单失败: {e}")
                
                # 删除可能的单个菜单项
                single_menu_items = ["GudaZip_Add", "GudaZip_Extract", "GudaZip_Open", "GudaZip_Zip", "GudaZip_7z"]
                for item in single_menu_items:
                    try:
                        item_key = f"{target}\\shell\\{item}"
                        self._delete_registry_key_recursive(winreg.HKEY_CLASSES_ROOT, item_key)
                    except FileNotFoundError:
                        pass  # 键不存在，忽略
                    except Exception as e:
                        print(f"删除 {target} 的{item}菜单失败: {e}")
            
            # 刷新Shell关联
            self._refresh_shell_associations()
            
            return True
            
        except Exception as e:
            QMessageBox.critical(None, "错误", f"卸载右键菜单失败：{str(e)}")
            return False
    
    def _delete_registry_key_recursive(self, hkey, key_path: str):
        """递归删除注册表键"""
        try:
            with winreg.OpenKey(hkey, key_path, 0, winreg.KEY_ALL_ACCESS) as key:
                # 获取所有子键
                subkeys = []
                i = 0
                while True:
                    try:
                        subkey_name = winreg.EnumKey(key, i)
                        subkeys.append(subkey_name)
                        i += 1
                    except OSError:
                        break
                
                # 递归删除所有子键
                for subkey in subkeys:
                    self._delete_registry_key_recursive(hkey, f"{key_path}\\{subkey}")
            
            # 删除当前键
            winreg.DeleteKey(hkey, key_path)
            
        except FileNotFoundError:
            pass  # 键不存在，忽略
        except Exception as e:
            raise Exception(f"删除注册表键 {key_path} 失败: {e}")
    
    def check_context_menu_status(self) -> bool:
        """检查右键菜单安装状态"""
        if sys.platform != "win32" or winreg is None:
            return False
        
        try:
            # 检查是否存在主菜单项
            winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, "*\\shell\\GudaZip")
            return True
        except FileNotFoundError:
            return False
        except Exception:
            return False 