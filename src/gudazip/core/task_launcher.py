#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务启动器
用于启动独立的后台任务进程
"""

import os
import sys
import subprocess
import json
from typing import List, Optional, Dict, Any
from pathlib import Path

# 全局任务启动器实例
_task_launcher = None


class TaskLauncher:
    """任务启动器"""
    
    def __init__(self):
        self.python_exe = sys.executable
        self.task_manager_script = os.path.join(
            os.path.dirname(__file__), 
            'standalone_task_manager.py'
        )
        
    def launch_compress_task(self, source_files: List[str], target_path: str,
                           compression_level: int = 6, password: Optional[str] = None,
                           delete_source: bool = False) -> bool:
        """启动压缩任务
        
        Args:
            source_files: 源文件列表
            target_path: 目标压缩包路径
            compression_level: 压缩级别 (0-9)
            password: 密码 (可选)
            delete_source: 是否删除源文件
            
        Returns:
            bool: 是否成功启动
        """
        try:
            # 准备命令行参数
            cmd = [
                self.python_exe,
                self.task_manager_script,
                'compress',
                '--source', source_files[0],  # 目前只支持单个文件
                '--target', target_path,
                '--level', str(compression_level)
            ]
            
            if password:
                cmd.extend(['--password', password])
                
            if delete_source:
                cmd.append('--delete-source')
            
            # 启动独立进程
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0,
                start_new_session=True if os.name != 'nt' else False
            )
            
            print(f"已启动独立压缩任务进程 (PID: {process.pid})")
            print(f"压缩文件: {source_files}")
            print(f"目标路径: {target_path}")
            
            return True
            
        except Exception as e:
            print(f"启动压缩任务失败: {e}")
            return False
            
    def launch_extract_task(self, archive_path: str, target_path: str,
                          password: Optional[str] = None) -> bool:
        """启动解压任务
        
        Args:
            archive_path: 压缩包路径
            target_path: 解压目标路径
            password: 密码 (可选)
            
        Returns:
            bool: 是否成功启动
        """
        try:
            # 准备命令行参数
            cmd = [
                self.python_exe,
                self.task_manager_script,
                'extract',
                '--source', archive_path,
                '--target', target_path
            ]
            
            if password:
                cmd.extend(['--password', password])
            
            # 启动独立进程
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0,
                start_new_session=True if os.name != 'nt' else False
            )
            
            print(f"已启动独立解压任务进程 (PID: {process.pid})")
            print(f"压缩包: {archive_path}")
            print(f"目标路径: {target_path}")
            
            return True
            
        except Exception as e:
            print(f"启动解压任务失败: {e}")
            return False
            
    def is_task_manager_running(self) -> bool:
        """检查是否有任务管理器进程在运行"""
        try:
            if os.name == 'nt':
                # Windows
                import psutil
                for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                    try:
                        cmdline = proc.info['cmdline']
                        if (cmdline and 
                            'python' in cmdline[0].lower() and 
                            'standalone_task_manager.py' in ' '.join(cmdline)):
                            return True
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
            else:
                # Unix/Linux
                result = subprocess.run(
                    ['pgrep', '-f', 'standalone_task_manager.py'],
                    capture_output=True,
                    text=True
                )
                return result.returncode == 0
                
        except Exception as e:
            print(f"检查任务管理器进程失败: {e}")
            
        return False
        
    def get_task_status(self) -> dict:
        """获取任务状态"""
        try:
            data_dir = Path.home() / '.gudazip' / 'tasks'
            if not data_dir.exists():
                return {}
                
            tasks = {}
            for task_file in data_dir.glob('*.json'):
                try:
                    with open(task_file, 'r', encoding='utf-8') as f:
                        task_data = json.load(f)
                        tasks[task_data['task_id']] = task_data
                except Exception as e:
                    print(f"读取任务文件失败 {task_file}: {e}")
                    
            return tasks
            
        except Exception as e:
            print(f"获取任务状态失败: {e}")
            return {}
            
    def cleanup_completed_tasks(self):
        """清理已完成的任务文件"""
        try:
            data_dir = Path.home() / '.gudazip' / 'tasks'
            if not data_dir.exists():
                return
                
            for task_file in data_dir.glob('*.json'):
                try:
                    with open(task_file, 'r', encoding='utf-8') as f:
                        task_data = json.load(f)
                        
                    # 删除已完成或失败的任务文件（保留最近24小时的）
                    if task_data.get('status') in ['completed', 'failed', 'cancelled']:
                        from datetime import datetime, timedelta
                        end_time = task_data.get('end_time')
                        if end_time:
                            end_dt = datetime.fromisoformat(end_time)
                            if datetime.now() - end_dt > timedelta(hours=24):
                                task_file.unlink()
                                print(f"已清理任务文件: {task_file.name}")
                                
                except Exception as e:
                    print(f"清理任务文件失败 {task_file}: {e}")
                    
        except Exception as e:
            print(f"清理已完成任务失败: {e}")


def get_task_launcher() -> TaskLauncher:
    """获取全局任务启动器实例"""
    global _task_launcher
    if _task_launcher is None:
        _task_launcher = TaskLauncher()
    return _task_launcher