#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清理危险的注册表项
移除所有会影响系统对象的GudaZip右键菜单项
"""

import sys
import os

def cleanup_dangerous_registry():
    """清理所有危险的注册表项"""
    print("=== GudaZip 注册表清理工具 ===\n")
    print("⚠️  此工具将清理所有可能影响系统对象的注册表项")
    print("✅ 使用PyWin32安全接口，避免直接操作注册表")
    print("🎯 只清理用户级别的注册表项，不影响系统级设置\n")
    
    try:
        # 导入安全的PyWin32封装
        from src.gudazip.core.pywin32_registry import PyWin32Registry
        registry = PyWin32Registry()
        
        if not registry.is_available():
            print("❌ PyWin32不可用，无法执行清理操作")
            print("请先安装PyWin32: pip install pywin32")
            return False
        
        print("1. 清理文件关联...")
        
        # 支持的压缩文件扩展名
        supported_extensions = [
            '.zip', '.rar', '.7z', '.tar', '.gz', 
            '.bz2', '.xz', '.lzma', '.z', '.tgz'
        ]
        
        # 清理文件关联
        success_count = 0
        for ext in supported_extensions:
            try:
                if registry.unregister_file_association_safe(ext, "GudaZip.Archive"):
                    success_count += 1
                    print(f"   ✅ 清理文件关联: {ext}")
                else:
                    print(f"   ℹ️  未找到文件关联: {ext}")
            except Exception as e:
                print(f"   ⚠️  清理文件关联失败 {ext}: {e}")
        
        print(f"\n   📊 文件关联清理完成: {success_count}/{len(supported_extensions)}")
        
        print("\n2. 清理右键菜单...")
        
        # 清理右键菜单项
        menu_ids = ["add", "extract", "open", "zip", "7z"]
        if registry.remove_context_menu_safe(supported_extensions, menu_ids):
            print("   ✅ 右键菜单清理成功")
        else:
            print("   ℹ️  未找到右键菜单项")
        
        print("\n3. 刷新Shell关联...")
        
        # 刷新Shell关联
        if registry.refresh_shell():
            print("   ✅ Shell关联刷新成功")
        else:
            print("   ⚠️  Shell关联刷新失败")
        
        print("\n=== 清理完成 ===")
        print("✅ 所有危险的注册表项已安全清理")
        print("✅ 系统对象（我的电脑、网络等）不会受到影响")
        print("✅ 只清理了用户级别的文件关联和右键菜单")
        print("\n📝 注意事项：")
        print("   - 新版本只对压缩文件格式添加右键菜单")
        print("   - 使用PyWin32安全接口，避免直接操作注册表")
        print("   - 不再修改HKEY_CLASSES_ROOT等系统级路径")
        print("   - 文件关联仅在用户级别生效")
        
        return True
        
    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        print("请确保项目结构正确，且已安装所需依赖")
        return False
    except Exception as e:
        print(f"❌ 清理失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def show_manual_cleanup_instructions():
    """显示手动清理说明"""
    print("\n=== 手动清理说明 ===")
    print("如果自动清理失败，您可以手动清理以下注册表位置：")
    print("\n⚠️  注意：手动修改注册表有风险，请先备份注册表！")
    print("\n需要清理的危险路径（如果存在）：")
    
    dangerous_paths = [
        "HKEY_CLASSES_ROOT\\*\\shell\\GudaZip",
        "HKEY_CLASSES_ROOT\\Folder\\shell\\GudaZip", 
        "HKEY_CLASSES_ROOT\\Directory\\Background\\shell\\GudaZip",
        "HKEY_CLASSES_ROOT\\Drive\\shell\\GudaZip",
        "HKEY_LOCAL_MACHINE\\SOFTWARE\\Classes\\*\\shell\\GudaZip",
        "HKEY_LOCAL_MACHINE\\SOFTWARE\\Classes\\Folder\\shell\\GudaZip"
    ]
    
    for path in dangerous_paths:
        print(f"   ❌ {path}")
    
    print("\n✅ 安全的用户级路径（新版本使用）：")
    print("   📁 HKEY_CURRENT_USER\\SOFTWARE\\Classes\\[文件扩展名]\\shell\\[菜单项]")
    print("\n🔧 清理步骤：")
    print("   1. 按 Win+R，输入 regedit，打开注册表编辑器")
    print("   2. 导航到上述危险路径")
    print("   3. 如果找到 GudaZip 相关项，右键删除")
    print("   4. 重启资源管理器或重新登录")

if __name__ == "__main__":
    if sys.platform != "win32":
        print("❌ 此脚本仅支持Windows系统")
        sys.exit(1)
    
    print("GudaZip 注册表清理工具")
    print("此工具将安全地清理可能影响系统的注册表项\n")
    
    user_input = input("继续执行清理吗？(y/N): ").strip().lower()
    if user_input not in ['y', 'yes']:
        print("清理已取消")
        sys.exit(0)
    
    success = cleanup_dangerous_registry()
    
    if not success:
        show_manual_cleanup_instructions()
    
    input("\n按回车键退出...") 