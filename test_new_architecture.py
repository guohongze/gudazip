#!/usr/bin/env python3
"""
测试新的解耦架构
"""
import sys
import os
import tempfile
import shutil
import time
from pathlib import Path

# 添加项目路径到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

# 导入必要的模块
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import QTimer

from gudazip.archive_manager import ArchiveManager
from gudazip.ui.create_archive_dialog import CreateArchiveDialog
from gudazip.ui.extract_archive_dialog import ExtractArchiveDialog
from gudazip.ui.background_task_manager import get_background_task_manager


def create_test_files():
    """创建测试文件"""
    temp_dir = tempfile.mkdtemp(prefix="gudazip_test_")
    
    # 创建一些测试文件
    for i in range(3):
        file_path = os.path.join(temp_dir, f"test_file_{i}.txt")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(f"这是测试文件 {i}\n" * 100)  # 增加文件大小
    
    # 创建子目录
    sub_dir = os.path.join(temp_dir, "子目录")
    os.makedirs(sub_dir)
    
    for i in range(2):
        file_path = os.path.join(sub_dir, f"sub_file_{i}.txt")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(f"这是子目录中的测试文件 {i}\n" * 50)
    
    print(f"测试文件创建在: {temp_dir}")
    return temp_dir


def test_background_compression():
    """测试后台压缩"""
    print("测试后台压缩...")
    
    # 创建测试文件
    test_dir = create_test_files()
    
    # 获取文件列表
    files_to_compress = []
    for root, dirs, files in os.walk(test_dir):
        for file in files:
            files_to_compress.append(os.path.join(root, file))
    
    print(f"要压缩的文件: {files_to_compress}")
    
    # 创建压缩包路径
    archive_path = os.path.join(tempfile.gettempdir(), "test_background.zip")
    
    try:
        # 创建档案管理器
        archive_manager = ArchiveManager()
        
        # 创建压缩对话框
        dialog = CreateArchiveDialog(archive_manager, archive_path)
        dialog.selected_files = files_to_compress
        
        # 模拟选择后台压缩
        dialog.background_compress_check.setChecked(True)
        
        # 显示对话框
        result = dialog.exec()
        
        if result == dialog.Accepted:
            print("压缩任务已提交到后台")
            
            # 等待一段时间让后台任务运行
            print("等待后台任务完成...")
            time.sleep(5)
            
            # 检查文件是否存在
            if os.path.exists(archive_path):
                print(f"✅ 压缩成功！文件: {archive_path}")
                return archive_path
            else:
                print("❌ 压缩失败：文件不存在")
                return None
        else:
            print("用户取消了压缩")
            return None
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return None
    finally:
        # 清理测试文件
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)


def test_background_extraction(archive_path):
    """测试后台解压"""
    if not archive_path or not os.path.exists(archive_path):
        print("没有可用的压缩包进行解压测试")
        return
        
    print("测试后台解压...")
    
    # 创建解压目标目录
    extract_dir = tempfile.mkdtemp(prefix="gudazip_extract_")
    
    try:
        # 创建档案管理器
        archive_manager = ArchiveManager()
        
        # 创建解压对话框
        dialog = ExtractArchiveDialog(archive_manager, archive_path)
        dialog.target_edit.setText(extract_dir)
        
        # 模拟选择后台解压
        dialog.background_extract_check.setChecked(True)
        
        # 显示对话框
        result = dialog.exec()
        
        if result == dialog.Accepted:
            print("解压任务已提交到后台")
            
            # 等待一段时间让后台任务运行
            print("等待后台任务完成...")
            time.sleep(5)
            
            # 检查解压结果
            extracted_files = []
            for root, dirs, files in os.walk(extract_dir):
                for file in files:
                    extracted_files.append(os.path.join(root, file))
            
            if extracted_files:
                print(f"✅ 解压成功！文件数量: {len(extracted_files)}")
                for file in extracted_files[:5]:  # 只显示前5个文件
                    print(f"  - {file}")
                if len(extracted_files) > 5:
                    print(f"  ... 还有 {len(extracted_files) - 5} 个文件")
            else:
                print("❌ 解压失败：没有找到解压的文件")
        else:
            print("用户取消了解压")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
    finally:
        # 清理解压目录
        if os.path.exists(extract_dir):
            shutil.rmtree(extract_dir)


def test_task_manager():
    """测试任务管理器"""
    print("测试后台任务管理器...")
    
    task_manager = get_background_task_manager()
    
    print(f"活动任务数量: {len(task_manager.active_tasks)}")
    
    # 显示任务管理器窗口
    task_manager.show_task_manager_window()


def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    print("GudaZip 新架构测试")
    print("===================")
    
    try:
        # 测试后台压缩
        archive_path = test_background_compression()
        
        # 测试后台解压
        if archive_path:
            test_background_extraction(archive_path)
        
        # 测试任务管理器
        QTimer.singleShot(1000, test_task_manager)
        
        print("\n测试完成！程序将运行5秒钟以观察后台任务...")
        QTimer.singleShot(10000, app.quit)  # 10秒后退出
        
        app.exec()
        
    except Exception as e:
        print(f"测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 清理任务管理器
        task_manager = get_background_task_manager()
        task_manager.cleanup()
        
        print("测试结束")


if __name__ == "__main__":
    main() 