# -*- coding: utf-8 -*-
"""
创建压缩包对话框
允许用户选择文件和设置压缩选项
"""

import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QListWidget, QListWidgetItem, QGroupBox,
    QComboBox, QCheckBox, QProgressBar, QTextEdit,
    QFileDialog, QMessageBox, QSplitter, QRadioButton, QButtonGroup,
    QFrame, QScrollArea, QSystemTrayIcon, QMenu, QWidget
)
from PySide6.QtCore import Qt, QThread, Signal, QPropertyAnimation, QEasingCurve, QTimer
from PySide6.QtGui import QFont, QPalette, QColor, QIcon, QAction
import qtawesome as qta
from ..core.permission_manager import PermissionManager


class CollapsibleWidget(QWidget):
    """可折叠的小部件"""
    
    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self.is_collapsed = True
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        # 创建标题按钮
        self.toggle_button = QPushButton(f"▶ {title}")
        self.toggle_button.setFlat(True)
        self.toggle_button.clicked.connect(self.toggle_collapsed)
        layout.addWidget(self.toggle_button)
        
        # 创建内容区域
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_widget.hide()  # 默认隐藏
        layout.addWidget(self.content_widget)
        
    def toggle_collapsed(self):
        """切换折叠状态"""
        self.is_collapsed = not self.is_collapsed
        if self.is_collapsed:
            self.content_widget.hide()
            self.toggle_button.setText(self.toggle_button.text().replace("▼", "▶"))
        else:
            self.content_widget.show()
            self.toggle_button.setText(self.toggle_button.text().replace("▶", "▼"))
    
    def addWidget(self, widget):
        """添加组件到内容区域"""
        self.content_layout.addWidget(widget)
    
    def addLayout(self, layout):
        """添加布局到内容区域"""
        self.content_layout.addLayout(layout)


class CollapsibleGroupBox(QGroupBox):
    """可折叠的组框"""
    
    def __init__(self, title="", parent=None):
        super().__init__(title, parent)
        self.setCheckable(True)
        self.setChecked(True)
        self.toggled.connect(self.on_toggled)
        
    def on_toggled(self, checked):
        """切换折叠状态"""
        # 获取内容布局
        layout = self.layout()
        if layout:
            # 隐藏或显示所有子控件
            for i in range(layout.count()):
                item = layout.itemAt(i)
                if item.widget():
                    item.widget().setVisible(checked)


