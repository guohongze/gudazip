#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MSI安装包PyWin32修复验证脚本
用于测试新的MSI安装包是否解决了PyWin32模块缺失问题
"""

def test_pywin32_modules():
    """测试PyWin32模块的可用性"""
    print("=" * 60)
    print("MSI安装包PyWin32模块验证测试")
    print("=" * 60)
    
    # 根据我们的构建输出，这些模块应该可用
    expected_available = [
        "win32api",
        "win32con",
        "win32com.client",
        "win32gui",
        "win32ui"
    ]
    
    # 这些模块在当前环境中不可用，预期会被跳过
    expected_missing = [
        "win32shell",
        "win32shellcon"
    ]
    
    available_count = 0
    missing_count = 0
    
    print("预期可用的模块:")
    for module_name in expected_available:
        try:
            __import__(module_name)
            print(f"✅ {module_name}: 可用")
            available_count += 1
        except ImportError as e:
            print(f"❌ {module_name}: 不可用 - {e}")
    
    print(f"\n预期缺失的模块 (已在构建时跳过):")
    for module_name in expected_missing:
        try:
            __import__(module_name)
            print(f"⚠️  {module_name}: 意外可用")
        except ImportError:
            print(f"⭕ {module_name}: 已跳过 (符合预期)")
            missing_count += 1
    
    print("\n" + "=" * 60)
    print("测试结果")
    print("=" * 60)
    
    success = available_count == len(expected_available) and missing_count == len(expected_missing)
    
    if success:
        print("🎉 测试通过！")
        print(f"✅ 成功包含 {available_count}/{len(expected_available)} 个可用模块")
        print(f"⭕ 正确跳过 {missing_count}/{len(expected_missing)} 个不可用模块")
        print("\n主要功能预期表现:")
        print("  - 基础文件关联功能: 应该可以工作")
        print("  - 右键菜单功能: 部分功能可用")
        print("  - Shell刷新功能: 将使用ctypes备用方案")
    else:
        print("❌ 测试失败!")
        print("请检查MSI安装包或重新构建")
    
    return success

def test_file_association_manager():
    """测试文件关联管理器的功能"""
    print("\n" + "=" * 60)
    print("文件关联管理器功能测试")
    print("=" * 60)
    
    try:
        # 这里需要调整导入路径，因为在MSI安装后结构会不同
        # 尝试几种可能的导入方式
        try:
            from gudazip.core.pywin32_registry import PyWin32Registry
        except ImportError:
            try:
                import sys
                import os
                # 假设在安装目录下
                install_dir = os.path.dirname(sys.executable)
                gudazip_path = os.path.join(install_dir, 'gudazip')
                if os.path.exists(gudazip_path):
                    sys.path.insert(0, gudazip_path)
                    from core.pywin32_registry import PyWin32Registry
                else:
                    raise ImportError("无法找到gudazip模块")
            except ImportError:
                print("❌ 无法导入PyWin32Registry模块")
                print("这可能是正常的，如果您是在开发环境中运行此脚本")
                return False
        
        registry = PyWin32Registry()
        
        if registry.is_available():
            print("✅ PyWin32Registry: 可用")
            
            status = registry.get_module_status()
            print(f"✅ 基础功能: {'可用' if status['basic_functions'] else '不可用'}")
            print(f"⚠️  Shell功能: {'可用' if status['shell_functions'] else '不可用(将使用备用方案)'}")
            
            if status['missing_modules']:
                print(f"⭕ 跳过的模块: {status['missing_modules']}")
            
            return True
        else:
            print("❌ PyWin32Registry: 不可用")
            return False
            
    except Exception as e:
        print(f"❌ 测试过程中出错: {e}")
        return False

def main():
    """主函数"""
    print("GudaZip MSI PyWin32修复验证\n")
    
    # 显示当前Python环境信息
    import sys
    print(f"Python版本: {sys.version}")
    print(f"Python路径: {sys.executable}")
    print(f"运行目录: {sys.path[0]}\n")
    
    # 测试模块可用性
    modules_ok = test_pywin32_modules()
    
    # 测试文件关联功能（仅在模块测试通过时）
    if modules_ok:
        func_ok = test_file_association_manager()
    else:
        func_ok = False
    
    print("\n" + "=" * 60)
    print("最终结果")
    print("=" * 60)
    
    if modules_ok:
        print("✅ PyWin32模块测试: 通过")
        print("   新的MSI安装包已正确包含可用的PyWin32模块")
    else:
        print("❌ PyWin32模块测试: 失败")
    
    if func_ok:
        print("✅ 文件关联功能测试: 通过")
        print("   右键菜单和文件关联功能应该可以正常工作")
    else:
        print("⚠️  文件关联功能测试: 跳过或失败")
        print("   需要在实际安装环境中测试")
    
    print("\n📋 使用说明:")
    print("1. 卸载当前版本的GudaZip")
    print("2. 安装新的MSI包: dist/GudaZip-1.0.0-Optimized-Setup.msi")
    print("3. 在安装后的环境中再次运行此测试脚本")
    print("4. 测试实际的右键菜单和文件关联功能")

if __name__ == "__main__":
    main() 