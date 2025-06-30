#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试子菜单结构的右键菜单功能
"""

import sys
import os

# 添加项目路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(project_root, 'src'))

from gudazip.core.file_association_manager import FileAssociationManager

def test_submenu():
    """测试子菜单功能"""
    manager = FileAssociationManager()
    
    print("=== GudaZip 子菜单测试 ===")
    print("这将测试新的折叠式子菜单结构")
    print("右键菜单将只显示一个'GudaZip'选项，悬停时展开子菜单")
    print()
    
    # 检查当前状态
    current_status = manager.check_context_menu_status()
    print(f"当前右键菜单状态: {'已安装' if current_status else '未安装'}")
    
    # 如果已安装，先卸载
    if current_status:
        print("\n正在卸载旧的右键菜单...")
        if manager.uninstall_context_menu():
            print("✓ 旧菜单卸载成功")
        else:
            print("✗ 旧菜单卸载失败")
            return
    
    # 安装新的子菜单结构
    print("\n正在安装新的子菜单结构...")
    menu_options = {
        'add': True,      # 添加到压缩包
        'extract': True,  # 解压到此处
        'open': True,     # 用GudaZip打开
        'zip': True,      # 压缩到.zip
        '7z': True        # 压缩到.7z
    }
    
    if manager.install_context_menu(menu_options):
        print("✓ 子菜单安装成功！")
        print("\n请测试以下内容：")
        print("1. 右键点击任意文件，应该只看到一个'GudaZip'菜单项")
        print("2. 鼠标悬停在'GudaZip'上，应该展开显示以下子菜单：")
        print("   - 添加到压缩包")
        print("   - 解压到此处")
        print("   - 用GudaZip打开")
        print("   - 压缩到.zip")
        print("   - 压缩到.7z")
        print("3. 在文件夹上右键也应该有相同的菜单")
        print("4. 在文件夹空白处右键也应该有相同的菜单")
        print("\n如果看到多个'GudaZip'相关的顶级菜单项，说明还需要调整！")
    else:
        print("✗ 子菜单安装失败")
        print("请检查是否有管理员权限")

if __name__ == "__main__":
    try:
        test_submenu()
    except KeyboardInterrupt:
        print("\n测试被用户中断")
    except Exception as e:
        print(f"测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
    
    input("\n按回车键退出...") 