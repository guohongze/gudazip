#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试修正后的子菜单结构
"""

import sys
import os
import winreg

# 添加项目路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(project_root, 'src'))

from gudazip.core.file_association_manager import FileAssociationManager

def check_registry_structure():
    """检查注册表结构是否正确"""
    print("=== 检查注册表结构 ===")
    
    try:
        # 检查主菜单项
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, "*\\shell\\GudaZip") as key:
            print("✓ 找到主菜单项: *\\shell\\GudaZip")
            
            # 检查MUIVerb
            try:
                mui_verb, _ = winreg.QueryValueEx(key, "MUIVerb")
                print(f"  MUIVerb: {mui_verb}")
            except FileNotFoundError:
                print("  ✗ 缺少MUIVerb")
            
            # 检查subcommands
            try:
                subcommands, _ = winreg.QueryValueEx(key, "subcommands")
                print(f"  subcommands: '{subcommands}'")
                if subcommands == "":
                    print("  ✓ subcommands设置正确（空字符串）")
                else:
                    print("  ✗ subcommands应该是空字符串")
            except FileNotFoundError:
                print("  ✗ 缺少subcommands")
            
            # 检查图标
            try:
                icon, _ = winreg.QueryValueEx(key, "Icon")
                print(f"  Icon: {icon}")
            except FileNotFoundError:
                print("  ! 缺少Icon（可选）")
        
        # 检查子菜单项
        submenu_items = ["add", "extract", "open", "zip", "7z"]
        for item in submenu_items:
            try:
                with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, f"*\\shell\\GudaZip\\shell\\{item}") as subkey:
                    print(f"✓ 找到子菜单项: {item}")
                    
                    # 检查显示名称
                    try:
                        default_name, _ = winreg.QueryValueEx(subkey, "")
                        print(f"    默认值: {default_name}")
                    except FileNotFoundError:
                        try:
                            mui_verb, _ = winreg.QueryValueEx(subkey, "MUIVerb")
                            print(f"    MUIVerb: {mui_verb}")
                        except FileNotFoundError:
                            print("    ✗ 缺少显示名称")
                    
                    # 检查命令
                    try:
                        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, f"*\\shell\\GudaZip\\shell\\{item}\\command") as cmd_key:
                            command, _ = winreg.QueryValueEx(cmd_key, "")
                            print(f"    命令: {command}")
                    except FileNotFoundError:
                        print(f"    ✗ 缺少命令定义")
                        
            except FileNotFoundError:
                print(f"✗ 未找到子菜单项: {item}")
    
    except FileNotFoundError:
        print("✗ 未找到主菜单项")
        return False
    
    return True

def test_corrected_submenu():
    """测试修正后的子菜单功能"""
    manager = FileAssociationManager()
    
    print("=== GudaZip 子菜单修正测试 ===")
    print("修正了subcommands设置，现在应该能正确显示子菜单")
    print()
    
    # 检查当前状态
    current_status = manager.check_context_menu_status()
    print(f"当前右键菜单状态: {'已安装' if current_status else '未安装'}")
    
    # 如果已安装，先卸载
    if current_status:
        print("\n正在卸载旧菜单...")
        if manager.uninstall_context_menu():
            print("✓ 旧菜单卸载成功")
        else:
            print("✗ 旧菜单卸载失败")
            return
    
    # 安装修正后的子菜单
    print("\n正在安装修正后的子菜单...")
    menu_options = {
        'add': True,      # 添加到压缩包
        'extract': True,  # 解压到此处
        'open': True,     # 用GudaZip打开
        'zip': True,      # 压缩到.zip
        '7z': True        # 压缩到.7z
    }
    
    if manager.install_context_menu(menu_options):
        print("✓ 子菜单安装成功！")
        print()
        
        # 检查注册表结构
        if check_registry_structure():
            print("\n=== 测试指南 ===")
            print("请测试以下内容：")
            print("1. 右键点击任意文件")
            print("2. 应该看到一个'GudaZip'菜单项")
            print("3. 鼠标悬停在'GudaZip'上")
            print("4. 应该展开显示子菜单：")
            print("   - 添加到压缩包")
            print("   - 解压到此处")
            print("   - 用GudaZip打开")
            print("   - 压缩到.zip")
            print("   - 压缩到.7z")
            print()
            print("如果子菜单仍然不出现，可能需要：")
            print("- 重启Windows资源管理器")
            print("- 或者重启计算机")
        else:
            print("\n✗ 注册表结构检查失败")
    else:
        print("✗ 子菜单安装失败")

if __name__ == "__main__":
    try:
        test_corrected_submenu()
    except KeyboardInterrupt:
        print("\n测试被用户中断")
    except Exception as e:
        print(f"测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
    
    input("\n按回车键退出...") 