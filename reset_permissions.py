#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GudaZip 权限配置重置工具
用于重置用户的权限偏好设置
"""

import os
import sys


def main():
    """主函数"""
    print("=== GudaZip 权限配置重置工具 ===")
    print("")
    
    config_file = os.path.join(os.path.dirname(__file__), '.gudazip_config')
    
    if os.path.exists(config_file):
        try:
            # 读取当前配置
            with open(config_file, 'r', encoding='utf-8') as f:
                current_mode = f.read().strip()
            
            if current_mode == 'admin':
                print("🔒 当前配置：申请管理员权限（自动申请UAC权限）")
            elif current_mode == 'normal':
                print("🏠 当前配置：普通模式（默认，无需UAC权限）")
            else:
                print("⚠️  当前配置：未知模式")
            
            print("")
            choice = input("是否要重置权限配置？(y/N): ").lower().strip()
            
            if choice in ['y', 'yes', '是']:
                os.remove(config_file)
                print("✅ 权限配置已重置")
                print("💡 下次启动 GudaZip 时会询问是否需要管理员权限")
            else:
                print("❌ 已取消重置操作")
                
        except Exception as e:
            print(f"❌ 读取配置文件失败: {e}")
            
    else:
        print("ℹ️  没有找到权限配置文件")
        print("💡 程序将在下次启动时询问是否需要管理员权限")
    
    print("")
    print("按任意键退出...")
    input()


if __name__ == "__main__":
    main() 