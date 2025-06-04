# -*- coding: utf-8 -*-
"""
GudaZip核心模块

包含所有核心功能类：
- 信号管理器：用于Qt信号的统一管理
- 文件操作管理器：处理文件系统操作
- 压缩包操作管理器：处理压缩包相关操作
- 错误管理器：统一的错误处理系统
- 状态管理器：程序状态的集中管理和持久化
"""

from .signal_manager import get_signal_manager
from .file_operation_manager import FileOperationManager  
from .archive_operation_manager import ArchiveOperationManager
from .error_manager import ErrorManager, ErrorCategory, ErrorSeverity, get_error_manager
from .state_manager import StateManager, StateScope, StatePersistenceType, get_state_manager, set_global_state, get_global_state, save_global_states

__all__ = [
    'get_signal_manager',
    'FileOperationManager',
    'ArchiveOperationManager', 
    'ErrorManager',
    'ErrorCategory',
    'ErrorSeverity',
    'get_error_manager',
    'StateManager',
    'StateScope',
    'StatePersistenceType',
    'get_state_manager',
    'set_global_state',
    'get_global_state',
    'save_global_states'
]

from .archive_manager import ArchiveManager
from .zip_handler import ZipHandler
from .rar_handler import RarHandler 