#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试改进后的设置功能
包括：
1. 默认压缩软件检测对话框
2. 改进的文件关联逻辑
3. 优化的状态显示
"""

import sys
import os

# 添加模块路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget, QPushButton, QLabel
from PySide6.QtCore import Qt

def test_default_app_dialog():
    """测试默认压缩软件设置对话框"""
    try:
        from gudazip.ui.default_app_dialog import DefaultAppDialog
        from gudazip.main_window import MainWindow
        
        # 创建主窗口（获取必要的管理器）
        main_window = MainWindow()
        
        # 创建默认应用设置对话框
        dialog = DefaultAppDialog(
            parent=main_window,
            file_association_manager=main_window.file_association_manager,
            config_manager=main_window.config_manager
        )
        
        print("\n=== 测试默认压缩软件设置对话框 ===")
        print("对话框已创建，即将显示...")
        
        result = dialog.exec()
        action = dialog.get_result_action()
        
        print(f"对话框结果: {result}")
        print(f"用户操作: {action}")
        
        return True
        
    except Exception as e:
        print(f"测试默认应用对话框失败: {e}")
        return False

def test_settings_dialog():
    """测试改进后的设置对话框"""
    try:
        from gudazip.ui.settings_dialog import SettingsDialog
        from gudazip.main_window import MainWindow
        
        # 创建主窗口
        main_window = MainWindow()
        
        # 创建设置对话框
        dialog = SettingsDialog(
            parent=main_window,
            config_manager=main_window.config_manager,
            file_association_manager=main_window.file_association_manager
        )
        
        print("\n=== 测试改进后的设置对话框 ===")
        print("设置对话框已创建，即将显示...")
        print("请检查以下改进：")
        print("1. 移除了'设置为默认压缩软件'选项")
        print("2. 状态显示使用正常字体和大小")
        print("3. 文件关联逻辑已优化")
        
        dialog.show()
        
        return True
        
    except Exception as e:
        print(f"测试设置对话框失败: {e}")
        return False

def test_file_association_logic():
    """测试文件关联逻辑"""
    try:
        from gudazip.main_window import MainWindow
        
        # 创建主窗口
        main_window = MainWindow()
        file_manager = main_window.file_association_manager
        
        print("\n=== 测试文件关联逻辑 ===")
        
        # 获取当前已关联的扩展名
        current_associated = file_manager.get_associated_extensions()
        print(f"当前已关联的文件类型: {current_associated}")
        
        # 获取所有支持的扩展名
        all_extensions = file_manager.supported_extensions
        print(f"所有支持的文件类型: {all_extensions}")
        
        # 计算关联比例
        if all_extensions:
            ratio = len(current_associated) / len(all_extensions)
            print(f"关联比例: {ratio:.2%}")
            
            if ratio >= 0.8:
                print("✅ 已是默认压缩软件（关联80%以上文件类型）")
            else:
                print("❌ 不是默认压缩软件（关联少于80%文件类型）")
        
        return True
        
    except Exception as e:
        print(f"测试文件关联逻辑失败: {e}")
        return False

def main():
    """主测试函数"""
    app = QApplication(sys.argv)
    app.setApplicationName("GudaZip Settings Test")
    
    # 创建测试窗口
    test_window = QWidget()
    test_window.setWindowTitle("GudaZip 改进功能测试")
    test_window.setFixedSize(400, 300)
    
    layout = QVBoxLayout(test_window)
    
    # 标题
    title_label = QLabel("GudaZip 改进功能测试")
    title_label.setAlignment(Qt.AlignCenter)
    title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px;")
    layout.addWidget(title_label)
    
    # 说明
    desc_label = QLabel(
        "点击下面的按钮测试各项改进功能：\n\n"
        "1. 默认压缩软件检测对话框\n"
        "2. 改进后的设置对话框\n"
        "3. 文件关联逻辑测试"
    )
    desc_label.setWordWrap(True)
    desc_label.setStyleSheet("margin: 10px; color: #666;")
    layout.addWidget(desc_label)
    
    # 测试按钮
    btn1 = QPushButton("测试默认压缩软件对话框")
    btn1.clicked.connect(test_default_app_dialog)
    layout.addWidget(btn1)
    
    btn2 = QPushButton("测试改进后的设置对话框")
    btn2.clicked.connect(test_settings_dialog)
    layout.addWidget(btn2)
    
    btn3 = QPushButton("测试文件关联逻辑")
    btn3.clicked.connect(test_file_association_logic)
    layout.addWidget(btn3)
    
    # 退出按钮
    exit_btn = QPushButton("退出")
    exit_btn.clicked.connect(app.quit)
    exit_btn.setStyleSheet("background-color: #f44336; color: white; margin-top: 10px;")
    layout.addWidget(exit_btn)
    
    test_window.show()
    
    print("\n=== GudaZip 改进功能测试 ===")
    print("测试窗口已启动，请使用界面进行测试")
    print("\n改进内容：")
    print("1. 安装时默认关联所有可处理文件类型")
    print("2. 用户手动选择后只关联选定文件")
    print("3. 移除了冗余的'设置为默认压缩软件'选项")
    print("4. 启动时检测是否为默认压缩软件")
    print("5. 状态提示使用正常字体和大小")
    
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())