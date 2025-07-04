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
        
        # 创建标签页
        self.create_about_tab()
        self.create_usage_tab()
        self.create_file_types_tab()
        
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
        <div style="font-size: 14px;">
        <h3 style="font-size: 16px;">GudaZip 使用说明</h3>
        
        <h4 style="font-size: 16px;">🔧 主要功能</h4>
        <ul>
            <li><b>创建压缩包：</b> 选择文件或文件夹，点击"添加"按钮创建新的压缩包</li>
            <li><b>解压文件：</b> 选择压缩包，点击"解压到"按钮解压文件</li>
            <li><b>浏览压缩包：</b> 点击"打开"按钮浏览压缩包内容</li>
            <li><b>程序设置：</b> 点击"设置"按钮调整程序选项</li>
        </ul>
        
        <h4 style="font-size: 16px;">📁 文件操作</h4>
        <ul>
            <li><b>双击文件：</b> 根据设置执行打开、选择或预览操作</li>
            <li><b>多选文件：</b> 按住Ctrl键点击多个文件进行批量操作</li>
            <li><b>返回上级：</b> 在压缩包浏览模式下，点击"返回文件系统"按钮</li>
        </ul>
        
        <h4 style="font-size: 16px;">⚙️ 快捷键</h4>
        <ul>
            <li><b>Ctrl+N：</b> 创建新压缩包</li>
            <li><b>Ctrl+O：</b> 打开压缩包</li>
            <li><b>Ctrl+E：</b> 解压文件</li>
            <li><b>Ctrl+B：</b> 返回文件系统</li>
            <li><b>F5：</b> 刷新当前视图</li>
        </ul>
        
        <h4 style="font-size: 16px;">💡 使用技巧</h4>
        <ul>
            <li>支持拖拽操作，可以将文件拖到程序中快速处理</li>
            <li>在压缩包浏览模式下，"添加"按钮会变为向压缩包添加文件</li>
            <li>可以在选项中调整字体大小、窗口透明度等外观设置</li>
            <li>程序会记住窗口大小和位置，下次启动时自动恢复</li>
        </ul>
        </div>
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
        <div style="font-size: 14px;">
        <h3 style="font-size: 16px;">支持的文件类型（共24种格式）</h3>
        
        <h4 style="font-size: 16px;">📦 完全支持（读取、创建、解压）</h4>
        <table border="1" style="border-collapse: collapse; width: 100%; font-size: 14px;">
            <tr style="background-color: #f0f0f0;">
                <th style="padding: 6px;">格式</th>
                <th style="padding: 6px;">扩展名</th>
                <th style="padding: 6px;">说明</th>
            </tr>
            <tr>
                <td style="padding: 6px;"><b>ZIP</b></td>
                <td style="padding: 6px;">.zip</td>
                <td style="padding: 6px;">最常用的压缩格式，兼容性最好</td>
            </tr>
            <tr>
                <td style="padding: 6px;"><b>7-Zip</b></td>
                <td style="padding: 6px;">.7z</td>
                <td style="padding: 6px;">高压缩率格式，文件体积更小</td>
            </tr>
        </table>
        
        <h4 style="font-size: 16px;">📂 部分支持（仅读取和解压）</h4>
        <table border="1" style="border-collapse: collapse; width: 100%; font-size: 14px;">
            <tr style="background-color: #f0f0f0;">
                <th style="padding: 6px;">格式类型</th>
                <th style="padding: 6px;">扩展名</th>
                <th style="padding: 6px;">说明</th>
            </tr>
            <tr>
                <td style="padding: 6px;"><b>RAR</b></td>
                <td style="padding: 6px;">.rar</td>
                <td style="padding: 6px;">常用压缩格式，仅支持解压</td>
            </tr>
            <tr>
                <td style="padding: 6px;"><b>TAR归档</b></td>
                <td style="padding: 6px;">.tar, .tgz, .tar.gz, .tbz, .tbz2, .tar.bz2, .txz, .tar.xz, .taz</td>
                <td style="padding: 6px;">Unix/Linux归档格式及其压缩变体</td>
            </tr>
            <tr>
                <td style="padding: 6px;"><b>GZIP</b></td>
                <td style="padding: 6px;">.gz, .gzip</td>
                <td style="padding: 6px;">GNU压缩格式</td>
            </tr>
            <tr>
                <td style="padding: 6px;"><b>BZIP2</b></td>
                <td style="padding: 6px;">.bz2, .bzip2</td>
                <td style="padding: 6px;">高压缩率格式</td>
            </tr>
            <tr>
                <td style="padding: 6px;"><b>XZ</b></td>
                <td style="padding: 6px;">.xz</td>
                <td style="padding: 6px;">高效压缩格式</td>
            </tr>
            <tr>
                <td style="padding: 6px;"><b>LZMA</b></td>
                <td style="padding: 6px;">.lzma</td>
                <td style="padding: 6px;">LZMA压缩格式</td>
            </tr>
        </table>
        
        <h4 style="font-size: 16px;">📝 注意事项</h4>
        <ul>
            <li>创建压缩包时，推荐使用ZIP或7Z格式</li>
            <li>RAR格式需要安装WinRAR或7-Zip才能正常解压</li>
            <li>某些加密的压缩包可能需要密码才能访问</li>
            <li>损坏的压缩包文件可能无法正常读取</li>
        </ul>
        </div>
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
        try:
            # 使用app.ico作为关于对话框的图标
            import os
            # 从当前文件位置计算正确的图标路径
            current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            icon_path = os.path.join(current_dir, "resources", "icons", "app.ico")
            icon_path = os.path.abspath(icon_path)
            if os.path.exists(icon_path):
                icon_label.setPixmap(QIcon(icon_path).pixmap(64, 64))
            else:
                # 备用图标
                icon_label.setPixmap(qta.icon('fa5s.file-archive', color='#2e7d32').pixmap(64, 64))
        except Exception:
            # 备用图标
            icon_label.setPixmap(qta.icon('fa5s.file-archive', color='#2e7d32').pixmap(64, 64))
        icon_label.setAlignment(Qt.AlignCenter)
        info_layout.addWidget(icon_label)
        
        # 基本信息
        info_text = QLabel()
        info_text.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        info_text.setFont(QFont("微软雅黑", 12))
        info_text.setText("""
         <div style="font-family: '微软雅黑', sans-serif; font-size: 12px; line-height: 1.6;">
         <h2 style="color: black; font-size: 18px; margin: 8px 0;">GudaZip v1.0 压缩管理器</h2>
         <p style="margin: 4px 0; font-size: 18px;"><b>作者：</b>孤鸿泽</p>
         <p style="margin: 4px 0; font-size: 18px;"><b>网站：</b><a href="https://guda.cn" style="color: black; text-decoration: none;">guda.cn</a></p>
         </div>
         """)
        info_text.setOpenExternalLinks(True)
        info_layout.addWidget(info_text)
        
        layout.addLayout(info_layout)
        
        # 添加许可协议和隐私声明
        license_text = QTextEdit()
        license_text.setReadOnly(True)
        license_text.setMaximumHeight(300)
        license_text.setHtml("""
         <div style="font-family: '微软雅黑', sans-serif; font-size: 12px; line-height: 1.6;">
         <h3 style="color: black; font-size: 16px; margin: 15px 0 10px 0;">软件许可协议</h3>
         <p style="margin: 8px 0; font-size: 14px;">GudaZip是一款免费的压缩文件管理工具，用户可以自由使用、复制和分发。</p>
         
         <h4 style="color: black; font-size: 16px; margin: 12px 0 8px 0;">使用条款：</h4>
         <ul style="margin: 8px 0; padding-left: 20px;">
             <li style="margin: 4px 0; font-size: 14px;">本软件按"现状"提供，不提供任何明示或暗示的保证</li>
             <li style="margin: 4px 0; font-size: 14px;">用户使用本软件的风险由用户自行承担</li>
             <li style="margin: 4px 0; font-size: 14px;">作者不对因使用本软件而造成的任何损失承担责任</li>
             <li style="margin: 4px 0; font-size: 14px;">禁止将本软件用于任何非法用途</li>
             <li style="margin: 4px 0; font-size: 14px;">用户有权自由使用、复制和分发本软件</li>
         </ul>
         
         <h3 style="color: black; font-size: 16px; margin: 15px 0 10px 0;">隐私声明</h3>
         
         <p style="margin: 8px 0;  font-size: 14px;  color: black;">本软件不收集任何个人隐私信息。</p>
         
         <h4 style="color: black; font-size: 14px; margin: 12px 0 8px 0;">数据处理说明：</h4>
         <ul style="margin: 8px 0; padding-left: 20px;">
             <li style="margin: 4px 0; font-size: 14px;"><b>本地处理：</b>所有文件操作均在本地计算机上进行，不会上传到任何服务器</li>
             <li style="margin: 4px 0; font-size: 14px;"><b>无网络通信：</b>软件运行过程中不会主动连接互联网或发送任何数据</li>
             <li style="margin: 4px 0; font-size: 14px;"><b>无用户跟踪：</b>不收集用户的使用习惯、文件信息或个人数据</li>
             <li style="margin: 4px 0; font-size: 14px;"><b>配置文件：</b>仅在本地保存用户的界面设置和偏好配置</li>
             <li style="margin: 4px 0; font-size: 14px;"><b>文件访问：</b>仅访问用户明确选择的文件，不会扫描或访问其他文件</li>
         </ul>
         
         <p style="margin: 12px 0; font-weight: bold; font-size: 14px;">使用本软件，您可以完全放心您的个人信息不会被收集或泄露。</p>
         
         <hr style="margin: 15px 0; border: none; border-top: 1px solid #ddd;">
         <p style="text-align: center; color: black; font-size: 10px; margin: 8px 0;">
             Copyright © 2024 孤鸿泽. All rights reserved.
         </p>
         </div>
         """)
        
        layout.addWidget(license_text)
        
        self.tab_widget.addTab(tab, "ℹ️ 关于")