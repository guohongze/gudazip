#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试右键菜单调用，模拟Windows右键菜单的命令行调用
"""

import sys
import os
import subprocess

def test_context_menu_calls():
    """测试各种右键菜单调用"""
    print("=== 测试右键菜单命令行调用 ===")
    
    # 创建一个测试文件
    test_file = os.path.join(os.getcwd(), "test_file.txt")
    print(f"创建测试文件: {test_file}")
    
    try:
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write("这是一个测试文件")
        print(f"✓ 测试文件已创建")
    except Exception as e:
        print(f"✗ 创建测试文件失败: {e}")
        return
    
    # 测试各种命令
    commands_to_test = [
        ["python", "main.py", "--compress-zip", test_file],
        ["python", "main.py", "--compress-7z", test_file],
        ["python", "main.py", "--add", test_file],
    ]
    
    for i, cmd in enumerate(commands_to_test, 1):
        print(f"\n--- 测试 {i}: {' '.join(cmd)} ---")
        print(f"命令参数:")
        for j, arg in enumerate(cmd):
            print(f"  [{j}] = '{arg}'")
        
        try:
            # 运行命令并捕获输出
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=30,
                cwd=os.getcwd()
            )
            
            print("标准输出:")
            if result.stdout:
                for line in result.stdout.split('\n'):
                    if line.strip():
                        print(f"  {line}")
            else:
                print("  (无输出)")
            
            print("标准错误:")
            if result.stderr:
                for line in result.stderr.split('\n'):
                    if line.strip():
                        print(f"  {line}")
            else:
                print("  (无错误)")
            
            print(f"返回码: {result.returncode}")
            
        except subprocess.TimeoutExpired:
            print("  ✗ 命令超时")
        except Exception as e:
            print(f"  ✗ 运行命令失败: {e}")
    
    # 清理测试文件
    try:
        if os.path.exists(test_file):
            os.remove(test_file)
            print(f"\n✓ 测试文件已清理")
    except Exception as e:
        print(f"\n! 清理测试文件失败: {e}")

def test_path_parsing():
    """测试路径解析逻辑"""
    print("\n=== 测试路径解析逻辑 ===")
    
    # 模拟各种可能的路径
    test_paths = [
        r"C:\Users\Test\Desktop\file.txt",
        r"C:\Program Files\Test App\file.txt",
        r"C:\Users\测试用户\桌面\文件.txt",
        r"D:\My Documents\file with spaces.txt",
    ]
    
    for path in test_paths:
        print(f"\n测试路径: {path}")
        
        # 模拟命令行参数
        fake_argv = ["main.py", "--compress-zip", path]
        print(f"模拟 sys.argv = {fake_argv}")
        
        # 测试参数解析
        i = 1
        context_menu_action = None
        target_file = None
        
        while i < len(fake_argv):
            arg = fake_argv[i]
            print(f"  处理参数 [{i}] = '{arg}'")
            
            if arg.startswith('--'):
                if arg in ['--add', '--extract-here', '--open', '--compress-zip', '--compress-7z']:
                    context_menu_action = arg
                    print(f"    找到右键菜单命令 = {context_menu_action}")
                    # 获取目标文件（下一个参数）
                    if i + 1 < len(fake_argv):
                        target_file = fake_argv[i + 1]
                        print(f"    目标文件参数 = '{target_file}'")
                        print(f"    参数长度 = {len(target_file)}")
                        print(f"    参数字符 = {list(target_file)}")
                        i += 1  # 跳过下一个参数
            i += 1
        
        print(f"  最终结果:")
        print(f"    action = {context_menu_action}")
        print(f"    target_file = {target_file}")
        print(f"    文件存在 = {os.path.exists(target_file) if target_file else 'N/A'}")

if __name__ == "__main__":
    try:
        test_path_parsing()
        print("\n" + "="*60)
        test_context_menu_calls()
    except KeyboardInterrupt:
        print("\n测试被用户中断")
    except Exception as e:
        print(f"\n测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
    
    input("\n按回车键退出...") 