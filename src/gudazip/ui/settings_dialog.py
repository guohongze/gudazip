# -*- coding: utf-8 -*-
"""
设置对话框
提供用户配置管理界面
"""

from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, 
    QLabel, QPushButton, QLineEdit, QComboBox, QSpinBox, 
    QCheckBox, QSlider, QGroupBox, QFormLayout, QMessageBox,
    QFileDialog, QDialogButtonBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from ..core.config_manager import ConfigManager, get_config_manager


class SettingsDialog(QDialog):
    """GudaZip设置对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.config_manager = get_config_manager(self)
        self.init_ui()
        self.connect_signals()
        self.load_current_settings()
        
    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle("GudaZip 设置")
        self.setMinimumSize(500, 400)
        self.resize(600, 500)
        
        layout = QVBoxLayout(self)
        
        # 标题
        title = QLabel("程序设置")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("微软雅黑", 12, QFont.Bold))
        layout.addWidget(title)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # 创建各个设置页
        self.create_general_tab()
        self.create_appearance_tab()
        self.create_behavior_tab()
        self.create_window_tab()
        
        # 对话框按钮
        self.create_dialog_buttons(layout)
        
    def create_general_tab(self):
        """创建常规设置页"""
        tab = QWidget()
        layout = QFormLayout(tab)
        
        # 语言设置
        self.language_combo = QComboBox()
        self.language_combo.addItems(["中文 (zh_CN)", "English (en_US)"])
        layout.addRow("界面语言:", self.language_combo)
        
        # 启动路径
        self.startup_path_combo = QComboBox()
        startup_items = [
            ("桌面", "desktop"),
            ("上次位置", "last_location"), 
            ("主目录", "home"),
            ("文档", "documents")
        ]
        for text, value in startup_items:
            self.startup_path_combo.addItem(text, value)
        layout.addRow("启动路径:", self.startup_path_combo)
        
        # 自动检查更新
        self.check_updates_cb = QCheckBox()
        layout.addRow("自动检查更新:", self.check_updates_cb)
        
        # 删除确认
        self.confirm_delete_cb = QCheckBox()
        layout.addRow("删除时确认:", self.confirm_delete_cb)
        
        # 自动备份
        self.auto_backup_cb = QCheckBox()
        layout.addRow("自动备份:", self.auto_backup_cb)
        
        self.tab_widget.addTab(tab, "常规")
        
    def create_appearance_tab(self):
        """创建外观设置页"""
        tab = QWidget()
        layout = QFormLayout(tab)
        
        # 主题
        self.theme_combo = QComboBox()
        theme_items = [
            ("浅色主题", "light"),
            ("深色主题", "dark"),
            ("跟随系统", "auto"),
            ("自定义", "custom")
        ]
        for text, value in theme_items:
            self.theme_combo.addItem(text, value)
        layout.addRow("界面主题:", self.theme_combo)
        
        # 字体
        self.font_family_edit = QLineEdit()
        layout.addRow("字体:", self.font_family_edit)
        
        # 字体大小
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 20)
        self.font_size_spin.setSuffix(" pt")
        layout.addRow("字体大小:", self.font_size_spin)
        
        # 窗口透明度
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(30, 100)
        self.opacity_label = QLabel("100%")
        opacity_layout = QHBoxLayout()
        opacity_layout.addWidget(self.opacity_slider)
        opacity_layout.addWidget(self.opacity_label)
        opacity_widget = QWidget()
        opacity_widget.setLayout(opacity_layout)
        layout.addRow("窗口透明度:", opacity_widget)
        
        # 显示工具栏
        self.show_toolbar_cb = QCheckBox()
        layout.addRow("显示工具栏:", self.show_toolbar_cb)
        
        # 显示状态栏
        self.show_statusbar_cb = QCheckBox()
        layout.addRow("显示状态栏:", self.show_statusbar_cb)
        
        # 图标大小
        self.icon_size_combo = QComboBox()
        self.icon_size_combo.addItems(["16px", "24px", "32px"])
        layout.addRow("图标大小:", self.icon_size_combo)
        
        self.tab_widget.addTab(tab, "外观")
        
    def create_behavior_tab(self):
        """创建行为设置页"""
        tab = QWidget()
        layout = QFormLayout(tab)
        
        # 双击操作
        self.double_click_combo = QComboBox()
        double_click_items = [
            ("打开", "open"),
            ("选择", "select"),
            ("预览", "preview")
        ]
        for text, value in double_click_items:
            self.double_click_combo.addItem(text, value)
        layout.addRow("双击操作:", self.double_click_combo)
        
        # 显示隐藏文件
        self.show_hidden_cb = QCheckBox()
        layout.addRow("显示隐藏文件:", self.show_hidden_cb)
        
        # 自动刷新
        self.auto_refresh_cb = QCheckBox()
        layout.addRow("自动刷新:", self.auto_refresh_cb)
        
        # 文件视图模式
        self.view_mode_combo = QComboBox()
        self.view_mode_combo.addItems(["详细信息", "图标"])
        layout.addRow("默认视图模式:", self.view_mode_combo)
        
        # 排序列
        self.sort_column_spin = QSpinBox()
        self.sort_column_spin.setRange(0, 3)
        layout.addRow("默认排序列:", self.sort_column_spin)
        
        # 排序顺序
        self.sort_order_combo = QComboBox()
        self.sort_order_combo.addItems(["升序", "降序"])
        layout.addRow("排序顺序:", self.sort_order_combo)
        
        self.tab_widget.addTab(tab, "行为")
        
    def create_window_tab(self):
        """创建窗口设置页"""
        tab = QWidget()
        layout = QFormLayout(tab)
        
        # 记住窗口大小
        self.remember_size_cb = QCheckBox()
        layout.addRow("记住窗口大小:", self.remember_size_cb)
        
        # 记住窗口位置
        self.remember_position_cb = QCheckBox()
        layout.addRow("记住窗口位置:", self.remember_position_cb)
        
        # 启动时居中
        self.center_startup_cb = QCheckBox()
        layout.addRow("启动时居中:", self.center_startup_cb)
        
        # 默认宽度
        self.default_width_spin = QSpinBox()
        self.default_width_spin.setRange(800, 2000)
        self.default_width_spin.setSuffix(" px")
        layout.addRow("默认宽度:", self.default_width_spin)
        
        # 默认高度
        self.default_height_spin = QSpinBox()
        self.default_height_spin.setRange(600, 1500)
        self.default_height_spin.setSuffix(" px")
        layout.addRow("默认高度:", self.default_height_spin)
        
        self.tab_widget.addTab(tab, "窗口")
        
    def create_dialog_buttons(self, layout):
        """创建对话框按钮"""
        button_box = QDialogButtonBox()
        
        # 确定按钮
        ok_button = button_box.addButton("确定", QDialogButtonBox.AcceptRole)
        ok_button.clicked.connect(self.accept_settings)
        
        # 应用按钮
        apply_button = button_box.addButton("应用", QDialogButtonBox.ApplyRole)
        apply_button.clicked.connect(self.apply_settings)
        
        # 取消按钮
        cancel_button = button_box.addButton("取消", QDialogButtonBox.RejectRole)
        cancel_button.clicked.connect(self.reject)
        
        # 重置按钮
        reset_button = button_box.addButton("重置", QDialogButtonBox.ResetRole)
        reset_button.clicked.connect(self.reset_settings)
        
        layout.addWidget(button_box)
        
    def connect_signals(self):
        """连接信号"""
        # 透明度滑块
        self.opacity_slider.valueChanged.connect(
            lambda v: self.opacity_label.setText(f"{v}%")
        )
        
    def load_current_settings(self):
        """加载当前设置"""
        try:
            # 常规设置
            language = self.config_manager.get_config('general.language', 'zh_CN')
            if language == 'zh_CN':
                self.language_combo.setCurrentIndex(0)
            else:
                self.language_combo.setCurrentIndex(1)
                
            startup_path = self.config_manager.get_config('general.startup_path', 'desktop')
            for i in range(self.startup_path_combo.count()):
                if self.startup_path_combo.itemData(i) == startup_path:
                    self.startup_path_combo.setCurrentIndex(i)
                    break
                    
            self.check_updates_cb.setChecked(
                self.config_manager.get_config('general.check_updates', True)
            )
            self.confirm_delete_cb.setChecked(
                self.config_manager.get_config('general.confirm_delete', True)
            )
            self.auto_backup_cb.setChecked(
                self.config_manager.get_config('general.auto_backup', True)
            )
            
            # 外观设置
            theme = self.config_manager.get_config('appearance.theme', 'light')
            for i in range(self.theme_combo.count()):
                if self.theme_combo.itemData(i) == theme:
                    self.theme_combo.setCurrentIndex(i)
                    break
                    
            self.font_family_edit.setText(
                self.config_manager.get_config('appearance.font_family', '微软雅黑')
            )
            self.font_size_spin.setValue(
                self.config_manager.get_config('appearance.font_size', 9)
            )
            opacity_value = int(
                self.config_manager.get_config('appearance.window_opacity', 1.0) * 100
            )
            self.opacity_slider.setValue(opacity_value)
            self.opacity_label.setText(f"{opacity_value}%")
            
            self.show_toolbar_cb.setChecked(
                self.config_manager.get_config('appearance.show_toolbar', True)
            )
            self.show_statusbar_cb.setChecked(
                self.config_manager.get_config('appearance.show_statusbar', True)
            )
            
            icon_size = self.config_manager.get_config('appearance.icon_size', 16)
            self.icon_size_combo.setCurrentText(f"{icon_size}px")
            
            # 行为设置
            double_click = self.config_manager.get_config('behavior.double_click_action', 'open')
            for i in range(self.double_click_combo.count()):
                if self.double_click_combo.itemData(i) == double_click:
                    self.double_click_combo.setCurrentIndex(i)
                    break
                    
            self.show_hidden_cb.setChecked(
                self.config_manager.get_config('behavior.show_hidden_files', False)
            )
            self.auto_refresh_cb.setChecked(
                self.config_manager.get_config('behavior.auto_refresh', True)
            )
            self.view_mode_combo.setCurrentText(
                self.config_manager.get_config('behavior.file_view_mode', '详细信息')
            )
            self.sort_column_spin.setValue(
                self.config_manager.get_config('behavior.sort_column', 0)
            )
            self.sort_order_combo.setCurrentIndex(
                self.config_manager.get_config('behavior.sort_order', 0)
            )
            
            # 窗口设置
            self.remember_size_cb.setChecked(
                self.config_manager.get_config('window.remember_size', True)
            )
            self.remember_position_cb.setChecked(
                self.config_manager.get_config('window.remember_position', True)
            )
            self.center_startup_cb.setChecked(
                self.config_manager.get_config('window.center_on_startup', True)
            )
            self.default_width_spin.setValue(
                self.config_manager.get_config('window.default_width', 1200)
            )
            self.default_height_spin.setValue(
                self.config_manager.get_config('window.default_height', 800)
            )
            
        except Exception as e:
            QMessageBox.warning(self, "警告", f"加载设置时出错：{e}")
    
    def apply_settings(self):
        """应用设置"""
        try:
            # 常规设置
            language = "zh_CN" if self.language_combo.currentIndex() == 0 else "en_US"
            self.config_manager.set_config('general.language', language)
            
            startup_path = self.startup_path_combo.currentData()
            self.config_manager.set_config('general.startup_path', startup_path)
            
            self.config_manager.set_config('general.check_updates', self.check_updates_cb.isChecked())
            self.config_manager.set_config('general.confirm_delete', self.confirm_delete_cb.isChecked())
            self.config_manager.set_config('general.auto_backup', self.auto_backup_cb.isChecked())
            
            # 外观设置
            theme = self.theme_combo.currentData()
            self.config_manager.set_config('appearance.theme', theme)
            
            self.config_manager.set_config('appearance.font_family', self.font_family_edit.text())
            self.config_manager.set_config('appearance.font_size', self.font_size_spin.value())
            self.config_manager.set_config('appearance.window_opacity', self.opacity_slider.value() / 100.0)
            self.config_manager.set_config('appearance.show_toolbar', self.show_toolbar_cb.isChecked())
            self.config_manager.set_config('appearance.show_statusbar', self.show_statusbar_cb.isChecked())
            
            icon_size = int(self.icon_size_combo.currentText().replace('px', ''))
            self.config_manager.set_config('appearance.icon_size', icon_size)
            
            # 行为设置
            double_click = self.double_click_combo.currentData()
            self.config_manager.set_config('behavior.double_click_action', double_click)
            
            self.config_manager.set_config('behavior.show_hidden_files', self.show_hidden_cb.isChecked())
            self.config_manager.set_config('behavior.auto_refresh', self.auto_refresh_cb.isChecked())
            self.config_manager.set_config('behavior.file_view_mode', self.view_mode_combo.currentText())
            self.config_manager.set_config('behavior.sort_column', self.sort_column_spin.value())
            self.config_manager.set_config('behavior.sort_order', self.sort_order_combo.currentIndex())
            
            # 窗口设置
            self.config_manager.set_config('window.remember_size', self.remember_size_cb.isChecked())
            self.config_manager.set_config('window.remember_position', self.remember_position_cb.isChecked())
            self.config_manager.set_config('window.center_on_startup', self.center_startup_cb.isChecked())
            self.config_manager.set_config('window.default_width', self.default_width_spin.value())
            self.config_manager.set_config('window.default_height', self.default_height_spin.value())
            
            # 保存配置
            self.config_manager.save_configs()
            
            QMessageBox.information(self, "成功", "设置已保存")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存设置失败：{e}")
    
    def accept_settings(self):
        """确定并关闭"""
        self.apply_settings()
        self.accept()
    
    def reset_settings(self):
        """重置设置"""
        reply = QMessageBox.question(
            self, "确认重置",
            "确定要重置所有设置为默认值吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.config_manager.reset_all_configs()
            self.load_current_settings()
            QMessageBox.information(self, "成功", "设置已重置为默认值") 