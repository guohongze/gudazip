#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试新的用户界面
"""

import sys
import os
from PySide6.QtWidgets import QApplication

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from gudazip.main_window import MainWindow

def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 设置应用信息
    app.setApplicationName("GudaZip")
    app.setApplicationVersion("0.1.0")
    
    # 创建并显示主窗口
    window = MainWindow()
    window.show()
    
    print("=== 新界面功能测试 ===")
    print("1. 右侧标签页已删除，只保留左侧文件浏览器")
    print("2. 左侧文件浏览器占据整个窗口空间")
    print("3. 默认路径设置为桌面")
    print("4. 顶部有路径下拉选择框，包含常用路径")
    print("5. 支持手动输入路径或从下拉列表选择")
    print("=========================")
    
    # 运行应用
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 