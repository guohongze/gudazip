#!/usr/bin/env python3
"""
简单测试脚本
"""
import sys
import os
import tempfile
from pathlib import Path

# 添加项目路径到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

try:
    print("导入 PySide6...")
    from PySide6.QtWidgets import QApplication
    print("✅ PySide6 导入成功")
    
    print("导入 ArchiveManager...")
    from gudazip.archive_manager import ArchiveManager
    print("✅ ArchiveManager 导入成功")
    
    print("导入后台任务管理器...")
    from gudazip.ui.background_task_manager import get_background_task_manager
    print("✅ 后台任务管理器导入成功")
    
    print("导入压缩对话框...")
    from gudazip.ui.create_archive_dialog import CreateArchiveDialog
    print("✅ 压缩对话框导入成功")
    
    print("创建应用程序...")
    app = QApplication(sys.argv)
    print("✅ 应用程序创建成功")
    
    print("创建档案管理器...")
    archive_manager = ArchiveManager()
    print("✅ 档案管理器创建成功")
    
    print("创建压缩对话框...")
    archive_path = os.path.join(tempfile.gettempdir(), "test.zip")
    dialog = CreateArchiveDialog(archive_manager, archive_path)
    print("✅ 压缩对话框创建成功")
    
    print("测试后台任务管理器...")
    task_manager = get_background_task_manager()
    print("✅ 后台任务管理器创建成功")
    
    print("所有组件测试通过！")
    
except Exception as e:
    print(f"❌ 错误: {e}")
    import traceback
    traceback.print_exc() 