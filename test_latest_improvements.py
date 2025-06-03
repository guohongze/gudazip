#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试最新的界面改进
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
    
    print("=== 最新界面改进测试 ===")
    print("1. 🏷️  标签样式修复：")
    print("   - '位置:' 和 '搜索:' 标签去掉边框")
    print("   - 使用透明背景，仅保留文字")
    print("")
    print("2. 📦 输入框边框恢复：")
    print("   - 位置下拉框加上1px边框 (#d0d0d0)")
    print("   - 搜索输入框加上1px边框")
    print("   - 悬停时边框变蓝色 (#90caf9)")
    print("   - 聚焦时边框深蓝色 (#1976d2)")
    print("")
    print("3. 📋 下拉框图标优化：")
    print("   - 图标字体增大到14px")
    print("   - 图标和文字间距增加 (📥  桌面)")
    print("   - 下拉项目高度增加到24px最小高度")
    print("")
    print("4. 📊 详细信息视图：")
    print("   - 默认显示：名称 | 大小 | 类型 | 修改日期")
    print("   - 名称列自适应宽度")
    print("   - 其他列根据内容调整")
    print("")
    print("5. 🎛️  视图切换按钮：")
    print("   - 位置最左侧的切换按钮")
    print("   - 📋 详细信息 ↔ 📱 图标视图")
    print("   - 带悬停和点击效果")
    print("")
    print("6. 📐 窗口尺寸调整：")
    print("   - 默认宽度：1100px → 1000px (减少100px)")
    print("   - 高度保持700px不变")
    print("")
    print("🧪 测试功能：")
    print("- 点击左上角按钮切换视图模式")
    print("- 观察详细信息的四列显示")
    print("- 测试位置框的下拉菜单(更大图标)")
    print("- 验证输入框的边框和悬停效果")
    print("- 检查标签的无边框透明样式")
    
    # 运行应用
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 