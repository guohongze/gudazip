#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
直接安装右键菜单脚本（绕过权限检查）
"""

import sys
import os
import winreg

def install_menu_direct():
    """直接安装右键菜单，绕过权限检查"""
    print("=== 直接安装GudaZip右键菜单 ===\n")
    
    # 获取正确的应用程序路径
    project_root = os.path.dirname(__file__)
    main_py = os.path.join(project_root, 'main.py')
    app_path = f'"{sys.executable}" "{main_py}"'
    
    print(f"应用程序路径: {app_path}")
    print(f"main.py存在: {os.path.exists(main_py)}")
    
    # 菜单选项
    menu_options = {
        'add': True,
        'extract': True,
        'open': True,
        'zip': True,
        '7z': True
    }
    
    try:
        # 先清理旧菜单
        print("\n1. 清理旧菜单...")
        targets = ["*", "Folder", "Directory\\Background"]
        
        for target in targets:
            try:
                menu_key = f"{target}\\shell\\GudaZip"
                winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, menu_key + "\\shell\\7z\\command")
                winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, menu_key + "\\shell\\7z")
                winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, menu_key + "\\shell\\add\\command")
                winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, menu_key + "\\shell\\add")
                winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, menu_key + "\\shell\\extract\\command")
                winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, menu_key + "\\shell\\extract")
                winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, menu_key + "\\shell\\open\\command")
                winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, menu_key + "\\shell\\open")
                winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, menu_key + "\\shell\\zip\\command")
                winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, menu_key + "\\shell\\zip")
                winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, menu_key + "\\shell")
                winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, menu_key)
                print(f"   清理 {target} 成功")
            except:
                pass
        
        # 重新安装菜单
        print("\n2. 重新安装菜单...")
        
        for target in targets:
            print(f"   安装到 {target}...")
            
            # 创建主菜单项
            main_menu_key = f"{target}\\shell\\GudaZip"
            with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, main_menu_key) as key:
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, "GudaZip")
                winreg.SetValueEx(key, "MUIVerb", 0, winreg.REG_SZ, "GudaZip")
                winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, f'"{sys.executable}",0')
            
            # 创建子菜单
            shell_key = f"{main_menu_key}\\shell"
            
            # 添加到压缩包
            if menu_options.get('add', False):
                item_key = f"{shell_key}\\add"
                with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, item_key) as key:
                    winreg.SetValueEx(key, "", 0, winreg.REG_SZ, "添加到压缩包")
                    winreg.SetValueEx(key, "MUIVerb", 0, winreg.REG_SZ, "添加到压缩包")
                    winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, f'"{sys.executable}",0')
                
                command_key = f"{item_key}\\command"
                with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, command_key) as key:
                    command = f'{app_path} --add "%1"'
                    winreg.SetValueEx(key, "", 0, winreg.REG_SZ, command)
            
            # 解压到此处
            if menu_options.get('extract', False):
                item_key = f"{shell_key}\\extract"
                with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, item_key) as key:
                    winreg.SetValueEx(key, "", 0, winreg.REG_SZ, "解压到此处")
                    winreg.SetValueEx(key, "MUIVerb", 0, winreg.REG_SZ, "解压到此处")
                    winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, f'"{sys.executable}",0')
                
                command_key = f"{item_key}\\command"
                with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, command_key) as key:
                    command = f'{app_path} --extract-here "%1"'
                    winreg.SetValueEx(key, "", 0, winreg.REG_SZ, command)
            
            # 用GudaZip打开
            if menu_options.get('open', False):
                item_key = f"{shell_key}\\open"
                with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, item_key) as key:
                    winreg.SetValueEx(key, "", 0, winreg.REG_SZ, "用GudaZip打开")
                    winreg.SetValueEx(key, "MUIVerb", 0, winreg.REG_SZ, "用GudaZip打开")
                    winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, f'"{sys.executable}",0')
                
                command_key = f"{item_key}\\command"
                with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, command_key) as key:
                    command = f'{app_path} --open "%1"'
                    winreg.SetValueEx(key, "", 0, winreg.REG_SZ, command)
            
            # 压缩到 zip
            if menu_options.get('zip', False):
                item_key = f"{shell_key}\\zip"
                with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, item_key) as key:
                    winreg.SetValueEx(key, "", 0, winreg.REG_SZ, "压缩到 {文件名}.zip")
                    winreg.SetValueEx(key, "MUIVerb", 0, winreg.REG_SZ, "压缩到 {文件名}.zip")
                    winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, f'"{sys.executable}",0')
                
                command_key = f"{item_key}\\command"
                with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, command_key) as key:
                    command = f'{app_path} --compress-zip "%1"'
                    winreg.SetValueEx(key, "", 0, winreg.REG_SZ, command)
            
            # 压缩到 7z
            if menu_options.get('7z', False):
                item_key = f"{shell_key}\\7z"
                with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, item_key) as key:
                    winreg.SetValueEx(key, "", 0, winreg.REG_SZ, "压缩到 {文件名}.7z")
                    winreg.SetValueEx(key, "MUIVerb", 0, winreg.REG_SZ, "压缩到 {文件名}.7z")
                    winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, f'"{sys.executable}",0')
                
                command_key = f"{item_key}\\command"
                with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, command_key) as key:
                    command = f'{app_path} --compress-7z "%1"'
                    winreg.SetValueEx(key, "", 0, winreg.REG_SZ, command)
        
        # 刷新Shell关联
        print("\n3. 刷新Shell关联...")
        import ctypes
        SHCNE_ASSOCCHANGED = 0x08000000
        SHCNF_IDLIST = 0x0000
        ctypes.windll.shell32.SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, None, None)
        
        print("\n=== 安装完成 ===")
        print("请检查右键菜单是否正常工作")
        print("现在所有命令都应该指向main.py")
        
    except Exception as e:
        print(f"安装失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if sys.platform != "win32":
        print("此脚本仅支持Windows系统")
        sys.exit(1)
    
    install_menu_direct() 