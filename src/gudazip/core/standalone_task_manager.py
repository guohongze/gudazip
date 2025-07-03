#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
独立的后台任务管理器进程
用于处理后台压缩/解压任务，独立于主程序运行
"""

import sys
import os
import json
import time
import uuid
import subprocess
import signal
import threading
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'src'))

from PySide6.QtCore import QCoreApplication, QThread, Signal, QObject, QTimer
from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PySide6.QtGui import QIcon, QAction


@dataclass
class TaskInfo:
    """任务信息"""
    task_id: str
    task_name: str
    task_type: str  # 'compress' 或 'extract'
    status: str  # 'running', 'completed', 'failed', 'cancelled'
    progress: int
    start_time: str
    end_time: Optional[str] = None
    error_message: Optional[str] = None
    
    # 任务参数
    source_files: list = None
    target_path: str = None
    compression_level: int = 6
    password: Optional[str] = None
    delete_source: bool = False


class StandaloneTaskWorker(QThread):
    """独立任务工作线程"""
    
    progress = Signal(int)
    status = Signal(str)
    finished = Signal(bool, str)
    
    def __init__(self, task_info: TaskInfo):
        super().__init__()
        self.task_info = task_info
        self._is_cancelled = False
        
    def cancel(self):
        """取消任务"""
        self._is_cancelled = True
        self.requestInterruption()
        
    def is_cancelled(self):
        """检查是否已取消"""
        return self._is_cancelled or self.isInterruptionRequested()
        
    def run(self):
        """执行任务"""
        try:
            if self.task_info.task_type == 'compress':
                self._run_compress_task()
            elif self.task_info.task_type == 'extract':
                self._run_extract_task()
            else:
                self.finished.emit(False, f"未知任务类型: {self.task_info.task_type}")
                
        except Exception as e:
            if self.is_cancelled():
                self.finished.emit(False, "任务已取消")
            else:
                self.finished.emit(False, f"任务执行失败: {str(e)}")
                
    def _run_compress_task(self):
        """执行压缩任务"""
        from gudazip.core.standalone_archive_manager import StandaloneArchiveManager
        
        self.status.emit("正在初始化压缩...")
        # 使用独立的压缩管理器，避免Qt线程问题
        archive_manager = StandaloneArchiveManager()
        
        # 进度回调函数（接受两个参数：进度值和状态文本）
        def progress_callback(progress, status_text=None):
            if self.is_cancelled():
                return False  # 返回False表示取消操作
            self.progress.emit(int(progress))
            if status_text:
                self.status.emit(status_text)
            return True
            
        try:
            # 执行压缩
            result = archive_manager.create_archive(
                file_path=self.task_info.target_path,
                files=self.task_info.source_files,
                compression_level=self.task_info.compression_level,
                password=self.task_info.password,
                progress_callback=progress_callback
            )
            
            if self.is_cancelled():
                self.finished.emit(False, "任务已取消")
                return
                
            if result:
                # 如果需要删除源文件
                if self.task_info.delete_source:
                    self.status.emit("正在删除源文件...")
                    for file_path in self.task_info.source_files:
                        try:
                            if os.path.isfile(file_path):
                                os.remove(file_path)
                            elif os.path.isdir(file_path):
                                import shutil
                                shutil.rmtree(file_path)
                        except Exception as e:
                            print(f"删除源文件失败: {file_path}, 错误: {e}")
                            
                self.finished.emit(True, "压缩完成")
            else:
                self.finished.emit(False, "压缩失败")
                
        except Exception as e:
            self.finished.emit(False, f"压缩过程中发生错误: {str(e)}")
            
    def _run_extract_task(self):
        """执行解压任务"""
        from gudazip.core.standalone_archive_manager import StandaloneArchiveManager
        
        self.status.emit("正在初始化解压...")
        # 使用独立的压缩管理器，避免Qt线程问题
        archive_manager = StandaloneArchiveManager()
        
        # 进度回调函数（接受两个参数：进度值和状态文本）
        def progress_callback(progress, status_text=None):
            if self.is_cancelled():
                return False
            self.progress.emit(int(progress))
            if status_text:
                self.status.emit(status_text)
            return True
            
        try:
            # 执行解压
            result = archive_manager.extract_archive(
                file_path=self.task_info.source_files[0],  # 解压时source_files[0]是压缩包路径
                extract_to=self.task_info.target_path,
                password=self.task_info.password,
                progress_callback=progress_callback
            )
            
            if self.is_cancelled():
                self.finished.emit(False, "任务已取消")
                return
                
            if result:
                self.finished.emit(True, "解压完成")
            else:
                self.finished.emit(False, "解压失败")
                
        except Exception as e:
            self.finished.emit(False, f"解压过程中发生错误: {str(e)}")


class StandaloneTaskManager(QObject):
    """独立的任务管理器"""
    
    def __init__(self):
        super().__init__()
        self.tasks: Dict[str, TaskInfo] = {}
        self.workers: Dict[str, StandaloneTaskWorker] = {}
        self.tray_icon = None
        self.app = None
        
        # 创建任务数据目录
        self.data_dir = Path.home() / '.gudazip' / 'tasks'
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 设置信号处理
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    def _signal_handler(self, signum, frame):
        """信号处理器"""
        print(f"收到信号 {signum}，正在清理...")
        self.cleanup()
        sys.exit(0)
        
    def setup_system_tray(self):
        """设置系统托盘"""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            print("系统托盘不可用")
            return
            
        # 设置托盘图标
        icon_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
            "resources", "icons", "app.ico"
        )
        
        if os.path.exists(icon_path):
            icon = QIcon(icon_path)
        else:
            icon = QIcon()  # 使用默认图标
            
        self.tray_icon = QSystemTrayIcon(icon)
        
        # 创建托盘菜单
        tray_menu = QMenu()
        
        # 显示任务管理器
        show_action = QAction("显示任务管理器", self)
        show_action.triggered.connect(self.show_task_manager)
        tray_menu.addAction(show_action)
        
        tray_menu.addSeparator()
        
        # 退出
        quit_action = QAction("退出", self)
        quit_action.triggered.connect(self.quit_application)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        
        # 更新托盘提示
        self.update_tray_tooltip()
        
    def update_tray_tooltip(self):
        """更新托盘提示"""
        if not self.tray_icon:
            return
            
        running_count = len([t for t in self.tasks.values() if t.status == 'running'])
        if running_count > 0:
            self.tray_icon.setToolTip(f"GudaZip 后台任务管理器 - {running_count} 个任务正在运行")
        else:
            self.tray_icon.setToolTip("GudaZip 后台任务管理器 - 无活动任务")
            
    def show_task_manager(self):
        """显示任务管理器窗口"""
        # 这里可以实现一个简单的任务管理器窗口
        print("当前任务:")
        for task_id, task in self.tasks.items():
            print(f"  {task.task_name}: {task.status} ({task.progress}%)")
            
    def quit_application(self):
        """退出应用程序"""
        self.cleanup()
        if self.app:
            self.app.quit()
            
    def add_task(self, task_info: TaskInfo) -> str:
        """添加任务"""
        task_id = task_info.task_id
        self.tasks[task_id] = task_info
        
        # 保存任务信息到文件
        self._save_task_info(task_info)
        
        # 创建工作线程
        worker = StandaloneTaskWorker(task_info)
        self.workers[task_id] = worker
        
        # 连接信号
        worker.progress.connect(lambda p: self._on_task_progress(task_id, p))
        worker.status.connect(lambda s: self._on_task_status(task_id, s))
        worker.finished.connect(lambda success, msg: self._on_task_finished(task_id, success, msg))
        
        # 启动任务
        worker.start()
        
        # 更新托盘
        self.update_tray_tooltip()
        
        print(f"任务已启动: {task_info.task_name}")
        return task_id
        
    def _on_task_progress(self, task_id: str, progress: int):
        """任务进度更新"""
        if task_id in self.tasks:
            self.tasks[task_id].progress = progress
            self._save_task_info(self.tasks[task_id])
            
    def _on_task_status(self, task_id: str, status: str):
        """任务状态更新"""
        if task_id in self.tasks:
            print(f"任务 {self.tasks[task_id].task_name}: {status}")
            
    def _on_task_finished(self, task_id: str, success: bool, message: str):
        """任务完成"""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task.status = 'completed' if success else 'failed'
            task.end_time = datetime.now().isoformat()
            task.error_message = message if not success else None
            
            self._save_task_info(task)
            
            # 显示通知
            if self.tray_icon:
                icon_type = QSystemTrayIcon.Information if success else QSystemTrayIcon.Critical
                self.tray_icon.showMessage(
                    "任务完成" if success else "任务失败",
                    f"{task.task_name}: {message}",
                    icon_type,
                    3000
                )
                
            print(f"任务完成: {task.task_name} - {message}")
            
            # 清理工作线程
            if task_id in self.workers:
                del self.workers[task_id]
                
            # 更新托盘
            self.update_tray_tooltip()
            
            # 如果没有活动任务，考虑退出
            self._check_auto_exit()
            
    def _save_task_info(self, task_info: TaskInfo):
        """保存任务信息到文件"""
        try:
            task_file = self.data_dir / f"{task_info.task_id}.json"
            with open(task_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(task_info), f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存任务信息失败: {e}")
            
    def _check_auto_exit(self):
        """检查是否应该自动退出"""
        # 如果没有正在运行的任务，延迟退出
        running_tasks = [t for t in self.tasks.values() if t.status == 'running']
        if not running_tasks:
            print("所有任务已完成，将在30秒后自动退出...")
            QTimer.singleShot(30000, self.quit_application)  # 30秒后退出
            
    def cancel_task(self, task_id: str):
        """取消任务"""
        if task_id in self.workers:
            worker = self.workers[task_id]
            worker.cancel()
            
        if task_id in self.tasks:
            self.tasks[task_id].status = 'cancelled'
            self._save_task_info(self.tasks[task_id])
            
    def cleanup(self):
        """清理资源"""
        print("正在清理后台任务管理器...")
        
        # 取消所有正在运行的任务
        for task_id, worker in list(self.workers.items()):
            if worker.isRunning():
                print(f"正在取消任务: {task_id}")
                worker.cancel()
                if not worker.wait(3000):  # 等待3秒
                    worker.terminate()
                    worker.wait()
                    
        # 隐藏托盘图标
        if self.tray_icon:
            self.tray_icon.hide()
            
        print("后台任务管理器清理完成")


def create_compress_task(source_files: list, target_path: str, 
                        compression_level: int = 6, password: str = None, 
                        delete_source: bool = False) -> TaskInfo:
    """创建压缩任务"""
    task_id = str(uuid.uuid4())
    task_name = f"压缩: {os.path.basename(target_path)}"
    
    return TaskInfo(
        task_id=task_id,
        task_name=task_name,
        task_type='compress',
        status='running',
        progress=0,
        start_time=datetime.now().isoformat(),
        source_files=source_files,
        target_path=target_path,
        compression_level=compression_level,
        password=password,
        delete_source=delete_source
    )


def create_extract_task(archive_path: str, target_path: str, 
                       password: str = None) -> TaskInfo:
    """创建解压任务"""
    task_id = str(uuid.uuid4())
    task_name = f"解压: {os.path.basename(archive_path)}"
    
    return TaskInfo(
        task_id=task_id,
        task_name=task_name,
        task_type='extract',
        status='running',
        progress=0,
        start_time=datetime.now().isoformat(),
        source_files=[archive_path],
        target_path=target_path,
        password=password
    )


def main():
    """主函数"""
    import argparse
    
    print("独立任务管理器启动中...")
    
    # 添加项目根目录到Python路径
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    src_path = os.path.join(project_root, 'src')
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
        print(f"已添加到Python路径: {src_path}")
    
    # 创建应用程序
    try:
        app = QApplication(sys.argv)
        app.setApplicationName("GudaZip 后台任务管理器")
        print("QApplication 创建成功")
    except Exception as e:
        print(f"QApplication 创建失败，使用 QCoreApplication: {e}")
        app = QCoreApplication(sys.argv)
        app.setApplicationName("GudaZip 后台任务管理器")
    
    # 创建任务管理器
    print("创建任务管理器...")
    task_manager = StandaloneTaskManager()
    task_manager.app = app
    print("任务管理器创建成功")
    
    # 设置系统托盘
    try:
        task_manager.setup_system_tray()
        print("系统托盘设置成功")
    except Exception as e:
        print(f"无法设置系统托盘: {e}")
    
    # 解析命令行参数
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'compress':
            # 解析压缩参数
            parser = argparse.ArgumentParser(description='压缩任务')
            parser.add_argument('--source', required=True, help='源文件路径')
            parser.add_argument('--target', required=True, help='目标文件路径')
            parser.add_argument('--level', type=int, default=6, help='压缩级别')
            parser.add_argument('--password', help='密码')
            parser.add_argument('--delete-source', action='store_true', help='删除源文件')
            
            try:
                args = parser.parse_args(sys.argv[2:])
                source_files = [args.source]  # 单个文件
                
                print(f"开始压缩任务: {args.source} -> {args.target}")
                
                task_info = create_compress_task(
                    source_files, args.target, args.level, args.password, args.delete_source
                )
                task_manager.add_task(task_info)
            except Exception as e:
                print(f"压缩参数解析错误: {e}")
                return 1
            
        elif command == 'extract':
            # 解析解压参数
            parser = argparse.ArgumentParser(description='解压任务')
            parser.add_argument('--source', required=True, help='压缩包路径')
            parser.add_argument('--target', required=True, help='目标目录路径')
            parser.add_argument('--password', help='密码')
            
            try:
                args = parser.parse_args(sys.argv[2:])
                
                print(f"开始解压任务: {args.source} -> {args.target}")
                
                task_info = create_extract_task(args.source, args.target, args.password)
                task_manager.add_task(task_info)
            except Exception as e:
                print(f"解压参数解析错误: {e}")
                return 1
            
        else:
            print("用法:")
            print("  压缩: python standalone_task_manager.py compress --source <file> --target <output> [--level <level>] [--password <pwd>] [--delete-source]")
            print("  解压: python standalone_task_manager.py extract --source <archive> --target <dir> [--password <pwd>]")
            return 1
    else:
        print("GudaZip 后台任务管理器已启动，等待任务...")
    
    # 运行应用程序
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())