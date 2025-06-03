#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GudaZip - Python桌面压缩管理器
主入口文件
"""

import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTranslator, QLocale
from PySide6.QtGui import QIcon

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from gudazip.main_window import MainWindow


def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 设置应用程序信息
    app.setApplicationName("GudaZip")
    app.setApplicationVersion("0.1.0")
    app.setOrganizationName("GudaZip Team")
    
    # 设置中文语言
    translator = QTranslator()
    locale = QLocale.system()
    if translator.load(locale, "gudazip", "_", "resources/translations"):
        app.installTranslator(translator)
    
    # 创建主窗口
    window = MainWindow()
    window.show()
    
    return app.exec()


if __name__ == "__main__":
    sys.exit(main()) 