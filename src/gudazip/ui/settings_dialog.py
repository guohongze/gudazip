# -*- coding: utf-8 -*-
"""
设置对话框
提供用户配置管理界面
"""

from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, 
    QLabel, QPushButton, QLineEdit, QComboBox, QSpinBox, 
    QCheckBox, QSlider, QGroupBox, QFormLayout, QMessageBox,
    QFileDialog, QDialogButtonBox, QListWidget, QListWidgetItem,
    QScrollArea, QGridLayout
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
import os
import sys

from ..core.config_manager import ConfigManager, get_config_manager
from ..core.file_association_manager import FileAssociationManager


class SettingsDialog(QDialog):
    """GudaZip设置对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.config_manager = get_config_manager(self)
        self.file_association_manager = FileAssociationManager()
        self.init_ui()
        self.connect_signals()
        self.load_current_settings()
        
    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle("选项")
        self.setMinimumSize(580, 650)  # 增大最小尺寸，确保所有内容正常显示
        self.resize(680, 750)
        
        layout = QVBoxLayout(self)
        
        # 标题
        title = QLabel("程序选项")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("微软雅黑", 12, QFont.Bold))
        layout.addWidget(title)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # 创建各个设置页
        self.create_general_settings_tab()
        self.create_file_association_tab()
        self.create_context_menu_tab()
        
        # 对话框按钮
        self.create_dialog_buttons(layout)
        
    def create_general_settings_tab(self):
        """创建通用设置页"""
        tab = QWidget()
        main_layout = QVBoxLayout(tab)
        
        # 常规设置组
        general_group = QGroupBox("常规设置")
        general_group.setMinimumHeight(80)  # 设置最小高度
        general_layout = QFormLayout(general_group)
        
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
        general_layout.addRow("启动路径:", self.startup_path_combo)
        
        # 删除确认
        self.confirm_delete_cb = QCheckBox()
        general_layout.addRow("删除时确认:", self.confirm_delete_cb)
        
        main_layout.addWidget(general_group)
        
        # 外观设置组
        appearance_group = QGroupBox("外观设置")
        appearance_group.setMinimumHeight(120)  # 设置最小高度
        appearance_layout = QFormLayout(appearance_group)
        
        # 字体
        self.font_family_edit = QLineEdit()
        appearance_layout.addRow("字体:", self.font_family_edit)
        
        # 字体大小
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 20)
        self.font_size_spin.setSuffix(" pt")
        appearance_layout.addRow("字体大小:", self.font_size_spin)
        
        # 窗口透明度
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(30, 100)
        self.opacity_label = QLabel("100%")
        opacity_layout = QHBoxLayout()
        opacity_layout.addWidget(self.opacity_slider)
        opacity_layout.addWidget(self.opacity_label)
        opacity_widget = QWidget()
        opacity_widget.setLayout(opacity_layout)
        appearance_layout.addRow("窗口透明度:", opacity_widget)
        
        main_layout.addWidget(appearance_group)
        
        # 行为设置组
        behavior_group = QGroupBox("行为设置")
        behavior_group.setMinimumHeight(180)  # 设置最小高度，避免内容被压缩
        behavior_layout = QFormLayout(behavior_group)
        
        # 双击操作
        self.double_click_combo = QComboBox()
        double_click_items = [
            ("打开", "open"),
            ("选择", "select"),
            ("预览", "preview")
        ]
        for text, value in double_click_items:
            self.double_click_combo.addItem(text, value)
        behavior_layout.addRow("双击操作:", self.double_click_combo)
        
        # 显示隐藏文件
        self.show_hidden_cb = QCheckBox()
        behavior_layout.addRow("显示隐藏文件:", self.show_hidden_cb)
        
        # 自动刷新
        self.auto_refresh_cb = QCheckBox()
        behavior_layout.addRow("自动刷新:", self.auto_refresh_cb)
        
        # 文件视图模式
        self.view_mode_combo = QComboBox()
        self.view_mode_combo.addItems(["详细信息", "图标"])
        behavior_layout.addRow("默认视图模式:", self.view_mode_combo)
        
        # 排序列
        self.sort_column_spin = QSpinBox()
        self.sort_column_spin.setRange(0, 3)
        behavior_layout.addRow("默认排序列:", self.sort_column_spin)
        
        # 排序顺序
        self.sort_order_combo = QComboBox()
        self.sort_order_combo.addItems(["升序", "降序"])
        behavior_layout.addRow("排序顺序:", self.sort_order_combo)
        
        main_layout.addWidget(behavior_group)
        
        # 窗口设置组
        window_group = QGroupBox("窗口设置")
        window_group.setMinimumHeight(160)  # 设置最小高度
        window_layout = QFormLayout(window_group)
        
        # 记住窗口大小
        self.remember_size_cb = QCheckBox()
        window_layout.addRow("记住窗口大小:", self.remember_size_cb)
        
        # 记住窗口位置
        self.remember_position_cb = QCheckBox()
        window_layout.addRow("记住窗口位置:", self.remember_position_cb)
        
        # 启动时居中
        self.center_startup_cb = QCheckBox()
        window_layout.addRow("启动时居中:", self.center_startup_cb)
        
        # 默认宽度
        self.default_width_spin = QSpinBox()
        self.default_width_spin.setRange(800, 2000)
        self.default_width_spin.setSuffix(" px")
        window_layout.addRow("默认宽度:", self.default_width_spin)
        
        # 默认高度
        self.default_height_spin = QSpinBox()
        self.default_height_spin.setRange(600, 1500)
        self.default_height_spin.setSuffix(" px")
        window_layout.addRow("默认高度:", self.default_height_spin)
        
        main_layout.addWidget(window_group)
        
        # 添加弹性空间
        main_layout.addStretch()
        
        self.tab_widget.addTab(tab, "通用设置")
        
    def create_file_association_tab(self):
        """创建文件关联设置页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 说明文字
        info_label = QLabel("选择要关联到 GudaZip 的文件类型：")
        info_label.setFont(QFont("微软雅黑", 9, QFont.Bold))
        layout.addWidget(info_label)
        
        # 创建滚动区域包含文件类型选择
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMaximumHeight(240)  # 减小高度，因为使用了更多列
        scroll_area.setMinimumHeight(180)  # 设置最小高度确保内容可见
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # 文件类型容器
        file_types_widget = QWidget()
        file_types_layout = QGridLayout(file_types_widget)
        file_types_layout.setSpacing(5)  # 减小间距以适应更多列
        file_types_layout.setContentsMargins(8, 8, 8, 8)  # 减小边距
        file_types_layout.setHorizontalSpacing(6)  # 设置水平间距
        file_types_layout.setVerticalSpacing(4)    # 设置垂直间距
        
        # 扩展的支持文件类型列表
        self.supported_types = [
            # 基础格式
            ('.zip', 'ZIP 压缩文件'),
            ('.rar', 'RAR 压缩文件'),
            ('.7z', '7-Zip 压缩文件'),
            
            # tar系列
            ('.tar', 'TAR 归档文件'),
            ('.tgz', 'TAR.GZ 压缩文件'),
            ('.tar.gz', 'TAR.GZ 压缩文件'),
            ('.tbz', 'TAR.BZ2 压缩文件'),
            ('.tbz2', 'TAR.BZ2 压缩文件'),
            ('.tar.bz2', 'TAR.BZ2 压缩文件'),
            ('.txz', 'TAR.XZ 压缩文件'),
            ('.tar.xz', 'TAR.XZ 压缩文件'),
            ('.taz', 'TAR.Z 压缩文件'),
            
            # 单一压缩格式
            ('.gz', 'GZIP 压缩文件'),
            ('.gzip', 'GZIP 压缩文件'),
            ('.bz2', 'BZIP2 压缩文件'),
            ('.bzip2', 'BZIP2 压缩文件'),
            ('.xz', 'XZ 压缩文件'),
            ('.lzma', 'LZMA 压缩文件'),
            ('.z', 'COMPRESS 压缩文件'),
            
            # 其他格式
            ('.cab', 'CAB 压缩文件'),
            ('.arj', 'ARJ 压缩文件'),
            ('.lzh', 'LZH 压缩文件'),
            ('.cpio', 'CPIO 归档文件'),
            ('.iso', 'ISO 镜像文件')
        ]
        
        # 创建复选框字典用于后续访问
        self.file_type_checkboxes = {}
        
        # 按6列排列文件类型复选框，更好地利用空间
        columns = 6
        for index, (ext, desc) in enumerate(self.supported_types):
            row = index // columns
            col = index % columns
            
            checkbox = QCheckBox(f"{ext}")
            checkbox.setToolTip(desc)  # 使用工具提示显示完整描述
            checkbox.setMinimumWidth(85)  # 减小最小宽度以适应更多列
            checkbox.setMaximumWidth(120)  # 设置最大宽度保持整齐
            
            # 设置样式让复选框更美观和紧凑
            checkbox.setStyleSheet("""
                QCheckBox {
                    font-size: 9pt;
                    padding: 1px 3px;
                    margin: 1px;
                }
                QCheckBox::indicator {
                    width: 13px;
                    height: 13px;
                }
            """)
            
            # 存储复选框引用
            self.file_type_checkboxes[ext] = checkbox
            
            file_types_layout.addWidget(checkbox, row, col)
        
        scroll_area.setWidget(file_types_widget)
        layout.addWidget(scroll_area)
        
        # 统计信息标签
        self.file_count_label = QLabel()
        self.file_count_label.setStyleSheet("color: #666; font-size: 8pt;")
        self.update_file_count_label()
        layout.addWidget(self.file_count_label)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        
        self.select_all_btn = QPushButton("全选")
        self.select_all_btn.clicked.connect(self.select_all_file_types)
        button_layout.addWidget(self.select_all_btn)
        
        self.deselect_all_btn = QPushButton("反选")
        self.deselect_all_btn.clicked.connect(self.deselect_all_file_types)
        button_layout.addWidget(self.deselect_all_btn)
        
        self.clear_all_btn = QPushButton("清除")
        self.clear_all_btn.clicked.connect(self.clear_all_file_types)
        button_layout.addWidget(self.clear_all_btn)
        
        # 添加常用格式快速选择
        common_btn = QPushButton("常用格式")
        common_btn.setToolTip("选择最常用的压缩格式: ZIP, RAR, 7Z, TAR.GZ")
        common_btn.clicked.connect(self.select_common_formats)
        button_layout.addWidget(common_btn)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # 默认程序设置
        default_group = QGroupBox("默认程序设置")
        default_layout = QVBoxLayout(default_group)
        
        self.set_as_default_cb = QCheckBox("将 GudaZip 设置为默认压缩程序")
        default_layout.addWidget(self.set_as_default_cb)
        
        # 警告提示
        warning_label = QLabel("⚠️ 修改文件关联需要管理员权限，某些操作可能需要重启资源管理器。")
        warning_label.setStyleSheet("color: #ff6600; font-size: 9pt;")
        warning_label.setWordWrap(True)
        default_layout.addWidget(warning_label)
        
        layout.addWidget(default_group)
        
        layout.addStretch()
        self.tab_widget.addTab(tab, "文件关联")
        
        # 连接复选框状态变化信号
        for checkbox in self.file_type_checkboxes.values():
            checkbox.stateChanged.connect(self.update_file_count_label)
        
    def create_context_menu_tab(self):
        """创建右键菜单设置页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 右键菜单设置
        context_menu_group = QGroupBox("右键菜单设置")
        context_menu_layout = QVBoxLayout(context_menu_group)
        
        self.enable_context_menu_cb = QCheckBox("启用文件右键菜单")
        context_menu_layout.addWidget(self.enable_context_menu_cb)
        
        # 右键菜单选项
        menu_options_layout = QVBoxLayout()
        menu_options_layout.setContentsMargins(20, 0, 0, 0)  # 添加左侧缩进
        
        self.context_menu_add_cb = QCheckBox("使用Gudazip压缩 (文件/文件夹)")
        self.context_menu_extract_cb = QCheckBox("解压功能 (压缩文件)")
        self.context_menu_open_cb = QCheckBox("打开压缩包 (压缩文件)")
        
        menu_options_layout.addWidget(self.context_menu_add_cb)
        menu_options_layout.addWidget(self.context_menu_extract_cb)
        menu_options_layout.addWidget(self.context_menu_open_cb)
        
        context_menu_layout.addLayout(menu_options_layout)
        
        # 右键菜单操作按钮
        context_menu_buttons = QHBoxLayout()
        
        self.install_context_menu_btn = QPushButton("安装右键菜单")
        self.install_context_menu_btn.clicked.connect(self.install_context_menu)
        context_menu_buttons.addWidget(self.install_context_menu_btn)
        
        self.uninstall_context_menu_btn = QPushButton("卸载右键菜单")
        self.uninstall_context_menu_btn.clicked.connect(self.uninstall_context_menu)
        context_menu_buttons.addWidget(self.uninstall_context_menu_btn)
        
        context_menu_buttons.addStretch()
        context_menu_layout.addLayout(context_menu_buttons)
        
        # 右键菜单警告提示
        context_warning_label = QLabel("⚠️ 右键菜单功能需要管理员权限，修改后可能需要重新登录或重启资源管理器。")
        context_warning_label.setStyleSheet("color: #ff6600; font-size: 9pt;")
        context_warning_label.setWordWrap(True)
        context_menu_layout.addWidget(context_warning_label)
        
        layout.addWidget(context_menu_group)
        
        layout.addStretch()
        self.tab_widget.addTab(tab, "右键菜单")
        
    def select_all_file_types(self):
        """全选文件类型"""
        for checkbox in self.file_type_checkboxes.values():
            checkbox.setChecked(True)
            
    def deselect_all_file_types(self):
        """反选文件类型"""
        for checkbox in self.file_type_checkboxes.values():
            current_state = checkbox.checkState()
            new_state = Qt.Unchecked if current_state == Qt.Checked else Qt.Checked
            checkbox.setCheckState(new_state)
            
    def clear_all_file_types(self):
        """清除所有选择"""
        for checkbox in self.file_type_checkboxes.values():
            checkbox.setChecked(False)
            
    def select_common_formats(self):
        """快速选择常用压缩格式"""
        common_formats = ['.zip', '.rar', '.7z', '.tar.gz']
        for ext in common_formats:
            if ext in self.file_type_checkboxes:
                self.file_type_checkboxes[ext].setChecked(True)
        self.update_file_count_label()
        
    def update_file_count_label(self):
        """更新文件类型统计标签"""
        checked_count = sum(1 for cb in self.file_type_checkboxes.values() if cb.isChecked())
        total_count = len(self.file_type_checkboxes)
        self.file_count_label.setText(f"已选择 {checked_count} 个文件类型，共 {total_count} 个支持格式。")
        
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
        
        # 右键菜单启用状态变化
        self.enable_context_menu_cb.stateChanged.connect(self.on_context_menu_enabled_changed)
        
    def on_context_menu_enabled_changed(self, state):
        """右键菜单启用状态变化时的处理"""
        enabled = state == 2  # Qt.Checked = 2
        
        # 启用/禁用子选项
        self.context_menu_add_cb.setEnabled(enabled)
        self.context_menu_extract_cb.setEnabled(enabled)
        self.context_menu_open_cb.setEnabled(enabled)
        
        # 启用/禁用操作按钮
        self.install_context_menu_btn.setEnabled(enabled)
        self.uninstall_context_menu_btn.setEnabled(enabled)
        
    def load_current_settings(self):
        """加载当前设置"""
        try:
            # 常规设置
            startup_path = self.config_manager.get_config('general.startup_path', 'desktop')
            for i in range(self.startup_path_combo.count()):
                if self.startup_path_combo.itemData(i) == startup_path:
                    self.startup_path_combo.setCurrentIndex(i)
                    break
                    
            self.confirm_delete_cb.setChecked(
                self.config_manager.get_config('general.confirm_delete', True)
            )
            
            # 外观设置
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
            
            # 文件关联设置
            associated_types = self.config_manager.get_config('file_association.associated_types', [])
            
            # 检查当前系统中的文件关联状态
            all_extensions = [ext for ext, _ in self.supported_types]
            current_associations = self.file_association_manager.check_association_status(all_extensions)
            
            for ext, checkbox in self.file_type_checkboxes.items():
                # 优先显示系统实际关联状态，其次是配置文件中的状态
                if current_associations.get(ext, False):
                    checkbox.setCheckState(Qt.Checked)
                elif ext in associated_types:
                    checkbox.setCheckState(Qt.Checked)
                else:
                    checkbox.setCheckState(Qt.Unchecked)
            
            self.set_as_default_cb.setChecked(
                self.config_manager.get_config('file_association.set_as_default', False)
            )
            
            # 右键菜单设置
            context_menu_installed = self.file_association_manager.check_context_menu_status_simple()
            
            self.enable_context_menu_cb.setChecked(
                context_menu_installed or self.config_manager.get_config('context_menu.enabled', False)
            )
            self.context_menu_add_cb.setChecked(
                self.config_manager.get_config('context_menu.add', True)
            )
            self.context_menu_extract_cb.setChecked(
                self.config_manager.get_config('context_menu.extract', True)
            )
            self.context_menu_open_cb.setChecked(
                self.config_manager.get_config('context_menu.open', True)
            )
            
            # 初始化右键菜单UI状态
            self.on_context_menu_enabled_changed(
                2 if self.enable_context_menu_cb.isChecked() else 0
            )
            
        except Exception as e:
            QMessageBox.warning(self, "警告", f"加载设置时出错：{e}")
    
    def apply_settings(self):
        """应用设置"""
        try:
            # 常规设置
            startup_path = self.startup_path_combo.currentData()
            self.config_manager.set_config('general.startup_path', startup_path)
            
            self.config_manager.set_config('general.confirm_delete', self.confirm_delete_cb.isChecked())
            
            # 外观设置
            self.config_manager.set_config('appearance.font_family', self.font_family_edit.text())
            self.config_manager.set_config('appearance.font_size', self.font_size_spin.value())
            self.config_manager.set_config('appearance.window_opacity', self.opacity_slider.value() / 100.0)
            
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
            
            # 文件关联设置
            associated_types = []
            for ext, checkbox in self.file_type_checkboxes.items():
                if checkbox.isChecked():
                    associated_types.append(ext)
            
            self.config_manager.set_config('file_association.associated_types', associated_types)
            self.config_manager.set_config('file_association.set_as_default', self.set_as_default_cb.isChecked())
            
            # 右键菜单设置
            self.config_manager.set_config('context_menu.enabled', self.enable_context_menu_cb.isChecked())
            self.config_manager.set_config('context_menu.add', self.context_menu_add_cb.isChecked())
            self.config_manager.set_config('context_menu.extract', self.context_menu_extract_cb.isChecked())
            self.config_manager.set_config('context_menu.open', self.context_menu_open_cb.isChecked())
            
            # 保存配置
            self.config_manager.save_configs()
            
            # 处理文件关联（静默）
            if associated_types:
                self.file_association_manager.register_file_association(
                    associated_types, 
                    self.set_as_default_cb.isChecked()
                )
            
            # 关闭对话框（不显示提示消息）
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存设置失败：{e}")
    
    def accept_settings(self):
        """确定并关闭"""
        try:
            # 应用设置但不显示提示消息
            startup_path = self.startup_path_combo.currentData()
            self.config_manager.set_config('general.startup_path', startup_path)
            
            self.config_manager.set_config('general.confirm_delete', self.confirm_delete_cb.isChecked())
            
            # 外观设置
            self.config_manager.set_config('appearance.font_family', self.font_family_edit.text())
            self.config_manager.set_config('appearance.font_size', self.font_size_spin.value())
            self.config_manager.set_config('appearance.window_opacity', self.opacity_slider.value() / 100.0)
            
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
            
            # 文件关联设置
            associated_types = []
            for ext, checkbox in self.file_type_checkboxes.items():
                if checkbox.isChecked():
                    associated_types.append(ext)
            
            self.config_manager.set_config('file_association.associated_types', associated_types)
            self.config_manager.set_config('file_association.set_as_default', self.set_as_default_cb.isChecked())
            
            # 右键菜单设置
            self.config_manager.set_config('context_menu.enabled', self.enable_context_menu_cb.isChecked())
            self.config_manager.set_config('context_menu.add', self.context_menu_add_cb.isChecked())
            self.config_manager.set_config('context_menu.extract', self.context_menu_extract_cb.isChecked())
            self.config_manager.set_config('context_menu.open', self.context_menu_open_cb.isChecked())
            
            # 保存配置
            self.config_manager.save_configs()
            
            # 处理文件关联（静默）
            if associated_types:
                self.file_association_manager.register_file_association(
                    associated_types, 
                    self.set_as_default_cb.isChecked()
                )
            
            # 关闭对话框（不显示提示消息）
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存设置失败：{e}")
    
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
    
    def install_context_menu(self):
        """安装右键菜单"""
        try:
            # 获取选中的菜单选项 - 简化版本
            menu_options = {
                'add': self.context_menu_add_cb.isChecked(),
                'extract': self.context_menu_extract_cb.isChecked(),
                'open': self.context_menu_open_cb.isChecked()
            }
            
            result = self.file_association_manager.install_context_menu(menu_options)
            if result.get("success", False):
                QMessageBox.information(self, "成功", 
                    f"{result.get('message', '右键菜单安装成功！')}\n"
                    "注意：新的安全右键菜单只针对压缩文件格式，"
                    "不会影响系统对象如'我的电脑'、'网络'等。")
                self.enable_context_menu_cb.setChecked(True)
            else:
                message = result.get('message', '右键菜单安装失败')
                error_code = result.get('error', '')
                
                if error_code == 'INSUFFICIENT_PRIVILEGES':
                    # 权限不足，提供重启为管理员的选项
                    reply = QMessageBox.question(
                        self, "需要管理员权限",
                        f"{message}\n\n"
                        "是否要以管理员身份重新启动程序？\n"
                        "点击'是'将以管理员权限重启程序。",
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.Yes
                    )
                    
                    if reply == QMessageBox.Yes:
                        try:
                            import ctypes
                            import sys
                            # 以管理员权限重启程序
                            ctypes.windll.shell32.ShellExecuteW(
                                None, "runas", sys.executable, 
                                f'"{sys.argv[0]}"' if len(sys.argv) > 0 else "", 
                                None, 1
                            )
                            # 关闭当前程序
                            sys.exit(0)
                        except Exception as e:
                            QMessageBox.critical(self, "错误", f"无法以管理员权限启动：{e}")
                else:
                    QMessageBox.warning(self, "失败", f"{message}\n\n"
                        "新版本使用安全的PyWin32接口，避免对系统造成影响。")
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"安装右键菜单时发生错误：{str(e)}")
    
    def uninstall_context_menu(self):
        """卸载右键菜单"""
        try:
            reply = QMessageBox.question(
                self, "确认卸载",
                "确定要卸载GudaZip右键菜单吗？\n"
                "这将移除所有与GudaZip相关的右键菜单项。",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                result = self.file_association_manager.uninstall_context_menu()
                if result.get("success", False):
                    QMessageBox.information(self, "成功", 
                        f"{result.get('message', '右键菜单卸载成功！')}")
                    self.enable_context_menu_cb.setChecked(False)
                    # 清除所有选项
                    self.context_menu_add_cb.setChecked(False)
                    self.context_menu_extract_cb.setChecked(False)
                    self.context_menu_open_cb.setChecked(False)
                else:
                    message = result.get('message', '右键菜单卸载失败')
                    QMessageBox.warning(self, "失败", f"{message}")
                    
        except Exception as e:
            QMessageBox.critical(self, "错误", f"卸载右键菜单时发生错误：{str(e)}")