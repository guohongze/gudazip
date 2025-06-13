#!/usr/bin/env python3
"""
独立的后台任务管理器
管理压缩/解压的后台任务，与主窗口完全解耦
"""

import os
from PySide6.QtCore import QObject, QThread, Signal, QTimer
from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QMessageBox, QDialog, QVBoxLayout, QLabel, QPushButton, QProgressBar
from PySide6.QtGui import QIcon, QAction


class BackgroundTaskManager(QObject):
    """独立的后台任务管理器"""
    
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
        dialog = TaskManagerDialog(self.active_tasks)
        dialog.exec()
        
    def show_task_status(self, task_id):
        """显示特定任务状态"""
        if task_id in self.active_tasks:
            task_info = self.active_tasks[task_id]
            dialog = TaskStatusDialog(task_info)
            dialog.exec()
            
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
            
    def update_task_status(self, task_id, status):
        """更新任务状态"""
        if task_id in self.active_tasks:
            self.active_tasks[task_id].status = status
            self.update_tray_tooltip()
            
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
        
        # 从活动任务中移除
        del self.active_tasks[task_id]
        
        # 更新托盘
        self.update_tray_menu()
        self.update_tray_tooltip()
        
        # 如果没有活动任务了，隐藏托盘图标
        if not self.active_tasks and self.tray_icon:
            QTimer.singleShot(5000, self.hide_tray_if_no_tasks)  # 5秒后隐藏
            
        # 显示结果对话框
        result_dialog = TaskResultDialog(task_info)
        result_dialog.exec()
        
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
    """任务管理器对话框"""
    
    def __init__(self, active_tasks):
        super().__init__()
        self.active_tasks = active_tasks
        self.setWindowTitle("GudaZip - 后台任务管理器")
        self.setMinimumSize(400, 300)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        if self.active_tasks:
            layout.addWidget(QLabel(f"当前有 {len(self.active_tasks)} 个活动任务:"))
            
            for task_info in self.active_tasks.values():
                task_widget = QLabel(f"{task_info.name}: {task_info.progress}% - {task_info.status}")
                layout.addWidget(task_widget)
        else:
            layout.addWidget(QLabel("当前没有活动任务"))
        
        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)


class TaskStatusDialog(QDialog):
    """任务状态对话框"""
    
    def __init__(self, task_info):
        super().__init__()
        self.task_info = task_info
        self.setWindowTitle(f"任务状态 - {task_info.name}")
        self.setMinimumSize(300, 200)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel(f"任务名称: {self.task_info.name}"))
        layout.addWidget(QLabel(f"任务类型: {self.task_info.task_type}"))
        layout.addWidget(QLabel(f"进度: {self.task_info.progress}%"))
        layout.addWidget(QLabel(f"状态: {self.task_info.status}"))
        
        # 进度条
        progress_bar = QProgressBar()
        progress_bar.setValue(self.task_info.progress)
        layout.addWidget(progress_bar)
        
        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)


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