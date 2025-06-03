# -*- coding: utf-8 -*-
"""
解压压缩包对话框
允许用户选择解压选项和目标路径
"""

import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QListWidget, QListWidgetItem, QGroupBox,
    QCheckBox, QProgressBar, QFileDialog, QMessageBox,
    QTreeWidget, QTreeWidgetItem, QRadioButton, QButtonGroup
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont


class ExtractArchiveWorker(QThread):
    """解压压缩包的工作线程"""
    progress = Signal(int)  # 进度信号
    status = Signal(str)    # 状态信号
    finished = Signal(bool, str)  # 完成信号 (成功, 消息)
    
    def __init__(self, archive_manager, archive_path, extract_to, password=None, selected_files=None):
        super().__init__()
        self.archive_manager = archive_manager
        self.archive_path = archive_path
        self.extract_to = extract_to
        self.password = password
        self.selected_files = selected_files
        
    def run(self):
        """执行解压任务"""
        try:
            self.status.emit("正在解压压缩包...")
            self.progress.emit(0)
            
            # 解压压缩包
            success = self.archive_manager.extract_archive(
                self.archive_path,
                self.extract_to,
                self.password,
                self.selected_files
            )
            
            if success:
                self.progress.emit(100)
                self.status.emit("解压完成")
                
                # 统计解压的文件数量
                file_count = 0
                if self.selected_files:
                    file_count = len(self.selected_files)
                else:
                    # 获取压缩包信息来计算文件数
                    archive_info = self.archive_manager.get_archive_info(self.archive_path)
                    if archive_info:
                        file_count = archive_info['file_count']
                
                self.finished.emit(True, f"解压完成！共解压了 {file_count} 个文件")
            else:
                self.finished.emit(False, "解压失败")
                
        except Exception as e:
            self.finished.emit(False, f"解压时发生错误：{str(e)}")


