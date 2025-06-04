# -*- coding: utf-8 -*-
"""
工具栏组件
独立的工具栏Widget，包含导航按钮、路径选择、搜索等功能
"""

from PySide6.QtCore import Qt, QStandardPaths, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QComboBox, 
    QLabel, QLineEdit
)
import qtawesome as qta
import os


class ToolbarWidget(QWidget):
    """工具栏组件 - 负责顶部导航工具栏的所有UI"""
    
    # 信号定义 - 向FileBrowser发送操作请求
    view_toggle_requested = Signal()  # 请求切换视图模式
    go_up_requested = Signal()  # 请求返回上级目录
    location_changed = Signal(str)  # 位置变更（下拉框选择）
    manual_path_requested = Signal()  # 手动输入路径（回车键）
    search_text_changed = Signal(str)  # 搜索文本变更
    refresh_requested = Signal()  # 请求刷新
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_view_mode = "详细信息"  # 当前视图模式
        self.init_ui()
        
    def init_ui(self):
        """初始化用户界面"""
        # 创建水平布局
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # 视图切换按钮（最左侧）
        self.view_toggle_btn = QPushButton()
        self.view_toggle_btn.setIcon(qta.icon('fa5s.list', color='#333'))
        self.view_toggle_btn.setToolTip("切换到图标视图")
        self.view_toggle_btn.setFixedSize(40, 40)
        self.view_toggle_btn.setStyleSheet("""
            QPushButton {
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                background-color: #f8f9fa;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #e3f2fd;
                border-color: #90caf9;
            }
            QPushButton:pressed {
                background-color: #bbdefb;
                border-color: #64b5f6;
            }
        """)
        self.view_toggle_btn.clicked.connect(self.view_toggle_requested.emit)
        layout.addWidget(self.view_toggle_btn)
        
        # 向上一级目录按钮
        self.up_button = QPushButton()
        self.up_button.setIcon(qta.icon('fa5s.arrow-up', color='#333'))
        self.up_button.setToolTip("上一级目录")
        self.up_button.setFixedSize(40, 40)
        self.up_button.setStyleSheet("""
            QPushButton {
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                background-color: #f8f9fa;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #e3f2fd;
                border-color: #90caf9;
            }
            QPushButton:pressed {
                background-color: #bbdefb;
                border-color: #64b5f6;
            }
            QPushButton:disabled {
                background-color: #f5f5f5;
                color: #ccc;
                border-color: #e0e0e0;
            }
        """)
        self.up_button.clicked.connect(self.go_up_requested.emit)
        layout.addWidget(self.up_button)
        
        # 位置标签和下拉框
        location_label = QLabel("位置:")
        location_label.setStyleSheet("""
            QLabel {
                font-weight: bold;
                color: #333;
                margin-right: 5px;
                margin-left: 8px;
                border: none;
                background: transparent;
                font-size: 15px;
            }
        """)
        layout.addWidget(location_label)
        
        # 路径下拉选择框
        self.path_combo = QComboBox()
        self.path_combo.setEditable(True)
        self.path_combo.setMinimumWidth(350)
        self.path_combo.setMaximumHeight(40)
        self.path_combo.setStyleSheet("""
            QComboBox {
                border: 1px solid #d0d0d0;
                padding: 6px 12px;
                background-color: white;
                font-size: 15px;
                min-height: 25px;
                border-radius: 4px;
            }
            QComboBox:hover {
                border-color: #90caf9;
            }
            QComboBox:focus {
                border-color: #1976d2;
                outline: none;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 25px;
                border-left-width: 1px;
                border-left-color: #d0d0d0;
                border-left-style: solid;
                border-top-right-radius: 4px;
                border-bottom-right-radius: 4px;
                background-color: #f8f9fa;
            }
            QComboBox::down-arrow {
                width: 0; 
                height: 0; 
                border-left: 6px solid transparent;
                border-right: 6px solid transparent; 
                border-top: 6px solid #666;
            }
            QComboBox::down-arrow:hover {
                border-top-color: #333;
            }
            QComboBox QAbstractItemView {
                border: 2px solid #ccc;
                border-radius: 6px;
                background-color: white;
                selection-background-color: #e3f2fd;
                outline: none;
                font-size: 23px;
                padding: 5px;
            }
            QComboBox QAbstractItemView::item {
                padding: 10px 15px;
                min-height: 35px;
            }
        """)
        
        # 初始化路径下拉框
        self._init_path_combo()
        
        # 连接信号 - 通过信号发送到FileBrowser处理
        self.path_combo.currentTextChanged.connect(self.location_changed.emit)
        self.path_combo.lineEdit().returnPressed.connect(self.manual_path_requested.emit)
        
        layout.addWidget(self.path_combo)
        
        # 搜索框紧随位置框
        search_label = QLabel("搜索:")
        search_label.setStyleSheet("""
            QLabel {
                font-weight: bold;
                color: #333;
                margin-left: 15px;
                margin-right: 5px;
                border: none;
                background: transparent;
                font-size: 15px;
            }
        """)
        layout.addWidget(search_label)
        
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("在当前位置中搜索...")
        self.search_box.textChanged.connect(self.search_text_changed.emit)
        self.search_box.setMinimumWidth(280)
        self.search_box.setMaximumWidth(350)
        self.search_box.setMaximumHeight(40)
        self.search_box.setStyleSheet("""
            QLineEdit {
                border: 1px solid #d0d0d0;
                padding: 6px 12px;
                background-color: white;
                font-size: 15px;
                min-height: 25px;
                border-radius: 4px;
            }
            QLineEdit:hover {
                border-color: #90caf9;
            }
            QLineEdit:focus {
                border-color: #1976d2;
                outline: none;
            }
            QLineEdit::placeholder {
                color: #999;
                font-style: italic;
                font-size: 14px;
            }
        """)
        layout.addWidget(self.search_box)
        
        # 添加刷新按钮
        self.refresh_button = QPushButton()
        self.refresh_button.setIcon(qta.icon('fa5s.sync-alt', color='#333'))
        self.refresh_button.setToolTip("刷新 (F5)")
        self.refresh_button.setFixedSize(40, 40)
        self.refresh_button.setStyleSheet("""
            QPushButton {
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                background-color: #f8f9fa;
                padding: 8px;
                margin-left: 8px;
            }
            QPushButton:hover {
                background-color: #e3f2fd;
                border-color: #90caf9;
            }
            QPushButton:pressed {
                background-color: #bbdefb;
                border-color: #64b5f6;
            }
        """)
        self.refresh_button.clicked.connect(self.refresh_requested.emit)
        layout.addWidget(self.refresh_button)
        
        # 添加弹性空间到最右侧
        layout.addStretch()
        
        # 为整个工具栏添加样式
        self.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 8px;
                margin: 2px;
            }
        """)
        
    def _init_path_combo(self):
        """初始化路径下拉框"""
        desktop_path = QStandardPaths.writableLocation(QStandardPaths.DesktopLocation)
        documents_path = QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation)
        downloads_path = QStandardPaths.writableLocation(QStandardPaths.DownloadLocation)
        pictures_path = QStandardPaths.writableLocation(QStandardPaths.PicturesLocation)
        videos_path = QStandardPaths.writableLocation(QStandardPaths.MoviesLocation)
        music_path = QStandardPaths.writableLocation(QStandardPaths.MusicLocation)
        home_path = QStandardPaths.writableLocation(QStandardPaths.HomeLocation)
        
        # 添加Windows11风格图标到下拉框
        windows_paths = [
            ("🖥️  桌面", desktop_path),
            ("💻  此电脑", ""),  # 特殊处理
            ("📂  文档", documents_path),
            ("🖼️  图片", pictures_path),
            ("⬇️  下载", downloads_path),
            ("🎬  视频", videos_path),
            ("🎵  音乐", music_path),
            ("👤  用户", home_path),
        ]
        
        for name, path in windows_paths:
            if path == "" or os.path.exists(path):
                if path == "":
                    # 此电脑特殊处理
                    self.path_combo.addItem(name, "ThisPC")
                else:
                    self.path_combo.addItem(name, path)
    
    def update_view_mode(self, mode):
        """更新视图模式显示"""
        self.current_view_mode = mode
        if mode == "详细信息":
            self.view_toggle_btn.setIcon(qta.icon('fa5s.list', color='#333'))
            self.view_toggle_btn.setToolTip("切换到图标视图")
        else:  # 图标模式
            self.view_toggle_btn.setIcon(qta.icon('fa5s.th', color='#333'))
            self.view_toggle_btn.setToolTip("切换到详细信息视图")
    
    def update_up_button_state(self, enabled, tooltip="上一级目录"):
        """更新向上按钮的状态"""
        self.up_button.setEnabled(enabled)
        self.up_button.setToolTip(tooltip)
    
    def update_path_display(self, path, use_signal_manager=None, block_context=None):
        """更新路径显示"""
        # 如果提供了信号管理器，使用它来安全更新
        if use_signal_manager and block_context:
            with use_signal_manager.block_signal(
                self.path_combo.currentTextChanged,
                self.location_changed.emit,
                block_context
            ):
                self._set_path_display(path)
        else:
            self._set_path_display(path)
    
    def _set_path_display(self, path):
        """设置路径显示的内部方法"""
        # 首先检查是否在预设列表中
        path_found = False
        for i in range(self.path_combo.count()):
            if self.path_combo.itemData(i) == path:
                self.path_combo.setCurrentIndex(i)
                path_found = True
                break
        
        if not path_found:
            # 如果路径不在预设列表中，直接设置文本
            self.path_combo.setCurrentText(path)
    
    def get_path_text(self):
        """获取当前路径文本"""
        return self.path_combo.lineEdit().text().strip()
    
    def get_path_data(self):
        """获取当前选中项的数据"""
        return self.path_combo.currentData()
    
    def clear_search(self):
        """清空搜索框"""
        self.search_box.clear() 