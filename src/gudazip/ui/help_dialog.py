# -*- coding: utf-8 -*-
"""
帮助对话框
提供使用说明、支持的文件类型和关于信息
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget, 
    QLabel, QPushButton, QTextEdit, QScrollArea, QDialogButtonBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPixmap, QIcon
import qtawesome as qta


class HelpDialog(QDialog):
    """GudaZip帮助对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle("帮助")
        self.setMinimumSize(600, 500)
        self.resize(700, 600)
        
        layout = QVBoxLayout(self)
        
        # 标题
        title = QLabel("GudaZip 帮助")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("微软雅黑", 14, QFont.Bold))
        layout.addWidget(title)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # 创建各个帮助页
        self.create_usage_tab()
        self.create_file_types_tab()
        self.create_about_tab()
        
        # 关闭按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)
        
    def create_usage_tab(self):
        """创建使用说明页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 使用说明内容
        usage_text = QTextEdit()
        usage_text.setReadOnly(True)
        usage_text.setHtml("""
        <h3>GudaZip 使用说明</h3>
        
        <h4>🔧 主要功能</h4>
        <ul>
            <li><b>创建压缩包：</b> 选择文件或文件夹，点击"添加"按钮创建新的压缩包</li>
            <li><b>解压文件：</b> 选择压缩包，点击"解压到"按钮解压文件</li>
            <li><b>浏览压缩包：</b> 点击"打开"按钮浏览压缩包内容</li>
            <li><b>程序设置：</b> 点击"设置"按钮调整程序选项</li>
        </ul>
        
        <h4>📁 文件操作</h4>
        <ul>
            <li><b>双击文件：</b> 根据设置执行打开、选择或预览操作</li>
            <li><b>多选文件：</b> 按住Ctrl键点击多个文件进行批量操作</li>
            <li><b>返回上级：</b> 在压缩包浏览模式下，点击"返回文件系统"按钮</li>
        </ul>
        
        <h4>⚙️ 快捷键</h4>
        <ul>
            <li><b>Ctrl+N：</b> 创建新压缩包</li>
            <li><b>Ctrl+O：</b> 打开压缩包</li>
            <li><b>Ctrl+E：</b> 解压文件</li>
            <li><b>Ctrl+B：</b> 返回文件系统</li>
            <li><b>F5：</b> 刷新当前视图</li>
        </ul>
        
        <h4>💡 使用技巧</h4>
        <ul>
            <li>支持拖拽操作，可以将文件拖到程序中快速处理</li>
            <li>在压缩包浏览模式下，"添加"按钮会变为向压缩包添加文件</li>
            <li>可以在选项中调整字体大小、窗口透明度等外观设置</li>
            <li>程序会记住窗口大小和位置，下次启动时自动恢复</li>
        </ul>
        """)
        
        layout.addWidget(usage_text)
        self.tab_widget.addTab(tab, "📖 使用说明")
        
    def create_file_types_tab(self):
        """创建支持的文件类型页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 文件类型说明
        file_types_text = QTextEdit()
        file_types_text.setReadOnly(True)
        file_types_text.setHtml("""
        <h3>支持的文件类型</h3>
        
        <h4>📦 完全支持（读取、创建、解压）</h4>
        <table border="1" style="border-collapse: collapse; width: 100%;">
            <tr style="background-color: #f0f0f0;">
                <th style="padding: 8px;">格式</th>
                <th style="padding: 8px;">扩展名</th>
                <th style="padding: 8px;">说明</th>
            </tr>
            <tr>
                <td style="padding: 8px;"><b>ZIP</b></td>
                <td style="padding: 8px;">.zip</td>
                <td style="padding: 8px;">最常用的压缩格式，兼容性最好</td>
            </tr>
            <tr>
                <td style="padding: 8px;"><b>7-Zip</b></td>
                <td style="padding: 8px;">.7z</td>
                <td style="padding: 8px;">高压缩率格式，文件体积更小</td>
            </tr>
        </table>
        
        <h4>📂 部分支持（仅读取和解压）</h4>
        <table border="1" style="border-collapse: collapse; width: 100%;">
            <tr style="background-color: #f0f0f0;">
                <th style="padding: 8px;">格式</th>
                <th style="padding: 8px;">扩展名</th>
                <th style="padding: 8px;">说明</th>
            </tr>
            <tr>
                <td style="padding: 8px;"><b>RAR</b></td>
                <td style="padding: 8px;">.rar</td>
                <td style="padding: 8px;">常用压缩格式，仅支持解压</td>
            </tr>
            <tr>
                <td style="padding: 8px;"><b>TAR</b></td>
                <td style="padding: 8px;">.tar</td>
                <td style="padding: 8px;">Unix/Linux归档格式</td>
            </tr>
            <tr>
                <td style="padding: 8px;"><b>GZIP</b></td>
                <td style="padding: 8px;">.gz, .tar.gz</td>
                <td style="padding: 8px;">GNU压缩格式</td>
            </tr>
            <tr>
                <td style="padding: 8px;"><b>BZIP2</b></td>
                <td style="padding: 8px;">.bz2, .tar.bz2</td>
                <td style="padding: 8px;">高压缩率格式</td>
            </tr>
        </table>
        
        <h4>📝 注意事项</h4>
        <ul>
            <li>创建压缩包时，推荐使用ZIP或7Z格式</li>
            <li>RAR格式需要安装WinRAR或7-Zip才能正常解压</li>
            <li>某些加密的压缩包可能需要密码才能访问</li>
            <li>损坏的压缩包文件可能无法正常读取</li>
        </ul>
        """)
        
        layout.addWidget(file_types_text)
        self.tab_widget.addTab(tab, "📁 文件类型")
        
    def create_about_tab(self):
        """创建关于页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 程序图标和基本信息
        info_layout = QHBoxLayout()
        
        # 图标
        icon_label = QLabel()
        icon_label.setPixmap(qta.icon('fa5s.file-archive', color='#2e7d32').pixmap(64, 64))
        icon_label.setAlignment(Qt.AlignCenter)
        info_layout.addWidget(icon_label)
        
        # 基本信息
        info_text = QLabel()
        info_text.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        info_text.setFont(QFont("微软雅黑", 12))
        info_text.setText("""
        <h2>GudaZip v1.0</h2>
        <p><b>压缩管理器</b></p>
        <p><b>作者：孤鸿泽</b></p>
        """)
        info_layout.addWidget(info_text)
        
        layout.addLayout(info_layout)
        
        self.tab_widget.addTab(tab, "ℹ️ 关于") 