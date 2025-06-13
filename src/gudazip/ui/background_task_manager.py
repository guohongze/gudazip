#!/usr/bin/env python3
"""
独立的后台任务管理器
管理压缩/解压的后台任务，与主窗口完全解耦
"""

import os
from PySide6.QtCore import QObject, QThread, Signal, QTimer
from PySide6.QtWidgets import (QSystemTrayIcon, QMenu, QMessageBox, QDialog, 
                               QVBoxLayout, QLabel, QPushButton, QProgressBar, QHBoxLayout, QWidget)
from PySide6.QtGui import QIcon, QAction, QFont
from PySide6.QtCore import Qt


class ProgressBarWidget(QProgressBar):
    """美化的进度条组件（与前台压缩相同）"""
    
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


class BackgroundTaskManager(QObject):
    """独立的后台任务管理器"""
    
    # 定义信号用于通知任务状态变化
    task_progress_updated = Signal(str, int)  # (task_id, progress)
    task_status_updated = Signal(str, str)    # (task_id, status)
    task_finished = Signal(str, bool, str)    # (task_id, success, message)
    
    def __init__(self):
        super().__init__()
        self.active_tasks = {}  # 活动任务字典 {task_id: TaskInfo}
        self.tray_icon = None
        self.setup_system_tray()
        
    def setup_system_tray(self):
        """设置系统托盘"""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            print("系统托盘不可用")
            return
            
        # 创建托盘图标
        self.tray_icon = QSystemTrayIcon(self)
        
        # 使用 GudaZip 的 ico 图标
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
            icon_path = os.path.join(project_root, "resources", "icons", "gudazip.ico")
            
            if os.path.exists(icon_path):
                self.tray_icon.setIcon(QIcon(icon_path))
                print(f"后台任务管理器使用 GudaZip 图标: {icon_path}")
            else:
                print(f"图标文件不存在: {icon_path}")
                
        except Exception as e:
            print(f"设置托盘图标失败: {e}")
        
        # 创建托盘菜单
        self.update_tray_menu()
        
        # 双击托盘图标显示任务状态
        self.tray_icon.activated.connect(self.on_tray_icon_activated)
        
        # 设置初始工具提示
        self.tray_icon.setToolTip("GudaZip - 后台任务管理器")
        
        print("后台任务管理器托盘设置完成")
        
    def update_tray_menu(self):
        """更新托盘菜单"""
        if not self.tray_icon:
            return
            
        tray_menu = QMenu()
        
        # 显示任务状态
        if self.active_tasks:
            status_action = QAction(f"活动任务: {len(self.active_tasks)} 个", self)
            status_action.setEnabled(False)
            tray_menu.addAction(status_action)
            
            tray_menu.addSeparator()
            
            # 为每个任务添加菜单项
            for task_id, task_info in self.active_tasks.items():
                task_action = QAction(f"{task_info.name} - {task_info.progress}%", self)
                task_action.triggered.connect(lambda checked, tid=task_id: self.show_task_status(tid))
                tray_menu.addAction(task_action)
                
            tray_menu.addSeparator()
        else:
            no_tasks_action = QAction("无活动任务", self)
            no_tasks_action.setEnabled(False)
            tray_menu.addAction(no_tasks_action)
            tray_menu.addSeparator()
        
        # 显示所有任务
        show_all_action = QAction("显示任务状态", self)
        show_all_action.triggered.connect(self.show_task_manager_window)
        tray_menu.addAction(show_all_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        
    def on_tray_icon_activated(self, reason):
        """托盘图标激活事件"""
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_task_manager_window()
            
    def show_task_manager_window(self):
        """显示任务管理器窗口"""
        dialog = TaskManagerDialog(self.active_tasks, self)
        dialog.exec()
        
    def show_task_status(self, task_id):
        """显示特定任务状态"""
        if task_id in self.active_tasks:
            task_info = self.active_tasks[task_id]
            # 创建任务状态对话框，传入任务管理器实例以便接收信号
            dialog = TaskStatusDialog(task_info, self)
            dialog.show()  # 使用show()而不是exec()，这样对话框不会阻塞
            
    def add_task(self, task_id, task_name, task_type, worker):
        """添加后台任务"""
        task_info = TaskInfo(task_id, task_name, task_type, worker)
        self.active_tasks[task_id] = task_info
        
        # 连接工作线程信号
        worker.progress.connect(lambda progress: self.update_task_progress(task_id, progress))
        worker.status.connect(lambda status: self.update_task_status(task_id, status))
        worker.finished.connect(lambda success, message: self.on_task_finished(task_id, success, message))
        
        # 显示托盘图标
        if self.tray_icon:
            self.tray_icon.show()
            self.update_tray_menu()
            self.update_tray_tooltip()
            
            # 显示开始通知
            self.tray_icon.showMessage(
                "GudaZip - 后台任务",
                f"开始{task_type}: {task_name}",
                QSystemTrayIcon.Information,
                5000
            )
        
        print(f"添加后台任务: {task_name}")
        
    def update_task_progress(self, task_id, progress):
        """更新任务进度"""
        if task_id in self.active_tasks:
            self.active_tasks[task_id].progress = progress
            self.update_tray_menu()
            self.update_tray_tooltip()
            
            # 发出信号通知所有监听者（包括打开的对话框）
            self.task_progress_updated.emit(task_id, progress)
            
    def update_task_status(self, task_id, status):
        """更新任务状态"""
        if task_id in self.active_tasks:
            self.active_tasks[task_id].status = status
            self.update_tray_tooltip()
            
            # 发出信号通知所有监听者
            self.task_status_updated.emit(task_id, status)
            
    def update_tray_tooltip(self):
        """更新托盘工具提示"""
        if not self.tray_icon or not self.active_tasks:
            if self.tray_icon:
                self.tray_icon.setToolTip("GudaZip - 后台任务管理器")
            return
            
        if len(self.active_tasks) == 1:
            task_info = list(self.active_tasks.values())[0]
            tooltip = f"GudaZip - {task_info.name} ({task_info.progress}%)"
        else:
            tooltip = f"GudaZip - {len(self.active_tasks)} 个活动任务"
            
        self.tray_icon.setToolTip(tooltip)
        
    def on_task_finished(self, task_id, success, message):
        """任务完成处理"""
        if task_id not in self.active_tasks:
            return
            
        task_info = self.active_tasks[task_id]
        task_info.completed = True
        task_info.success = success
        task_info.message = message
        
        # 发出任务完成信号
        self.task_finished.emit(task_id, success, message)
        
        # 显示完成通知
        if self.tray_icon:
            if success:
                self.tray_icon.showMessage(
                    "GudaZip - 任务完成",
                    f"{task_info.name} 完成！双击查看详情。",
                    QSystemTrayIcon.Information,
                    10000
                )
            else:
                self.tray_icon.showMessage(
                    "GudaZip - 任务失败",
                    f"{task_info.name} 失败！双击查看详情。",
                    QSystemTrayIcon.Critical,
                    10000
                )
        
        # 显示弹窗提示（更明显的通知）
        from PySide6.QtWidgets import QMessageBox
        if success:
            QMessageBox.information(
                None, 
                "GudaZip - 任务完成", 
                f"后台任务已成功完成！\n\n任务：{task_info.name}\n类型：{task_info.task_type}\n\n{message}",
                QMessageBox.Ok
            )
        else:
            QMessageBox.warning(
                None, 
                "GudaZip - 任务失败", 
                f"后台任务执行失败！\n\n任务：{task_info.name}\n类型：{task_info.task_type}\n\n错误信息：{message}",
                QMessageBox.Ok
            )
        
        # 从活动任务中移除
        del self.active_tasks[task_id]
        
        # 更新托盘
        self.update_tray_menu()
        self.update_tray_tooltip()
        
        # 如果没有活动任务了，隐藏托盘图标
        if not self.active_tasks and self.tray_icon:
            QTimer.singleShot(5000, self.hide_tray_if_no_tasks)  # 5秒后隐藏
            
        print(f"任务完成: {task_info.name}, 成功: {success}")
        
    def hide_tray_if_no_tasks(self):
        """如果没有活动任务，隐藏托盘图标"""
        if not self.active_tasks and self.tray_icon:
            self.tray_icon.hide()
            
    def cancel_task(self, task_id):
        """取消任务"""
        if task_id in self.active_tasks:
            task_info = self.active_tasks[task_id]
            if task_info.worker and task_info.worker.isRunning():
                task_info.worker.terminate()
                task_info.worker.wait()
            del self.active_tasks[task_id]
            self.update_tray_menu()
            self.update_tray_tooltip()
            
    def cleanup(self):
        """清理资源"""
        # 终止所有活动任务
        for task_info in self.active_tasks.values():
            if task_info.worker and task_info.worker.isRunning():
                task_info.worker.terminate()
                task_info.worker.wait()
        
        self.active_tasks.clear()
        
        # 隐藏托盘图标
        if self.tray_icon:
            self.tray_icon.hide()


class TaskInfo:
    """任务信息类"""
    
    def __init__(self, task_id, name, task_type, worker):
        self.task_id = task_id
        self.name = name
        self.task_type = task_type  # "压缩" 或 "解压"
        self.worker = worker
        self.progress = 0
        self.status = "准备中"
        self.completed = False
        self.success = False
        self.message = ""


class TaskManagerDialog(QDialog):
    """任务管理器对话框（支持实时进度条更新）"""
    
    def __init__(self, active_tasks, task_manager=None):
        super().__init__()
        self.active_tasks = active_tasks
        self.task_manager = task_manager
        self.task_widgets = {}  # 存储任务组件的引用
        self.setWindowTitle("GudaZip - 后台任务管理器")
        self.setMinimumSize(350, 180)
        self.setMaximumSize(450, 300)
        self.init_ui()
        self.setup_signals()
        
        # 设置窗口图标
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
            icon_path = os.path.join(project_root, "resources", "icons", "gudazip.ico")
            if os.path.exists(icon_path):
                self.setWindowIcon(QIcon(icon_path))
        except Exception:
            pass
        
    def init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 滚动区域用于显示任务
        from PySide6.QtWidgets import QScrollArea
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumHeight(120)
        scroll_area.setFrameStyle(0)  # 移除滚动区域边框
        
        # 任务容器
        self.tasks_container = QWidget()
        self.tasks_layout = QVBoxLayout(self.tasks_container)
        self.tasks_layout.setSpacing(0)
        self.tasks_layout.setContentsMargins(0, 0, 0, 0)
        
        scroll_area.setWidget(self.tasks_container)
        layout.addWidget(scroll_area)
        
        # 创建任务组件
        self.update_task_display()
        
    def setup_signals(self):
        """设置信号连接以接收实时更新"""
        if self.task_manager:
            # 连接任务管理器的信号
            self.task_manager.task_progress_updated.connect(self.on_progress_updated)
            self.task_manager.task_status_updated.connect(self.on_status_updated)
            self.task_manager.task_finished.connect(self.on_task_finished)
            
    def update_task_display(self):
        """更新任务显示"""
        # 清除现有的任务组件
        for i in reversed(range(self.tasks_layout.count())):
            child = self.tasks_layout.itemAt(i).widget()
            if child:
                child.setParent(None)
        
        self.task_widgets.clear()
        
        if not self.active_tasks:
            # 没有活动任务
            no_tasks_label = QLabel("当前没有活动任务")
            no_tasks_label.setAlignment(Qt.AlignCenter)
            no_tasks_label.setStyleSheet("color: #666666; font-size: 11px; padding: 15px;")
            self.tasks_layout.addWidget(no_tasks_label)
        else:
            # 为每个任务创建组件
            for task_id, task_info in self.active_tasks.items():
                task_widget = self.create_task_widget(task_id, task_info)
                self.tasks_layout.addWidget(task_widget)
                self.task_widgets[task_id] = task_widget
                
        # 添加弹性空间
        self.tasks_layout.addStretch()
        
    def create_task_widget(self, task_id, task_info):
        """为单个任务创建组件"""
        from PySide6.QtWidgets import QFrame
        
        # 创建任务框架（使用系统默认样式）
        task_frame = QFrame()
        task_frame.setFrameStyle(QFrame.Box)
        
        frame_layout = QVBoxLayout(task_frame)
        frame_layout.setSpacing(4)
        frame_layout.setContentsMargins(6, 6, 6, 6)
        
        # 任务标题
        title_layout = QHBoxLayout()
        title_label = QLabel(f"任务: {task_info.name}")
        title_font = QFont()
        title_font.setPointSize(10)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_layout.addWidget(title_label)
        
        # 任务类型标签
        type_label = QLabel(f"[{task_info.task_type}]")
        type_label.setStyleSheet("color: #666666; font-weight: bold; font-size: 9px;")
        title_layout.addWidget(type_label)
        
        title_layout.addStretch()
        frame_layout.addLayout(title_layout)
        
        # 进度条（使用与前台相同的美化进度条）
        progress_bar = ProgressBarWidget()
        progress_bar.setValue(task_info.progress)
        progress_bar.setMaximumHeight(20)
        frame_layout.addWidget(progress_bar)
        
        # 状态标签
        status_label = QLabel(task_info.status)
        status_label.setAlignment(Qt.AlignCenter)
        status_label.setStyleSheet("font-size: 9px; color: #666666; margin: 1px;")
        frame_layout.addWidget(status_label)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # 取消任务按钮
        cancel_btn = QPushButton("取消任务")
        cancel_btn.clicked.connect(lambda: self.cancel_task(task_id))
        button_layout.addWidget(cancel_btn)
        
        # 关闭窗口按钮
        close_btn = QPushButton("关闭窗口")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        frame_layout.addLayout(button_layout)
        
        # 存储组件引用以便后续更新
        task_frame.progress_bar = progress_bar
        task_frame.status_label = status_label
        task_frame.task_id = task_id
        
        return task_frame
        
    def cancel_task(self, task_id):
        """取消任务"""
        if task_id in self.active_tasks:
            task_info = self.active_tasks[task_id]
            reply = QMessageBox.question(
                self, "确认取消", 
                f"确定要取消任务 '{task_info.name}' 吗？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                if self.task_manager:
                    self.task_manager.cancel_task(task_id)
                # 刷新显示
                self.update_task_display()
                
    def on_progress_updated(self, task_id, progress):
        """处理进度更新信号"""
        if task_id in self.task_widgets:
            task_widget = self.task_widgets[task_id]
            if hasattr(task_widget, 'progress_bar'):
                task_widget.progress_bar.setValue(progress)
                
    def on_status_updated(self, task_id, status):
        """处理状态更新信号"""
        if task_id in self.task_widgets:
            task_widget = self.task_widgets[task_id]
            if hasattr(task_widget, 'status_label'):
                task_widget.status_label.setText(status)
                
    def on_task_finished(self, task_id, success, message):
        """处理任务完成信号"""
        # 刷新任务显示，移除已完成的任务
        self.update_task_display()


class TaskStatusDialog(QDialog):
    """任务状态对话框（支持实时更新）"""
    
    def __init__(self, task_info, task_manager=None):
        super().__init__()
        self.task_info = task_info
        self.task_manager = task_manager
        self.setWindowTitle(f"任务进度 - {task_info.name}")
        self.setMinimumSize(400, 300)
        self.setMaximumSize(600, 400)
        self.init_ui()
        self.setup_signals()
        
        # 设置窗口图标
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
            icon_path = os.path.join(project_root, "resources", "icons", "gudazip.ico")
            if os.path.exists(icon_path):
                self.setWindowIcon(QIcon(icon_path))
        except Exception:
            pass
        
    def init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 任务信息标题
        title_label = QLabel(f"任务: {self.task_info.name}")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # 任务类型
        type_label = QLabel(f"类型: {self.task_info.task_type}")
        type_label.setStyleSheet("color: #666666; font-size: 11px;")
        layout.addWidget(type_label)
        
        # 使用与前台相同的美化进度条
        self.progress_bar = ProgressBarWidget()
        self.progress_bar.setValue(self.task_info.progress)
        layout.addWidget(self.progress_bar)
        
        # 状态标签
        self.status_label = QLabel(self.task_info.status)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("font-size: 10px; color: #666666; margin: 5px;")
        layout.addWidget(self.status_label)
        
        # 完成状态区域（初始隐藏）
        self.completion_widget = QWidget()
        self.completion_layout = QVBoxLayout(self.completion_widget)
        self.completion_layout.setContentsMargins(0, 0, 0, 0)
        
        self.completion_label = QLabel()
        self.completion_label.setAlignment(Qt.AlignCenter)
        self.completion_layout.addWidget(self.completion_label)
        
        self.message_label = QLabel()
        self.message_label.setWordWrap(True)
        self.message_label.setStyleSheet("color: #666666; font-size: 10px; margin: 5px;")
        self.completion_layout.addWidget(self.message_label)
        
        self.completion_widget.hide()
        layout.addWidget(self.completion_widget)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # 取消按钮（仅在任务进行中显示）
        self.cancel_button = QPushButton("取消任务")
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
            QPushButton:pressed {
                background-color: #b71c1c;
            }
        """)
        self.cancel_button.clicked.connect(self.cancel_task)
        button_layout.addWidget(self.cancel_button)
        
        # 关闭按钮
        self.close_button = QPushButton("关闭")
        self.close_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
        """)
        self.close_button.clicked.connect(self.accept)
        button_layout.addWidget(self.close_button)
        
        layout.addLayout(button_layout)
        
    def setup_signals(self):
        """设置信号连接以接收实时更新"""
        if self.task_manager:
            # 连接任务管理器的信号
            self.task_manager.task_progress_updated.connect(self.on_progress_updated)
            self.task_manager.task_status_updated.connect(self.on_status_updated)
            self.task_manager.task_finished.connect(self.on_task_finished)
            
    def on_progress_updated(self, task_id, progress):
        """处理进度更新信号"""
        if task_id == self.task_info.task_id:
            self.progress_bar.setValue(progress)
            
    def on_status_updated(self, task_id, status):
        """处理状态更新信号"""
        if task_id == self.task_info.task_id:
            self.status_label.setText(status)
            
    def on_task_finished(self, task_id, success, message):
        """处理任务完成信号"""
        if task_id == self.task_info.task_id:
            # 隐藏取消按钮
            self.cancel_button.hide()
            
            # 显示完成状态
            if success:
                self.completion_label.setText("✅ 任务成功完成")
                self.completion_label.setStyleSheet("color: #4CAF50; font-weight: bold; font-size: 14px;")
            else:
                self.completion_label.setText("❌ 任务执行失败")
                self.completion_label.setStyleSheet("color: #f44336; font-weight: bold; font-size: 14px;")
                
            # 显示结果消息
            if message:
                self.message_label.setText(f"结果: {message}")
                
            self.completion_widget.show()
            
    def cancel_task(self):
        """取消任务"""
        reply = QMessageBox.question(
            self, "确认取消", 
            f"确定要取消任务 '{self.task_info.name}' 吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if self.task_manager:
                self.task_manager.cancel_task(self.task_info.task_id)
            self.accept()


class TaskResultDialog(QDialog):
    """任务结果对话框"""
    
    def __init__(self, task_info):
        super().__init__()
        self.task_info = task_info
        self.setWindowTitle(f"任务结果 - {task_info.name}")
        self.setMinimumSize(350, 200)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 设置窗口图标
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
            icon_path = os.path.join(project_root, "resources", "icons", "gudazip.ico")
            if os.path.exists(icon_path):
                self.setWindowIcon(QIcon(icon_path))
        except Exception:
            pass
        
        layout.addWidget(QLabel(f"任务: {self.task_info.name}"))
        layout.addWidget(QLabel(f"类型: {self.task_info.task_type}"))
        
        if self.task_info.success:
            status_label = QLabel("✅ 任务成功完成")
            status_label.setStyleSheet("color: green; font-weight: bold;")
        else:
            status_label = QLabel("❌ 任务执行失败")
            status_label.setStyleSheet("color: red; font-weight: bold;")
            
        layout.addWidget(status_label)
        
        # 结果消息
        if self.task_info.message:
            message_label = QLabel(f"结果: {self.task_info.message}")
            message_label.setWordWrap(True)
            layout.addWidget(message_label)
        
        # 确定按钮
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self.accept)
        layout.addWidget(ok_btn)


# 全局后台任务管理器实例
_background_task_manager = None

def get_background_task_manager():
    """获取全局后台任务管理器实例"""
    global _background_task_manager
    if _background_task_manager is None:
        _background_task_manager = BackgroundTaskManager()
    return _background_task_manager 