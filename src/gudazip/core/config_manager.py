#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理系统
负责用户设置、主题、快捷键等配置的管理
与状态管理系统协同工作，提供完整的应用程序配置解决方案
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List, Callable, Union
from pathlib import Path
from enum import Enum
from datetime import datetime
from PySide6.QtCore import QObject, Signal, QStandardPaths, QSize, QPoint
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QWidget

from .state_manager import StateManager, StateScope, StatePersistenceType, get_state_manager
from .error_manager import ErrorManager, ErrorCategory, ErrorSeverity, get_error_manager

logger = logging.getLogger(__name__)


class ConfigCategory(Enum):
    """配置类别枚举"""
    GENERAL = "general"         # 常规设置
    APPEARANCE = "appearance"   # 外观设置
    BEHAVIOR = "behavior"       # 行为设置
    SHORTCUTS = "shortcuts"     # 快捷键设置
    ADVANCED = "advanced"       # 高级设置
    PLUGINS = "plugins"         # 插件设置


class ThemeType(Enum):
    """主题类型枚举"""
    LIGHT = "light"             # 浅色主题
    DARK = "dark"               # 深色主题
    AUTO = "auto"               # 跟随系统
    CUSTOM = "custom"           # 自定义主题


class ConfigItem:
    """配置项封装"""
    
    def __init__(self, key: str, value: Any, category: ConfigCategory = ConfigCategory.GENERAL,
                 description: str = "", validator: Optional[Callable] = None,
                 options: Optional[List[Any]] = None, requires_restart: bool = False):
        self.key = key
        self.value = value
        self.category = category
        self.description = description
        self.validator = validator
        self.options = options or []  # 可选值列表
        self.requires_restart = requires_restart
        self.default_value = value
    
    def validate(self, value: Any) -> bool:
        """验证配置值"""
        if self.validator:
            try:
                return self.validator(value)
            except Exception:
                return False
        
        # 如果有选项列表，检查值是否在列表中
        if self.options and value not in self.options:
            return False
        
        return True
    
    def reset_to_default(self):
        """重置为默认值"""
        self.value = self.default_value
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'key': self.key,
            'value': self.value,
            'category': self.category.value,
            'description': self.description,
            'options': self.options,
            'requires_restart': self.requires_restart,
            'default_value': self.default_value
        }


