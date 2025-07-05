#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
默认压缩软件设置对话框
在软件启动时检测是否为默认压缩软件，并提供设置选项
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QCheckBox, QMessageBox, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QIcon
import qtawesome as qta

class DefaultAppDialog(QDialog):
    """默认压缩软件设置对话框"""
    
    def __init__(self, parent=None, file_association_manager=None, config_manager=None):
        super().__init__(parent)
        self.file_association_manager = file_association_manager
        self.config_manager = config_manager
        self.result_action = None  # 'set_default', 'skip', 'never_ask'
        
        self.init_ui()
        self.setup_connections()
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("设置默认压缩软件")
        self.setFixedSize(450, 280)
        self.setModal(True)
        
        # 主布局
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 图标和标题
        title_layout = QHBoxLayout()
        
        # 图标
        icon_label = QLabel()
        try:
            icon = qta.icon('fa5s.archive', color='#2196F3')
            icon_label.setPixmap(icon.pixmap(48, 48))
        except:
            icon_label.setText("📦")
            icon_label.setStyleSheet("font-size: 32px;")
        icon_label.setFixedSize(48, 48)
        icon_label.setAlignment(Qt.AlignCenter)
        
        # 标题
        title_label = QLabel("设置 GudaZip 为默认压缩软件")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        
        title_layout.addWidget(icon_label)
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        layout.addLayout(title_layout)
        
        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)
        
        # 说明文本
        desc_label = QLabel(
            "检测到 GudaZip 尚未设置为默认压缩软件。\n\n"
            "设置为默认压缩软件后，您可以：\n"
            "• 双击压缩文件直接用 GudaZip 打开\n"
            "• 享受更便捷的文件关联体验\n"
            "• 统一管理所有压缩文件格式"
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet(
            "QLabel { "
            "    color: #555; "
            "    line-height: 1.4; "
            "    padding: 10px; "
            "    background-color: #f8f9fa; "
            "    border: 1px solid #e9ecef; "
            "    border-radius: 6px; "
            "}"
        )
        layout.addWidget(desc_label)
        
        # 不再提示选项
        self.never_ask_cb = QCheckBox("不再提示此消息")
        self.never_ask_cb.setStyleSheet("QCheckBox { color: #666; }")
        layout.addWidget(self.never_ask_cb)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        # 设置为默认按钮
        self.set_default_btn = QPushButton("设置为默认")
        self.set_default_btn.setStyleSheet(
            "QPushButton {"
            "    background-color: #2196F3;"
            "    color: white;"
            "    border: none;"
            "    padding: 8px 16px;"
            "    border-radius: 4px;"
            "    font-weight: bold;"
            "}"
            "QPushButton:hover {"
            "    background-color: #1976D2;"
            "}"
            "QPushButton:pressed {"
            "    background-color: #1565C0;"
            "}"
        )
        
        # 跳过按钮
        self.skip_btn = QPushButton("跳过")
        self.skip_btn.setStyleSheet(
            "QPushButton {"
            "    background-color: #f5f5f5;"
            "    color: #333;"
            "    border: 1px solid #ddd;"
            "    padding: 8px 16px;"
            "    border-radius: 4px;"
            "}"
            "QPushButton:hover {"
            "    background-color: #e9ecef;"
            "}"
        )
        
        button_layout.addStretch()
        button_layout.addWidget(self.skip_btn)
        button_layout.addWidget(self.set_default_btn)
        
        layout.addLayout(button_layout)
    
    def setup_connections(self):
        """设置信号连接"""
        self.set_default_btn.clicked.connect(self.set_as_default)
        self.skip_btn.clicked.connect(self.skip_setting)
    
    def set_as_default(self):
        """设置为默认压缩软件"""
        try:
            # 关联所有支持的文件类型
            all_extensions = self.file_association_manager.supported_extensions
            
            result = self.file_association_manager.register_file_association(
                all_extensions, set_as_default=True
            )
            
            if result.get('success', False):
                success_count = result.get('success_count', 0)
                total_count = len(all_extensions)
                
                QMessageBox.information(
                    self, "设置成功", 
                    f"已成功关联 {success_count}/{total_count} 种文件类型。\n\n"
                    f"GudaZip 现在是您的默认压缩软件！"
                )
                
                # 保存设置
                if self.config_manager:
                    self.config_manager.set_config('file_association.associated_types', all_extensions)
                    self.config_manager.set_config('file_association.set_as_default', True)
                    
                    if self.never_ask_cb.isChecked():
                        self.config_manager.set_config('startup.never_ask_default_app', True)
                    
                    self.config_manager.save_configs()
                
                self.result_action = 'set_default'
                self.accept()
            else:
                QMessageBox.warning(
                    self, "设置失败", 
                    f"设置默认压缩软件失败：\n{result.get('message', '未知错误')}"
                )
        
        except Exception as e:
            QMessageBox.critical(
                self, "错误", 
                f"设置默认压缩软件时发生错误：\n{str(e)}"
            )
    
    def skip_setting(self):
        """跳过设置"""
        if self.config_manager and self.never_ask_cb.isChecked():
            self.config_manager.set_config('startup.never_ask_default_app', True)
            self.config_manager.save_configs()
        
        self.result_action = 'never_ask' if self.never_ask_cb.isChecked() else 'skip'
        self.reject()
    
    def get_result_action(self):
        """获取用户选择的操作"""
        return self.result_action