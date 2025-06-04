#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
状态管理系统
负责程序状态的集中管理、持久化存储和恢复
提供状态一致性和程序恢复能力
"""

import os
import json
import pickle
import logging
from typing import Dict, Any, Optional, Callable, List
from pathlib import Path
from datetime import datetime
from enum import Enum
from PySide6.QtCore import QObject, Signal, QSettings, QStandardPaths
from PySide6.QtWidgets import QWidget

from .error_manager import ErrorManager, ErrorCategory, ErrorSeverity, get_error_manager

logger = logging.getLogger(__name__)


class StateScope(Enum):
    """状态作用域枚举"""
    GLOBAL = "global"           # 全局状态（应用程序级别）
    SESSION = "session"         # 会话状态（一次运行期间）
    WINDOW = "window"          # 窗口状态（单个窗口）
    COMPONENT = "component"    # 组件状态（特定组件）
    USER = "user"             # 用户状态（用户级别设置）
    TEMP = "temp"             # 临时状态（不持久化）


class StatePersistenceType(Enum):
    """状态持久化类型"""
    NONE = "none"              # 不持久化
    JSON = "json"              # JSON格式持久化
    PICKLE = "pickle"          # Python Pickle格式
    QSETTINGS = "qsettings"    # Qt设置系统
    MEMORY = "memory"          # 仅内存存储


class StateItem:
    """状态项封装"""
    
    def __init__(self, key: str, value: Any, scope: StateScope = StateScope.GLOBAL,
                 persistence_type: StatePersistenceType = StatePersistenceType.JSON,
                 description: str = "", validator: Optional[Callable] = None):
        self.key = key
        self.value = value
        self.scope = scope
        self.persistence_type = persistence_type
        self.description = description
        self.validator = validator
        self.created_time = datetime.now()
        self.modified_time = datetime.now()
        self.access_count = 0
    
    def validate(self, value: Any) -> bool:
        """验证状态值"""
        if self.validator:
            try:
                return self.validator(value)
            except Exception:
                return False
        return True
    
    def update_value(self, value: Any) -> bool:
        """更新状态值"""
        if self.validate(value):
            self.value = value
            self.modified_time = datetime.now()
            return True
        return False
    
    def access(self) -> Any:
        """访问状态值（统计访问次数）"""
        self.access_count += 1
        return self.value
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'key': self.key,
            'value': self.value,
            'scope': self.scope.value,
            'persistence_type': self.persistence_type.value,
            'description': self.description,
            'created_time': self.created_time.isoformat(),
            'modified_time': self.modified_time.isoformat(),
            'access_count': self.access_count
        }


class StateManager(QObject):
    """
    状态管理器
    
    功能：
    1. 程序状态的集中管理
    2. 状态持久化存储和恢复
    3. 状态变更通知机制
    4. 状态一致性保证
    5. 状态历史和回滚
    6. 状态导入导出
    """
    
    # 信号定义
    state_changed = Signal(str, object, object)  # key, old_value, new_value
    state_added = Signal(str, object)            # key, value
    state_removed = Signal(str)                  # key
    state_saved = Signal(str)                    # persistence_path
    state_loaded = Signal(str)                   # persistence_path
    
    def __init__(self, parent: Optional[QWidget] = None, app_name: str = "GudaZip"):
        super().__init__(parent)
        self.parent_widget = parent
        self.app_name = app_name
        
        # 初始化错误管理器
        self.error_manager = get_error_manager(parent)
        
        # 状态存储
        self._states: Dict[str, StateItem] = {}
        self._state_history: Dict[str, List[StateItem]] = {}
        
        # 持久化设置
        self.persistence_enabled = True
        self.auto_save_enabled = True
        self.auto_save_interval = 30  # 秒
        
        # 存储路径
        self._init_storage_paths()
        
        # Qt设置对象
        self.qsettings = QSettings(self.app_name, self.app_name)
        
        # 初始化默认状态
        self._init_default_states()
        
        # 加载已保存的状态
        self.load_all_states()
        
        logger.info(f"StateManager initialized for {app_name}")
    
    def _init_storage_paths(self):
        """初始化存储路径"""
        try:
            # 获取应用数据目录
            app_data_dir = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
            if not app_data_dir:
                app_data_dir = os.path.join(os.path.expanduser("~"), f".{self.app_name.lower()}")
            
            self.app_data_dir = Path(app_data_dir)
            self.states_dir = self.app_data_dir / "states"
            self.backups_dir = self.app_data_dir / "backups"
            
            # 创建目录
            self.states_dir.mkdir(parents=True, exist_ok=True)
            self.backups_dir.mkdir(parents=True, exist_ok=True)
            
            # 定义各种状态文件路径
            self.global_state_file = self.states_dir / "global_state.json"
            self.session_state_file = self.states_dir / "session_state.json"
            self.window_state_file = self.states_dir / "window_state.json"
            self.user_state_file = self.states_dir / "user_state.json"
            
            logger.info(f"State storage initialized at: {self.states_dir}")
            
        except Exception as e:
            self.error_manager.handle_exception(
                e,
                context={"operation": "init_storage_paths", "app_name": self.app_name},
                category=ErrorCategory.APP_CONFIGURATION,
                show_dialog=False
            )
            # 使用临时目录作为备选
            import tempfile
            self.app_data_dir = Path(tempfile.gettempdir()) / f"{self.app_name.lower()}_states"
            self.states_dir = self.app_data_dir
            self.backups_dir = self.app_data_dir / "backups"
            self.states_dir.mkdir(parents=True, exist_ok=True)
    
    def _init_default_states(self):
        """初始化默认状态"""
        default_states = [
            # 应用程序状态
            StateItem("app.version", "1.0.0", StateScope.GLOBAL, StatePersistenceType.JSON, "应用程序版本"),
            StateItem("app.first_run", True, StateScope.GLOBAL, StatePersistenceType.JSON, "是否首次运行"),
            StateItem("app.last_run_time", None, StateScope.SESSION, StatePersistenceType.JSON, "上次运行时间"),
            
            # 窗口状态
            StateItem("window.geometry", None, StateScope.WINDOW, StatePersistenceType.QSETTINGS, "窗口几何信息"),
            StateItem("window.maximized", False, StateScope.WINDOW, StatePersistenceType.QSETTINGS, "窗口是否最大化"),
            StateItem("window.splitter_state", None, StateScope.WINDOW, StatePersistenceType.QSETTINGS, "分割器状态"),
            
            # 文件浏览器状态
            StateItem("browser.current_path", "", StateScope.SESSION, StatePersistenceType.JSON, "当前浏览路径"),
            StateItem("browser.view_mode", "详细信息", StateScope.USER, StatePersistenceType.JSON, "文件视图模式"),
            StateItem("browser.show_hidden_files", False, StateScope.USER, StatePersistenceType.JSON, "显示隐藏文件"),
            StateItem("browser.sort_column", 0, StateScope.USER, StatePersistenceType.JSON, "排序列"),
            StateItem("browser.sort_order", 0, StateScope.USER, StatePersistenceType.JSON, "排序顺序"),
            
            # 压缩包状态
            StateItem("archive.viewing_mode", False, StateScope.SESSION, StatePersistenceType.MEMORY, "压缩包查看模式"),
            StateItem("archive.current_path", "", StateScope.SESSION, StatePersistenceType.MEMORY, "当前压缩包路径"),
            StateItem("archive.current_dir", "", StateScope.SESSION, StatePersistenceType.MEMORY, "压缩包内当前目录"),
            
            # 最近使用
            StateItem("recent.files", [], StateScope.USER, StatePersistenceType.JSON, "最近打开的文件"),
            StateItem("recent.folders", [], StateScope.USER, StatePersistenceType.JSON, "最近访问的文件夹"),
            StateItem("recent.archives", [], StateScope.USER, StatePersistenceType.JSON, "最近打开的压缩包"),
            
            # 剪贴板状态
            StateItem("clipboard.operation", "", StateScope.SESSION, StatePersistenceType.MEMORY, "剪贴板操作类型"),
            StateItem("clipboard.items", [], StateScope.SESSION, StatePersistenceType.MEMORY, "剪贴板项目"),
            
            # 操作历史
            StateItem("history.navigation", [], StateScope.SESSION, StatePersistenceType.MEMORY, "导航历史"),
            StateItem("history.operations", [], StateScope.SESSION, StatePersistenceType.MEMORY, "操作历史"),
        ]
        
        for state_item in default_states:
            if state_item.key not in self._states:
                self._states[state_item.key] = state_item
                self._state_history[state_item.key] = [state_item]
    
    # ========== 状态操作方法 ==========
    
    def set_state(self, key: str, value: Any, scope: StateScope = StateScope.GLOBAL,
                  persistence_type: StatePersistenceType = StatePersistenceType.JSON,
                  description: str = "", validator: Optional[Callable] = None,
                  notify: bool = True) -> bool:
        """
        设置状态值
        
        Args:
            key: 状态键
            value: 状态值
            scope: 状态作用域
            persistence_type: 持久化类型
            description: 状态描述
            validator: 值验证器
            notify: 是否发送通知信号
            
        Returns:
            bool: 是否设置成功
        """
        try:
            old_value = None
            if key in self._states:
                old_value = self._states[key].value
                # 更新现有状态
                if not self._states[key].update_value(value):
                    self.error_manager.handle_error(
                        ErrorCategory.USER_INPUT,
                        ErrorSeverity.WARNING,
                        f"状态值验证失败: {key}",
                        details=f"提供的值 {value} 未通过验证",
                        show_dialog=False
                    )
                    return False
            else:
                # 创建新状态
                state_item = StateItem(key, value, scope, persistence_type, description, validator)
                if not state_item.validate(value):
                    self.error_manager.handle_error(
                        ErrorCategory.USER_INPUT,
                        ErrorSeverity.WARNING,
                        f"状态值验证失败: {key}",
                        details=f"提供的值 {value} 未通过验证",
                        show_dialog=False
                    )
                    return False
                
                self._states[key] = state_item
                self._state_history[key] = [state_item]
                
                if notify:
                    self.state_added.emit(key, value)
            
            # 保存状态历史
            if key in self._state_history:
                self._state_history[key].append(self._states[key])
                # 限制历史记录数量
                if len(self._state_history[key]) > 10:
                    self._state_history[key] = self._state_history[key][-10:]
            
            # 发送状态变更信号
            if notify and old_value is not None:
                self.state_changed.emit(key, old_value, value)
            
            # 自动保存
            if self.auto_save_enabled and persistence_type != StatePersistenceType.MEMORY:
                self._auto_save_state(key)
            
            return True
            
        except Exception as e:
            self.error_manager.handle_exception(
                e,
                context={"operation": "set_state", "key": key, "value": str(value)},
                category=ErrorCategory.APP_INTERNAL,
                show_dialog=False
            )
            return False
    
    def get_state(self, key: str, default: Any = None) -> Any:
        """
        获取状态值
        
        Args:
            key: 状态键
            default: 默认值
            
        Returns:
            Any: 状态值
        """
        try:
            if key in self._states:
                return self._states[key].access()
            return default
        except Exception as e:
            self.error_manager.handle_exception(
                e,
                context={"operation": "get_state", "key": key},
                category=ErrorCategory.APP_INTERNAL,
                show_dialog=False
            )
            return default
    
    def has_state(self, key: str) -> bool:
        """检查是否存在指定状态"""
        return key in self._states
    
    def remove_state(self, key: str, notify: bool = True) -> bool:
        """
        移除状态
        
        Args:
            key: 状态键
            notify: 是否发送通知信号
            
        Returns:
            bool: 是否移除成功
        """
        try:
            if key in self._states:
                del self._states[key]
                if key in self._state_history:
                    del self._state_history[key]
                
                if notify:
                    self.state_removed.emit(key)
                
                return True
            return False
        except Exception as e:
            self.error_manager.handle_exception(
                e,
                context={"operation": "remove_state", "key": key},
                category=ErrorCategory.APP_INTERNAL,
                show_dialog=False
            )
            return False
    
    def get_states_by_scope(self, scope: StateScope) -> Dict[str, Any]:
        """获取指定作用域的所有状态"""
        result = {}
        for key, state_item in self._states.items():
            if state_item.scope == scope:
                result[key] = state_item.value
        return result
    
    def clear_scope(self, scope: StateScope) -> int:
        """清除指定作用域的所有状态"""
        removed_count = 0
        keys_to_remove = []
        
        for key, state_item in self._states.items():
            if state_item.scope == scope:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            if self.remove_state(key, notify=False):
                removed_count += 1
        
        return removed_count
    
    # ========== 持久化方法 ==========
    
    def _auto_save_state(self, key: str):
        """自动保存单个状态"""
        if not self.persistence_enabled or key not in self._states:
            return
        
        state_item = self._states[key]
        if state_item.persistence_type == StatePersistenceType.MEMORY:
            return
        
        try:
            if state_item.persistence_type == StatePersistenceType.QSETTINGS:
                self.qsettings.setValue(key, state_item.value)
                self.qsettings.sync()
            else:
                # 其他类型的持久化将在save_all_states中处理
                pass
        except Exception as e:
            self.error_manager.handle_exception(
                e,
                context={"operation": "auto_save_state", "key": key},
                category=ErrorCategory.APP_CONFIGURATION,
                show_dialog=False
            )
    
    def save_all_states(self) -> bool:
        """保存所有状态到文件"""
        if not self.persistence_enabled:
            return True
        
        try:
            # 按作用域和持久化类型分类状态
            states_by_file = {
                self.global_state_file: {},
                self.session_state_file: {},
                self.window_state_file: {},
                self.user_state_file: {}
            }
            
            for key, state_item in self._states.items():
                if state_item.persistence_type == StatePersistenceType.MEMORY:
                    continue
                elif state_item.persistence_type == StatePersistenceType.QSETTINGS:
                    self.qsettings.setValue(key, state_item.value)
                    continue
                
                # 确定保存文件
                target_file = None
                if state_item.scope == StateScope.GLOBAL:
                    target_file = self.global_state_file
                elif state_item.scope == StateScope.SESSION:
                    target_file = self.session_state_file
                elif state_item.scope == StateScope.WINDOW:
                    target_file = self.window_state_file
                elif state_item.scope == StateScope.USER:
                    target_file = self.user_state_file
                
                if target_file:
                    states_by_file[target_file][key] = state_item.to_dict()
            
            # 保存到文件
            for file_path, states_data in states_by_file.items():
                if states_data:  # 只保存非空的状态文件
                    self._save_states_to_file(file_path, states_data)
            
            # 同步Qt设置
            self.qsettings.sync()
            
            self.state_saved.emit(str(self.states_dir))
            logger.info(f"All states saved successfully to {self.states_dir}")
            return True
            
        except Exception as e:
            self.error_manager.handle_exception(
                e,
                context={"operation": "save_all_states"},
                category=ErrorCategory.APP_CONFIGURATION
            )
            return False
    
    def _save_states_to_file(self, file_path: Path, states_data: Dict[str, Any]):
        """保存状态数据到文件"""
        try:
            # 创建备份
            if file_path.exists():
                backup_path = self.backups_dir / f"{file_path.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                import shutil
                shutil.copy2(file_path, backup_path)
            
            # 保存新数据
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(states_data, f, indent=2, ensure_ascii=False, default=str)
            
        except Exception as e:
            raise Exception(f"Failed to save states to {file_path}: {e}")
    
    def load_all_states(self) -> bool:
        """加载所有保存的状态"""
        try:
            # 加载各个状态文件
            state_files = [
                self.global_state_file,
                self.session_state_file,
                self.window_state_file,
                self.user_state_file
            ]
            
            loaded_count = 0
            for file_path in state_files:
                if file_path.exists():
                    count = self._load_states_from_file(file_path)
                    loaded_count += count
            
            # 加载Qt设置
            qt_count = self._load_qsettings_states()
            loaded_count += qt_count
            
            if loaded_count > 0:
                self.state_loaded.emit(str(self.states_dir))
                logger.info(f"Loaded {loaded_count} states from storage")
            
            return True
            
        except Exception as e:
            self.error_manager.handle_exception(
                e,
                context={"operation": "load_all_states"},
                category=ErrorCategory.APP_CONFIGURATION,
                show_dialog=False
            )
            return False
    
    def _load_states_from_file(self, file_path: Path) -> int:
        """从文件加载状态数据"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                states_data = json.load(f)
            
            loaded_count = 0
            for key, state_dict in states_data.items():
                try:
                    # 重建StateItem对象
                    scope = StateScope(state_dict.get('scope', StateScope.GLOBAL.value))
                    persistence_type = StatePersistenceType(state_dict.get('persistence_type', StatePersistenceType.JSON.value))
                    
                    state_item = StateItem(
                        key=key,
                        value=state_dict['value'],
                        scope=scope,
                        persistence_type=persistence_type,
                        description=state_dict.get('description', '')
                    )
                    
                    # 恢复时间信息
                    if 'created_time' in state_dict:
                        state_item.created_time = datetime.fromisoformat(state_dict['created_time'])
                    if 'modified_time' in state_dict:
                        state_item.modified_time = datetime.fromisoformat(state_dict['modified_time'])
                    if 'access_count' in state_dict:
                        state_item.access_count = state_dict['access_count']
                    
                    self._states[key] = state_item
                    self._state_history[key] = [state_item]
                    loaded_count += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to load state {key}: {e}")
                    continue
            
            return loaded_count
            
        except Exception as e:
            logger.warning(f"Failed to load states from {file_path}: {e}")
            return 0
    
    def _load_qsettings_states(self) -> int:
        """加载Qt设置中的状态"""
        try:
            loaded_count = 0
            
            # 遍历Qt设置中的所有键
            for key in self.qsettings.allKeys():
                if key not in self._states:
                    # 对于Qt设置，我们创建一个默认的StateItem
                    value = self.qsettings.value(key)
                    state_item = StateItem(
                        key=key,
                        value=value,
                        scope=StateScope.WINDOW,
                        persistence_type=StatePersistenceType.QSETTINGS,
                        description=f"Qt设置: {key}"
                    )
                    self._states[key] = state_item
                    self._state_history[key] = [state_item]
                    loaded_count += 1
            
            return loaded_count
            
        except Exception as e:
            logger.warning(f"Failed to load Qt settings: {e}")
            return 0
    
    # ========== 状态历史和回滚 ==========
    
    def get_state_history(self, key: str) -> List[StateItem]:
        """获取状态历史"""
        return self._state_history.get(key, [])
    
    def rollback_state(self, key: str, steps: int = 1) -> bool:
        """回滚状态到之前的值"""
        try:
            if key not in self._state_history or len(self._state_history[key]) <= steps:
                return False
            
            # 获取回滚目标
            target_state = self._state_history[key][-(steps + 1)]
            
            # 更新当前状态
            old_value = self._states[key].value
            self._states[key] = target_state
            
            # 发送变更信号
            self.state_changed.emit(key, old_value, target_state.value)
            
            return True
            
        except Exception as e:
            self.error_manager.handle_exception(
                e,
                context={"operation": "rollback_state", "key": key, "steps": steps},
                category=ErrorCategory.APP_INTERNAL,
                show_dialog=False
            )
            return False
    
    # ========== 工具方法 ==========
    
    def get_state_info(self, key: str) -> Optional[Dict[str, Any]]:
        """获取状态的详细信息"""
        if key in self._states:
            return self._states[key].to_dict()
        return None
    
    def get_all_states_info(self) -> Dict[str, Dict[str, Any]]:
        """获取所有状态的详细信息"""
        result = {}
        for key, state_item in self._states.items():
            result[key] = state_item.to_dict()
        return result
    
    def export_states(self, file_path: str, scope: Optional[StateScope] = None) -> bool:
        """导出状态到文件"""
        try:
            states_to_export = {}
            
            for key, state_item in self._states.items():
                if scope is None or state_item.scope == scope:
                    states_to_export[key] = state_item.to_dict()
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(states_to_export, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"Exported {len(states_to_export)} states to {file_path}")
            return True
            
        except Exception as e:
            self.error_manager.handle_exception(
                e,
                context={"operation": "export_states", "file_path": file_path},
                category=ErrorCategory.FILE_OPERATION
            )
            return False
    
    def import_states(self, file_path: str, merge: bool = True) -> bool:
        """从文件导入状态"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                imported_data = json.load(f)
            
            if not merge:
                self._states.clear()
                self._state_history.clear()
            
            imported_count = 0
            for key, state_dict in imported_data.items():
                try:
                    scope = StateScope(state_dict.get('scope', StateScope.GLOBAL.value))
                    persistence_type = StatePersistenceType(state_dict.get('persistence_type', StatePersistenceType.JSON.value))
                    
                    state_item = StateItem(
                        key=key,
                        value=state_dict['value'],
                        scope=scope,
                        persistence_type=persistence_type,
                        description=state_dict.get('description', '')
                    )
                    
                    self._states[key] = state_item
                    self._state_history[key] = [state_item]
                    imported_count += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to import state {key}: {e}")
                    continue
            
            logger.info(f"Imported {imported_count} states from {file_path}")
            return True
            
        except Exception as e:
            self.error_manager.handle_exception(
                e,
                context={"operation": "import_states", "file_path": file_path},
                category=ErrorCategory.FILE_OPERATION
            )
            return False
    
    def cleanup_old_backups(self, keep_days: int = 7):
        """清理旧的备份文件"""
        try:
            cutoff_time = datetime.now().timestamp() - (keep_days * 24 * 60 * 60)
            
            removed_count = 0
            for backup_file in self.backups_dir.glob("*.json"):
                if backup_file.stat().st_mtime < cutoff_time:
                    backup_file.unlink()
                    removed_count += 1
            
            if removed_count > 0:
                logger.info(f"Cleaned up {removed_count} old backup files")
            
        except Exception as e:
            self.error_manager.handle_exception(
                e,
                context={"operation": "cleanup_old_backups", "keep_days": keep_days},
                category=ErrorCategory.FILE_OPERATION,
                show_dialog=False
            )
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取状态管理器统计信息"""
        stats = {
            'total_states': len(self._states),
            'states_by_scope': {},
            'states_by_persistence': {},
            'most_accessed_states': [],
            'storage_paths': {
                'app_data_dir': str(self.app_data_dir),
                'states_dir': str(self.states_dir),
                'backups_dir': str(self.backups_dir)
            }
        }
        
        # 按作用域统计
        for scope in StateScope:
            count = sum(1 for state in self._states.values() if state.scope == scope)
            stats['states_by_scope'][scope.value] = count
        
        # 按持久化类型统计
        for persistence_type in StatePersistenceType:
            count = sum(1 for state in self._states.values() if state.persistence_type == persistence_type)
            stats['states_by_persistence'][persistence_type.value] = count
        
        # 最常访问的状态
        sorted_states = sorted(self._states.items(), key=lambda x: x[1].access_count, reverse=True)
        stats['most_accessed_states'] = [
            {'key': key, 'access_count': state.access_count}
            for key, state in sorted_states[:10]
        ]
        
        return stats


# ========== 全局状态管理器实例 ==========

_global_state_manager: Optional[StateManager] = None


def get_state_manager(parent: Optional[QWidget] = None, app_name: str = "GudaZip") -> StateManager:
    """获取全局状态管理器实例"""
    global _global_state_manager
    
    if _global_state_manager is None:
        _global_state_manager = StateManager(parent, app_name)
    
    return _global_state_manager


def set_global_state(key: str, value: Any, **kwargs) -> bool:
    """设置全局状态的便捷函数"""
    state_manager = get_state_manager()
    return state_manager.set_state(key, value, **kwargs)


def get_global_state(key: str, default: Any = None) -> Any:
    """获取全局状态的便捷函数"""
    state_manager = get_state_manager()
    return state_manager.get_state(key, default)


def save_global_states() -> bool:
    """保存全局状态的便捷函数"""
    state_manager = get_state_manager()
    return state_manager.save_all_states() 