class ConfigManager(QObject):
    """
    配置管理器
    
    功能：
    1. 用户配置的集中管理
    2. 主题和外观设置
    3. 快捷键管理
    4. 配置验证和默认值
    5. 配置导入导出
    6. 配置变更通知
    """
    
    # 信号定义
    config_changed = Signal(str, object, object)    # key, old_value, new_value
    theme_changed = Signal(str)                     # theme_name
    config_reset = Signal()                         # 配置重置
    config_loaded = Signal()                        # 配置加载完成
    config_saved = Signal()                         # 配置保存完成
    
    def __init__(self, parent: Optional[QWidget] = None, app_name: str = "GudaZip"):
        super().__init__(parent)
        self.parent_widget = parent
        self.app_name = app_name
        
        # 获取管理器
        self.state_manager = get_state_manager(parent, app_name)
        self.error_manager = get_error_manager(parent)
        
        # 配置存储
        self._configs: Dict[str, ConfigItem] = {}
        
        # 配置文件路径
        self._init_config_paths()
        
        # 初始化默认配置
        self._init_default_configs()
        
        # 加载配置
        self.load_configs()
        
        logger.info(f"ConfigManager initialized for {app_name}")
    
    def _init_config_paths(self):
        """初始化配置文件路径"""
        try:
            # 在Windows上明确使用AppData\Roaming路径
            if os.name == 'nt':  # Windows
                config_dir = os.path.join(os.environ.get('APPDATA', ''), self.app_name, 'config')
            else:
                # 其他系统使用标准路径
                config_dir = QStandardPaths.writableLocation(QStandardPaths.AppConfigLocation)
                if not config_dir:
                    config_dir = os.path.join(os.path.expanduser("~"), f".{self.app_name.lower()}", "config")
            
            self.config_dir = Path(config_dir)
            self.config_dir.mkdir(parents=True, exist_ok=True)
            
            # 配置文件路径
            self.config_file = self.config_dir / "config.json"
            self.themes_dir = self.config_dir / "themes"
            self.shortcuts_file = self.config_dir / "shortcuts.json"
            
            # 创建主题目录
            self.themes_dir.mkdir(exist_ok=True)
            
            logger.info(f"Config paths initialized at: {self.config_dir}")
            
        except Exception as e:
            self.error_manager.handle_exception(
                e,
                context={"operation": "init_config_paths", "app_name": self.app_name},
                category=ErrorCategory.APP_CONFIGURATION,
                show_dialog=False
            )
    
    def _init_default_configs(self):
        """初始化默认配置"""
        # 常规设置
        self._add_config("general.language", "zh_CN", ConfigCategory.GENERAL, 
                        "界面语言", options=["zh_CN", "en_US"], requires_restart=True)
        self._add_config("general.startup_path", "desktop", ConfigCategory.GENERAL,
                        "启动时的默认路径", options=["desktop", "last_location", "home", "documents"])
        self._add_config("general.check_updates", True, ConfigCategory.GENERAL,
                        "自动检查更新")
        self._add_config("general.confirm_delete", True, ConfigCategory.GENERAL,
                        "删除文件时确认")
        self._add_config("general.auto_backup", True, ConfigCategory.GENERAL,
                        "自动备份重要文件")
        
        # 外观设置
        self._add_config("appearance.theme", ThemeType.LIGHT.value, ConfigCategory.APPEARANCE,
                        "界面主题", options=[t.value for t in ThemeType])
        self._add_config("appearance.font_family", "微软雅黑", ConfigCategory.APPEARANCE,
                        "界面字体")
        self._add_config("appearance.font_size", 9, ConfigCategory.APPEARANCE,
                        "字体大小", validator=lambda x: isinstance(x, int) and 8 <= x <= 20)
        self._add_config("appearance.window_opacity", 1.0, ConfigCategory.APPEARANCE,
                        "窗口透明度", validator=lambda x: isinstance(x, (int, float)) and 0.3 <= x <= 1.0)
        self._add_config("appearance.show_toolbar", True, ConfigCategory.APPEARANCE,
                        "显示工具栏")
        self._add_config("appearance.show_statusbar", True, ConfigCategory.APPEARANCE,
                        "显示状态栏")
        self._add_config("appearance.icon_size", 16, ConfigCategory.APPEARANCE,
                        "图标大小", options=[16, 24, 32], validator=lambda x: x in [16, 24, 32])
        
        # 行为设置
        self._add_config("behavior.double_click_action", "open", ConfigCategory.BEHAVIOR,
                        "双击操作", options=["open", "select", "preview"])
        self._add_config("behavior.show_hidden_files", False, ConfigCategory.BEHAVIOR,
                        "显示隐藏文件")
        self._add_config("behavior.file_view_mode", "list", ConfigCategory.BEHAVIOR,
                        "文件视图模式", options=["list", "icon", "detail"])
        self._add_config("behavior.auto_refresh", True, ConfigCategory.BEHAVIOR,
                        "自动刷新文件列表")
        self._add_config("behavior.navigation_history_size", 20, ConfigCategory.BEHAVIOR,
                        "导航历史记录数量", validator=lambda x: isinstance(x, int) and 1 <= x <= 100)
        
        # 压缩设置
        self._add_config("compression.default_mode", "fast", ConfigCategory.BEHAVIOR,
                        "默认压缩模式", options=["fast", "small", "custom"])
        self._add_config("compression.custom_level", 5, ConfigCategory.BEHAVIOR,
                        "自定义压缩级别", validator=lambda x: isinstance(x, int) and 0 <= x <= 9)
        self._add_config("compression.default_format", "zip", ConfigCategory.BEHAVIOR,
                        "默认压缩格式", options=["zip"])
        
        # 窗口设置
        self._add_config("window.remember_size", True, ConfigCategory.GENERAL,
                        "记住窗口大小")
        self._add_config("window.remember_position", True, ConfigCategory.GENERAL,
                        "记住窗口位置")
        self._add_config("window.center_on_startup", True, ConfigCategory.GENERAL,
                        "启动时窗口居中")
        self._add_config("window.default_width", 1200, ConfigCategory.GENERAL,
                        "默认窗口宽度", validator=lambda x: isinstance(x, int) and 800 <= x <= 2000)
        self._add_config("window.default_height", 800, ConfigCategory.GENERAL,
                        "默认窗口高度", validator=lambda x: isinstance(x, int) and 600 <= x <= 1500)
        
        # 高级设置
        self._add_config("advanced.thread_pool_size", 4, ConfigCategory.ADVANCED,
                        "线程池大小", validator=lambda x: isinstance(x, int) and 1 <= x <= 16)
        self._add_config("advanced.cache_size", 100, ConfigCategory.ADVANCED,
                        "缓存大小(MB)", validator=lambda x: isinstance(x, int) and 50 <= x <= 1000)
        self._add_config("advanced.debug_mode", False, ConfigCategory.ADVANCED,
                        "调试模式", requires_restart=True)
        
        # 快捷键设置
        self._init_default_shortcuts()
    
    def _init_default_shortcuts(self):
        """初始化默认快捷键"""
        default_shortcuts = {
            "file.new_folder": "Ctrl+Shift+N",
            "file.new_file": "Ctrl+N",
            "file.open": "Ctrl+O",
            "file.refresh": "F5",
            "file.rename": "F2",
            "file.delete": "Delete",
            "file.copy": "Ctrl+C",
            "file.cut": "Ctrl+X",
            "file.paste": "Ctrl+V",
            "view.toggle_mode": "Ctrl+1",
            "view.show_hidden": "Ctrl+H",
            "view.go_up": "Alt+Up",
            "window.close": "Ctrl+W",
            "app.exit": "Ctrl+Q",
            "help.about": "F1"
        }
        
        for action, shortcut in default_shortcuts.items():
            self._add_config(f"shortcuts.{action}", shortcut, ConfigCategory.SHORTCUTS,
                           f"快捷键: {action}")
    
    def _add_config(self, key: str, value: Any, category: ConfigCategory = ConfigCategory.GENERAL,
                   description: str = "", **kwargs):
        """添加配置项"""
        config_item = ConfigItem(key, value, category, description, **kwargs)
        self._configs[key] = config_item
    
    def set_config(self, key: str, value: Any, notify: bool = True) -> bool:
        """设置配置值"""
        try:
            if key not in self._configs:
                logger.warning(f"Config key not found: {key}")
                return False
            
            config_item = self._configs[key]
            old_value = config_item.value
            
            # 验证配置值
            if not config_item.validate(value):
                logger.warning(f"Invalid config value for {key}: {value}")
                return False
            
            # 更新配置值
            config_item.value = value
            
            # 保存到状态管理器
            self.state_manager.set_state(
                f"config.{key}",
                value,
                scope=StateScope.USER,
                persistence_type=StatePersistenceType.JSON,
                description=config_item.description,
                notify=False
            )
            
            # 发送信号
            if notify:
                self.config_changed.emit(key, old_value, value)
                
                # 特殊处理主题变更
                if key == "appearance.theme":
                    self.theme_changed.emit(value)
            
            logger.debug(f"Config updated: {key} = {value}")
            return True
            
        except Exception as e:
            self.error_manager.handle_exception(
                e,
                context={"operation": "set_config", "key": key, "value": value},
                category=ErrorCategory.APP_CONFIGURATION,
                show_dialog=False
            )
            return False
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        try:
            if key in self._configs:
                return self._configs[key].value
            
            # 尝试从状态管理器获取
            state_value = self.state_manager.get_state(f"config.{key}")
            if state_value is not None:
                return state_value
            
            return default
            
        except Exception as e:
            self.error_manager.handle_exception(
                e,
                context={"operation": "get_config", "key": key},
                category=ErrorCategory.APP_CONFIGURATION,
                show_dialog=False
            )
            return default
    
    def get_configs_by_category(self, category: ConfigCategory) -> Dict[str, Any]:
        """按类别获取配置"""
        result = {}
        for key, config_item in self._configs.items():
            if config_item.category == category:
                result[key] = config_item.value
        return result
    
    def reset_config(self, key: str) -> bool:
        """重置配置为默认值"""
        try:
            if key not in self._configs:
                return False
            
            config_item = self._configs[key]
            old_value = config_item.value
            config_item.reset_to_default()
            
            # 更新状态管理器
            self.state_manager.set_state(
                f"config.{key}",
                config_item.value,
                scope=StateScope.USER,
                persistence_type=StatePersistenceType.JSON,
                notify=False
            )
            
            # 发送信号
            self.config_changed.emit(key, old_value, config_item.value)
            
            return True
            
        except Exception as e:
            self.error_manager.handle_exception(
                e,
                context={"operation": "reset_config", "key": key},
                category=ErrorCategory.APP_CONFIGURATION,
                show_dialog=False
            )
            return False
    
    def reset_all_configs(self) -> bool:
        """重置所有配置为默认值"""
        try:
            for config_item in self._configs.values():
                config_item.reset_to_default()
                self.state_manager.set_state(
                    f"config.{config_item.key}",
                    config_item.value,
                    scope=StateScope.USER,
                    persistence_type=StatePersistenceType.JSON,
                    notify=False
                )
            
            self.config_reset.emit()
            logger.info("All configs reset to default values")
            return True
            
        except Exception as e:
            self.error_manager.handle_exception(
                e,
                context={"operation": "reset_all_configs"},
                category=ErrorCategory.APP_CONFIGURATION
            )
            return False
    
    def load_configs(self) -> bool:
        """加载配置"""
        try:
            config_loaded = False
            
            # 如果配置文件存在，加载配置
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                for key, value in config_data.items():
                    if key in self._configs:
                        self._configs[key].value = value
                        # 同步到状态管理器
                        self.state_manager.set_state(
                            f"config.{key}",
                            value,
                            scope=StateScope.USER,
                            persistence_type=StatePersistenceType.JSON,
                            notify=False
                        )
                
                config_loaded = True
                logger.info(f"Configs loaded from {self.config_file}")
            
            # 如果没有配置文件，生成默认配置文件
            else:
                self.save_configs()
                logger.info("Default config file generated")
            
            self.config_loaded.emit()
            return config_loaded
            
        except Exception as e:
            self.error_manager.handle_exception(
                e,
                context={"operation": "load_configs", "config_file": str(self.config_file)},
                category=ErrorCategory.APP_CONFIGURATION,
                show_dialog=False
            )
            # 生成默认配置文件
            self.save_configs()
            return False
    
    def save_configs(self) -> bool:
        """保存配置"""
        try:
            config_data = {}
            for key, config_item in self._configs.items():
                config_data[key] = config_item.value
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
            
            self.config_saved.emit()
            logger.debug(f"Configs saved to {self.config_file}")
            return True
            
        except Exception as e:
            self.error_manager.handle_exception(
                e,
                context={"operation": "save_configs", "config_file": str(self.config_file)},
                category=ErrorCategory.APP_CONFIGURATION
            )
            return False
    
    def get_window_config(self) -> Dict[str, Any]:
        """获取窗口配置"""
        return {
            'remember_size': self.get_config('window.remember_size', True),
            'remember_position': self.get_config('window.remember_position', True),
            'center_on_startup': self.get_config('window.center_on_startup', True),
            'default_width': self.get_config('window.default_width', 1200),
            'default_height': self.get_config('window.default_height', 800)
        }
    
    def get_appearance_config(self) -> Dict[str, Any]:
        """获取外观配置"""
        return {
            'theme': self.get_config('appearance.theme', ThemeType.LIGHT.value),
            'font_family': self.get_config('appearance.font_family', '微软雅黑'),
            'font_size': self.get_config('appearance.font_size', 9),
            'window_opacity': self.get_config('appearance.window_opacity', 1.0),
            'show_toolbar': self.get_config('appearance.show_toolbar', True),
            'show_statusbar': self.get_config('appearance.show_statusbar', True),
            'icon_size': self.get_config('appearance.icon_size', 16)
        }
    
    def get_behavior_config(self) -> Dict[str, Any]:
        """获取行为配置"""
        return {
            'double_click_action': self.get_config('behavior.double_click_action', 'open'),
            'show_hidden_files': self.get_config('behavior.show_hidden_files', False),
            'auto_refresh': self.get_config('behavior.auto_refresh', True),
            'file_view_mode': self.get_config('behavior.file_view_mode', 'list'),
            'navigation_history_size': self.get_config('behavior.navigation_history_size', 20)
        }
    
    def get_shortcut(self, action: str) -> str:
        """获取快捷键"""
        return self.get_config(f"shortcuts.{action}", "")
    
    def set_shortcut(self, action: str, shortcut: str) -> bool:
        """设置快捷键"""
        return self.set_config(f"shortcuts.{action}", shortcut)
    
    def export_configs(self, file_path: str) -> bool:
        """导出配置"""
        try:
            config_data = {
                'app_name': self.app_name,
                'export_time': datetime.now().isoformat(),
                'configs': {}
            }
            
            for key, config_item in self._configs.items():
                config_data['configs'][key] = config_item.to_dict()
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Configs exported to {file_path}")
            return True
            
        except Exception as e:
            self.error_manager.handle_exception(
                e,
                context={"operation": "export_configs", "file_path": file_path},
                category=ErrorCategory.APP_CONFIGURATION
            )
            return False
    
    def import_configs(self, file_path: str) -> bool:
        """导入配置"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            if 'configs' not in import_data:
                logger.warning("Invalid config file format")
                return False
            
            imported_count = 0
            for key, config_data in import_data['configs'].items():
                if key in self._configs:
                    value = config_data.get('value')
                    if self._configs[key].validate(value):
                        self._configs[key].value = value
                        imported_count += 1
            
            # 保存导入的配置
            self.save_configs()
            
            logger.info(f"Imported {imported_count} configs from {file_path}")
            self.config_loaded.emit()
            return True
            
        except Exception as e:
            self.error_manager.handle_exception(
                e,
                context={"operation": "import_configs", "file_path": file_path},
                category=ErrorCategory.APP_CONFIGURATION
            )
            return False
    
    def get_config_info(self, key: str) -> Optional[Dict[str, Any]]:
        """获取配置项信息"""
        if key in self._configs:
            return self._configs[key].to_dict()
        return None
    
    def get_all_configs_info(self) -> Dict[str, Dict[str, Any]]:
        """获取所有配置项信息"""
        result = {}
        for key, config_item in self._configs.items():
            result[key] = config_item.to_dict()
        return result


# 全局配置管理器实例
_config_manager_instance: Optional[ConfigManager] = None


def get_config_manager(parent: Optional[QWidget] = None, app_name: str = "GudaZip") -> ConfigManager:
    """获取配置管理器单例"""
    global _config_manager_instance
    if _config_manager_instance is None:
        _config_manager_instance = ConfigManager(parent, app_name)
    return _config_manager_instance


def get_config(key: str, default: Any = None) -> Any:
    """全局函数：获取配置值"""
    return get_config_manager().get_config(key, default)


def set_config(key: str, value: Any) -> bool:
    """全局函数：设置配置值"""
    return get_config_manager().set_config(key, value) 