# -*- coding: utf-8 -*-
"""
信号管理器
提供安全的Qt信号阻塞和恢复机制，防止信号冲突
"""

from contextlib import contextmanager
from typing import Any, Callable, Dict, Set
from PySide6.QtCore import QObject
import logging

logger = logging.getLogger(__name__)


class SignalManager:
    """
    信号管理器，提供安全的信号阻塞和恢复功能
    
    主要功能：
    1. 临时阻塞信号，防止递归调用
    2. 确保信号一定会被重新连接
    3. 支持批量信号管理
    4. 提供调试和日志功能
    """
    
    def __init__(self, debug_mode: bool = False):
        self.debug_mode = debug_mode
        self._blocked_connections: Dict[str, list] = {}
        self._connection_counter = 0
        
    def _log_debug(self, message: str):
        """调试日志"""
        if self.debug_mode:
            logger.debug(f"[SignalManager] {message}")
    
    @contextmanager
    def block_signal(self, signal, handler: Callable, operation_name: str = "operation"):
        """
        安全地临时阻塞单个信号
        
        Args:
            signal: Qt信号对象
            handler: 信号处理函数
            operation_name: 操作名称，用于调试
            
        Example:
            with signal_manager.block_signal(combo.currentTextChanged, self.on_text_changed):
                combo.setText("new text")  # 不会触发信号
        """
        connection_id = f"{operation_name}_{self._connection_counter}"
        self._connection_counter += 1
        
        self._log_debug(f"阻塞信号 {signal} -> {handler.__name__} (ID: {connection_id})")
        
        # 记录连接信息
        self._blocked_connections[connection_id] = [(signal, handler)]
        
        try:
            # 断开信号
            signal.disconnect(handler)
            self._log_debug(f"信号已断开: {connection_id}")
            
            yield connection_id
            
        except Exception as e:
            self._log_debug(f"操作执行时出错: {e}")
            raise
            
        finally:
            # 确保重新连接信号
            try:
                signal.connect(handler)
                self._log_debug(f"信号已重新连接: {connection_id}")
            except Exception as e:
                logger.error(f"重新连接信号失败 {connection_id}: {e}")
                raise
            finally:
                # 清理记录
                if connection_id in self._blocked_connections:
                    del self._blocked_connections[connection_id]
    
    @contextmanager
    def block_signals(self, signal_handlers: list, operation_name: str = "batch_operation"):
        """
        安全地临时阻塞多个信号
        
        Args:
            signal_handlers: [(signal, handler), ...] 列表
            operation_name: 操作名称，用于调试
            
        Example:
            with signal_manager.block_signals([
                (combo1.currentTextChanged, self.on_combo1_changed),
                (combo2.currentTextChanged, self.on_combo2_changed)
            ]):
                combo1.setText("text1")
                combo2.setText("text2")
        """
        connection_id = f"{operation_name}_{self._connection_counter}"
        self._connection_counter += 1
        
        self._log_debug(f"批量阻塞 {len(signal_handlers)} 个信号 (ID: {connection_id})")
        
        # 记录所有连接
        self._blocked_connections[connection_id] = signal_handlers.copy()
        
        # 存储断开失败的连接
        failed_disconnects = []
        
        try:
            # 断开所有信号
            for signal, handler in signal_handlers:
                try:
                    signal.disconnect(handler)
                    self._log_debug(f"断开信号: {signal} -> {handler.__name__}")
                except Exception as e:
                    self._log_debug(f"断开信号失败: {signal} -> {handler.__name__}: {e}")
                    failed_disconnects.append((signal, handler))
            
            yield connection_id
            
        except Exception as e:
            self._log_debug(f"批量操作执行时出错: {e}")
            raise
            
        finally:
            # 重新连接所有信号
            failed_reconnects = []
            
            for signal, handler in signal_handlers:
                if (signal, handler) not in failed_disconnects:
                    try:
                        signal.connect(handler)
                        self._log_debug(f"重新连接信号: {signal} -> {handler.__name__}")
                    except Exception as e:
                        logger.error(f"重新连接信号失败: {signal} -> {handler.__name__}: {e}")
                        failed_reconnects.append((signal, handler))
            
            # 清理记录
            if connection_id in self._blocked_connections:
                del self._blocked_connections[connection_id]
            
            # 如果有重新连接失败的，抛出异常
            if failed_reconnects:
                raise RuntimeError(f"重新连接 {len(failed_reconnects)} 个信号失败")
    
    def force_reconnect_all(self):
        """
        强制重新连接所有被记录的信号（紧急恢复）
        谨慎使用：只在程序异常时调用
        """
        logger.warning("执行强制信号重连...")
        
        for connection_id, signal_handlers in self._blocked_connections.items():
            logger.warning(f"强制重连连接组: {connection_id}")
            
            for signal, handler in signal_handlers:
                try:
                    signal.connect(handler)
                    self._log_debug(f"强制重连成功: {signal} -> {handler.__name__}")
                except Exception as e:
                    logger.error(f"强制重连失败: {signal} -> {handler.__name__}: {e}")
        
        # 清空所有记录
        self._blocked_connections.clear()
    
    def get_blocked_connections(self) -> Dict[str, int]:
        """
        获取当前被阻塞的连接统计（用于调试）
        
        Returns:
            {connection_id: signal_count}
        """
        return {
            conn_id: len(handlers) 
            for conn_id, handlers in self._blocked_connections.items()
        }
    
    def is_healthy(self) -> bool:
        """
        检查信号管理器是否处于健康状态
        健康状态 = 没有被阻塞的连接
        """
        return len(self._blocked_connections) == 0


class GlobalSignalManager:
    """全局信号管理器单例"""
    
    _instance = None
    
    @classmethod
    def get_instance(cls, debug_mode: bool = False) -> SignalManager:
        """获取全局信号管理器实例"""
        if cls._instance is None:
            cls._instance = SignalManager(debug_mode=debug_mode)
        return cls._instance
    
    @classmethod
    def reset_instance(cls):
        """重置全局实例（主要用于测试）"""
        if cls._instance:
            cls._instance.force_reconnect_all()
        cls._instance = None


# 便捷函数
def get_signal_manager(debug_mode: bool = False) -> SignalManager:
    """获取全局信号管理器实例"""
    return GlobalSignalManager.get_instance(debug_mode=debug_mode)


# 装饰器版本（可选，用于方法级别的信号阻塞）
def block_signals_during(signal_handlers: list, operation_name: str = "decorated_operation"):
    """
    装饰器：在函数执行期间阻塞指定信号
    
    Args:
        signal_handlers: [(signal, handler), ...] 列表
        operation_name: 操作名称
    """
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            signal_manager = get_signal_manager()
            with signal_manager.block_signals(signal_handlers, operation_name):
                return func(self, *args, **kwargs)
        return wrapper
    return decorator 