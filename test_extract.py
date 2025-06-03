#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GudaZip解压功能测试脚本
"""

import sys
import os
import tempfile
import shutil

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from gudazip.core.archive_manager import ArchiveManager


def test_extract():
    """测试解压功能"""
    print("🧪 开始测试GudaZip解压功能...")
    
    # 创建压缩包管理器
    manager = ArchiveManager()
    
    # 创建临时测试文件和压缩包
    temp_dir = tempfile.mkdtemp()
    print(f"📁 使用临时目录: {temp_dir}")
    
    try:
        # 1. 创建测试文件
        test_files = []
        
        # 创建测试文件1
        test_file1 = os.path.join(temp_dir, "test1.txt")
        with open(test_file1, 'w', encoding='utf-8') as f:
            f.write("这是测试文件1的内容\n包含一些中文字符\n用于测试解压功能")
        test_files.append(test_file1)
        print(f"✅ 创建测试文件: {test_file1}")
        
        # 创建测试文件2
        test_file2 = os.path.join(temp_dir, "test2.md")
        with open(test_file2, 'w', encoding='utf-8') as f:
            f.write("# 测试文档\n\n这是一个markdown测试文件\n\n- 项目1\n- 项目2\n- 项目3\n\n## 解压测试\n\n这个文件用于测试解压功能。")
        test_files.append(test_file2)
        print(f"✅ 创建测试文件: {test_file2}")
        
        # 创建子目录和文件
        sub_dir = os.path.join(temp_dir, "subdir")
        os.makedirs(sub_dir)
        
        sub_file = os.path.join(sub_dir, "sub_test.txt")
        with open(sub_file, 'w', encoding='utf-8') as f:
            f.write("这是子目录中的测试文件\n用于测试目录结构的保持")
        test_files.append(sub_dir)  # 添加整个子目录
        print(f"✅ 创建子目录和文件: {sub_dir}")
        
        # 2. 创建ZIP压缩包
        zip_path = os.path.join(temp_dir, "test_archive.zip")
        print(f"📦 创建压缩包: {zip_path}")
        
        success = manager.create_archive(zip_path, test_files, compression_level=6)
        
        if not success:
            print("❌ 压缩包创建失败")
            return
            
        print("✅ 压缩包创建成功!")
        
        # 验证压缩包信息
        archive_info = manager.get_archive_info(zip_path)
        if archive_info:
            print(f"📋 压缩包信息:")
            print(f"   - 格式: {archive_info['format']}")
            print(f"   - 文件数量: {archive_info['file_count']}")
            print(f"   - 原始大小: {archive_info['total_size']} 字节")
            print(f"   - 包含文件:")
            for file_info in archive_info['files']:
                print(f"     • {file_info['path']} ({file_info['size']} 字节)")
        
        # 3. 测试解压功能
        extract_dir = os.path.join(temp_dir, "extracted")
        print(f"\n📤 开始解压到: {extract_dir}")
        
        # 解压所有文件
        success = manager.extract_archive(zip_path, extract_dir)
        
        if success:
            print("✅ 解压成功!")
            
            # 验证解压结果
            print("\n🔍 验证解压结果:")
            
            def verify_extracted_files(base_dir, prefix=""):
                """递归验证解压的文件"""
                items = os.listdir(base_dir)
                for item in sorted(items):
                    item_path = os.path.join(base_dir, item)
                    if os.path.isfile(item_path):
                        size = os.path.getsize(item_path)
                        print(f"   📄 {prefix}{item} ({size} 字节)")
                        
                        # 读取文件内容验证
                        try:
                            with open(item_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                print(f"      内容预览: {content[:50]}{'...' if len(content) > 50 else ''}")
                        except:
                            print(f"      无法读取文件内容")
                            
                    elif os.path.isdir(item_path):
                        print(f"   📁 {prefix}{item}/")
                        verify_extracted_files(item_path, prefix + "  ")
            
            if os.path.exists(extract_dir):
                verify_extracted_files(extract_dir)
            else:
                print("❌ 解压目录不存在")
                
            # 4. 测试部分解压
            print(f"\n📤 测试部分解压功能...")
            partial_extract_dir = os.path.join(temp_dir, "partial_extracted")
            
            # 只解压第一个文件
            selected_files = [archive_info['files'][0]['path']] if archive_info['files'] else []
            
            if selected_files:
                print(f"   选择解压文件: {selected_files}")
                
                success = manager.extract_archive(
                    zip_path, 
                    partial_extract_dir, 
                    password=None, 
                    selected_files=selected_files
                )
                
                if success:
                    print("✅ 部分解压成功!")
                    if os.path.exists(partial_extract_dir):
                        print("   解压内容:")
                        verify_extracted_files(partial_extract_dir, "   ")
                else:
                    print("❌ 部分解压失败")
            
        else:
            print("❌ 解压失败")
            
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 清理临时目录
        print(f"\n🧹 清理临时目录: {temp_dir}")
        try:
            shutil.rmtree(temp_dir)
            print("✅ 清理完成")
        except Exception as e:
            print(f"⚠️  清理失败: {e}")
    
    print("\n✨ 解压功能测试完成!")


if __name__ == "__main__":
    test_extract() 