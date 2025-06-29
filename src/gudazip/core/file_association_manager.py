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


class FileAssociationManager:
    """文件关联管理器"""
    
    def __init__(self):
        self.app_name = "GudaZip"
        self.app_description = "GudaZip 压缩管理器"
        self.prog_id = "GudaZip.Archive"
        
    def get_app_path(self) -> str:
        """获取应用程序路径"""
        if getattr(sys, 'frozen', False):
            # 如果是打包的exe文件
            return sys.executable
        else:
            # 如果是Python脚本
            return f'"{sys.executable}" "{os.path.abspath(sys.argv[0])}"'
    
    def is_admin(self) -> bool:
        """检查是否有管理员权限"""
        try:
            return os.getuid() == 0
        except AttributeError:
            # Windows系统
            try:
                import ctypes
                return ctypes.windll.shell32.IsUserAnAdmin() != 0
            except:
                return False
    
    def request_admin_privileges(self) -> bool:
        """请求管理员权限"""
        if sys.platform != "win32":
            return False
            
        try:
            import ctypes
            if ctypes.windll.shell32.IsUserAnAdmin():
                return True
            else:
                # 重新以管理员权限启动
                ctypes.windll.shell32.ShellExecuteW(
                    None, "runas", sys.executable, " ".join(sys.argv), None, 1
                )
                return False
        except Exception as e:
            print(f"请求管理员权限失败: {e}")
            return False
    
    def register_file_association(self, extensions: List[str], set_as_default: bool = False) -> bool:
        """注册文件关联"""
        if sys.platform != "win32" or winreg is None:
            QMessageBox.warning(None, "不支持", "文件关联功能仅在Windows系统上可用")
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