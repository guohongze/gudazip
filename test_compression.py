#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GudaZip压缩功能测试脚本
"""

import sys
import os
import tempfile

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from gudazip.core.archive_manager import ArchiveManager


def test_compression():
    """测试压缩功能"""
    print("🧪 开始测试GudaZip压缩功能...")
    
    # 创建压缩包管理器
    manager = ArchiveManager()
    
    # 创建临时测试文件
    test_files = []
    
    # 创建测试文件1
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("这是测试文件1的内容\n包含一些中文字符")
        test_files.append(f.name)
        print(f"✅ 创建测试文件: {f.name}")
    
    # 创建测试文件2
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write("# 测试文档\n\n这是一个markdown测试文件\n\n- 项目1\n- 项目2\n- 项目3")
        test_files.append(f.name)
        print(f"✅ 创建测试文件: {f.name}")
    
    # 创建测试ZIP文件
    with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as f:
        zip_path = f.name
        
    print(f"📦 准备创建压缩包: {zip_path}")
    print(f"📄 包含文件: {len(test_files)} 个")
    
    try:
        # 创建压缩包
        success = manager.create_archive(
            zip_path, 
            test_files,
            compression_level=6
        )
        
        if success:
            print("✅ 压缩包创建成功!")
            
            # 验证压缩包
            if os.path.exists(zip_path):
                file_size = os.path.getsize(zip_path)
                print(f"📊 压缩包大小: {file_size} 字节")
                
                # 获取压缩包信息
                archive_info = manager.get_archive_info(zip_path)
                if archive_info:
                    print(f"📋 压缩包信息:")
                    print(f"   - 格式: {archive_info['format']}")
                    print(f"   - 文件数量: {archive_info['file_count']}")
                    print(f"   - 原始大小: {archive_info['total_size']} 字节")
                    print(f"   - 压缩后大小: {archive_info['compressed_size']} 字节")
                    
                    if archive_info['total_size'] > 0:
                        ratio = (1 - archive_info['compressed_size'] / archive_info['total_size']) * 100
                        print(f"   - 压缩率: {ratio:.1f}%")
                    
                    print(f"   - 包含文件:")
                    for file_info in archive_info['files']:
                        print(f"     • {file_info['path']} ({file_info['size']} 字节)")
                else:
                    print("⚠️  无法获取压缩包信息")
            else:
                print("❌ 压缩包文件不存在")
        else:
            print("❌ 压缩包创建失败")
            
    except Exception as e:
        print(f"❌ 压缩过程中发生错误: {e}")
    
    finally:
        # 清理临时文件
        print("\n🧹 清理临时文件...")
        for file_path in test_files:
            try:
                os.unlink(file_path)
                print(f"🗑️  删除: {file_path}")
            except:
                pass
                
        # 删除测试压缩包
        try:
            if os.path.exists(zip_path):
                os.unlink(zip_path)
                print(f"🗑️  删除压缩包: {zip_path}")
        except:
            pass
    
    print("\n✨ 测试完成!")


if __name__ == "__main__":
    test_compression() 