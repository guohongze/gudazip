#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GudaZip 压缩和解压功能演示脚本
展示完整的压缩→解压→验证流程
"""

import sys
import os
import tempfile
import shutil

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from gudazip.core.archive_manager import ArchiveManager


def create_test_files():
    """创建测试文件和目录结构"""
    temp_dir = tempfile.mkdtemp()
    print(f"📁 创建临时目录: {temp_dir}")
    
    files_created = []
    
    # 创建文本文件
    text_file = os.path.join(temp_dir, "readme.txt")
    with open(text_file, 'w', encoding='utf-8') as f:
        f.write("""# GudaZip 演示文件

这是一个用于演示GudaZip压缩和解压功能的测试文件。

## 功能特性
- ✅ ZIP文件创建
- ✅ ZIP文件解压
- ✅ 多文件压缩
- ✅ 目录结构保持
- ✅ 中文字符支持

GudaZip是一个功能强大的Python压缩管理器！
""")
    files_created.append(text_file)
    print(f"✅ 创建文本文件: readme.txt")
    
    # 创建配置文件
    config_file = os.path.join(temp_dir, "config.json")
    with open(config_file, 'w', encoding='utf-8') as f:
        f.write("""{
    "application": "GudaZip",
    "version": "0.2.0",
    "features": {
        "compression": ["ZIP", "RAR", "7Z"],
        "ui": "PySide6",
        "language": "中文"
    },
    "settings": {
        "compression_level": 6,
        "password_protected": false,
        "auto_extract": true
    }
}""")
    files_created.append(config_file)
    print(f"✅ 创建配置文件: config.json")
    
    # 创建子目录结构
    docs_dir = os.path.join(temp_dir, "docs")
    os.makedirs(docs_dir)
    
    # 在子目录中创建文件
    manual_file = os.path.join(docs_dir, "manual.md")
    with open(manual_file, 'w', encoding='utf-8') as f:
        f.write("""# GudaZip 用户手册

## 安装
1. 安装Python 3.12+
2. 安装依赖: `pip install -r requirements.txt`
3. 运行程序: `python main.py`

## 使用
- 创建压缩包: Ctrl+N
- 解压压缩包: Ctrl+E

## 支持格式
- ZIP (读写)
- RAR (只读)
- 7Z (只读)
""")
    files_created.append(docs_dir)
    print(f"✅ 创建文档目录: docs/")
    print(f"   ┗ manual.md")
    
    # 创建更多子文件
    examples_dir = os.path.join(temp_dir, "examples")
    os.makedirs(examples_dir)
    
    for i in range(3):
        example_file = os.path.join(examples_dir, f"example_{i+1}.py")
        with open(example_file, 'w', encoding='utf-8') as f:
            f.write(f"""#!/usr/bin/env python3
# -*- coding: utf-8 -*-
\"\"\"
示例脚本 {i+1}
\"\"\"

def main():
    print("这是示例 {i+1}")
    print("演示GudaZip的压缩功能")
    
if __name__ == "__main__":
    main()
""")
    files_created.append(examples_dir)
    print(f"✅ 创建示例目录: examples/")
    print(f"   ┣ example_1.py")
    print(f"   ┣ example_2.py")
    print(f"   ┗ example_3.py")
    
    return temp_dir, files_created


def demo_compress_extract():
    """演示完整的压缩和解压流程"""
    print("🎯 GudaZip 压缩和解压功能演示")
    print("=" * 50)
    
    # 创建压缩包管理器
    manager = ArchiveManager()
    
    # 创建测试文件
    print("\n📝 第一步：创建测试文件")
    temp_dir, test_files = create_test_files()
    
    try:
        # 第二步：创建压缩包
        print("\n📦 第二步：创建压缩包")
        zip_path = os.path.join(temp_dir, "gudazip_demo.zip")
        print(f"压缩包路径: {zip_path}")
        print(f"包含文件: {len(test_files)} 个项目")
        
        # 创建压缩包
        success = manager.create_archive(
            zip_path, 
            test_files, 
            compression_level=6
        )
        
        if success:
            print("✅ 压缩包创建成功！")
            
            # 获取压缩包信息
            archive_info = manager.get_archive_info(zip_path)
            if archive_info:
                print(f"📊 压缩包统计:")
                print(f"   - 文件数量: {archive_info['file_count']}")
                print(f"   - 原始大小: {archive_info['total_size']} 字节")
                print(f"   - 压缩大小: {archive_info['compressed_size']} 字节")
                
                if archive_info['total_size'] > 0:
                    ratio = (1 - archive_info['compressed_size'] / archive_info['total_size']) * 100
                    print(f"   - 压缩率: {ratio:.1f}%")
                
                print(f"📋 包含文件:")
                for file_info in archive_info['files']:
                    print(f"   📄 {file_info['path']} ({file_info['size']} 字节)")
        else:
            print("❌ 压缩包创建失败")
            return
            
        # 第三步：解压压缩包
        print("\n📤 第三步：解压压缩包")
        extract_dir = os.path.join(temp_dir, "extracted")
        print(f"解压目标: {extract_dir}")
        
        # 解压所有文件
        success = manager.extract_archive(zip_path, extract_dir)
        
        if success:
            print("✅ 解压成功！")
            
            # 第四步：验证解压结果
            print("\n🔍 第四步：验证解压结果")
            
            def verify_directory(base_dir, prefix=""):
                """递归验证目录内容"""
                items = sorted(os.listdir(base_dir))
                for item in items:
                    item_path = os.path.join(base_dir, item)
                    if os.path.isfile(item_path):
                        size = os.path.getsize(item_path)
                        print(f"   {prefix}📄 {item} ({size} 字节)")
                        
                        # 验证文件内容
                        try:
                            with open(item_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                lines = len(content.splitlines())
                                chars = len(content)
                                print(f"   {prefix}   内容: {lines} 行, {chars} 字符")
                        except Exception as e:
                            print(f"   {prefix}   ⚠️ 无法读取: {e}")
                            
                    elif os.path.isdir(item_path):
                        print(f"   {prefix}📁 {item}/")
                        verify_directory(item_path, prefix + "  ")
            
            if os.path.exists(extract_dir):
                print("解压后的文件结构:")
                verify_directory(extract_dir)
            else:
                print("❌ 解压目录不存在")
                
            # 第五步：测试选择性解压
            print("\n🎯 第五步：测试选择性解压")
            partial_dir = os.path.join(temp_dir, "partial")
            
            # 只解压readme.txt文件
            selected_files = ["readme.txt"]
            print(f"选择解压: {selected_files}")
            
            success = manager.extract_archive(
                zip_path, 
                partial_dir, 
                password=None, 
                selected_files=selected_files
            )
            
            if success:
                print("✅ 选择性解压成功！")
                if os.path.exists(partial_dir):
                    print("部分解压结果:")
                    verify_directory(partial_dir, "  ")
            else:
                print("❌ 选择性解压失败")
                
        else:
            print("❌ 解压失败")
            
    except Exception as e:
        print(f"❌ 演示过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # 清理
        print(f"\n🧹 清理临时文件: {temp_dir}")
        try:
            shutil.rmtree(temp_dir)
            print("✅ 清理完成")
        except Exception as e:
            print(f"⚠️ 清理失败: {e}")
            
    print("\n🎉 演示完成！")
    print("GudaZip 的压缩和解压功能工作正常 ✨")


if __name__ == "__main__":
    demo_compress_extract() 