#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的右键菜单测试脚本
"""

import sys
import os

# Windows注册表模块
try:
    import winreg
except ImportError:
    winreg = None

def check_registry_key(key_path):
    """检查注册表键是否存在"""
    try:
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, key_path):
            return True
    except FileNotFoundError:
        return False
    except Exception as e:
        print(f"检查键 {key_path} 时出错: {e}")
        return False

def list_subkeys(key_path):
    """列出注册表键的子键"""
    try:
        subkeys = []
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, key_path) as key:
            i = 0
            while True:
                try:
                    subkey_name = winreg.EnumKey(key, i)
                    subkeys.append(subkey_name)
                    i += 1
                except OSError:
                    break
        return subkeys
    except FileNotFoundError:
        return []
    except Exception as e:
        print(f"列出子键失败: {e}")
        return []

def get_registry_value(key_path, value_name=""):
    """获取注册表值"""
    try:
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, key_path) as key:
            value, _ = winreg.QueryValueEx(key, value_name)
            return value
    except FileNotFoundError:
        return None
    except Exception as e:
        print(f"获取值失败: {e}")
        return None

def analyze_context_menu():
    """分析当前的右键菜单状态"""
    print("=== 分析右键菜单注册表状态 ===\n")
    
    # 检查主要目标
    targets = ["*", "Folder", "Directory\\Background"]
    
    for target in targets:
        print(f"--- 目标: {target} ---")
        
        # 检查GudaZip主菜单
        main_key = f"{target}\\shell\\GudaZip"
        exists = check_registry_key(main_key)
        print(f"主菜单存在: {exists}")
        
        if exists:
            # 获取主菜单信息
            name = get_registry_value(main_key, "")
            muiverb = get_registry_value(main_key, "MUIVerb")
            icon = get_registry_value(main_key, "Icon")
            print(f"  名称: {name}")
            print(f"  MUIVerb: {muiverb}")
            print(f"  图标: {icon}")
            
            # 检查是否有shell子键（子菜单）
            shell_key = f"{main_key}\\shell"
            shell_exists = check_registry_key(shell_key)
            print(f"  子菜单容器存在: {shell_exists}")
            
            if shell_exists:
                subkeys = list_subkeys(shell_key)
                print(f"  子菜单项: {subkeys}")
                
                for subkey in subkeys:
                    subkey_path = f"{shell_key}\\{subkey}"
                    sub_name = get_registry_value(subkey_path, "")
                    command_path = f"{subkey_path}\\command"
                    command = get_registry_value(command_path, "")
                    print(f"    {subkey}: {sub_name}")
                    print(f"      命令: {command}")
        
        # 检查独立菜单项
        single_items = ["GudaZip_Add", "GudaZip_Extract", "GudaZip_Open", "GudaZip_Zip", "GudaZip_7z"]
        single_found = []
        
        print(f"  独立菜单项:")
        for item in single_items:
            item_key = f"{target}\\shell\\{item}"
            if check_registry_key(item_key):
                name = get_registry_value(item_key, "")
                command_path = f"{item_key}\\command"
                command = get_registry_value(command_path, "")
                single_found.append(f"{item}: {name}")
                print(f"    ✓ {item}: {name}")
                print(f"      命令: {command}")
            else:
                print(f"    ✗ {item}: 不存在")
        
        if not single_found and not exists:
            print("  没有找到任何GudaZip菜单项")
        
        total_items = len(single_found) + (1 if exists else 0)
        print(f"  总计菜单项: {total_items}")
        
        print()

def main():
    """主函数"""
    if sys.platform != "win32" or winreg is None:
        print("此测试仅支持Windows系统")
        return
    
    print("=== GudaZip 右键菜单状态分析 ===\n")
    
    try:
        analyze_context_menu()
        
        print("=== 状态说明 ===")
        print("1. ✓ 表示菜单项存在且正常")
        print("2. ✗ 表示菜单项不存在")
        print("3. 当前使用独立菜单项模式（推荐）")
        print("4. 每个菜单项都是独立的，可直接点击使用")
        print("5. 如果看到旧的主菜单(GudaZip)，建议先清理再重新安装")
        
    except Exception as e:
        print(f"分析过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 