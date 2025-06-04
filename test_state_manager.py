#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
StateManager 状态管理系统测试程序
验证4.2任务完成情况 - 程序状态的集中管理和持久化
"""

import sys
import os
sys.path.insert(0, 'src')

from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QTextEdit, QHBoxLayout, QLabel, QLineEdit, QComboBox
from PySide6.QtCore import Qt

# 导入状态管理器
from gudazip.core.state_manager import StateManager, StateScope, StatePersistenceType, get_state_manager


class StateManagerTestWindow(QMainWindow):
    """StateManager测试窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GudaZip StateManager 测试工具")
        self.setGeometry(100, 100, 900, 700)
        
        # 获取状态管理器
        self.state_manager = get_state_manager(self, "GudaZipTest")
        
        self.init_ui()
        self.connect_state_signals()
        
        # 显示初始统计信息
        self.show_statistics()
    
    def init_ui(self):
        """初始化界面"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # 标题
        title_label = QLabel("🔧 StateManager 状态管理系统测试")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        layout.addWidget(title_label)
        
        # 状态操作区域
        self.create_state_control_section(layout)
        
        # 状态显示区域
        self.create_state_display_section(layout)
        
        # 测试按钮区域
        self.create_test_buttons_section(layout)
        
        # 日志输出区域
        self.create_log_section(layout)
    
    def create_state_control_section(self, parent_layout):
        """创建状态控制区域"""
        control_widget = QWidget()
        control_layout = QVBoxLayout(control_widget)
        
        # 标题
        control_title = QLabel("📝 状态操作")
        control_title.setStyleSheet("font-weight: bold; margin: 5px 0;")
        control_layout.addWidget(control_title)
        
        # 设置状态的控件
        set_layout = QHBoxLayout()
        
        set_layout.addWidget(QLabel("键:"))
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("例如：test.setting")
        set_layout.addWidget(self.key_input)
        
        set_layout.addWidget(QLabel("值:"))
        self.value_input = QLineEdit()
        self.value_input.setPlaceholderText("例如：Hello World")
        set_layout.addWidget(self.value_input)
        
        set_layout.addWidget(QLabel("作用域:"))
        self.scope_combo = QComboBox()
        for scope in StateScope:
            self.scope_combo.addItem(scope.value, scope)
        set_layout.addWidget(self.scope_combo)
        
        set_layout.addWidget(QLabel("持久化:"))
        self.persistence_combo = QComboBox()
        for persistence in StatePersistenceType:
            self.persistence_combo.addItem(persistence.value, persistence)
        set_layout.addWidget(self.persistence_combo)
        
        set_button = QPushButton("设置状态")
        set_button.clicked.connect(self.set_state)
        set_layout.addWidget(set_button)
        
        control_layout.addLayout(set_layout)
        
        # 获取状态的控件
        get_layout = QHBoxLayout()
        
        get_layout.addWidget(QLabel("获取键:"))
        self.get_key_input = QLineEdit()
        self.get_key_input.setPlaceholderText("例如：test.setting")
        get_layout.addWidget(self.get_key_input)
        
        get_button = QPushButton("获取状态")
        get_button.clicked.connect(self.get_state)
        get_layout.addWidget(get_button)
        
        remove_button = QPushButton("删除状态")
        remove_button.clicked.connect(self.remove_state)
        get_layout.addWidget(remove_button)
        
        control_layout.addLayout(get_layout)
        
        parent_layout.addWidget(control_widget)
    
    def create_state_display_section(self, parent_layout):
        """创建状态显示区域"""
        display_widget = QWidget()
        display_layout = QVBoxLayout(display_widget)
        
        # 标题
        display_title = QLabel("📊 状态信息")
        display_title.setStyleSheet("font-weight: bold; margin: 5px 0;")
        display_layout.addWidget(display_title)
        
        # 状态显示文本框
        self.states_display = QTextEdit()
        self.states_display.setMaximumHeight(200)
        self.states_display.setReadOnly(True)
        display_layout.addWidget(self.states_display)
        
        # 刷新按钮
        refresh_button = QPushButton("🔄 刷新状态显示")
        refresh_button.clicked.connect(self.refresh_states_display)
        display_layout.addWidget(refresh_button)
        
        parent_layout.addWidget(display_widget)
    
    def create_test_buttons_section(self, parent_layout):
        """创建测试按钮区域"""
        test_widget = QWidget()
        test_layout = QVBoxLayout(test_widget)
        
        # 标题
        test_title = QLabel("🧪 功能测试")
        test_title.setStyleSheet("font-weight: bold; margin: 5px 0;")
        test_layout.addWidget(test_title)
        
        # 按钮布局
        buttons_layout = QHBoxLayout()
        
        # 基本功能测试
        basic_test_btn = QPushButton("基本功能测试")
        basic_test_btn.clicked.connect(self.test_basic_functions)
        buttons_layout.addWidget(basic_test_btn)
        
        # 持久化测试
        persistence_test_btn = QPushButton("持久化测试")
        persistence_test_btn.clicked.connect(self.test_persistence)
        buttons_layout.addWidget(persistence_test_btn)
        
        # 状态历史测试
        history_test_btn = QPushButton("历史记录测试")
        history_test_btn.clicked.connect(self.test_state_history)
        buttons_layout.addWidget(history_test_btn)
        
        # 导入导出测试
        export_test_btn = QPushButton("导入导出测试")
        export_test_btn.clicked.connect(self.test_import_export)
        buttons_layout.addWidget(export_test_btn)
        
        # 保存所有状态
        save_btn = QPushButton("💾 保存所有状态")
        save_btn.clicked.connect(self.save_all_states)
        buttons_layout.addWidget(save_btn)
        
        # 显示统计信息
        stats_btn = QPushButton("📈 显示统计")
        stats_btn.clicked.connect(self.show_statistics)
        buttons_layout.addWidget(stats_btn)
        
        test_layout.addLayout(buttons_layout)
        parent_layout.addWidget(test_widget)
    
    def create_log_section(self, parent_layout):
        """创建日志区域"""
        log_widget = QWidget()
        log_layout = QVBoxLayout(log_widget)
        
        # 标题
        log_title = QLabel("📋 测试日志")
        log_title.setStyleSheet("font-weight: bold; margin: 5px 0;")
        log_layout.addWidget(log_title)
        
        # 日志文本框
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        
        # 清空日志按钮
        clear_log_btn = QPushButton("🗑️ 清空日志")
        clear_log_btn.clicked.connect(self.log_text.clear)
        log_layout.addWidget(clear_log_btn)
        
        parent_layout.addWidget(log_widget)
    
    def connect_state_signals(self):
        """连接状态管理器的信号"""
        self.state_manager.state_changed.connect(self.on_state_changed)
        self.state_manager.state_added.connect(self.on_state_added)
        self.state_manager.state_removed.connect(self.on_state_removed)
        self.state_manager.state_saved.connect(self.on_state_saved)
        self.state_manager.state_loaded.connect(self.on_state_loaded)
    
    def log(self, message):
        """添加日志消息"""
        self.log_text.append(f"🔸 {message}")
        
    def set_state(self):
        """设置状态"""
        key = self.key_input.text().strip()
        value = self.value_input.text().strip()
        
        if not key:
            self.log("❌ 错误：键不能为空")
            return
        
        scope = self.scope_combo.currentData()
        persistence = self.persistence_combo.currentData()
        
        # 尝试转换值的类型
        if value.lower() in ['true', 'false']:
            value = value.lower() == 'true'
        elif value.isdigit():
            value = int(value)
        elif value.replace('.', '').isdigit():
            value = float(value)
        
        success = self.state_manager.set_state(
            key, value, scope, persistence,
            description=f"测试状态 - {key}"
        )
        
        if success:
            self.log(f"✅ 成功设置状态：{key} = {value} (作用域: {scope.value}, 持久化: {persistence.value})")
            self.refresh_states_display()
        else:
            self.log(f"❌ 设置状态失败：{key}")
    
    def get_state(self):
        """获取状态"""
        key = self.get_key_input.text().strip()
        
        if not key:
            self.log("❌ 错误：键不能为空")
            return
        
        value = self.state_manager.get_state(key, "未找到")
        self.log(f"🔍 获取状态：{key} = {value}")
        
        # 获取状态详细信息
        info = self.state_manager.get_state_info(key)
        if info:
            self.log(f"📊 状态详情：作用域={info['scope']}, 持久化={info['persistence_type']}, 访问次数={info['access_count']}")
    
    def remove_state(self):
        """删除状态"""
        key = self.get_key_input.text().strip()
        
        if not key:
            self.log("❌ 错误：键不能为空")
            return
        
        success = self.state_manager.remove_state(key)
        if success:
            self.log(f"🗑️ 成功删除状态：{key}")
            self.refresh_states_display()
        else:
            self.log(f"❌ 删除状态失败：{key} (可能不存在)")
    
    def refresh_states_display(self):
        """刷新状态显示"""
        all_states = self.state_manager.get_all_states_info()
        
        display_text = "当前所有状态：\n\n"
        
        for key, info in all_states.items():
            display_text += f"🔑 {key}\n"
            display_text += f"   值: {info['value']}\n"
            display_text += f"   作用域: {info['scope']}\n"
            display_text += f"   持久化: {info['persistence_type']}\n"
            display_text += f"   访问次数: {info['access_count']}\n"
            display_text += f"   描述: {info['description']}\n\n"
        
        self.states_display.setPlainText(display_text)
    
    def test_basic_functions(self):
        """测试基本功能"""
        self.log("🧪 开始基本功能测试...")
        
        # 测试设置和获取
        test_key = "test.basic.string"
        test_value = "Hello StateManager!"
        
        success = self.state_manager.set_state(test_key, test_value)
        if success:
            self.log(f"✅ 设置测试状态成功")
        
        retrieved_value = self.state_manager.get_state(test_key)
        if retrieved_value == test_value:
            self.log(f"✅ 获取测试状态成功：{retrieved_value}")
        else:
            self.log(f"❌ 获取测试状态失败：期望 {test_value}，得到 {retrieved_value}")
        
        # 测试不同类型的值
        test_cases = [
            ("test.basic.int", 42),
            ("test.basic.float", 3.14),
            ("test.basic.bool", True),
            ("test.basic.list", [1, 2, 3]),
            ("test.basic.dict", {"key": "value"})
        ]
        
        for key, value in test_cases:
            self.state_manager.set_state(key, value)
            retrieved = self.state_manager.get_state(key)
            if retrieved == value:
                self.log(f"✅ 类型测试成功：{type(value).__name__}")
            else:
                self.log(f"❌ 类型测试失败：{type(value).__name__}")
        
        # 测试状态存在检查
        if self.state_manager.has_state(test_key):
            self.log("✅ 状态存在检查成功")
        else:
            self.log("❌ 状态存在检查失败")
        
        self.log("🏁 基本功能测试完成")
        self.refresh_states_display()
    
    def test_persistence(self):
        """测试持久化功能"""
        self.log("🧪 开始持久化功能测试...")
        
        # 测试不同持久化类型
        persistence_tests = [
            ("test.persist.json", "JSON数据", StatePersistenceType.JSON),
            ("test.persist.qsettings", "Qt设置数据", StatePersistenceType.QSETTINGS),
            ("test.persist.memory", "内存数据", StatePersistenceType.MEMORY),
        ]
        
        for key, value, persistence_type in persistence_tests:
            success = self.state_manager.set_state(
                key, value,
                scope=StateScope.USER,
                persistence_type=persistence_type
            )
            if success:
                self.log(f"✅ 持久化测试设置成功：{persistence_type.value}")
            else:
                self.log(f"❌ 持久化测试设置失败：{persistence_type.value}")
        
        # 保存所有状态
        if self.state_manager.save_all_states():
            self.log("✅ 状态保存成功")
        else:
            self.log("❌ 状态保存失败")
        
        self.log("🏁 持久化功能测试完成")
    
    def test_state_history(self):
        """测试状态历史功能"""
        self.log("🧪 开始状态历史测试...")
        
        history_key = "test.history.value"
        
        # 设置多个版本的值
        values = ["版本1", "版本2", "版本3", "版本4"]
        
        for i, value in enumerate(values):
            self.state_manager.set_state(history_key, value)
            self.log(f"设置历史版本 {i+1}: {value}")
        
        # 获取历史记录
        history = self.state_manager.get_state_history(history_key)
        self.log(f"📚 历史记录数量: {len(history)}")
        
        # 测试回滚
        if self.state_manager.rollback_state(history_key, 1):
            rolled_back_value = self.state_manager.get_state(history_key)
            self.log(f"↩️ 回滚1步成功，当前值: {rolled_back_value}")
        else:
            self.log("❌ 回滚失败")
        
        if self.state_manager.rollback_state(history_key, 2):
            rolled_back_value = self.state_manager.get_state(history_key)
            self.log(f"↩️ 回滚2步成功，当前值: {rolled_back_value}")
        else:
            self.log("❌ 回滚2步失败")
        
        self.log("🏁 状态历史测试完成")
    
    def test_import_export(self):
        """测试导入导出功能"""
        self.log("🧪 开始导入导出测试...")
        
        # 设置一些测试数据
        test_data = {
            "export.test.string": "测试字符串",
            "export.test.number": 123,
            "export.test.bool": True
        }
        
        for key, value in test_data.items():
            self.state_manager.set_state(key, value, scope=StateScope.USER)
        
        # 导出用户作用域的状态
        export_file = "test_export_states.json"
        if self.state_manager.export_states(export_file, StateScope.USER):
            self.log(f"✅ 导出状态成功：{export_file}")
            
            # 删除测试数据
            for key in test_data.keys():
                self.state_manager.remove_state(key)
            self.log("🗑️ 删除测试数据，准备导入测试")
            
            # 导入状态
            if self.state_manager.import_states(export_file):
                self.log("✅ 导入状态成功")
                
                # 验证导入的数据
                all_correct = True
                for key, expected_value in test_data.items():
                    actual_value = self.state_manager.get_state(key)
                    if actual_value != expected_value:
                        all_correct = False
                        self.log(f"❌ 导入验证失败：{key} 期望 {expected_value}，得到 {actual_value}")
                
                if all_correct:
                    self.log("✅ 导入数据验证成功")
            else:
                self.log("❌ 导入状态失败")
            
            # 清理文件
            try:
                os.remove(export_file)
                self.log(f"🗑️ 清理临时文件：{export_file}")
            except:
                pass
        else:
            self.log("❌ 导出状态失败")
        
        self.log("🏁 导入导出测试完成")
    
    def save_all_states(self):
        """保存所有状态"""
        if self.state_manager.save_all_states():
            self.log("✅ 所有状态保存成功")
        else:
            self.log("❌ 状态保存失败")
    
    def show_statistics(self):
        """显示统计信息"""
        stats = self.state_manager.get_statistics()
        
        self.log("📈 状态管理器统计信息：")
        self.log(f"   总状态数: {stats['total_states']}")
        
        self.log("   按作用域分布:")
        for scope, count in stats['states_by_scope'].items():
            self.log(f"     {scope}: {count}")
        
        self.log("   按持久化类型分布:")
        for persistence, count in stats['states_by_persistence'].items():
            self.log(f"     {persistence}: {count}")
        
        self.log("   最常访问的状态:")
        for item in stats['most_accessed_states'][:5]:
            self.log(f"     {item['key']}: {item['access_count']} 次")
        
        self.log(f"   存储路径: {stats['storage_paths']['states_dir']}")
    
    def on_state_changed(self, key, old_value, new_value):
        """状态变更信号处理"""
        self.log(f"🔄 状态变更：{key} 从 {old_value} 变为 {new_value}")
    
    def on_state_added(self, key, value):
        """状态添加信号处理"""
        self.log(f"➕ 新增状态：{key} = {value}")
    
    def on_state_removed(self, key):
        """状态删除信号处理"""
        self.log(f"➖ 删除状态：{key}")
    
    def on_state_saved(self, path):
        """状态保存信号处理"""
        self.log(f"💾 状态已保存到：{path}")
    
    def on_state_loaded(self, path):
        """状态加载信号处理"""
        self.log(f"📂 状态已从以下路径加载：{path}")


def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 设置应用信息
    app.setApplicationName("GudaZip StateManager Test")
    app.setApplicationVersion("1.0.0")
    
    # 创建测试窗口
    window = StateManagerTestWindow()
    window.show()
    
    # 运行应用
    sys.exit(app.exec())


if __name__ == "__main__":
    main() 