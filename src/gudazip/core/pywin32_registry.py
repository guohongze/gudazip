#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安全的PyWin32注册表封装
使用Shell接口而非直接注册表操作，避免对系统对象的影响
"""

import sys
import os
from typing import Optional, Dict, List, Any
import ctypes  # 用于Shell刷新备用实现

# 分别检查PyWin32各个模块的可用性
PYWIN32_MODULES = {}
import_errors = []

try:
    import win32api
    PYWIN32_MODULES['win32api'] = True
except ImportError as e:
    PYWIN32_MODULES['win32api'] = False
    import_errors.append(f"win32api: {e}")

try:
    import win32con
    PYWIN32_MODULES['win32con'] = True
except ImportError as e:
    PYWIN32_MODULES['win32con'] = False
    import_errors.append(f"win32con: {e}")

try:
    from win32com.shell import shell as win32shell
    from win32com.shell.shell import SHChangeNotify
    PYWIN32_MODULES['win32shell'] = True
except ImportError as e:
    PYWIN32_MODULES['win32shell'] = False
    import_errors.append(f"win32shell: {e}")

try:
    from win32com.shell import shellcon as win32shellcon
    PYWIN32_MODULES['win32shellcon'] = True
except ImportError as e:
    PYWIN32_MODULES['win32shellcon'] = False
    import_errors.append(f"win32shellcon: {e}")

# 备用常量（在缺少win32shellcon时使用）
SHCNE_ASSOCCHANGED = 0x08000000  # 文件关联更改
SHCNF_IDLIST = 0x0000            # 参数类型

# 只要基础模块可用就认为部分可用
PYWIN32_AVAILABLE = PYWIN32_MODULES['win32api'] and PYWIN32_MODULES['win32con']

if not PYWIN32_AVAILABLE:
    print(f"PyWin32基础模块不可用: {import_errors}")
elif import_errors:
    print(f"PyWin32部分模块不可用: {import_errors}")
    print("将使用基础功能，Shell刷新功能可能不可用。")


class PyWin32Registry:
    """安全的PyWin32注册表封装类"""
    
    def __init__(self):
        self.available = PYWIN32_AVAILABLE
        
    def is_available(self) -> bool:
        """检查PyWin32是否可用"""
        return self.available
    
    def get_module_status(self) -> Dict[str, Any]:
        """获取PyWin32各模块的详细状态"""
        return {
            'available': self.available,
            'modules': PYWIN32_MODULES.copy(),
            'basic_functions': PYWIN32_MODULES.get('win32api', False) and PYWIN32_MODULES.get('win32con', False),
            'shell_functions': PYWIN32_MODULES.get('win32shell', False) and PYWIN32_MODULES.get('win32shellcon', False),
            'missing_modules': [module for module, available in PYWIN32_MODULES.items() if not available]
        }
    
    def get_reg_none(self):
        """获取REG_NONE类型"""
        if self.available:
            return win32con.REG_NONE
        return None
    
    def get_hkey_classes_root(self):
        """获取HKEY_CLASSES_ROOT句柄"""
        if self.available:
            return win32con.HKEY_CLASSES_ROOT
        return None
    
    def refresh_shell(self):
        """刷新Shell关联（安全方式）"""
        if not self.available:
            return False
        
        # 如果Shell模块可用，优先使用PyWin32提供的接口
        if PYWIN32_MODULES.get('win32shell', False) and PYWIN32_MODULES.get('win32shellcon', False):
            try:
                SHChangeNotify(
                    win32shellcon.SHCNE_ASSOCCHANGED,
                    win32shellcon.SHCNF_IDLIST,
                    None,
                    None
                )
                return True
            except Exception as e:
                print(f"刷新Shell关联失败(PyWin32): {e}")

        # 如果缺少win32shell模块，则使用ctypes直接调用Shell32.dll
        try:
            ctypes.windll.shell32.SHChangeNotify(
                SHCNE_ASSOCCHANGED,
                SHCNF_IDLIST,
                None,
                None
            )
            print("使用ctypes调用SHChangeNotify完成Shell刷新")
            return True
        except Exception as e:
            print(f"刷新Shell关联失败(ctypes): {e}")
            return False
    
    def register_file_association_safe(self, extension: str, prog_id: str, 
                                     description: str, icon_path: str, 
                                     command_path: str) -> bool:
        """
        安全地注册文件关联
        只针对特定文件扩展名，避免影响系统对象
        """
        if not self.available:
            return False
        
        try:
            # 使用用户级别注册表，避免系统级别影响
            
            # 注册文件类型到用户配置
            reg_key = f"SOFTWARE\\Classes\\{extension}"
            
            # 使用win32api而非直接winreg操作
            try:
                win32api.RegCreateKey(win32con.HKEY_CURRENT_USER, reg_key)
                win32api.RegSetValue(
                    win32con.HKEY_CURRENT_USER, 
                    reg_key, 
                    win32con.REG_SZ, 
                    prog_id
                )
                
                # 注册程序ID
                prog_key = f"SOFTWARE\\Classes\\{prog_id}"
                win32api.RegCreateKey(win32con.HKEY_CURRENT_USER, prog_key)
                win32api.RegSetValue(
                    win32con.HKEY_CURRENT_USER, 
                    prog_key, 
                    win32con.REG_SZ, 
                    description
                )
                
                # 注册图标
                if icon_path and os.path.exists(icon_path):
                    icon_key = f"{prog_key}\\DefaultIcon"
                    win32api.RegCreateKey(win32con.HKEY_CURRENT_USER, icon_key)
                    win32api.RegSetValue(
                        win32con.HKEY_CURRENT_USER, 
                        icon_key, 
                        win32con.REG_SZ, 
                        f'"{icon_path}",0'
                    )
                
                # 注册打开命令
                command_key = f"{prog_key}\\shell\\open\\command"
                win32api.RegCreateKey(win32con.HKEY_CURRENT_USER, command_key)
                win32api.RegSetValue(
                    win32con.HKEY_CURRENT_USER, 
                    command_key, 
                    win32con.REG_SZ, 
                    f'{command_path} "%1"'
                )
                
                return True
                
            except Exception as e:
                print(f"注册文件关联失败 {extension}: {e}")
                return False
                
        except Exception as e:
            print(f"文件关联操作失败: {e}")
            return False
    
    def unregister_file_association_safe(self, extension: str, prog_id: str) -> bool:
        """
        安全地取消文件关联
        """
        if not self.available:
            return False
        
        try:
            # 删除用户级别的文件关联
            reg_key = f"SOFTWARE\\Classes\\{extension}"
            try:
                win32api.RegDeleteKey(win32con.HKEY_CURRENT_USER, reg_key)
            except:
                pass  # 键可能不存在
            
            # 删除程序ID
            prog_key = f"SOFTWARE\\Classes\\{prog_id}"
            try:
                self._delete_registry_tree(win32con.HKEY_CURRENT_USER, prog_key)
            except:
                pass  # 键可能不存在
            
            return True
            
        except Exception as e:
            print(f"取消文件关联失败: {e}")
            return False
    
    def create_context_menu_safe(self, file_extensions: List[str], 
                                menu_items: Dict[str, Dict[str, str]]) -> bool:
        """
        安全地创建右键菜单
        只针对特定文件类型，避免影响系统对象
        """
        if not self.available:
            return False
        
        try:
            success_count = 0
            
            for extension in file_extensions:
                for menu_id, menu_data in menu_items.items():
                    display_name = menu_data.get('display_name', menu_id)
                    command = menu_data.get('command', '')
                    icon_path = menu_data.get('icon_path', '')
                    
                    if self._create_file_type_context_menu(
                        extension, menu_id, display_name, command, icon_path
                    ):
                        success_count += 1
            
            return success_count > 0
            
        except Exception as e:
            print(f"创建右键菜单失败: {e}")
            return False
    
    def _create_file_type_context_menu(self, extension: str, menu_id: str, 
                                     display_name: str, command: str, 
                                     icon_path: str = "") -> bool:
        """为特定文件类型创建右键菜单项"""
        try:
            # 可能需要写入多个位置以确保 Explorer 识别：
            # 1. 扩展名键           (.zip)
            # 2. SystemFileAssociations 键 (.zip)
            # 3. ProgID 键            (如 CompressedFolder)

            target_keys: List[str] = []

            # 扩展名键
            target_keys.append(f"SOFTWARE\\Classes\\{extension}\\shell\\{menu_id}")

            # SystemFileAssociations 键
            target_keys.append(f"SOFTWARE\\Classes\\SystemFileAssociations\\{extension}\\shell\\{menu_id}")

            # ProgID 键（如果可获取）
            try:
                prog_id = win32api.RegQueryValue(win32con.HKEY_CLASSES_ROOT, extension)
                if prog_id:
                    target_keys.append(f"SOFTWARE\\Classes\\{prog_id}\\shell\\{menu_id}")
            except Exception:
                pass

            created_any = False

            for menu_key in target_keys:
                try:
                    win32api.RegCreateKey(win32con.HKEY_CURRENT_USER, menu_key)
                    win32api.RegSetValue(
                        win32con.HKEY_CURRENT_USER,
                        menu_key,
                        win32con.REG_SZ,
                        display_name
                    )

                    # 设置图标
                    if icon_path and os.path.exists(icon_path):
                        key_handle = win32api.RegOpenKeyEx(
                            win32con.HKEY_CURRENT_USER,
                            menu_key,
                            0,
                            win32con.KEY_SET_VALUE
                        )
                        win32api.RegSetValueEx(
                            key_handle,
                            "Icon",
                            0,
                            win32con.REG_SZ,
                            f"{icon_path},0"
                        )
                        win32api.RegCloseKey(key_handle)

                    # 创建命令子键
                    command_key = f"{menu_key}\\command"
                    win32api.RegCreateKey(win32con.HKEY_CURRENT_USER, command_key)
                    win32api.RegSetValue(
                        win32con.HKEY_CURRENT_USER,
                        command_key,
                        win32con.REG_SZ,
                        command
                    )

                    created_any = True
                except Exception as e:
                    print(f"创建菜单失败 {menu_key}: {e}")

            return created_any
            
        except Exception as e:
            print(f"创建文件类型右键菜单失败 {extension}\\{menu_id}: {e}")
            return False
    
    def remove_context_menu_safe(self, file_extensions: List[str], 
                                menu_ids: List[str]) -> bool:
        """
        安全地移除右键菜单
        """
        if not self.available:
            return False
        
        try:
            for extension in file_extensions:
                # 构造所有可能路径
                keys_to_remove: List[str] = []
                keys_to_remove.append(f"SOFTWARE\\Classes\\{extension}\\shell")
                keys_to_remove.append(f"SOFTWARE\\Classes\\SystemFileAssociations\\{extension}\\shell")

                try:
                    prog_id = win32api.RegQueryValue(win32con.HKEY_CLASSES_ROOT, extension)
                    if prog_id:
                        keys_to_remove.append(f"SOFTWARE\\Classes\\{prog_id}\\shell")
                except Exception:
                    pass

                for base_key in keys_to_remove:
                    for menu_id in menu_ids:
                        menu_key = f"{base_key}\\{menu_id}"
                        try:
                            self._delete_registry_tree(win32con.HKEY_CURRENT_USER, menu_key)
                        except:
                            pass  # 键可能不存在
            
            return True
            
        except Exception as e:
            print(f"移除右键菜单失败: {e}")
            return False
    
    def _delete_registry_tree(self, hkey, key_path: str):
        """递归删除注册表树"""
        try:
            # 打开键
            key = win32api.RegOpenKeyEx(hkey, key_path, 0, win32con.KEY_ALL_ACCESS)
            
            # 获取子键数量
            try:
                subkey_count = win32api.RegQueryInfoKey(key)[0]
                
                # 删除所有子键
                for i in range(subkey_count):
                    subkey_name = win32api.RegEnumKey(key, 0)  # 总是删除第一个
                    self._delete_registry_tree(hkey, f"{key_path}\\{subkey_name}")
                    
            except:
                pass
            
            # 关闭键
            win32api.RegCloseKey(key)
            
            # 删除键本身
            win32api.RegDeleteKey(hkey, key_path)
            
        except Exception as e:
            print(f"删除注册表树失败 {key_path}: {e}")
    
    def check_file_association(self, extension: str, prog_id: str) -> bool:
        """检查文件关联状态"""
        if not self.available:
            return False
        
        try:
            reg_key = f"SOFTWARE\\Classes\\{extension}"
            current_prog_id = win32api.RegQueryValue(win32con.HKEY_CURRENT_USER, reg_key)
            return current_prog_id == prog_id
        except:
            return False
    
    def list_context_menus(self, extension: str) -> List[str]:
        """列出文件类型的右键菜单项"""
        if not self.available:
            return []
        
        try:
            shell_key = f"SOFTWARE\\Classes\\{extension}\\shell"
            key = win32api.RegOpenKeyEx(win32con.HKEY_CURRENT_USER, shell_key, 0, win32con.KEY_READ)
            
            menus = []
            try:
                i = 0
                while True:
                    menu_name = win32api.RegEnumKey(key, i)
                    menus.append(menu_name)
                    i += 1
            except:
                pass  # 没有更多子键
            
            win32api.RegCloseKey(key)
            return menus
            
        except:
            return []

    # 兼容旧接口的方法（空实现，避免报错）
    def create_key_and_set_value(self, *args, **kwargs):
        """兼容方法：不再直接操作注册表"""
        return False
    
    def delete_value(self, *args, **kwargs):
        """兼容方法：不再直接操作注册表"""
        return False
    
    def query_value(self, *args, **kwargs):
        """兼容方法：不再直接操作注册表"""
        return None
    
    def create_context_menu_item(self, *args, **kwargs):
        """兼容方法：不再直接操作注册表"""
        return False
    
    def remove_context_menu_item(self, *args, **kwargs):
        """兼容方法：不再直接操作注册表"""
        return False
    
    def delete_key(self, *args, **kwargs):
        """兼容方法：不再直接操作注册表"""
        return False
    
    def key_exists(self, *args, **kwargs):
        """兼容方法：不再直接操作注册表"""
        return False
    
    def create_context_menu_for_files_and_folders(self, targets: List[str], 
                                                 menu_items: Dict[str, Dict[str, str]]) -> bool:
        """
        为普通文件和文件夹创建压缩相关的右键菜单
        targets: ["*", "Directory"]（不包括Directory\\Background）
        """
        if not self.available:
            return False
        
        try:
            success_count = 0
            
            for target in targets:
                for menu_id, menu_data in menu_items.items():
                    display_name = menu_data.get('display_name', menu_id)
                    command = menu_data.get('command', '')
                    icon_path = menu_data.get('icon_path', '')
                    
                    if self._create_general_context_menu(
                        target, menu_id, display_name, command, icon_path
                    ):
                        success_count += 1
            
            return success_count > 0
            
        except Exception as e:
            print(f"创建文件/文件夹右键菜单失败: {e}")
            return False
    
    def _create_general_context_menu(self, target: str, menu_id: str, 
                                   display_name: str, command: str, 
                                   icon_path: str = "") -> bool:
        """为普通文件/文件夹创建右键菜单项"""
        try:
            # 为普通文件和文件夹创建菜单，使用HKEY_CURRENT_USER
            menu_key = f"SOFTWARE\\Classes\\{target}\\shell\\{menu_id}"
            
            # 创建菜单项主键
            win32api.RegCreateKey(win32con.HKEY_CURRENT_USER, menu_key)
            win32api.RegSetValue(
                win32con.HKEY_CURRENT_USER,
                menu_key,
                win32con.REG_SZ,
                display_name
            )
            
            # 设置图标
            if icon_path and os.path.exists(icon_path):
                key_handle = win32api.RegOpenKeyEx(
                    win32con.HKEY_CURRENT_USER,
                    menu_key,
                    0,
                    win32con.KEY_SET_VALUE
                )
                win32api.RegSetValueEx(
                    key_handle,
                    "Icon",
                    0,
                    win32con.REG_SZ,
                    f"{icon_path},0"
                )
                win32api.RegCloseKey(key_handle)
            
            # 创建命令子键
            command_key = f"{menu_key}\\command"
            win32api.RegCreateKey(win32con.HKEY_CURRENT_USER, command_key)
            win32api.RegSetValue(
                win32con.HKEY_CURRENT_USER,
                command_key,
                win32con.REG_SZ,
                command
            )
            
            print(f"✅ 创建菜单成功: {target}\\shell\\{menu_id}")
            return True
            
        except Exception as e:
            print(f"创建菜单失败 {target}\\{menu_id}: {e}")
            return False
    
    def remove_context_menu_for_files_and_folders(self, targets: List[str], 
                                                 menu_ids: List[str]) -> bool:
        """
        移除普通文件和文件夹的右键菜单
        """
        if not self.available:
            return False
        
        try:
            success_count = 0
            
            for target in targets:
                for menu_id in menu_ids:
                    menu_key = f"SOFTWARE\\Classes\\{target}\\shell\\{menu_id}"
                    try:
                        self._delete_registry_tree(win32con.HKEY_CURRENT_USER, menu_key)
                        success_count += 1
                        print(f"✅ 移除菜单成功: {target}\\shell\\{menu_id}")
                    except Exception as e:
                        print(f"移除菜单失败 {target}\\{menu_id}: {e}")
            
            return success_count > 0
            
        except Exception as e:
            print(f"移除文件/文件夹右键菜单失败: {e}")
            return False
    
    def check_general_context_menu(self, target: str, menu_id: str) -> bool:
        """检查普通文件/文件夹的右键菜单是否存在"""
        if not self.available:
            return False
        
        try:
            menu_key = f"SOFTWARE\\Classes\\{target}\\shell\\{menu_id}"
            try:
                win32api.RegOpenKeyEx(
                    win32con.HKEY_CURRENT_USER,
                    menu_key,
                    0,
                    win32con.KEY_READ
                ).Close()
                return True
            except FileNotFoundError:
                return False
        except Exception as e:
            print(f"检查菜单状态失败 {target}\\{menu_id}: {e}")
            return False