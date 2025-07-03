#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GudaZip图标预览工具
用于查看生成的图标效果
"""

import sys
import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QLabel, QGridLayout, QFrame)
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtCore import Qt

class IconViewer(QMainWindow):
    """图标查看器"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle("GudaZip 图标预览")
        self.setFixedSize(600, 500)
        
        # 设置窗口图标
        try:
            icon_path = "icons/app.ico"
            if os.path.exists(icon_path):
                self.setWindowIcon(QIcon(icon_path))
        except:
            pass
        
        # 创建中央widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        layout = QVBoxLayout(central_widget)
        
        # 标题
        title = QLabel("GudaZip 应用程序图标")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #2980b9;
            margin: 10px;
        """)
        layout.addWidget(title)
        
        # 描述
        desc = QLabel("现代化压缩软件图标 - 蓝绿色调设计")
        desc.setAlignment(Qt.AlignCenter)
        desc.setStyleSheet("color: #666; margin-bottom: 20px;")
        layout.addWidget(desc)
        
        # 创建网格布局显示不同尺寸的图标
        grid_layout = QGridLayout()
        
        # 图标尺寸列表
        icon_sizes = [
            (16, "小图标"),
            (32, "标准图标"), 
            (48, "中等图标"),
            (64, "大图标"),
            (128, "特大图标"),
            (256, "超高清图标")
        ]
        
        row = 0
        col = 0
        for size, desc_text in icon_sizes:
            # 创建图标显示框架
            frame = QFrame()
            frame.setFrameStyle(QFrame.Box)
            frame.setStyleSheet("""
                QFrame {
                    border: 2px solid #ddd;
                    border-radius: 8px;
                    background-color: white;
                    margin: 5px;
                }
            """)
            
            frame_layout = QVBoxLayout(frame)
            
            # 图标显示
            try:
                icon_path = f"icons/gudazip_{size}x{size}.png"
                if os.path.exists(icon_path):
                    pixmap = QPixmap(icon_path)
                    icon_label = QLabel()
                    icon_label.setPixmap(pixmap)
                    icon_label.setAlignment(Qt.AlignCenter)
                    
                    # 如果图标太小，放大显示
                    if size < 48:
                        scaled_pixmap = pixmap.scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        icon_label.setPixmap(scaled_pixmap)
                    
                    frame_layout.addWidget(icon_label)
                else:
                    # 图标文件不存在
                    error_label = QLabel("图标缺失")
                    error_label.setAlignment(Qt.AlignCenter)
                    error_label.setStyleSheet("color: red;")
                    frame_layout.addWidget(error_label)
                    
            except Exception as e:
                error_label = QLabel(f"加载错误")
                error_label.setAlignment(Qt.AlignCenter)
                error_label.setStyleSheet("color: red;")
                frame_layout.addWidget(error_label)
            
            # 尺寸标签
            size_label = QLabel(f"{size}×{size}")
            size_label.setAlignment(Qt.AlignCenter)
            size_label.setStyleSheet("font-weight: bold; color: #2980b9;")
            frame_layout.addWidget(size_label)
            
            # 描述标签
            desc_label = QLabel(desc_text)
            desc_label.setAlignment(Qt.AlignCenter)
            desc_label.setStyleSheet("font-size: 10px; color: #666;")
            frame_layout.addWidget(desc_label)
            
            # 添加到网格
            grid_layout.addWidget(frame, row, col)
            
            col += 1
            if col >= 3:  # 每行3个
                col = 0
                row += 1
        
        layout.addLayout(grid_layout)
        
        # 图标信息
        info_text = """
        <b>设计特点:</b><br>
        • 现代化扁平设计风格<br>
        • 蓝绿色调，区别于主流压缩软件<br>
        • 文件夹形状 + 压缩指示器<br>
        • "GZ" 标识代表 GudaZip<br>
        • 支持多种尺寸，从16×16到256×256
        """
        
        info_label = QLabel(info_text)
        info_label.setStyleSheet("""
            background-color: #f8f9fa;
            border: 1px solid #ddd;
            border-radius: 6px;
            padding: 10px;
            margin: 10px;
        """)
        layout.addWidget(info_label)

def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 创建并显示图标查看器
    viewer = IconViewer()
    viewer.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()