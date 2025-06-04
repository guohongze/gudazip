#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试右键菜单
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout
from PySide6.QtCore import Qt
from gudazip.ui.file_browser import FileBrowser

class DebugWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("右键菜单调试")
        self.resize(800, 600)
        
        layout = QVBoxLayout(self)
        
        # 创建文件浏览器
        self.browser = FileBrowser()
        layout.addWidget(self.browser)
        
        # 设置到桌面
        from PySide6.QtCore import QStandardPaths
        desktop_path = QStandardPaths.writableLocation(QStandardPaths.DesktopLocation)
        self.browser.set_root_path(desktop_path)
        
        print(f"📁 调试窗口已启动，当前路径: {desktop_path}")
        print("🖱️  请尝试右键点击：")
        print("   - 文件/文件夹上右键")
        print("   - 空白处右键")
        print("🔍 调试信息会在控制台显示")

if __name__ == "__main__":
    app = QApplication([])
    
    window = DebugWindow()
    window.show()
    
    app.exec() 