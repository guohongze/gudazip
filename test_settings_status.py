#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试设置对话框中的文件关联和右键菜单状态显示
"""

import sys
import os

# 添加src目录到Python路径
src_path = os.path.join(os.path.dirname(__file__), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from PySide6.QtWidgets import QApplication
from gudazip.ui.settings_dialog import SettingsDialog
from gudazip.main_window import MainWindow

def test_settings_status():
    """测试设置对话框状态显示"""
    app = QApplication(sys.argv)
    
    # 创建主窗口（作为父窗口）
    main_window = MainWindow()
    
    # 创建设置对话框
    settings_dialog = SettingsDialog(main_window)
    
    # 显示设置对话框
    settings_dialog.show()
    
    print("设置对话框已打开，请检查文件关联和右键菜单的状态显示")
    print("- 文件关联状态应该显示当前关联的文件类型数量")
    print("- 右键菜单状态应该显示是否已安装")
    
    # 运行应用程序
    sys.exit(app.exec())

if __name__ == "__main__":
    test_settings_status()