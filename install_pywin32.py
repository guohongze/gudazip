#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PyWin32自动安装脚本
用于解决GudaZip文件关联功能所需的PyWin32依赖问题
"""

import sys
import subprocess
import os
from pathlib import Path

def check_pywin32_availability():
    """检查PyWin32模块的可用性"""
    modules = {
        'win32api': False,
        'win32con': False,
        'win32shell': False,
        'win32shellcon': False
    }
    
    missing_modules = []
    
    for module_name in modules.keys():
        try:
            __import__(module_name)
            modules[module_name] = True
            print(f"✅ {module_name} 模块可用")
        except ImportError as e:
            modules[module_name] = False
            missing_modules.append(module_name)
            print(f"❌ {module_name} 模块缺失: {e}")
    
    return modules, missing_modules

def install_pywin32():
    """安装PyWin32模块"""
    print("正在安装PyWin32模块...")
    
    try:
        # 使用pip安装pywin32
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "pywin32>=306"],
            capture_output=True,
            text=True,
            check=True
        )
        
        print("✅ PyWin32安装成功")
        print("安装输出:")
        print(result.stdout)
        
        # 运行pywin32_postinstall.py脚本（如果存在）
        try:
            postinstall_result = subprocess.run(
                [sys.executable, "-m", "pywin32_postinstall", "-install"],
                capture_output=True,
                text=True,
                check=True
            )
            print("✅ PyWin32后安装配置完成")
            print(postinstall_result.stdout)
        except subprocess.CalledProcessError as e:
            print(f"⚠️ PyWin32后安装配置失败（这通常不影响基本功能）: {e}")
            print(f"错误输出: {e.stderr}")
        except FileNotFoundError:
            print("⚠️ 未找到pywin32_postinstall脚本（这通常不影响基本功能）")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ PyWin32安装失败: {e}")
        print(f"错误输出: {e.stderr}")
        return False
    except Exception as e:
        print(f"❌ 安装过程中发生异常: {e}")
        return False

def fix_file_associations():
    """修复文件关联（在PyWin32安装后）"""
    print("\n正在修复文件关联...")
    
    try:
        # 导入修复脚本
        fix_script_path = Path(__file__).parent / "fix_file_associations.py"
        
        if fix_script_path.exists():
            result = subprocess.run(
                [sys.executable, str(fix_script_path)],
                capture_output=True,
                text=True
            )
            
            print("文件关联修复输出:")
            print(result.stdout)
            
            if result.stderr:
                print("错误输出:")
                print(result.stderr)
                
            return result.returncode == 0
        else:
            print(f"❌ 未找到文件关联修复脚本: {fix_script_path}")
            return False
            
    except Exception as e:
        print(f"❌ 文件关联修复失败: {e}")
        return False

def main():
    """主函数"""
    print("=" * 60)
    print("GudaZip PyWin32 依赖安装工具")
    print("=" * 60)
    
    # 检查当前PyWin32状态
    print("\n1. 检查PyWin32模块状态...")
    modules, missing_modules = check_pywin32_availability()
    
    if not missing_modules:
        print("\n✅ 所有PyWin32模块都已可用，无需安装")
        return True
    
    print(f"\n发现缺失的模块: {', '.join(missing_modules)}")
    
    # 询问用户是否要安装
    try:
        response = input("\n是否要安装PyWin32模块？(y/n): ").strip().lower()
        if response not in ['y', 'yes', '是']:
            print("用户取消安装")
            return False
    except KeyboardInterrupt:
        print("\n用户取消安装")
        return False
    
    # 安装PyWin32
    print("\n2. 安装PyWin32模块...")
    if not install_pywin32():
        print("\n❌ PyWin32安装失败，请手动安装")
        print("手动安装命令: pip install pywin32>=306")
        return False
    
    # 重新检查安装结果
    print("\n3. 验证安装结果...")
    modules_after, missing_after = check_pywin32_availability()
    
    if missing_after:
        print(f"\n⚠️ 仍有模块缺失: {', '.join(missing_after)}")
        print("请尝试重启程序或手动安装PyWin32")
        return False
    
    print("\n✅ PyWin32安装验证成功")
    
    # 修复文件关联
    print("\n4. 修复文件关联...")
    if fix_file_associations():
        print("✅ 文件关联修复成功")
    else:
        print("⚠️ 文件关联修复失败，请在GudaZip中手动重新设置")
    
    print("\n=" * 60)
    print("安装完成！请重启GudaZip以使用文件关联功能")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n用户中断操作")
        sys.exit(1)
    except Exception as e:
        print(f"\n程序异常: {e}")
        sys.exit(1)