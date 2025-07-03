#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
开发环境设置脚本
用于在本地开发环境中设置GudaZip的环境变量
"""

import os
import sys

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from gudazip.core.environment_manager import get_environment_manager


def main():
    """主函数"""
    print("=" * 60)
    print("GudaZip 开发环境设置")
    print("=" * 60)
    
    env_manager = get_environment_manager()
    
    # 检查当前环境变量状态
    print("\n1. 检查当前环境变量状态...")
    status = env_manager.check_environment_variables()
    
    if status["all_set"]:
        print("✅ 所有环境变量已设置")
        for var_name, var_info in status["variables"].items():
            print(f"  {var_name} = {var_info['value']}")
        
        # 询问是否重新设置
        choice = input("\n是否重新设置环境变量？(y/N): ").strip().lower()
        if choice not in ['y', 'yes']:
            print("\n操作已取消")
            return
    else:
        print("⚠️ 发现缺失的环境变量:")
        for var_name in status["missing"]:
            print(f"  - {var_name}")
        
        if status["invalid_paths"]:
            print("⚠️ 发现无效路径的环境变量:")
            for var_name in status["invalid_paths"]:
                print(f"  - {var_name}")
    
    # 设置开发环境
    print("\n2. 设置开发环境变量...")
    project_root = os.path.dirname(os.path.abspath(__file__))
    print(f"项目根目录: {project_root}")
    
    if env_manager.set_environment_variables(project_root):
        print("\n✅ 开发环境变量设置成功！")
        
        # 显示设置的路径信息
        print("\n3. 路径信息:")
        paths_info = env_manager.get_paths_info()
        for key, path in paths_info.items():
            exists = os.path.exists(path) if path else False
            status_icon = "✅" if exists else "❌"
            print(f"  {key}: {status_icon} {path}")
        
        print("\n4. 注意事项:")
        print("  - 环境变量已设置到用户级别注册表")
        print("  - 重启命令行或IDE后生效")
        print("  - 在新的命令行窗口中运行程序将使用环境变量路径")
        
    else:
        print("\n❌ 开发环境变量设置失败！")
        return 1
    
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n操作已取消")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        sys.exit(1)