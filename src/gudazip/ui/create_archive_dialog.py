# -*- coding: utf-8 -*-
"""
创建压缩包对话框
允许用户选择文件和设置压缩选项
"""

import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QListWidget, QListWidgetItem, QGroupBox,
    QComboBox, QSlider, QCheckBox, QProgressBar, QTextEdit,
    QFileDialog, QMessageBox, QSplitter
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont


class CreateArchiveWorker(QThread):
    """创建压缩包的工作线程"""
    progress = Signal(int)  # 进度信号
    status = Signal(str)    # 状态信号
    finished = Signal(bool, str)  # 完成信号 (成功, 消息)
    
    def __init__(self, archive_manager, archive_path, files, compression_level=6, password=None):
        super().__init__()
        self.archive_manager = archive_manager
        self.archive_path = archive_path
        self.files = files
        self.compression_level = compression_level
        self.password = password
        
    def run(self):
        """执行压缩任务"""
        try:
            self.status.emit("正在创建压缩包...")
            self.progress.emit(0)
            
            # 创建压缩包
            success = self.archive_manager.create_archive(
                self.archive_path, 
                self.files,
                self.compression_level,
                self.password
            )
            
            if success:
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
        
        self.init_ui()
        
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("创建压缩包")
        self.setMinimumSize(600, 500)
        
        # 主布局
        layout = QVBoxLayout(self)
        
        # 压缩包设置组
        archive_group = QGroupBox("压缩包设置")
        archive_layout = QVBoxLayout(archive_group)
        
        # 压缩包路径
        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel("保存到:"))
        self.path_edit = QLineEdit()
        self.path_edit.setText(self.initial_path)
        path_layout.addWidget(self.path_edit)
        
        self.browse_button = QPushButton("浏览...")
        self.browse_button.clicked.connect(self.browse_save_path)
        path_layout.addWidget(self.browse_button)
        archive_layout.addLayout(path_layout)
        
        # 压缩格式选择
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("格式:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(["ZIP文件 (*.zip)"])
        self.format_combo.currentTextChanged.connect(self.on_format_changed)
        format_layout.addWidget(self.format_combo)
        format_layout.addStretch()
        archive_layout.addLayout(format_layout)
        
        layout.addWidget(archive_group)
        
        # 文件选择组
        files_group = QGroupBox("选择文件和文件夹")
        files_layout = QVBoxLayout(files_group)
        
        # 文件选择按钮
        buttons_layout = QHBoxLayout()
        self.add_files_button = QPushButton("添加文件...")
        self.add_files_button.clicked.connect(self.add_files)
        buttons_layout.addWidget(self.add_files_button)
        
        self.add_folder_button = QPushButton("添加文件夹...")
        self.add_folder_button.clicked.connect(self.add_folder)
        buttons_layout.addWidget(self.add_folder_button)
        
        self.remove_button = QPushButton("移除选中")
        self.remove_button.clicked.connect(self.remove_selected)
        buttons_layout.addWidget(self.remove_button)
        
        self.clear_button = QPushButton("清空列表")
        self.clear_button.clicked.connect(self.clear_list)
        buttons_layout.addWidget(self.clear_button)
        
        buttons_layout.addStretch()
        files_layout.addLayout(buttons_layout)
        
        # 文件列表
        self.files_list = QListWidget()
        self.files_list.setSelectionMode(QListWidget.ExtendedSelection)
        files_layout.addWidget(self.files_list)
        
        layout.addWidget(files_group)
        
        # 压缩选项组
        options_group = QGroupBox("压缩选项")
        options_layout = QVBoxLayout(options_group)
        
        # 压缩级别
        level_layout = QHBoxLayout()
        level_layout.addWidget(QLabel("压缩级别:"))
        self.level_slider = QSlider(Qt.Horizontal)
        self.level_slider.setRange(0, 9)
        self.level_slider.setValue(6)
        self.level_slider.valueChanged.connect(self.on_level_changed)
        level_layout.addWidget(self.level_slider)
        
        self.level_label = QLabel("6 (标准)")
        level_layout.addWidget(self.level_label)
        options_layout.addLayout(level_layout)
        
        # 密码保护
        password_layout = QHBoxLayout()
        self.password_check = QCheckBox("密码保护")
        self.password_check.toggled.connect(self.on_password_toggled)
        password_layout.addWidget(self.password_check)
        
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setEnabled(False)
        password_layout.addWidget(self.password_edit)
        options_layout.addLayout(password_layout)
        
        layout.addWidget(options_group)
        
        # 进度条和状态
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("")
        layout.addWidget(self.status_label)
        
        # 按钮
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        self.create_button = QPushButton("创建压缩包")
        self.create_button.clicked.connect(self.create_archive)
        buttons_layout.addWidget(self.create_button)
        
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(self.cancel_button)
        
        layout.addLayout(buttons_layout)
        
        # 更新界面状态
        self.update_ui_state()
        
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
                
    def add_files(self):
        """添加文件"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择文件", "",
            "所有文件 (*.*)"
        )
        
        for file_path in files:
            if file_path not in self.selected_files:
                self.selected_files.append(file_path)
                item = QListWidgetItem(f"📄 {file_path}")
                item.setData(Qt.UserRole, file_path)
                self.files_list.addItem(item)
                
        self.update_ui_state()
        
    def add_folder(self):
        """添加文件夹"""
        folder_path = QFileDialog.getExistingDirectory(
            self, "选择文件夹"
        )
        
        if folder_path:
            if folder_path not in self.selected_files:
                self.selected_files.append(folder_path)
                item = QListWidgetItem(f"📁 {folder_path}")
                item.setData(Qt.UserRole, folder_path)
                self.files_list.addItem(item)
            
        self.update_ui_state()
        
    def remove_selected(self):
        """移除选中的项目"""
        selected_items = self.files_list.selectedItems()
        for item in selected_items:
            file_path = item.data(Qt.UserRole)
            if file_path in self.selected_files:
                self.selected_files.remove(file_path)
            row = self.files_list.row(item)
            self.files_list.takeItem(row)
            
        self.update_ui_state()
        
    def clear_list(self):
        """清空文件列表"""
        self.selected_files.clear()
        self.files_list.clear()
        self.update_ui_state()
        
    def on_level_changed(self, value):
        """压缩级别改变"""
        level_names = [
            "0 (无压缩)", "1 (最快)", "2", "3", "4", "5", 
            "6 (标准)", "7", "8", "9 (最小)"
        ]
        self.level_label.setText(level_names[value])
        
    def on_password_toggled(self, checked):
        """密码选项切换"""
        self.password_edit.setEnabled(checked)
        if not checked:
            self.password_edit.clear()
            
    def update_ui_state(self):
        """更新界面状态"""
        has_files = len(self.selected_files) > 0
        has_path = bool(self.path_edit.text().strip())
        
        self.create_button.setEnabled(has_files and has_path)
        self.remove_button.setEnabled(has_files and bool(self.files_list.selectedItems()))
        self.clear_button.setEnabled(has_files)
        
        # 更新状态
        if has_files:
            self.status_label.setText(f"已选择 {len(self.selected_files)} 个项目")
        else:
            self.status_label.setText("请选择要压缩的文件或文件夹")
            
    def create_archive(self):
        """创建压缩包"""
        if not self.selected_files:
            QMessageBox.warning(self, "警告", "请先选择要压缩的文件或文件夹")
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
        if self.password_check.isChecked():
            password = self.password_edit.text()
            if not password:
                QMessageBox.warning(self, "警告", "请输入密码")
                return
                
        # 禁用界面
        self.create_button.setEnabled(False)
        self.cancel_button.setText("停止")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # 创建工作线程
        self.worker = CreateArchiveWorker(
            self.archive_manager,
            archive_path,
            self.selected_files,
            self.level_slider.value(),
            password
        )
        
        # 连接信号
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.status.connect(self.status_label.setText)
        self.worker.finished.connect(self.on_create_finished)
        
        # 启动线程
        self.worker.start()
        
    def on_create_finished(self, success, message):
        """创建完成"""
        self.progress_bar.setVisible(False)
        self.create_button.setEnabled(True)
        self.cancel_button.setText("取消")
        
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
                
        event.accept() 