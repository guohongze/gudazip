#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
错误管理器
统一管理所有错误处理，包括错误分类、用户友好提示、错误日志等
提升用户体验和问题诊断能力
"""

import os
import sys
import time
import traceback
import logging
from enum import Enum
from typing import Optional, Dict, Any, Callable, Union
from pathlib import Path
from datetime import datetime
from PySide6.QtWidgets import QMessageBox, QWidget, QApplication
from PySide6.QtCore import QObject, Signal

# 设置日志
logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    """错误分类枚举"""
    # 文件操作错误
    FILE_NOT_FOUND = "file_not_found"
    FILE_PERMISSION = "file_permission"
    FILE_OPERATION = "file_operation"
    FILE_SYSTEM = "file_system"
    
    # 压缩包错误
    ARCHIVE_CORRUPTED = "archive_corrupted"
    ARCHIVE_FORMAT = "archive_format"
    ARCHIVE_PASSWORD = "archive_password"
    ARCHIVE_OPERATION = "archive_operation"
    
    # 系统错误
    SYSTEM_RESOURCE = "system_resource"
    SYSTEM_PERMISSION = "system_permission"
    SYSTEM_COMPATIBILITY = "system_compatibility"
    
    # 网络错误
    NETWORK_CONNECTION = "network_connection"
    NETWORK_TIMEOUT = "network_timeout"
    
    # 应用程序错误
    APP_CONFIGURATION = "app_configuration"
    APP_DEPENDENCY = "app_dependency"
    APP_INTERNAL = "app_internal"
    
    # 用户操作错误
    USER_INPUT = "user_input"
    USER_CANCELLED = "user_cancelled"
    
    # 未知错误
    UNKNOWN = "unknown"


class ErrorSeverity(Enum):
    """错误严重程度"""
    INFO = "info"           # 信息提示
    WARNING = "warning"     # 警告
    ERROR = "error"         # 错误
    CRITICAL = "critical"   # 严重错误


class ErrorInfo:
    """错误信息封装"""
    
    def __init__(self, category: ErrorCategory, severity: ErrorSeverity, 
                 title: str, message: str, details: str = "",
                 suggestions: list = None, error_code: str = "",
                 exception: Exception = None, context: Dict[str, Any] = None):
        self.category = category
        self.severity = severity
        self.title = title
        self.message = message
        self.details = details
        self.suggestions = suggestions or []
        self.error_code = error_code
        self.exception = exception
        self.context = context or {}
        self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'category': self.category.value,
            'severity': self.severity.value,
            'title': self.title,
            'message': self.message,
            'details': self.details,
            'suggestions': self.suggestions,
            'error_code': self.error_code,
            'timestamp': self.timestamp.isoformat(),
            'context': self.context
        }


class ErrorManager(QObject):
    """
    统一错误管理器
    
    功能：
    1. 错误分类和标准化
    2. 用户友好的错误消息
    3. 错误日志记录
    4. 错误统计和分析
    5. 错误处理建议
    """
    
    # 信号定义
    error_occurred = Signal(object)  # ErrorInfo对象
    
    def __init__(self, parent=None, log_file: str = None):
        super().__init__(parent)
        self.parent_widget = parent
        self.error_history = []
        self.error_statistics = {}
        
        # 设置日志文件
        self.log_file = log_file or self._get_default_log_file()
        self._setup_logging()
        
        # 错误模板定义
        self._init_error_templates()
    
    def _get_default_log_file(self) -> str:
        """获取默认日志文件路径"""
        try:
            # 尝试在用户目录创建日志
            user_dir = os.path.expanduser("~")
            log_dir = os.path.join(user_dir, ".gudazip", "logs")
            os.makedirs(log_dir, exist_ok=True)
            return os.path.join(log_dir, "errors.log")
        except:
            # 如果失败，使用临时目录
            import tempfile
            return os.path.join(tempfile.gettempdir(), "gudazip_errors.log")
    
    def _setup_logging(self):
        """设置日志记录"""
        try:
            # 创建文件处理器
            file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
            file_handler.setLevel(logging.ERROR)
            
            # 创建格式化器
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(formatter)
            
            # 获取根日志器并添加处理器
            root_logger = logging.getLogger()
            if not any(isinstance(h, logging.FileHandler) for h in root_logger.handlers):
                root_logger.addHandler(file_handler)
                
        except Exception as e:
            print(f"Warning: Failed to setup error logging: {e}")
    
    def _init_error_templates(self):
        """初始化错误模板"""
        self.error_templates = {
            # 文件操作错误
            ErrorCategory.FILE_NOT_FOUND: {
                'title': '文件未找到',
                'message_template': '找不到文件：{path}',
                'suggestions': [
                    '检查文件路径是否正确',
                    '确认文件是否被移动或删除',
                    '检查文件名的大小写'
                ]
            },
            
            ErrorCategory.FILE_PERMISSION: {
                'title': '权限不足',
                'message_template': '没有权限访问：{path}',
                'suggestions': [
                    '以管理员身份运行程序',
                    '检查文件权限设置',
                    '确认文件没有被其他程序占用'
                ]
            },
            
            ErrorCategory.FILE_OPERATION: {
                'title': '文件操作失败',
                'message_template': '文件操作失败：{operation}',
                'suggestions': [
                    '检查磁盘空间是否充足',
                    '确认目标位置有写入权限',
                    '重试操作'
                ]
            },
            
            # 压缩包错误
            ErrorCategory.ARCHIVE_CORRUPTED: {
                'title': '压缩包损坏',
                'message_template': '压缩包文件已损坏：{path}',
                'suggestions': [
                    '重新下载压缩包',
                    '检查文件完整性',
                    '尝试使用其他压缩工具'
                ]
            },
            
            ErrorCategory.ARCHIVE_FORMAT: {
                'title': '不支持的格式',
                'message_template': '不支持的压缩包格式：{format}',
                'suggestions': [
                    '检查文件扩展名',
                    '安装额外的解压组件',
                    '转换为支持的格式'
                ]
            },
            
            ErrorCategory.ARCHIVE_PASSWORD: {
                'title': '密码错误',
                'message_template': '压缩包密码不正确',
                'suggestions': [
                    '检查密码是否正确',
                    '注意大小写和特殊字符',
                    '联系压缩包提供者'
                ]
            },
            
            # 系统错误
            ErrorCategory.SYSTEM_RESOURCE: {
                'title': '系统资源不足',
                'message_template': '系统资源不足：{resource}',
                'suggestions': [
                    '关闭其他应用程序',
                    '清理磁盘空间',
                    '增加虚拟内存'
                ]
            },
            
            ErrorCategory.SYSTEM_PERMISSION: {
                'title': '系统权限不足',
                'message_template': '需要系统管理员权限',
                'suggestions': [
                    '以管理员身份运行程序',
                    '修改用户账户控制设置',
                    '联系系统管理员'
                ]
            },
            
            # 用户操作错误
            ErrorCategory.USER_INPUT: {
                'title': '输入错误',
                'message_template': '输入信息有误：{field}',
                'suggestions': [
                    '检查输入格式',
                    '确认必填项已填写',
                    '参考输入示例'
                ]
            },
            
            # 默认模板
            ErrorCategory.UNKNOWN: {
                'title': '未知错误',
                'message_template': '发生未知错误：{error}',
                'suggestions': [
                    '重试操作',
                    '重启程序',
                    '联系技术支持'
                ]
            }
        }
    
    def handle_exception(self, exception: Exception, context: Dict[str, Any] = None,
                        show_dialog: bool = True, category: ErrorCategory = None) -> ErrorInfo:
        """
        处理异常
        
        Args:
            exception: 异常对象
            context: 上下文信息
            show_dialog: 是否显示错误对话框
            category: 错误分类（如果不指定则自动推断）
            
        Returns:
            ErrorInfo: 错误信息对象
        """
        # 自动推断错误分类
        if category is None:
            category = self._categorize_exception(exception)
        
        # 确定错误严重程度
        severity = self._determine_severity(exception, category)
        
        # 生成错误信息
        error_info = self._create_error_info(exception, category, severity, context)
        
        # 记录错误
        self._log_error(error_info)
        
        # 更新统计
        self._update_statistics(error_info)
        
        # 添加到历史记录
        self.error_history.append(error_info)
        
        # 发送信号
        self.error_occurred.emit(error_info)
        
        # 显示用户界面
        if show_dialog:
            self.show_error_dialog(error_info)
        
        return error_info
    
    def handle_error(self, category: ErrorCategory, severity: ErrorSeverity,
                    message: str, details: str = "", context: Dict[str, Any] = None,
                    show_dialog: bool = True, suggestions: list = None) -> ErrorInfo:
        """
        处理自定义错误
        
        Args:
            category: 错误分类
            severity: 错误严重程度
            message: 错误消息
            details: 详细信息
            context: 上下文信息
            show_dialog: 是否显示错误对话框
            suggestions: 解决建议
            
        Returns:
            ErrorInfo: 错误信息对象
        """
        # 获取错误模板
        template = self.error_templates.get(category, self.error_templates[ErrorCategory.UNKNOWN])
        
        # 创建错误信息
        error_info = ErrorInfo(
            category=category,
            severity=severity,
            title=template['title'],
            message=message,
            details=details,
            suggestions=suggestions or template['suggestions'],
            context=context or {}
        )
        
        # 记录错误
        self._log_error(error_info)
        
        # 更新统计
        self._update_statistics(error_info)
        
        # 添加到历史记录
        self.error_history.append(error_info)
        
        # 发送信号
        self.error_occurred.emit(error_info)
        
        # 显示用户界面
        if show_dialog:
            self.show_error_dialog(error_info)
        
        return error_info
    
    def _categorize_exception(self, exception: Exception) -> ErrorCategory:
        """自动推断异常分类"""
        exception_type = type(exception).__name__
        exception_str = str(exception).lower()
        
        # 文件相关错误
        if isinstance(exception, FileNotFoundError):
            return ErrorCategory.FILE_NOT_FOUND
        elif isinstance(exception, PermissionError):
            return ErrorCategory.FILE_PERMISSION
        elif isinstance(exception, OSError):
            if 'disk' in exception_str or 'space' in exception_str:
                return ErrorCategory.SYSTEM_RESOURCE
            else:
                return ErrorCategory.FILE_SYSTEM
        
        # 内存相关错误
        elif isinstance(exception, MemoryError):
            return ErrorCategory.SYSTEM_RESOURCE
        
        # 值错误（通常是用户输入）
        elif isinstance(exception, ValueError):
            return ErrorCategory.USER_INPUT
        
        # 其他常见错误
        elif isinstance(exception, ImportError):
            return ErrorCategory.APP_DEPENDENCY
        elif isinstance(exception, KeyboardInterrupt):
            return ErrorCategory.USER_CANCELLED
        
        # 根据错误消息推断
        elif any(keyword in exception_str for keyword in ['password', '密码']):
            return ErrorCategory.ARCHIVE_PASSWORD
        elif any(keyword in exception_str for keyword in ['corrupt', 'damaged', '损坏']):
            return ErrorCategory.ARCHIVE_CORRUPTED
        elif any(keyword in exception_str for keyword in ['format', '格式']):
            return ErrorCategory.ARCHIVE_FORMAT
        elif any(keyword in exception_str for keyword in ['network', 'connection', '网络']):
            return ErrorCategory.NETWORK_CONNECTION
        
        return ErrorCategory.UNKNOWN
    
    def _determine_severity(self, exception: Exception, category: ErrorCategory) -> ErrorSeverity:
        """确定错误严重程度"""
        # 系统级严重错误
        if isinstance(exception, (MemoryError, SystemError)):
            return ErrorSeverity.CRITICAL
        
        # 用户操作相关的一般为警告
        if category in [ErrorCategory.USER_INPUT, ErrorCategory.USER_CANCELLED]:
            return ErrorSeverity.WARNING
        
        # 权限和系统资源问题为错误
        if category in [ErrorCategory.FILE_PERMISSION, ErrorCategory.SYSTEM_PERMISSION, 
                       ErrorCategory.SYSTEM_RESOURCE]:
            return ErrorSeverity.ERROR
        
        # 文件操作问题为错误
        if category in [ErrorCategory.FILE_NOT_FOUND, ErrorCategory.FILE_OPERATION,
                       ErrorCategory.ARCHIVE_CORRUPTED]:
            return ErrorSeverity.ERROR
        
        # 格式和配置问题为警告
        if category in [ErrorCategory.ARCHIVE_FORMAT, ErrorCategory.APP_CONFIGURATION]:
            return ErrorSeverity.WARNING
        
        # 默认为错误
        return ErrorSeverity.ERROR
    
    def _create_error_info(self, exception: Exception, category: ErrorCategory, 
                          severity: ErrorSeverity, context: Dict[str, Any] = None) -> ErrorInfo:
        """创建错误信息对象"""
        template = self.error_templates.get(category, self.error_templates[ErrorCategory.UNKNOWN])
        
        # 格式化消息
        try:
            message = template['message_template'].format(**(context or {}))
        except (KeyError, ValueError):
            message = str(exception)
        
        # 生成详细信息
        details = f"异常类型: {type(exception).__name__}\n"
        details += f"异常消息: {str(exception)}\n"
        if context:
            details += f"上下文: {context}\n"
        
        # 生成错误代码
        error_code = f"{category.value.upper()}_{int(time.time() % 10000):04d}"
        
        return ErrorInfo(
            category=category,
            severity=severity,
            title=template['title'],
            message=message,
            details=details,
            suggestions=template['suggestions'],
            error_code=error_code,
            exception=exception,
            context=context or {}
        )
    
    def _log_error(self, error_info: ErrorInfo):
        """记录错误到日志"""
        try:
            log_message = f"[{error_info.error_code}] {error_info.title}: {error_info.message}"
            
            if error_info.severity == ErrorSeverity.CRITICAL:
                logger.critical(log_message)
            elif error_info.severity == ErrorSeverity.ERROR:
                logger.error(log_message)
            elif error_info.severity == ErrorSeverity.WARNING:
                logger.warning(log_message)
            else:
                logger.info(log_message)
            
            # 记录详细信息
            if error_info.details:
                logger.debug(f"详细信息: {error_info.details}")
            
            # 记录异常堆栈
            if error_info.exception:
                logger.debug(f"异常堆栈: {traceback.format_exception(type(error_info.exception), error_info.exception, error_info.exception.__traceback__)}")
                
        except Exception as e:
            print(f"Warning: Failed to log error: {e}")
    
    def _update_statistics(self, error_info: ErrorInfo):
        """更新错误统计"""
        category_key = error_info.category.value
        severity_key = error_info.severity.value
        
        if category_key not in self.error_statistics:
            self.error_statistics[category_key] = {}
        
        if severity_key not in self.error_statistics[category_key]:
            self.error_statistics[category_key][severity_key] = 0
        
        self.error_statistics[category_key][severity_key] += 1
    
    def show_error_dialog(self, error_info: ErrorInfo, parent: QWidget = None):
        """显示错误对话框"""
        try:
            parent_widget = parent or self.parent_widget or None
            
            # 选择消息框类型
            if error_info.severity == ErrorSeverity.CRITICAL:
                icon = QMessageBox.Critical
                title = "严重错误"
            elif error_info.severity == ErrorSeverity.ERROR:
                icon = QMessageBox.Critical
                title = "错误"
            elif error_info.severity == ErrorSeverity.WARNING:
                icon = QMessageBox.Warning
                title = "警告"
            else:
                icon = QMessageBox.Information
                title = "信息"
            
            # 创建消息框
            msg_box = QMessageBox(parent_widget)
            msg_box.setIcon(icon)
            msg_box.setWindowTitle(title)
            msg_box.setText(error_info.message)
            
            # 添加详细信息
            detailed_text = ""
            if error_info.suggestions:
                detailed_text += "建议解决方案：\n"
                for i, suggestion in enumerate(error_info.suggestions, 1):
                    detailed_text += f"{i}. {suggestion}\n"
                detailed_text += "\n"
            
            if error_info.details:
                detailed_text += f"详细信息：\n{error_info.details}\n"
            
            if error_info.error_code:
                detailed_text += f"错误代码：{error_info.error_code}"
            
            if detailed_text:
                msg_box.setDetailedText(detailed_text)
            
            # 设置按钮
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.setDefaultButton(QMessageBox.Ok)
            
            # 显示对话框
            msg_box.exec()
            
        except Exception as e:
            # 如果连错误对话框都无法显示，使用print
            print(f"Critical Error - Unable to show error dialog: {e}")
            print(f"Original Error: {error_info.message}")
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """获取错误统计信息"""
        return self.error_statistics.copy()
    
    def get_error_history(self, limit: int = 100) -> list:
        """获取错误历史记录"""
        return self.error_history[-limit:]
    
    def clear_error_history(self):
        """清空错误历史记录"""
        self.error_history.clear()
    
    def export_error_log(self, file_path: str) -> bool:
        """导出错误日志"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("GudaZip 错误日志\n")
                f.write("=" * 50 + "\n\n")
                
                for error_info in self.error_history:
                    f.write(f"时间: {error_info.timestamp}\n")
                    f.write(f"错误代码: {error_info.error_code}\n")
                    f.write(f"分类: {error_info.category.value}\n")
                    f.write(f"严重程度: {error_info.severity.value}\n")
                    f.write(f"标题: {error_info.title}\n")
                    f.write(f"消息: {error_info.message}\n")
                    if error_info.details:
                        f.write(f"详细信息: {error_info.details}\n")
                    if error_info.suggestions:
                        f.write("建议解决方案:\n")
                        for suggestion in error_info.suggestions:
                            f.write(f"  - {suggestion}\n")
                    f.write("-" * 50 + "\n\n")
                
                # 添加统计信息
                f.write("错误统计:\n")
                f.write("=" * 20 + "\n")
                for category, severities in self.error_statistics.items():
                    f.write(f"{category}:\n")
                    for severity, count in severities.items():
                        f.write(f"  {severity}: {count}\n")
                
            return True
        except Exception as e:
            logger.error(f"Failed to export error log: {e}")
            return False


# 全局错误管理器实例
_global_error_manager = None


def get_error_manager(parent=None, log_file: str = None) -> ErrorManager:
    """获取全局错误管理器实例"""
    global _global_error_manager
    if _global_error_manager is None:
        _global_error_manager = ErrorManager(parent, log_file)
    return _global_error_manager


def handle_exception(exception: Exception, context: Dict[str, Any] = None,
                    show_dialog: bool = True, category: ErrorCategory = None) -> ErrorInfo:
    """便捷的异常处理函数"""
    error_manager = get_error_manager()
    return error_manager.handle_exception(exception, context, show_dialog, category)


def handle_error(category: ErrorCategory, severity: ErrorSeverity,
                message: str, details: str = "", context: Dict[str, Any] = None,
                show_dialog: bool = True, suggestions: list = None) -> ErrorInfo:
    """便捷的错误处理函数"""
    error_manager = get_error_manager()
    return error_manager.handle_error(category, severity, message, details, context, show_dialog, suggestions) 