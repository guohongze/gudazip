#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
环境变量管理器
用于管理GudaZip的安装路径和资源路径环境变量
"""

import os
import sys
import winreg
from typing import Optional, Dict, Any
from pathlib import Path


class EnvironmentManager:
    """环境变量管理器"""
    
    def __init__(self):
        self.app_name = "GudaZip"
        self.env_vars = {
            "GUDAZIP_INSTALL_PATH": "GudaZip安装路径",
            "GUDAZIP_RESOURCES_PATH": "GudaZip资源路径",
            "GUDAZIP_ICONS_PATH": "GudaZip图标路径",
            "GUDAZIP_CONFIG_PATH": "GudaZip配置路径"
        }
    
    def get_install_path(self) -> str:
        """获取安装路径"""
        # 优先从环境变量获取
        install_path = os.environ.get('GUDAZIP_INSTALL_PATH')
        if install_path and os.path.exists(install_path):
            return install_path
        
        # 如果是打包的exe
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        
        # 开发环境，返回项目根目录
        return os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    
    def get_resources_path(self) -> str:
        """获取资源路径"""
        # 优先从环境变量获取
        resources_path = os.environ.get('GUDAZIP_RESOURCES_PATH')
        if resources_path and os.path.exists(resources_path):
            return resources_path
        
        # 基于安装路径计算
        install_path = self.get_install_path()
        return os.path.join(install_path, "resources")
    
    def get_icons_path(self) -> str:
        """获取图标路径"""
        # 优先从环境变量获取
        icons_path = os.environ.get('GUDAZIP_ICONS_PATH')
        if icons_path and os.path.exists(icons_path):
            return icons_path
        
        # 基于资源路径计算
        resources_path = self.get_resources_path()
        return os.path.join(resources_path, "icons")
    
    def get_config_path(self) -> str:
        """获取配置路径"""
        # 优先从环境变量获取
        config_path = os.environ.get('GUDAZIP_CONFIG_PATH')
        if config_path:
            return config_path
        
        # 默认使用AppData路径
        if os.name == 'nt':  # Windows
            return os.path.join(os.environ.get('APPDATA', ''), self.app_name, 'config')
        else:
            return os.path.join(os.path.expanduser("~"), f".{self.app_name.lower()}", "config")
    
    def get_app_executable_path(self) -> str:
        """获取应用程序可执行文件路径"""
        if getattr(sys, 'frozen', False):
            # 打包的exe
            return sys.executable
        else:
            # 开发环境 - 优先使用构建的exe文件
            install_path = self.get_install_path()
            exe_path = os.path.join(install_path, "build", "exe", "GudaZip.exe")
            if os.path.exists(exe_path):
                # 如果存在构建的exe，优先使用（用于文件关联）
                return exe_path
            
            # 否则回退到python脚本（用于开发调试）
            main_py = os.path.join(install_path, "main.py")
            if os.path.exists(main_py):
                return f'"{sys.executable}" "{main_py}"'
            else:
                return sys.executable
    
    def get_app_icon_path(self) -> str:
        """获取应用程序图标路径"""
        icons_path = self.get_icons_path()
        icon_file = os.path.join(icons_path, "app.ico")
        if os.path.exists(icon_file):
            return icon_file
        
        # 备选图标
        for icon_name in ["gudazip.ico", "app.png", "gudazip_32x32.png"]:
            icon_file = os.path.join(icons_path, icon_name)
            if os.path.exists(icon_file):
                return icon_file
        
        return ""
    
    def set_environment_variables(self, install_path: str) -> bool:
        """设置环境变量到注册表（用户级别）"""
        try:
            # 计算各个路径
            resources_path = os.path.join(install_path, "resources")
            icons_path = os.path.join(resources_path, "icons")
            config_path = self.get_config_path()  # 配置路径保持在AppData
            
            # 打开用户环境变量注册表键
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Environment",
                0,
                winreg.KEY_SET_VALUE
            ) as key:
                # 设置各个环境变量
                winreg.SetValueEx(key, "GUDAZIP_INSTALL_PATH", 0, winreg.REG_SZ, install_path)
                winreg.SetValueEx(key, "GUDAZIP_RESOURCES_PATH", 0, winreg.REG_SZ, resources_path)
                winreg.SetValueEx(key, "GUDAZIP_ICONS_PATH", 0, winreg.REG_SZ, icons_path)
                winreg.SetValueEx(key, "GUDAZIP_CONFIG_PATH", 0, winreg.REG_SZ, config_path)
            
            # 通知系统环境变量已更改
            import ctypes
            from ctypes import wintypes
            
            HWND_BROADCAST = 0xFFFF
            WM_SETTINGCHANGE = 0x001A
            SMTO_ABORTIFHUNG = 0x0002
            
            ctypes.windll.user32.SendMessageTimeoutW(
                HWND_BROADCAST,
                WM_SETTINGCHANGE,
                0,
                "Environment",
                SMTO_ABORTIFHUNG,
                5000,
                None
            )
            
            print(f"✅ 环境变量设置成功:")
            print(f"  GUDAZIP_INSTALL_PATH = {install_path}")
            print(f"  GUDAZIP_RESOURCES_PATH = {resources_path}")
            print(f"  GUDAZIP_ICONS_PATH = {icons_path}")
            print(f"  GUDAZIP_CONFIG_PATH = {config_path}")
            
            return True
            
        except Exception as e:
            print(f"❌ 设置环境变量失败: {e}")
            return False
    
    def remove_environment_variables(self) -> bool:
        """移除环境变量"""
        try:
            # 打开用户环境变量注册表键
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Environment",
                0,
                winreg.KEY_SET_VALUE
            ) as key:
                # 删除各个环境变量
                for env_var in self.env_vars.keys():
                    try:
                        winreg.DeleteValue(key, env_var)
                        print(f"✅ 已删除环境变量: {env_var}")
                    except FileNotFoundError:
                        print(f"⚠️ 环境变量不存在: {env_var}")
                    except Exception as e:
                        print(f"❌ 删除环境变量失败 {env_var}: {e}")
            
            # 通知系统环境变量已更改
            import ctypes
            
            HWND_BROADCAST = 0xFFFF
            WM_SETTINGCHANGE = 0x001A
            SMTO_ABORTIFHUNG = 0x0002
            
            ctypes.windll.user32.SendMessageTimeoutW(
                HWND_BROADCAST,
                WM_SETTINGCHANGE,
                0,
                "Environment",
                SMTO_ABORTIFHUNG,
                5000,
                None
            )
            
            return True
            
        except Exception as e:
            print(f"❌ 移除环境变量失败: {e}")
            return False
    
    def check_environment_variables(self) -> Dict[str, Any]:
        """检查环境变量状态"""
        result = {
            "all_set": True,
            "variables": {},
            "missing": [],
            "invalid_paths": []
        }
        
        for env_var, description in self.env_vars.items():
            value = os.environ.get(env_var)
            exists = value is not None
            valid_path = False
            
            if exists and env_var != "GUDAZIP_CONFIG_PATH":  # 配置路径可能不存在
                valid_path = os.path.exists(value)
                if not valid_path:
                    result["invalid_paths"].append(env_var)
            elif exists:
                valid_path = True  # 配置路径不需要预先存在
            
            result["variables"][env_var] = {
                "description": description,
                "value": value,
                "exists": exists,
                "valid_path": valid_path
            }
            
            if not exists:
                result["missing"].append(env_var)
                result["all_set"] = False
        
        return result
    
    def setup_development_environment(self) -> bool:
        """设置开发环境的环境变量"""
        # 获取项目根目录
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        return self.set_environment_variables(project_root)
    
    def get_paths_info(self) -> Dict[str, str]:
        """获取所有路径信息"""
        return {
            "install_path": self.get_install_path(),
            "resources_path": self.get_resources_path(),
            "icons_path": self.get_icons_path(),
            "config_path": self.get_config_path(),
            "executable_path": self.get_app_executable_path(),
            "icon_path": self.get_app_icon_path()
        }


# 全局实例
_environment_manager = None

def get_environment_manager() -> EnvironmentManager:
    """获取环境变量管理器单例"""
    global _environment_manager
    if _environment_manager is None:
        _environment_manager = EnvironmentManager()
    return _environment_manager