#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试修复后的右键菜单功能
"""

import sys
import os

# 添加项目路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(project_root, 'src'))

from gudazip.core.file_association_manager import FileAssociationManager

def test_fixed_submenu():
    """测试修复后的子菜单功能"""
    manager = FileAssociationManager()
    
    print("=== GudaZip 修复后菜单测试 ===")
    print("修复问题:")
    print("1. ✓ 修正了subcommands设置（小写）")
    print("2. ✓ 修正了create_archive参数顺序")
    print("3. ✓ 改进了菜单显示文字")
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
    
    # 安装修复后的子菜单
    print("\n正在安装修复后的子菜单...")
    menu_options = {
        'add': True,      # 添加到压缩包
        'extract': True,  # 解压到此处
        'open': True,     # 用GudaZip打开
        'zip': True,      # 创建同名ZIP压缩包
        '7z': True        # 创建同名7Z压缩包
    }
    
    if manager.install_context_menu(menu_options):
        print("✓ 修复后的子菜单安装成功！")
        print()
        print("=== 新的菜单结构 ===")
        print("右键菜单显示：")
        print("  GudaZip ►")
        print("    ├── 添加到压缩包")
        print("    ├── 解压到此处")
        print("    ├── 用GudaZip打开")
        print("    ├── 创建同名ZIP压缩包")
        print("    └── 创建同名7Z压缩包")
        print()
        print("=== 测试指南 ===")
        print("1. 右键点击任意文件（如test.txt）")
        print("2. 选择 'GudaZip' > '创建同名ZIP压缩包'")
        print("3. 应该会在同目录创建 test.zip 文件")
        print("4. 选择 'GudaZip' > '创建同名7Z压缩包'")
        print("5. 应该会在同目录创建 test.7z 文件")
        print()
        print("现在应该不会再出现路径拆分错误！")
    else:
        print("✗ 修复后的子菜单安装失败")

def create_test_files():
    """创建测试文件"""
    print("\n=== 创建测试文件 ===")
    
    test_files = [
        "测试文件.txt",
        "test file with spaces.txt",
        "简单文件.txt"
    ]
    
    for filename in test_files:
        try:
            filepath = os.path.join(os.getcwd(), filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"这是测试文件: {filename}\n")
                f.write("用于测试GudaZip右键菜单功能\n")
                f.write("文件路径解析修复测试\n")
            print(f"✓ 创建测试文件: {filename}")
        except Exception as e:
            print(f"✗ 创建文件 {filename} 失败: {e}")
    
    print()
    print("你现在可以右键点击这些测试文件来测试压缩功能！")

if __name__ == "__main__":
    try:
        test_fixed_submenu()
        
        create_files = input("\n是否创建测试文件用于验证？(y/n): ").lower().strip()
        if create_files in ['y', 'yes', '是']:
            create_test_files()
            
    except KeyboardInterrupt:
        print("\n测试被用户中断")
    except Exception as e:
        print(f"测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
    
    input("\n按回车键退出...") 