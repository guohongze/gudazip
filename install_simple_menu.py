#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安装简单独立菜单项的脚本
"""

import sys
import os
import winreg

def clean_old_menus():
    """清理所有旧菜单"""
    print("1. 清理旧菜单...")
    targets = ["*", "Folder", "Directory\\Background"]
    
    # 要清理的菜单项
    all_menu_items = [
        "GudaZip",  # 旧的主菜单
        "GudaZip_Add", "GudaZip_Extract", "GudaZip_Open", 
        "GudaZip_Zip", "GudaZip_7z"  # 独立菜单项
    ]
    
    for target in targets:
        for menu_item in all_menu_items:
            try:
                # 删除可能的子菜单结构
                try:
                    menu_key = f"{target}\\shell\\{menu_item}"
                    # 尝试删除shell子键下的所有内容
                    shell_key = f"{menu_key}\\shell"
                    
                    # 删除子菜单项
                    submenus = ["add", "extract", "open", "zip", "7z"]
                    for submenu in submenus:
                        try:
                            winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, f"{shell_key}\\{submenu}\\command")
                            winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, f"{shell_key}\\{submenu}")
                        except:
                            pass
                    
                    # 删除shell键本身
                    try:
                        winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, shell_key)
                    except:
                        pass
                        
                except:
                    pass
                
                # 删除command键
                try:
                    winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, f"{target}\\shell\\{menu_item}\\command")
                except:
                    pass
                
                # 删除主键
                try:
                    winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, f"{target}\\shell\\{menu_item}")
                    print(f"   清理 {target}\\{menu_item} 成功")
                except:
                    pass
            except Exception as e:
                print(f"   清理 {target}\\{menu_item} 失败: {e}")

def create_menu_item(target, menu_id, display_name, app_path, command_arg):
    """创建单个菜单项"""
    try:
        # 创建菜单项键
        item_key = f"{target}\\shell\\{menu_id}"
        with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, item_key) as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, display_name)
            winreg.SetValueEx(key, "MUIVerb", 0, winreg.REG_SZ, display_name)
            
            # 设置图标
            app_exe = app_path.split('"')[1] if '"' in app_path else app_path.split()[0]
            winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, f'"{app_exe}",0')
        
        # 创建命令
        command_key = f"{item_key}\\command"
        with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, command_key) as key:
            command = f'{app_path} {command_arg} "%1"'
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, command)
            
        print(f"   创建菜单项 {menu_id}: {display_name}")
        return True
        
    except Exception as e:
        print(f"   创建菜单项 {menu_id} 失败: {e}")
        return False

def install_simple_menus():
    """安装简单的独立菜单项"""
    print("=== 安装GudaZip独立菜单项 ===\n")
    
    # 获取应用程序路径
    project_root = os.path.dirname(__file__)
    main_py = os.path.join(project_root, 'main.py')
    app_path = f'"{sys.executable}" "{main_py}"'
    
    print(f"应用程序路径: {app_path}")
    print(f"main.py存在: {os.path.exists(main_py)}\n")
    
    try:
        # 清理旧菜单
        clean_old_menus()
        
        # 安装新菜单
        print("\n2. 安装新菜单...")
        targets = ["*", "Folder", "Directory\\Background"]
        
        # 菜单项定义
        menu_items = [
            ("GudaZip_Add", "GudaZip - 添加到压缩包", "--add"),
            ("GudaZip_Extract", "GudaZip - 解压到此处", "--extract-here"),
            ("GudaZip_Open", "GudaZip - 打开压缩包", "--open"),
            ("GudaZip_Zip", "GudaZip - 压缩为ZIP", "--compress-zip"),
            ("GudaZip_7z", "GudaZip - 压缩为7Z", "--compress-7z")
        ]
        
        success_count = 0
        total_count = 0
        
        for target in targets:
            print(f"\n   安装到 {target}:")
            for menu_id, display_name, command_arg in menu_items:
                if create_menu_item(target, menu_id, display_name, app_path, command_arg):
                    success_count += 1
                total_count += 1
        
        # 刷新Shell关联
        print("\n3. 刷新Shell关联...")
        import ctypes
        SHCNE_ASSOCCHANGED = 0x08000000
        SHCNF_IDLIST = 0x0000
        ctypes.windll.shell32.SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, None, None)
        
        print(f"\n=== 安装完成 ===")
        print(f"成功: {success_count}/{total_count}")
        print("\n现在右键菜单应该显示5个独立的GudaZip菜单项")
        print("每个菜单项都可以直接点击，不需要子菜单")
        
    except Exception as e:
        print(f"\n安装失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if sys.platform != "win32":
        print("此脚本仅支持Windows系统")
        sys.exit(1)
    
    install_simple_menus() 