#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试压缩包"打开当前文件夹"功能
"""

import sys
import os
import tempfile
import shutil
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel, QHBoxLayout
from PySide6.QtCore import Qt

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from gudazip.ui.file_browser import FileBrowser
from gudazip.core.archive_manager import ArchiveManager


class TestWindow(QMainWindow):
    """测试窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GudaZip 打开当前文件夹功能测试")
        self.setGeometry(100, 100, 1000, 700)
        
        # 创建中央控件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建布局
        layout = QVBoxLayout(central_widget)
        
        # 状态标签
        self.status_label = QLabel("测试说明：\n1. 点击'创建测试压缩包'按钮\n2. 双击压缩包进入查看模式\n3. 右键任意文件或空白处\n4. 选择'打开当前文件夹'\n5. 应该打开压缩包所在的文件夹并选中压缩包文件")
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: #e3f2fd;
                padding: 15px;
                border: 1px solid #90caf9;
                border-radius: 8px;
                font-size: 14px;
                color: #1976d2;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.status_label)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        
        # 创建测试按钮
        self.create_test_btn = QPushButton("创建测试压缩包")
        self.create_test_btn.setStyleSheet("""
            QPushButton {
                background-color: #4caf50;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.create_test_btn.clicked.connect(self.create_test_archive)
        button_layout.addWidget(self.create_test_btn)
        
        # 退出压缩包模式按钮
        self.exit_archive_btn = QPushButton("退出压缩包查看")
        self.exit_archive_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff9800;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #f57c00;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.exit_archive_btn.clicked.connect(self.exit_archive_mode)
        self.exit_archive_btn.setEnabled(False)
        button_layout.addWidget(self.exit_archive_btn)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # 文件浏览器
        self.file_browser = FileBrowser()
        self.file_browser.archiveOpenRequested.connect(self.open_archive)
        layout.addWidget(self.file_browser)
        
        self.test_zip_path = None
        
    def create_test_archive(self):
        """创建测试压缩包"""
        try:
            # 创建临时目录和文件
            temp_dir = tempfile.mkdtemp(prefix="gudazip_folder_test_")
            test_files = []
            
            # 创建几个测试文件
            for i in range(3):
                file_path = os.path.join(temp_dir, f"文件_{i}.txt")
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(f"这是测试文件 {i}\n用于测试'打开当前文件夹'功能")
                test_files.append(file_path)
            
            # 创建ZIP文件
            self.test_zip_path = os.path.join(temp_dir, "测试压缩包_打开文件夹.zip")
            archive_manager = ArchiveManager()
            success = archive_manager.create_archive(self.test_zip_path, test_files)
            
            if success:
                self.status_label.setText(f"✅ 测试压缩包创建成功！\n\n📍 压缩包位置: {self.test_zip_path}\n\n🎯 测试步骤:\n1. 双击压缩包进入查看模式\n2. 右键任意文件选择'打开当前文件夹'\n3. 应该打开包含压缩包的文件夹并选中压缩包文件\n4. 验证打开的是正确的文件夹")
                self.status_label.setStyleSheet("""
                    QLabel {
                        background-color: #e8f5e8;
                        padding: 15px;
                        border: 1px solid #4caf50;
                        border-radius: 8px;
                        font-size: 14px;
                        color: #2e7d32;
                        font-weight: bold;
                    }
                """)
                
                # 导航到包含压缩包的目录
                parent_dir = os.path.dirname(self.test_zip_path)
                self.file_browser.set_root_path(parent_dir)
                
                # 禁用创建按钮
                self.create_test_btn.setEnabled(False)
                
            else:
                self.status_label.setText("❌ 创建测试压缩包失败")
                self.status_label.setStyleSheet("""
                    QLabel {
                        background-color: #ffebee;
                        padding: 15px;
                        border: 1px solid #f44336;
                        border-radius: 8px;
                        font-size: 14px;
                        color: #c62828;
                        font-weight: bold;
                    }
                """)
                
        except Exception as e:
            self.status_label.setText(f"❌ 创建测试压缩包时出错: {str(e)}")
            self.status_label.setStyleSheet("""
                QLabel {
                    background-color: #ffebee;
                    padding: 15px;
                    border: 1px solid #f44336;
                    border-radius: 8px;
                    font-size: 14px;
                    color: #c62828;
                    font-weight: bold;
                }
            """)
    
    def open_archive(self, archive_path):
        """打开压缩包进入查看模式"""
        try:
            # 使用ArchiveManager获取压缩包信息
            archive_manager = ArchiveManager()
            archive_info = archive_manager.get_archive_info(archive_path)
            
            if archive_info:
                # 进入压缩包查看模式
                self.file_browser.enter_archive_mode(archive_path, archive_info['files'])
                
                self.status_label.setText(f"📁 已进入压缩包查看模式: {os.path.basename(archive_path)}\n\n🎯 现在测试'打开当前文件夹'功能:\n• 右键任意文件 → 选择'打开当前文件夹'\n• 或者在空白处右键 → 选择'打开当前文件夹'\n\n✅ 预期结果:\n• 打开包含此压缩包的文件夹\n• 选中压缩包文件\n• 文件夹路径应为: {os.path.dirname(archive_path)}")
                self.status_label.setStyleSheet("""
                    QLabel {
                        background-color: #fff3e0;
                        padding: 15px;
                        border: 1px solid #ff9800;
                        border-radius: 8px;
                        font-size: 14px;
                        color: #f57c00;
                        font-weight: bold;
                    }
                """)
                
                # 启用退出按钮
                self.exit_archive_btn.setEnabled(True)
            else:
                self.status_label.setText("❌ 无法读取压缩包信息")
                
        except Exception as e:
            self.status_label.setText(f"❌ 打开压缩包失败: {str(e)}")
    
    def exit_archive_mode(self):
        """退出压缩包查看模式"""
        self.file_browser.exit_archive_mode()
        self.status_label.setText("✅ 已退出压缩包查看模式\n\n测试完成！可以重新创建测试压缩包继续测试。")
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: #e3f2fd;
                padding: 15px;
                border: 1px solid #90caf9;
                border-radius: 8px;
                font-size: 14px;
                color: #1976d2;
                font-weight: bold;
            }
        """)
        self.create_test_btn.setEnabled(True)
        self.exit_archive_btn.setEnabled(False)
    
    def closeEvent(self, event):
        """窗口关闭时清理临时文件"""
        if self.test_zip_path and os.path.exists(self.test_zip_path):
            try:
                parent_dir = os.path.dirname(self.test_zip_path)
                shutil.rmtree(parent_dir, ignore_errors=True)
                print(f"已清理测试文件: {parent_dir}")
            except Exception as e:
                print(f"清理测试文件失败: {e}")
        
        event.accept()


def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 设置应用程序属性
    app.setApplicationName("GudaZip 打开当前文件夹测试")
    app.setApplicationVersion("1.0")
    
    # 创建主窗口
    window = TestWindow()
    window.show()
    
    # 运行应用程序
    sys.exit(app.exec())


if __name__ == "__main__":
    main() 