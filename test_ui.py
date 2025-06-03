#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GudaZip UI测试脚本
验证美化后的界面是否正常工作
"""

import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from PySide6.QtWidgets import QApplication
from gudazip.main_window import MainWindow

def test_ui():
    """测试用户界面"""
    print("🎨 启动GudaZip美化界面测试...")
    
    app = QApplication(sys.argv)
    
    try:
        # 创建主窗口
        window = MainWindow()
        window.show()
        
        print("✅ 界面启动成功！")
        print("🎯 界面特性:")
        print("   - ✅ 快捷操作面板")
        print("   - ✅ 图标化按钮")
        print("   - ✅ 美化工具栏")
        print("   - ✅ 响应式布局")
        print("\n📋 可用操作:")
        print("   - 🆕 新建压缩包 (Ctrl+N)")
        print("   - 📂 打开压缩包 (Ctrl+O)")
        print("   - 📤 解压到... (Ctrl+E)")
        print("   - ➕ 添加文件 (Ctrl+A)")
        print("   - ✅ 测试压缩包 (Ctrl+T)")
        print("\n💡 提示: 关闭窗口退出测试")
        
        # 运行应用程序
        return app.exec()
        
    except Exception as e:
        print(f"❌ 界面启动失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(test_ui()) 