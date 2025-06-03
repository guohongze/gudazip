import sys
import os
sys.path.insert(0, 'src')

from gudazip.core.archive_manager import ArchiveManager

print("测试GudaZip压缩功能...")

# 创建管理器
manager = ArchiveManager()

# 创建测试文件
with open('test_simple.txt', 'w', encoding='utf-8') as f:
    f.write('这是一个简单的测试文件\n用于验证压缩功能')

print("✅ 创建测试文件: test_simple.txt")

# 压缩文件
print("📦 开始压缩...")
result = manager.create_archive('test_simple.zip', ['test_simple.txt'])

if result:
    print("✅ 压缩成功!")
    if os.path.exists('test_simple.zip'):
        size = os.path.getsize('test_simple.zip')
        print(f"📊 压缩包大小: {size} 字节")
        
        # 获取压缩包信息
        info = manager.get_archive_info('test_simple.zip')
        if info:
            print(f"📋 文件数量: {info['file_count']}")
            print(f"📋 原始大小: {info['total_size']} 字节")
else:
    print("❌ 压缩失败")

print("测试完成!") 