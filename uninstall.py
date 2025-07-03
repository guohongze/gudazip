#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GudaZip 独立卸载脚本
用于完全卸载 GudaZip 及其所有组件
"""

import sys
import os
from pathlib import Path

# 添加项目路径到 Python 路径
project_root = Path(__file__).parent
src_path = project_root / "src"
if src_path.exists():
    sys.path.insert(0, str(src_path))

try:
    from gudazip.core.uninstaller import create_uninstaller
except ImportError as e:
    print(f"错误: 无法导入卸载模块: {e}")
    print("请确保在 GudaZip 项目目录中运行此脚本")
    sys.exit(1)


def main():
    """主函数"""
    print("GudaZip 卸载工具")
    print("=" * 50)
    
    # 检查是否在正确的目录
    if not (project_root / "src" / "gudazip").exists():
        print("错误: 请在 GudaZip 项目根目录中运行此脚本")
        sys.exit(1)
    
    # 询问用户确认
    print("\n⚠️  警告: 此操作将完全卸载 GudaZip 及其所有组件，包括:")
    print("   • 环境变量")
    print("   • 文件关联")
    print("   • 右键菜单")
    print("   • 配置文件")
    print("   • 安装目录（如果是打包版本）")
    
    response = input("\n确定要继续吗？(y/N): ").strip().lower()
    if response not in ['y', 'yes', '是']:
        print("卸载已取消")
        return
    
    # 询问是否删除安装目录
    remove_install_dir = False
    if getattr(sys, 'frozen', False):  # 打包版本
        response = input("\n是否删除安装目录？(y/N): ").strip().lower()
        remove_install_dir = response in ['y', 'yes', '是']
    else:
        print("\n检测到开发环境，将跳过安装目录删除")
    
    try:
        # 创建卸载器
        uninstaller = create_uninstaller()
        
        # 执行卸载
        result = uninstaller.uninstall_complete(remove_install_dir=remove_install_dir)
        
        # 显示结果
        if result["overall_success"]:
            print("\n🎉 卸载完成！")
            print("\n如果您遇到任何问题，请检查上述详细信息。")
        else:
            print("\n⚠️ 卸载过程中遇到一些问题，请查看详细信息。")
            print("\n您可能需要手动清理一些残留项目。")
        
        # 询问是否查看卸载状态
        response = input("\n是否检查卸载状态？(y/N): ").strip().lower()
        if response in ['y', 'yes', '是']:
            print("\n检查卸载状态...")
            status = uninstaller.check_uninstall_status()
            
            if status["all_clean"]:
                print("✅ 所有组件已成功清理")
            else:
                print("⚠️ 发现一些残留项目:")
                for component, details in status["details"].items():
                    if details["exists"]:
                        component_name = {
                            "environment_variables": "环境变量",
                            "file_associations": "文件关联",
                            "context_menus": "右键菜单",
                            "config_files": "配置文件",
                            "install_directory": "安装目录"
                        }.get(component, component)
                        print(f"  • {component_name}: 仍然存在")
        
    except Exception as e:
        print(f"\n❌ 卸载过程中发生错误: {e}")
        print("\n请尝试以管理员权限运行此脚本，或手动清理相关项目。")
        sys.exit(1)
    
    print("\n感谢您使用 GudaZip！")
    input("\n按 Enter 键退出...")


if __name__ == "__main__":
    main()