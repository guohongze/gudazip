#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试右键菜单顺序调整
验证"创建同名ZIP压缩包"是否已移到第二位
"""

import sys
import os

# 添加项目路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(project_root, 'src'))

from gudazip.core.file_association_manager import FileAssociationManager

def test_menu_order():
    """测试菜单顺序调整"""
    manager = FileAssociationManager()
    
    print("=== GudaZip 菜单顺序调整测试 ===")
    print("将'创建同名ZIP压缩包'移到第二位")
    print()
    
    # 检查当前状态
    current_status = manager.check_context_menu_status()
    print(f"当前右键菜单状态: {'已安装' if current_status else '未安装'}")
    
    # 如果已安装，先卸载旧菜单
    if current_status:
        print("\n正在卸载旧菜单...")
        if manager.uninstall_context_menu():
            print("✓ 旧菜单卸载成功")
        else:
            print("✗ 旧菜单卸载失败")
            return False
    
    # 安装调整顺序后的菜单
    print("\n正在安装调整顺序后的右键菜单...")
    menu_options = {
        'add': True,      # 添加到压缩包
        'extract': True,  # 解压到此处
        'open': True,     # 用GudaZip打开
        'zip': True,      # 创建同名ZIP压缩包
        '7z': True        # 创建同名7Z压缩包
    }
    
    if manager.install_context_menu(menu_options):
        print("✓ 调整顺序后的菜单安装成功！")
        return True
    else:
        print("✗ 菜单安装失败")
        return False

def show_expected_order():
    """显示预期的菜单顺序"""
    print("\n" + "="*50)
    print("📋 预期的菜单顺序")
    print("="*50)
    
    print("\n右键点击文件后应该看到：")
    print()
    print("  GudaZip ►")
    print("    1. 创建同名7Z压缩包   ✨")
    print("    2. 创建同名ZIP压缩包  🆕 (已移到第二位)")
    print("    3. 添加到压缩包")
    print("    4. 解压到此处")
    print("    5. 用GudaZip打开")
    print()
    
    print("🔧 技术实现:")
    print("   使用数字前缀控制注册表键名顺序:")
    print("   • 1_7z    → 创建同名7Z压缩包")
    print("   • 2_zip   → 创建同名ZIP压缩包")
    print("   • 3_add   → 添加到压缩包")
    print("   • 4_extract → 解压到此处")
    print("   • 5_open  → 用GudaZip打开")

def create_test_file():
    """创建一个测试文件"""
    print("\n=== 创建测试文件 ===")
    
    test_filename = "菜单顺序测试文件.txt"
    
    try:
        test_filepath = os.path.join(os.getcwd(), test_filename)
        with open(test_filepath, 'w', encoding='utf-8') as f:
            f.write("这是用于测试GudaZip右键菜单顺序的文件\n")
            f.write("请右键点击此文件来验证菜单顺序\n")
            f.write(f"文件路径: {test_filepath}\n")
            f.write("预期顺序:\n")
            f.write("1. 创建同名7Z压缩包\n")
            f.write("2. 创建同名ZIP压缩包 (新位置)\n")
            f.write("3. 添加到压缩包\n")
            f.write("4. 解压到此处\n")
            f.write("5. 用GudaZip打开\n")
        
        print(f"✓ 创建测试文件: {test_filename}")
        print(f"📁 文件位置: {os.getcwd()}")
        print()
        print("请右键点击这个文件来验证菜单顺序！")
        return test_filepath
        
    except Exception as e:
        print(f"✗ 创建测试文件失败: {e}")
        return None

if __name__ == "__main__":
    try:
        # 安装调整后的菜单
        if not test_menu_order():
            print("菜单安装失败，无法继续测试")
            sys.exit(1)
        
        # 显示预期顺序
        show_expected_order()
        
        # 创建测试文件
        create_file = input("\n是否创建测试文件来验证菜单顺序？(y/n): ").lower().strip()
        if create_file in ['y', 'yes', '是']:
            test_file = create_test_file()
            
            if test_file:
                print("\n⚠️  重要提示:")
                print("   • 如果菜单顺序没有更新，请运行 restart_explorer.bat")
                print("   • 或者手动重启Windows资源管理器")
                
                # 询问是否清理测试文件
                input("\n验证完成后按回车键继续...")
                
                cleanup = input("是否删除测试文件？(y/n): ").lower().strip()
                if cleanup in ['y', 'yes', '是']:
                    try:
                        os.remove(test_file)
                        print(f"✓ 已删除测试文件: {os.path.basename(test_file)}")
                    except Exception as e:
                        print(f"✗ 删除测试文件失败: {e}")
        
        print("\n🎉 菜单顺序调整完成！")
        print("'创建同名ZIP压缩包'现在应该显示在第二位。")
            
    except KeyboardInterrupt:
        print("\n测试被用户中断")
    except Exception as e:
        print(f"测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
    
    input("\n按回车键退出...") 