class ProgressBarWidget(QProgressBar):
    """美化的进度条组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_style()
        
    def setup_style(self):
        """设置进度条样式"""
        self.setStyleSheet("""
        QProgressBar {
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            text-align: center;
            background-color: #f5f5f5;
            font-weight: bold;
            font-size: 12px;
            color: #333333;
            height: 24px;
        }
        
        QProgressBar::chunk {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                      stop:0 #4CAF50, stop:0.5 #66BB6A, stop:1 #81C784);
            border-radius: 6px;
        }
        
        QProgressBar[value="0"] {
            color: #666666;
        }
        
        QProgressBar[value="100"] {
            color: #ffffff;
        }
        """)


class CreateArchiveWorker(QThread):
    """创建压缩包的工作线程"""
    progress = Signal(int)  # 进度信号
    status = Signal(str)    # 状态信号
    finished = Signal(bool, str)  # 完成信号 (成功, 消息)
    
    def __init__(self, archive_manager, archive_path, files, compression_level=6, 
                 password=None, delete_source=False, create_sfx=False):
        super().__init__()
        self.archive_manager = archive_manager
        self.archive_path = archive_path
        self.files = files
        self.compression_level = compression_level
        self.password = password
        self.delete_source = delete_source
        self.create_sfx = create_sfx
        
    def run(self):
        """执行压缩任务"""
        try:
            self.status.emit("正在准备压缩...")
            self.progress.emit(0)
            
            # 定义进度回调函数
            def progress_callback(progress, status_text):
                self.progress.emit(progress)
                self.status.emit(status_text)
            
            # 创建压缩包
            success = self.archive_manager.create_archive(
                self.archive_path, 
                self.files,
                self.compression_level,
                self.password,
                progress_callback
            )
            
            if success:
                # 如果需要创建自解压文件
                if self.create_sfx:
                    self.status.emit("正在创建自解压文件...")
                    self.progress.emit(95)
                    # TODO: 实现自解压文件创建
                    # 这里可以调用archive_manager的相关方法
                    pass
                
                # 如果需要删除源文件
                if self.delete_source:
                    self.status.emit("正在删除源文件...")
                    self.progress.emit(98)
                    try:
                        import shutil
                        for file_path in self.files:
                            if os.path.exists(file_path):
                                if os.path.isfile(file_path):
                                    os.remove(file_path)
                                elif os.path.isdir(file_path):
                                    shutil.rmtree(file_path)
                    except Exception as e:
                        self.finished.emit(False, f"压缩包创建成功，但删除源文件失败：{str(e)}")
                        return
                
                self.progress.emit(100)
                self.status.emit("压缩完成")
                self.finished.emit(True, "压缩包创建成功！")
            else:
                self.finished.emit(False, "创建压缩包失败")
                
        except Exception as e:
            self.finished.emit(False, f"创建压缩包时发生错误：{str(e)}")


class CreateArchiveDialog(QDialog):
    """创建压缩包对话框"""
    
    def __init__(self, archive_manager, initial_path="", parent=None):
        super().__init__(parent)
        self.archive_manager = archive_manager
        self.initial_path = initial_path
        self.selected_files = []
        self.worker = None
        self.is_background_mode = False
        self.tray_icon = None
        
        self.init_ui()
        self.setup_system_tray()
        
    def setup_system_tray(self):
        """设置系统托盘"""
        # 检查系统是否支持托盘
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
            
        # 创建托盘图标
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(qta.icon('fa5s.file-archive', color='#2e7d32'))
        
        # 创建托盘菜单
        tray_menu = QMenu()
        
        # 恢复窗口
        restore_action = QAction("恢复窗口", self)
        restore_action.triggered.connect(self.restore_from_tray)
        tray_menu.addAction(restore_action)
        
        # 分隔符
        tray_menu.addSeparator()
        
        # 取消压缩
        cancel_action = QAction("取消压缩", self)
        cancel_action.triggered.connect(self.cancel_compression)
        tray_menu.addAction(cancel_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        
        # 双击托盘图标恢复窗口
        self.tray_icon.activated.connect(self.on_tray_icon_activated)
        
    def on_tray_icon_activated(self, reason):
        """托盘图标激活事件"""
        if reason == QSystemTrayIcon.DoubleClick:
            self.restore_from_tray()
            
    def restore_from_tray(self):
        """从托盘恢复窗口"""
        self.setWindowState(self.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)
        self.show()
        self.raise_()
        self.activateWindow()
        
        # 隐藏托盘图标
        if self.tray_icon:
            self.tray_icon.hide()
    
    def minimize_to_tray(self):
        """最小化到托盘"""
        if self.tray_icon and QSystemTrayIcon.isSystemTrayAvailable():
            self.hide()
            self.tray_icon.show()
            
            # 显示托盘消息
            self.tray_icon.showMessage(
                "GudaZip",
                "压缩任务正在后台运行，双击图标可恢复窗口",
                QSystemTrayIcon.Information,
                3000
            )
        else:
            # 如果不支持托盘，只是最小化窗口
            self.showMinimized()
    
    def cancel_compression(self):
        """取消压缩任务"""
        if self.worker and self.worker.isRunning():
            reply = QMessageBox.question(
                self, "确认", "确定要取消压缩任务吗？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.worker.terminate()
                self.worker.wait()
                self.reject()
    
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("创建压缩包")
        self.setFixedSize(450, 240)  # 进一步缩小窗口
        self.setWindowIcon(qta.icon('fa5s.file-archive', color='#2e7d32'))
        
        # 主布局，紧凑设计
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 直接添加各个控件，不使用GroupBox
        # 保存路径
        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel("保存到:"))
        
        self.path_edit = QLineEdit()
        self.path_edit.setText(self.initial_path)
        self.path_edit.setPlaceholderText("选择压缩包保存位置...")
        path_layout.addWidget(self.path_edit)
        
        self.browse_button = QPushButton("浏览...")
        self.browse_button.clicked.connect(self.browse_save_path)
        path_layout.addWidget(self.browse_button)
        
        layout.addLayout(path_layout)
        
        # 压缩选项一行
        compression_layout = QHBoxLayout()
        
        self.compression_group = QButtonGroup()
        
        # 快速压缩（默认选择）
        self.fast_compression_radio = QRadioButton("快速压缩")
        self.fast_compression_radio.setChecked(True)
        self.compression_group.addButton(self.fast_compression_radio, 3)
        compression_layout.addWidget(self.fast_compression_radio)
        
        # 极致压缩
        self.max_compression_radio = QRadioButton("极致压缩")
        self.compression_group.addButton(self.max_compression_radio, 9)
        compression_layout.addWidget(self.max_compression_radio)
        
        # 格式选择
        compression_layout.addWidget(QLabel("格式:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(["zip"])
        self.format_combo.currentTextChanged.connect(self.on_format_changed)
        compression_layout.addWidget(self.format_combo)
        
        compression_layout.addStretch()
        layout.addLayout(compression_layout)
        
        # 功能按钮行
        button_layout = QHBoxLayout()
        
        # 密码保护按钮
        self.password_button = QPushButton("密码保护")
        self.password_button.setCheckable(True)
        self.password_button.toggled.connect(self.on_password_button_toggled)
        button_layout.addWidget(self.password_button)
        
        # 自定义选项按钮
        self.custom_options_button = QPushButton("自定义选项")
        self.custom_options_button.setCheckable(True)
        self.custom_options_button.toggled.connect(self.on_custom_options_button_toggled)
        button_layout.addWidget(self.custom_options_button)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # 可折叠的密码输入区域
        self.password_widget = QWidget()
        password_layout = QHBoxLayout(self.password_widget)
        password_layout.setContentsMargins(20, 0, 0, 0)
        
        password_layout.addWidget(QLabel("密码:"))
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setPlaceholderText("输入密码...")
        password_layout.addWidget(self.password_edit)
        
        self.password_widget.hide()  # 默认隐藏
        layout.addWidget(self.password_widget)
        
        # 可折叠的自定义选项区域
        self.custom_options_widget = QWidget()
        custom_layout = QVBoxLayout(self.custom_options_widget)
        custom_layout.setContentsMargins(20, 0, 0, 0)
        custom_layout.setSpacing(3)
        
        # 自定义选项使用紧凑布局
        options_row1 = QHBoxLayout()
        self.delete_source_check = QCheckBox("压缩后删除源文件")
        self.create_sfx_check = QCheckBox("创建自解压文件")
        options_row1.addWidget(self.delete_source_check)
        options_row1.addWidget(self.create_sfx_check)
        options_row1.addStretch()
        custom_layout.addLayout(options_row1)
        
        options_row2 = QHBoxLayout()
        self.background_compress_check = QCheckBox("后台压缩")
        self.background_compress_check.toggled.connect(self.on_background_toggled)
        options_row2.addWidget(self.background_compress_check)
        
        background_desc = QLabel("(最小化到系统托盘)")
        background_desc.setStyleSheet("color: #666666; font-size: 9px;")
        options_row2.addWidget(background_desc)
        options_row2.addStretch()
        custom_layout.addLayout(options_row2)
        
        self.custom_options_widget.hide()  # 默认隐藏
        layout.addWidget(self.custom_options_widget)
        
        # 进度区域
        progress_frame = self.create_progress_frame()
        layout.addWidget(progress_frame)
        
        # 状态和按钮行
        bottom_layout = QHBoxLayout()
        
        # 状态标签
        self.info_label = QLabel("")
        self.info_label.setStyleSheet("color: #666666; font-size: 10px;")
        bottom_layout.addWidget(self.info_label)
        
        bottom_layout.addStretch()
        
        # 创建压缩包按钮
        self.create_button = QPushButton("创建压缩包")
        self.create_button.setMinimumSize(110, 32)
        self.create_button.setStyleSheet("""
            QPushButton {
                font-size: 12px;
                font-weight: bold;
                padding: 6px 12px;
            }
        """)
        self.create_button.clicked.connect(self.create_archive)
        bottom_layout.addWidget(self.create_button)
        
        layout.addLayout(bottom_layout)
        
        # 更新界面状态
        self.update_ui_state()
        
    def create_archive_settings_group(self):
        """创建压缩包设置组（包含所有选项）"""
        group = QGroupBox("压缩包设置")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)  # 减少间距
        
        # 压缩包路径
        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel("保存到:"))
        
        self.path_edit = QLineEdit()
        self.path_edit.setText(self.initial_path)
        self.path_edit.setPlaceholderText("选择压缩包保存位置...")
        path_layout.addWidget(self.path_edit)
        
        self.browse_button = QPushButton("浏览...")
        self.browse_button.clicked.connect(self.browse_save_path)
        path_layout.addWidget(self.browse_button)
        
        layout.addLayout(path_layout)
        
        # 压缩级别和格式选择一行
        compression_layout = QHBoxLayout()
        
        self.compression_group = QButtonGroup()
        
        # 快速压缩（默认选择）
        self.fast_compression_radio = QRadioButton("快速压缩")
        self.fast_compression_radio.setChecked(True)
        self.compression_group.addButton(self.fast_compression_radio, 3)  # 压缩率3
        compression_layout.addWidget(self.fast_compression_radio)
        
        # 极致压缩
        self.max_compression_radio = QRadioButton("极致压缩")
        self.compression_group.addButton(self.max_compression_radio, 9)  # 压缩率9
        compression_layout.addWidget(self.max_compression_radio)
        
        # 格式选择
        compression_layout.addWidget(QLabel("格式:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(["zip"])
        self.format_combo.currentTextChanged.connect(self.on_format_changed)
        compression_layout.addWidget(self.format_combo)
        
        compression_layout.addStretch()
        layout.addLayout(compression_layout)
        
        # 按钮行：密码保护和自定义选项
        button_layout = QHBoxLayout()
        
        # 密码保护按钮
        self.password_button = QPushButton("密码保护")
        self.password_button.setCheckable(True)
        self.password_button.toggled.connect(self.on_password_button_toggled)
        button_layout.addWidget(self.password_button)
        
        # 自定义选项按钮
        self.custom_options_button = QPushButton("自定义选项")
        self.custom_options_button.setCheckable(True)
        self.custom_options_button.toggled.connect(self.on_custom_options_button_toggled)
        button_layout.addWidget(self.custom_options_button)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # 可折叠的密码输入区域
        self.password_widget = QWidget()
        password_layout = QVBoxLayout(self.password_widget)
        password_layout.setContentsMargins(15, 5, 0, 5)
        
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setPlaceholderText("输入密码...")
        password_layout.addWidget(self.password_edit)
        
        self.password_widget.hide()  # 默认隐藏
        layout.addWidget(self.password_widget)
        
        # 可折叠的自定义选项区域
        self.custom_options_widget = QWidget()
        custom_layout = QVBoxLayout(self.custom_options_widget)
        custom_layout.setContentsMargins(15, 5, 0, 5)
        custom_layout.setSpacing(5)
        
        # 压缩后删除源文件
        self.delete_source_check = QCheckBox("压缩后删除源文件")
        custom_layout.addWidget(self.delete_source_check)
        
        # 创建自解压文件
        self.create_sfx_check = QCheckBox("创建自解压文件")
        custom_layout.addWidget(self.create_sfx_check)
        
        # 后台压缩功能
        self.background_compress_check = QCheckBox("后台压缩")
        self.background_compress_check.toggled.connect(self.on_background_toggled)
        custom_layout.addWidget(self.background_compress_check)
        
        # 后台压缩说明
        background_desc = QLabel("启用后将最小化到系统托盘")
        background_desc.setStyleSheet("color: #666666; font-size: 9px; margin-left: 15px;")
        custom_layout.addWidget(background_desc)
        
        self.custom_options_widget.hide()  # 默认隐藏
        layout.addWidget(self.custom_options_widget)
        
        return group
        
    def create_progress_frame(self):
        """创建进度区域"""
        frame = QFrame()
        frame.setVisible(False)
        layout = QVBoxLayout(frame)
        layout.setSpacing(3)
        layout.setContentsMargins(0, 5, 0, 5)
        
        # 使用美化的进度条
        self.progress_bar = ProgressBarWidget()
        layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("font-size: 10px; color: #666666;")
        layout.addWidget(self.status_label)
        
        self.progress_frame = frame
        return frame
        
    def create_buttons_frame(self):
        """创建按钮区域"""
        frame = QFrame()
        layout = QHBoxLayout(frame)
        
        # 状态标签
        self.info_label = QLabel("")
        self.info_label.setStyleSheet("color: #666666; font-size: 10px;")
        layout.addWidget(self.info_label)
        
        layout.addStretch()
        
        # 创建压缩包按钮 - 放大尺寸
        self.create_button = QPushButton("创建压缩包")
        self.create_button.setMinimumSize(120, 35)  # 设置最小尺寸
        self.create_button.setStyleSheet("""
            QPushButton {
                font-size: 13px;
                font-weight: bold;
                padding: 8px 16px;
            }
        """)
        self.create_button.clicked.connect(self.create_archive)
        layout.addWidget(self.create_button)
        
        return frame
        
    def browse_save_path(self):
        """浏览保存路径"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存压缩包", self.path_edit.text(),
            "ZIP文件 (*.zip);;所有文件 (*.*)"
        )
        if file_path:
            self.path_edit.setText(file_path)
            
    def on_format_changed(self, format_text):
        """格式改变事件"""
        # 根据格式更新文件扩展名
        current_path = self.path_edit.text()
        if current_path:
            base_path = os.path.splitext(current_path)[0]
            if "zip" in format_text.lower():
                self.path_edit.setText(base_path + ".zip")
                
    def on_password_button_toggled(self, checked):
        """密码保护按钮切换"""
        if checked:
            self.password_widget.show()
            self.password_button.setText("密码保护 ▼")
        else:
            self.password_widget.hide()
            self.password_button.setText("密码保护")
            self.password_edit.clear()
            
    def on_custom_options_button_toggled(self, checked):
        """自定义选项按钮切换"""
        if checked:
            self.custom_options_widget.show()
            self.custom_options_button.setText("自定义选项 ▼")
        else:
            self.custom_options_widget.hide()
            self.custom_options_button.setText("自定义选项")
        
    def on_background_toggled(self, checked):
        """后台压缩选项切换"""
        self.is_background_mode = checked
        
    def update_ui_state(self):
        """更新界面状态"""
        has_files = len(self.selected_files) > 0
        has_path = bool(self.path_edit.text().strip())
        
        self.create_button.setEnabled(has_files and has_path)
        
        # 更新状态
        if has_files:
            self.info_label.setText(f"已选择 {len(self.selected_files)} 个项目")
        else:
            self.info_label.setText("请在主界面选择要压缩的文件或文件夹")
            
    def create_archive(self):
        """创建压缩包"""
        if not self.selected_files:
            QMessageBox.warning(self, "警告", "请先在主界面选择要压缩的文件或文件夹")
            return
            
        archive_path = self.path_edit.text().strip()
        if not archive_path:
            QMessageBox.warning(self, "警告", "请指定压缩包保存路径")
            return
            
        # 确保文件扩展名正确
        if not archive_path.lower().endswith('.zip'):
            archive_path += '.zip'
            self.path_edit.setText(archive_path)
            
        # 检查文件是否已存在
        if os.path.exists(archive_path):
            reply = QMessageBox.question(
                self, "确认", 
                f"文件 '{archive_path}' 已存在，是否覆盖？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
                
        # 获取密码
        password = None
        if self.password_button.isChecked():
            password = self.password_edit.text()
            if not password:
                QMessageBox.warning(self, "警告", "请输入密码")
                return
                
        # 在主线程中检查权限
        all_paths = self.selected_files + [archive_path]
        if not PermissionManager.request_admin_if_needed(all_paths, "创建压缩包"):
            # 用户拒绝权限申请或权限申请失败
            return
                
        # 获取压缩级别
        compression_level = self.compression_group.checkedId()
        if compression_level == -1:  # 如果没有选择，默认快速压缩
            compression_level = 3
            
        # 获取自定义选项
        delete_source = self.delete_source_check.isChecked()
        create_sfx = self.create_sfx_check.isChecked()
        
        # 如果选择后台压缩，最小化到托盘
        if self.is_background_mode:
            self.minimize_to_tray()
        
        # 显示进度界面
        self.progress_frame.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("准备开始...")
        
        # 禁用界面
        self.create_button.setEnabled(False)
        
        # 创建工作线程
        self.worker = CreateArchiveWorker(
            self.archive_manager,
            archive_path,
            self.selected_files,
            compression_level,
            password,
            delete_source,
            create_sfx
        )
        
        # 连接信号
        self.worker.progress.connect(self.on_progress_updated)
        self.worker.status.connect(self.status_label.setText)
        self.worker.finished.connect(self.on_create_finished)
        
        # 启动线程
        self.worker.start()
        
    def on_progress_updated(self, value):
        """进度更新"""
        self.progress_bar.setValue(value)
        
        # 如果是后台模式，更新托盘工具提示
        if self.is_background_mode and self.tray_icon:
            self.tray_icon.setToolTip(f"GudaZip - 压缩进度: {value}%")
        
    def show_completion_notification(self):
        """显示完成通知"""
        if self.tray_icon and self.is_background_mode:
            self.tray_icon.showMessage(
                "GudaZip",
                "压缩任务已完成！",
                QSystemTrayIcon.Information,
                5000
            )
        
    def on_create_finished(self, success, message):
        """创建完成"""
        self.progress_frame.setVisible(False)
        self.create_button.setEnabled(True)
        
        # 如果是后台模式，恢复窗口并显示通知
        if self.is_background_mode:
            self.restore_from_tray()
            if success:
                self.show_completion_notification()
        
        if success:
            QMessageBox.information(self, "成功", message)
            self.accept()
        else:
            QMessageBox.critical(self, "错误", message)
            
        # 清理工作线程
        if self.worker:
            self.worker.deleteLater()
            self.worker = None
            
    def closeEvent(self, event):
        """关闭事件"""
        if self.worker and self.worker.isRunning():
            reply = QMessageBox.question(
                self, "确认", "压缩操作正在进行中，是否要停止？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.worker.terminate()
                self.worker.wait()
            else:
                event.ignore()
                return
                
        # 隐藏托盘图标
        if self.tray_icon:
            self.tray_icon.hide()
            
        event.accept() 