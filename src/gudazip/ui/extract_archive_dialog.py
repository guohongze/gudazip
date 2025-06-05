# -*- coding: utf-8 -*-
"""
解压压缩包对话框
允许用户选择解压选项和目标路径
"""

import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QGroupBox, QProgressBar, QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont


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
                                      stop:0 #2196F3, stop:0.5 #42A5F5, stop:1 #64B5F6);
            border-radius: 6px;
        }
        
        QProgressBar[value="0"] {
            color: #666666;
        }
        
        QProgressBar[value="100"] {
            color: #ffffff;
        }
        """)


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
        self.stop_requested = False  # 停止请求标志
        
    def run(self):
        """执行解压任务"""
        try:
            if self.stop_requested:
                return
                
            self.status.emit("正在解压压缩包...")
            self.progress.emit(0)
            
            # 检查是否被请求停止
            if self.stop_requested:
                self.finished.emit(False, "解压被用户取消")
                return
            
            # 定义进度回调函数
            def progress_callback(progress, status_text):
                if not self.stop_requested:
                    self.progress.emit(progress)
                    self.status.emit(status_text)
            
            # 解压压缩包
            success = self.archive_manager.extract_archive(
                self.archive_path,
                self.extract_to,
                self.password,
                self.selected_files,
                progress_callback
            )
            
            # 再次检查是否被请求停止
            if self.stop_requested:
                self.finished.emit(False, "解压被用户取消")
                return
            
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
            if not self.stop_requested:
                self.finished.emit(False, f"解压时发生错误：{str(e)}")


class ExtractArchiveDialog(QDialog):
    """解压压缩包对话框"""
    
    def __init__(self, archive_manager, archive_path, selected_files=None, parent=None):
        super().__init__(parent)
        self.archive_manager = archive_manager
        self.archive_path = archive_path
        self.selected_files = selected_files  # 要解压的特定文件（None表示解压全部）
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
        
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("解压压缩包")
        self.setMinimumSize(500, 300)
        self.resize(500, 300)
        
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
            
            # 显示解压信息
            if self.selected_files:
                info_layout.addWidget(QLabel(f"解压文件数: {len(self.selected_files)} 个选中文件"))
            else:
                info_layout.addWidget(QLabel(f"解压文件数: {self.archive_info['file_count']} 个文件（全部）"))
            
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
        ).replace("\\", "/")
        
        self.target_edit = QLineEdit()
        self.target_edit.setText(default_path)
        target_layout.addWidget(self.target_edit)
        
        self.browse_button = QPushButton("浏览...")
        self.browse_button.clicked.connect(self.browse_target_path)
        target_layout.addWidget(self.browse_button)
        
        options_layout.addLayout(target_layout)
        
        # 密码输入（仅在需要时显示）
        if self.archive_info and self.archive_info.get('has_password'):
            password_layout = QHBoxLayout()
            password_layout.addWidget(QLabel("密码:"))
            self.password_edit = QLineEdit()
            self.password_edit.setEchoMode(QLineEdit.Password)
            self.password_edit.setPlaceholderText("请输入压缩包密码")
            password_layout.addWidget(self.password_edit)
            options_layout.addLayout(password_layout)
        else:
            self.password_edit = None
        
        layout.addWidget(options_group)
        
        # 进度条和状态
        self.progress_bar = ProgressBarWidget()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("准备解压")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("font-size: 10px; color: #666666;")
        layout.addWidget(self.status_label)
        
        # 按钮
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        self.extract_button = QPushButton("开始解压")
        self.extract_button.clicked.connect(self.extract_archive)
        self.extract_button.setStyleSheet("""
        QPushButton {
            background-color: #1976d2;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #1565c0;
        }
        QPushButton:pressed {
            background-color: #0d47a1;
        }
        QPushButton:disabled {
            background-color: #cccccc;
            color: #666666;
        }
        """)
        buttons_layout.addWidget(self.extract_button)
        
        layout.addLayout(buttons_layout)
        
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
            
    def browse_target_path(self):
        """浏览目标路径"""
        dir_path = QFileDialog.getExistingDirectory(
            self, "选择解压目标文件夹", self.target_edit.text()
        )
        if dir_path:
            self.target_edit.setText(dir_path)
        
    def extract_archive(self):
        """开始解压"""
        extract_to = self.target_edit.text().strip()
        if not extract_to:
            QMessageBox.warning(self, "警告", "请指定解压目标路径")
            return
            
        # 获取密码
        password = None
        if self.password_edit:
            password = self.password_edit.text() if self.password_edit.text() else None
                
        # 确保目标目录存在
        try:
            os.makedirs(extract_to, exist_ok=True)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法创建目标目录：{str(e)}")
            return
            
        # 禁用界面
        self.extract_button.setEnabled(False)
        self.extract_button.setText("解压中...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # 创建工作线程
        self.worker = ExtractArchiveWorker(
            self.archive_manager,
            self.archive_path,
            extract_to,
            password,
            self.selected_files
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
        self.extract_button.setText("开始解压")
        
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
                # 设置标志通知工作线程停止
                if hasattr(self.worker, 'stop_requested'):
                    self.worker.stop_requested = True
                
                # 等待线程正常结束
                self.worker.wait(3000)  # 等待3秒
                
                # 如果线程仍在运行，强制终止
                if self.worker.isRunning():
                    self.worker.terminate()
                    self.worker.wait(1000)
                
                # 清理工作线程
                self.worker.deleteLater()
                self.worker = None
            else:
                event.ignore()
                return
        
        # 如果有未运行的工作线程，也要清理
        if self.worker:
            self.worker.deleteLater()
            self.worker = None
                
        event.accept() 