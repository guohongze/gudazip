#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ErrorManager集成测试程序
验证4.1任务完成情况 - 统一错误处理
"""

import sys
import os
sys.path.insert(0, 'src')

from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QTextEdit
from PySide6.QtCore import Qt

# 导入各个组件
from gudazip.core.error_manager import get_error_manager, ErrorCategory, ErrorSeverity
from gudazip.core.file_operation_manager import FileOperationManager
from gudazip.core.archive_operation_manager import ArchiveOperationManager
from gudazip.core.archive_manager import ArchiveManager
from gudazip.core.health_checker import HealthChecker
from gudazip.main_window import MainWindow
from gudazip.ui.file_browser import FileBrowser


class ErrorManagerTestWindow(QMainWindow):
    """ErrorManager测试窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ErrorManager 集成测试")
        self.setGeometry(100, 100, 800, 600)
        
        # 初始化ErrorManager
        self.error_manager = get_error_manager(self)
        
        self.init_ui()
        self.test_integrations()
    
    def init_ui(self):
        """初始化UI"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # 结果显示区域
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        layout.addWidget(self.result_text)
        
        # 测试按钮
        test_btn = QPushButton("开始测试")
        test_btn.clicked.connect(self.run_tests)
        layout.addWidget(test_btn)
    
    def log(self, message):
        """记录测试结果"""
        self.result_text.append(message)
        print(message)
    
    def test_integrations(self):
        """测试各组件的ErrorManager集成"""
        self.log("🔍 开始检查 ErrorManager 集成状态...")
        self.log("=" * 50)
        
        # 1. 测试 FileOperationManager
        try:
            file_manager = FileOperationManager(self)
            if hasattr(file_manager, 'error_manager') and file_manager.error_manager:
                self.log("✅ FileOperationManager - ErrorManager集成正常")
            else:
                self.log("❌ FileOperationManager - ErrorManager集成失败")
        except Exception as e:
            self.log(f"❌ FileOperationManager - 初始化失败: {e}")
        
        # 2. 测试 ArchiveOperationManager
        try:
            archive_op_manager = ArchiveOperationManager(self)
            if hasattr(archive_op_manager, 'error_manager') and archive_op_manager.error_manager:
                self.log("✅ ArchiveOperationManager - ErrorManager集成正常")
            else:
                self.log("❌ ArchiveOperationManager - ErrorManager集成失败")
        except Exception as e:
            self.log(f"❌ ArchiveOperationManager - 初始化失败: {e}")
        
        # 3. 测试 ArchiveManager
        try:
            archive_manager = ArchiveManager(self)
            if hasattr(archive_manager, 'error_manager') and archive_manager.error_manager:
                self.log("✅ ArchiveManager - ErrorManager集成正常")
            else:
                self.log("❌ ArchiveManager - ErrorManager集成失败")
        except Exception as e:
            self.log(f"❌ ArchiveManager - 初始化失败: {e}")
        
        # 4. 测试 HealthChecker
        try:
            health_checker = HealthChecker(self)
            if hasattr(health_checker, 'error_manager') and health_checker.error_manager:
                self.log("✅ HealthChecker - ErrorManager集成正常")
            else:
                self.log("❌ HealthChecker - ErrorManager集成失败")
        except Exception as e:
            self.log(f"❌ HealthChecker - 初始化失败: {e}")
        
        # 5. 测试 FileBrowser (UI层)
        try:
            file_browser = FileBrowser(self)
            if hasattr(file_browser, 'error_manager') and file_browser.error_manager:
                self.log("✅ FileBrowser - ErrorManager集成正常")
            else:
                self.log("❌ FileBrowser - ErrorManager集成失败")
        except Exception as e:
            self.log(f"❌ FileBrowser - 初始化失败: {e}")
        
        self.log("=" * 50)
        self.log("✨ ErrorManager集成检查完成!")
    
    def run_tests(self):
        """运行功能测试"""
        self.log("\n🧪 开始功能测试...")
        self.log("=" * 50)
        
        # 测试错误处理功能
        try:
            # 测试基本错误处理
            error_info = self.error_manager.handle_error(
                ErrorCategory.FILE_NOT_FOUND,
                ErrorSeverity.WARNING,
                "测试错误",
                details="这是一个测试错误，用于验证ErrorManager功能",
                show_dialog=False
            )
            self.log("✅ 基本错误处理测试通过")
            
            # 测试异常处理
            try:
                raise FileNotFoundError("测试文件未找到异常")
            except Exception as e:
                error_info = self.error_manager.handle_exception(
                    e,
                    context={"test": "exception_handling"},
                    show_dialog=False
                )
                self.log("✅ 异常处理测试通过")
            
            # 获取错误统计
            stats = self.error_manager.get_error_statistics()
            self.log(f"📊 错误统计: {stats}")
            
            # 获取错误历史
            history = self.error_manager.get_error_history(limit=5)
            self.log(f"📝 错误历史 (最近5条): {len(history)} 条记录")
            
        except Exception as e:
            self.log(f"❌ 功能测试失败: {e}")
        
        self.log("=" * 50)
        self.log("🎉 所有测试完成!")


def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    print("🚀 启动 ErrorManager 集成测试...")
    
    # 创建测试窗口
    test_window = ErrorManagerTestWindow()
    test_window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main() 