class ExtractArchiveDialog(QDialog):
    """解压压缩包对话框"""
    
    def __init__(self, archive_manager, archive_path, parent=None):
        super().__init__(parent)
        self.archive_manager = archive_manager
        self.archive_path = archive_path
        self.archive_info = None
        self.worker = None
        
        # 获取压缩包信息
        try:
            self.archive_info = self.archive_manager.get_archive_info(archive_path)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法读取压缩包信息：{str(e)}")
            self.reject()
            return
            
        self.init_ui()
        self.load_archive_contents()
        
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("解压压缩包")
        self.setMinimumSize(700, 600)
        
        # 主布局
        layout = QVBoxLayout(self)
        
        # 压缩包信息组
        info_group = QGroupBox("压缩包信息")
        info_layout = QVBoxLayout(info_group)
        
        # 压缩包路径
        archive_name = os.path.basename(self.archive_path)
        info_layout.addWidget(QLabel(f"文件名: {archive_name}"))
        
        if self.archive_info:
            info_layout.addWidget(QLabel(f"格式: {self.archive_info['format']}"))
            info_layout.addWidget(QLabel(f"文件数量: {self.archive_info['file_count']}"))
            
            # 格式化文件大小
            total_size = self.archive_info['total_size']
            size_str = self.format_size(total_size)
            info_layout.addWidget(QLabel(f"原始大小: {size_str}"))
            
            if self.archive_info['has_password']:
                password_label = QLabel("🔒 此压缩包需要密码")
                password_label.setStyleSheet("color: orange; font-weight: bold;")
                info_layout.addWidget(password_label)
        
        layout.addWidget(info_group)
        
        # 解压选项组
        options_group = QGroupBox("解压选项")
        options_layout = QVBoxLayout(options_group)
        
        # 解压目标路径
        target_layout = QHBoxLayout()
        target_layout.addWidget(QLabel("解压到:"))
        
        # 默认解压到压缩包同目录下的同名文件夹
        default_path = os.path.join(
            os.path.dirname(self.archive_path),
            os.path.splitext(os.path.basename(self.archive_path))[0]
        )
        
        self.target_edit = QLineEdit()
        self.target_edit.setText(default_path)
        target_layout.addWidget(self.target_edit)
        
        self.browse_button = QPushButton("浏览...")
        self.browse_button.clicked.connect(self.browse_target_path)
        target_layout.addWidget(self.browse_button)
        
        options_layout.addLayout(target_layout)
        
        # 解压方式选择
        extract_mode_layout = QVBoxLayout()
        self.mode_group = QButtonGroup()
        
        self.extract_all_radio = QRadioButton("解压所有文件")
        self.extract_all_radio.setChecked(True)
        self.extract_all_radio.toggled.connect(self.on_mode_changed)
        self.mode_group.addButton(self.extract_all_radio, 0)
        extract_mode_layout.addWidget(self.extract_all_radio)
        
        self.extract_selected_radio = QRadioButton("仅解压选中的文件")
        self.extract_selected_radio.toggled.connect(self.on_mode_changed)
        self.mode_group.addButton(self.extract_selected_radio, 1)
        extract_mode_layout.addWidget(self.extract_selected_radio)
        
        options_layout.addLayout(extract_mode_layout)
        
        # 密码输入
        password_layout = QHBoxLayout()
        password_layout.addWidget(QLabel("密码:"))
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setPlaceholderText("如果压缩包有密码保护，请输入密码")
        password_layout.addWidget(self.password_edit)
        options_layout.addLayout(password_layout)
        
        layout.addWidget(options_group)
        
        # 文件列表组
        files_group = QGroupBox("压缩包内容")
        files_layout = QVBoxLayout(files_group)
        
        # 文件树
        self.files_tree = QTreeWidget()
        self.files_tree.setHeaderLabels(["名称", "大小", "修改时间"])
        self.files_tree.setSelectionMode(QTreeWidget.ExtendedSelection)
        self.files_tree.itemChanged.connect(self.on_item_changed)
        files_layout.addWidget(self.files_tree)
        
        # 文件选择按钮
        file_buttons_layout = QHBoxLayout()
        
        self.select_all_button = QPushButton("全选")
        self.select_all_button.clicked.connect(self.select_all_files)
        file_buttons_layout.addWidget(self.select_all_button)
        
        self.deselect_all_button = QPushButton("全不选")
        self.deselect_all_button.clicked.connect(self.deselect_all_files)
        file_buttons_layout.addWidget(self.deselect_all_button)
        
        file_buttons_layout.addStretch()
        files_layout.addLayout(file_buttons_layout)
        
        layout.addWidget(files_group)
        
        # 进度条和状态
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("准备解压")
        layout.addWidget(self.status_label)
        
        # 按钮
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        self.extract_button = QPushButton("开始解压")
        self.extract_button.clicked.connect(self.extract_archive)
        buttons_layout.addWidget(self.extract_button)
        
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(self.cancel_button)
        
        layout.addLayout(buttons_layout)
        
        # 初始状态设置
        self.on_mode_changed()
        
    def format_size(self, size_bytes):
        """格式化文件大小"""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
            
        return f"{size_bytes:.1f} {size_names[i]}"
        
    def load_archive_contents(self):
        """加载压缩包内容"""
        if not self.archive_info or not self.archive_info.get('files'):
            return
            
        # 构建文件树
        self.files_tree.clear()
        root_items = {}  # 路径到项目的映射
        
        for file_info in self.archive_info['files']:
            file_path = file_info['path']
            parts = file_path.split('/')
            
            current_parent = self.files_tree.invisibleRootItem()
            current_path = ""
            
            # 构建目录结构
            for i, part in enumerate(parts):
                if i < len(parts) - 1:  # 这是一个目录
                    current_path = current_path + part + "/" if current_path else part + "/"
                    
                    if current_path not in root_items:
                        dir_item = QTreeWidgetItem(current_parent)
                        dir_item.setText(0, f"📁 {part}")
                        dir_item.setText(1, "")
                        dir_item.setText(2, "")
                        dir_item.setCheckState(0, Qt.Checked)
                        dir_item.setData(0, Qt.UserRole, current_path)
                        dir_item.setData(0, Qt.UserRole + 1, "folder")
                        
                        root_items[current_path] = dir_item
                        current_parent = dir_item
                    else:
                        current_parent = root_items[current_path]
                else:  # 这是文件
                    file_item = QTreeWidgetItem(current_parent)
                    file_item.setText(0, f"📄 {part}")
                    file_item.setText(1, self.format_size(file_info.get('size', 0)))
                    file_item.setText(2, file_info.get('modified_time', ''))
                    file_item.setCheckState(0, Qt.Checked)
                    file_item.setData(0, Qt.UserRole, file_path)
                    file_item.setData(0, Qt.UserRole + 1, "file")
                    
        # 展开所有项目
        self.files_tree.expandAll()
        
        # 调整列宽
        for i in range(3):
            self.files_tree.resizeColumnToContents(i)
            
    def browse_target_path(self):
        """浏览目标路径"""
        dir_path = QFileDialog.getExistingDirectory(
            self, "选择解压目标文件夹", self.target_edit.text()
        )
        if dir_path:
            self.target_edit.setText(dir_path)
            
    def on_mode_changed(self):
        """解压模式改变"""
        extract_selected = self.extract_selected_radio.isChecked()
        
        # 启用/禁用文件选择相关控件
        self.files_tree.setEnabled(extract_selected)
        self.select_all_button.setEnabled(extract_selected)
        self.deselect_all_button.setEnabled(extract_selected)
        
        if not extract_selected:
            # 如果是解压全部，选中所有项目
            self.select_all_files()
            
    def select_all_files(self):
        """全选文件"""
        self._set_all_check_state(Qt.Checked)
        
    def deselect_all_files(self):
        """全不选文件"""
        self._set_all_check_state(Qt.Unchecked)
        
    def _set_all_check_state(self, state):
        """设置所有项目的选中状态"""
        def set_item_state(item):
            item.setCheckState(0, state)
            for i in range(item.childCount()):
                set_item_state(item.child(i))
                
        root = self.files_tree.invisibleRootItem()
        for i in range(root.childCount()):
            set_item_state(root.child(i))
            
    def on_item_changed(self, item, column):
        """项目状态改变"""
        if column == 0:  # 只处理第一列的复选框
            # 更新子项目状态
            state = item.checkState(0)
            self._update_children_state(item, state)
            
            # 更新父项目状态
            self._update_parent_state(item)
            
    def _update_children_state(self, parent, state):
        """更新子项目状态"""
        for i in range(parent.childCount()):
            child = parent.child(i)
            child.setCheckState(0, state)
            self._update_children_state(child, state)
            
    def _update_parent_state(self, item):
        """更新父项目状态"""
        parent = item.parent()
        if parent is None:
            return
            
        # 检查所有兄弟项目的状态
        checked_count = 0
        total_count = parent.childCount()
        
        for i in range(total_count):
            if parent.child(i).checkState(0) == Qt.Checked:
                checked_count += 1
                
        # 设置父项目状态
        if checked_count == 0:
            parent.setCheckState(0, Qt.Unchecked)
        elif checked_count == total_count:
            parent.setCheckState(0, Qt.Checked)
        else:
            parent.setCheckState(0, Qt.PartiallyChecked)
            
        # 递归更新上级父项目
        self._update_parent_state(parent)
        
    def get_selected_files(self):
        """获取选中的文件列表"""
        selected_files = []
        
        def collect_files(item):
            if item.checkState(0) == Qt.Checked:
                item_type = item.data(0, Qt.UserRole + 1)
                item_path = item.data(0, Qt.UserRole)
                
                if item_type == "file":
                    selected_files.append(item_path)
                elif item_type == "folder":
                    # 收集文件夹下的所有文件
                    for i in range(item.childCount()):
                        collect_files(item.child(i))
            else:
                # 即使父项目未选中，也要检查子项目
                for i in range(item.childCount()):
                    collect_files(item.child(i))
                    
        root = self.files_tree.invisibleRootItem()
        for i in range(root.childCount()):
            collect_files(root.child(i))
            
        return selected_files
        
    def extract_archive(self):
        """开始解压"""
        extract_to = self.target_edit.text().strip()
        if not extract_to:
            QMessageBox.warning(self, "警告", "请指定解压目标路径")
            return
            
        # 获取密码
        password = self.password_edit.text() if self.password_edit.text() else None
        
        # 获取选中的文件
        selected_files = None
        if self.extract_selected_radio.isChecked():
            selected_files = self.get_selected_files()
            if not selected_files:
                QMessageBox.warning(self, "警告", "请至少选择一个文件进行解压")
                return
                
        # 确保目标目录存在
        try:
            os.makedirs(extract_to, exist_ok=True)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法创建目标目录：{str(e)}")
            return
            
        # 禁用界面
        self.extract_button.setEnabled(False)
        self.cancel_button.setText("停止")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # 创建工作线程
        self.worker = ExtractArchiveWorker(
            self.archive_manager,
            self.archive_path,
            extract_to,
            password,
            selected_files
        )
        
        # 连接信号
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.status.connect(self.status_label.setText)
        self.worker.finished.connect(self.on_extract_finished)
        
        # 启动线程
        self.worker.start()
        
    def on_extract_finished(self, success, message):
        """解压完成"""
        self.progress_bar.setVisible(False)
        self.extract_button.setEnabled(True)
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
                self, "确认", "解压操作正在进行中，是否要停止？",
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