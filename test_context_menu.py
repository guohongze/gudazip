#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试右键菜单功能
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
    
    print("=== Windows 文件管理器右键菜单功能测试 ===")
    print("")
    print("✅ 已实现的右键菜单功能：")
    print("")
    print("📁 对文件夹右键：")
    print("   📂 打开文件夹 - 进入该文件夹")
    print("   ✏️ 重命名 - 重命名文件夹")
    print("   🗑️ 删除 - 删除文件夹及所有内容")
    print("   ➕ 新建文件夹 - 在此文件夹内新建子文件夹")
    print("   📄 新建文件 - 在此文件夹内新建文件")
    print("")
    print("📄 对文件右键：")
    print("   🔧 打开 - 用默认程序打开文件")
    print("   ✏️ 重命名 - 重命名文件")
    print("   🗑️ 删除 - 删除文件")
    print("")
    print("🖱️ 在空白处右键：")
    print("   ➕ 新建文件夹 - 在当前目录新建文件夹")
    print("   📄 新建文件 - 在当前目录新建文件")
    print("   🔄 刷新 - 刷新当前视图")
    print("")
    print("🎨 界面特色：")
    print("   🎯 每个菜单项都有彩色图标")
    print("   ⚠️ 删除操作有详细确认对话框")
    print("   ✅ 操作完成后有成功提示")
    print("   ❌ 错误处理和友好的错误提示")
    print("   🔄 操作后自动刷新视图")
    print("")
    print("🧪 测试步骤：")
    print("1. 在文件列表中右键点击文件夹")
    print("2. 在文件列表中右键点击文件")
    print("3. 在空白处右键")
    print("4. 测试新建、重命名、删除功能")
    print("5. 切换到图标视图也测试右键菜单")
    print("")
    print("💡 支持两种视图模式的右键菜单：")
    print("   📋 详细信息视图（默认）")
    print("   📱 图标视图（点击左上角按钮切换）")
    
    # 运行应用
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 