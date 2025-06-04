# -*- coding: utf-8 -*-
"""
上下文菜单管理器
独立的右键菜单管理组件，负责所有右键菜单的创建和处理逻辑
"""

from PySide6.QtCore import QObject, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu
import qtawesome as qta
import os


class ContextMenuManager(QObject):
    """上下文菜单管理器 - 负责所有右键菜单逻辑"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_widget = parent  # FileBrowser实例
        
    def show_context_menu(self, index, global_position):
        """显示上下文菜单的主入口"""
        print(f"🔧 右键菜单触发 - 位置: {global_position}, 索引有效: {index.isValid()}")
        
        menu = QMenu(self.parent_widget)
        
        if self.parent_widget.archive_viewing_mode:
            # 压缩包查看模式下的专用右键菜单
            self._show_archive_context_menu(index, menu)
        else:
            # 普通文件系统模式下的右键菜单
            self._show_filesystem_context_menu(index, menu)
        
        print(f"📋 菜单项数量: {len(menu.actions())}")
        if menu.actions():  # 只有在有菜单项时才显示
            print("🎯 显示菜单...")
            menu.exec(global_position)
        else:
            print("❌ 没有菜单项，不显示菜单")
    
    def _show_archive_context_menu(self, index, menu):
        """显示压缩包模式的上下文菜单"""
        parent = self.parent_widget
        
        if index.isValid():
            # 压缩包内文件/文件夹的右键菜单
            item_type = index.data(Qt.UserRole)
            file_path = index.data(Qt.UserRole + 1)
            item_name = index.data(Qt.DisplayRole)
            
            if item_type == 'file':
                # 文件右键菜单
                open_action = QAction("打开", parent)
                open_action.setIcon(qta.icon('fa5s.file', color='#2196f3'))
                open_action.triggered.connect(lambda: parent.open_archive_file(file_path))
                menu.addAction(open_action)
                
                menu.addSeparator()
                
                # 复制
                copy_action = QAction("复制", parent)
                copy_action.setIcon(qta.icon('fa5s.copy', color='#2196f3'))
                copy_action.triggered.connect(lambda: parent.copy_archive_items([file_path]))
                menu.addAction(copy_action)
                
                # 重命名
                rename_action = QAction("重命名", parent)
                rename_action.setIcon(qta.icon('fa5s.edit', color='#ff9800'))
                rename_action.triggered.connect(lambda: parent.rename_archive_file(file_path, item_name))
                menu.addAction(rename_action)
                
                # 删除
                delete_action = QAction("删除", parent)
                delete_action.setIcon(qta.icon('fa5s.trash', color='#f44336'))
                delete_action.triggered.connect(lambda: parent.delete_archive_file(file_path))
                menu.addAction(delete_action)
                
                menu.addSeparator()
                
                # 解压到临时目录
                extract_action = QAction("解压到临时目录", parent)
                extract_action.setIcon(qta.icon('fa5s.download', color='#4caf50'))
                extract_action.triggered.connect(lambda: parent.extract_archive_file(file_path))
                menu.addAction(extract_action)
                
                # 打开当前文件夹
                open_folder_action = QAction("打开当前文件夹", parent)
                open_folder_action.setIcon(qta.icon('fa5s.external-link-alt', color='#2196f3'))
                open_folder_action.triggered.connect(parent.open_archive_folder_in_explorer)
                menu.addAction(open_folder_action)
                
            elif item_type == 'folder':
                # 文件夹右键菜单
                open_action = QAction("打开", parent)
                open_action.setIcon(qta.icon('fa5s.folder-open', color='#f57c00'))
                open_action.triggered.connect(lambda: parent.navigate_archive_directory(file_path))
                menu.addAction(open_action)
                
                menu.addSeparator()
                
                # 复制
                copy_action = QAction("复制", parent)
                copy_action.setIcon(qta.icon('fa5s.copy', color='#2196f3'))
                copy_action.triggered.connect(lambda: parent.copy_archive_items([file_path]))
                menu.addAction(copy_action)
                
                # 重命名
                rename_action = QAction("重命名", parent)
                rename_action.setIcon(qta.icon('fa5s.edit', color='#ff9800'))
                rename_action.triggered.connect(lambda: parent.rename_archive_file(file_path, item_name))
                menu.addAction(rename_action)
                
                # 删除
                delete_action = QAction("删除", parent)
                delete_action.setIcon(qta.icon('fa5s.trash', color='#f44336'))
                delete_action.triggered.connect(lambda: parent.delete_archive_file(file_path))
                menu.addAction(delete_action)
                
                menu.addSeparator()
                
                # 新建文件夹
                new_folder_action = QAction("新建文件夹", parent)
                new_folder_action.setIcon(qta.icon('fa5s.folder', color='#4caf50'))
                new_folder_action.triggered.connect(lambda: parent.create_archive_folder(file_path))
                menu.addAction(new_folder_action)
                
                # 打开当前文件夹
                open_folder_action = QAction("打开当前文件夹", parent)
                open_folder_action.setIcon(qta.icon('fa5s.external-link-alt', color='#2196f3'))
                open_folder_action.triggered.connect(parent.open_archive_folder_in_explorer)
                menu.addAction(open_folder_action)
        else:
            # 压缩包内空白处右键菜单
            # 粘贴（如果有剪贴板内容）
            if hasattr(parent, 'archive_clipboard_items') and parent.archive_clipboard_items:
                paste_action = QAction("粘贴", parent)
                paste_action.setIcon(qta.icon('fa5s.paste', color='#4caf50'))
                paste_action.triggered.connect(parent.paste_to_archive)
                menu.addAction(paste_action)
                menu.addSeparator()
            
            # 如果有系统剪贴板文件，可以粘贴到压缩包
            if parent.clipboard_items:
                paste_files_action = QAction("粘贴文件到压缩包", parent)
                paste_files_action.setIcon(qta.icon('fa5s.file-import', color='#4caf50'))
                paste_files_action.triggered.connect(parent.paste_files_to_archive)
                menu.addAction(paste_files_action)
                menu.addSeparator()
            
            # 创建文件夹
            new_folder_action = QAction("新建文件夹", parent)
            new_folder_action.setIcon(qta.icon('fa5s.folder', color='#4caf50'))
            new_folder_action.triggered.connect(lambda: parent.create_archive_folder())
            menu.addAction(new_folder_action)
            
            # 打开当前文件夹
            open_folder_action = QAction("打开当前文件夹", parent)
            open_folder_action.setIcon(qta.icon('fa5s.external-link-alt', color='#2196f3'))
            open_folder_action.triggered.connect(parent.open_archive_folder_in_explorer)
            menu.addAction(open_folder_action)
            
            menu.addSeparator()
            
            # 返回上级目录或退出压缩包
            if parent.archive_current_dir:
                up_action = QAction("返回上级目录", parent)
                up_action.setIcon(qta.icon('fa5s.arrow-up', color='#2196f3'))
                up_action.triggered.connect(parent.go_up_directory)
                menu.addAction(up_action)
            
            exit_action = QAction("退出压缩包查看", parent)
            exit_action.setIcon(qta.icon('fa5s.times', color='#f44336'))
            exit_action.triggered.connect(parent._exit_archive_mode)
            menu.addAction(exit_action)

    def _show_filesystem_context_menu(self, index, menu):
        """显示文件系统模式的上下文菜单"""
        parent = self.parent_widget
        
        # 获取当前所有选中的文件路径
        selected_paths = parent.get_selected_paths()
        print(f"📂 已选中路径: {selected_paths}")
        
        if index.isValid():
            file_path = parent.file_model.filePath(index)
            is_dir = parent.file_model.isDir(index)
            print(f"📁 右键文件: {file_path}, 是文件夹: {is_dir}")
            
            # 如果右键的文件不在选中列表中，则只操作右键的文件
            if file_path not in selected_paths:
                selected_paths = [file_path]
                print(f"📝 更新选中列表为右键文件: {selected_paths}")
            
            # 判断选中项目的类型
            is_multiple = len(selected_paths) > 1
            has_folders = any(os.path.isdir(path) for path in selected_paths)
            has_files = any(os.path.isfile(path) for path in selected_paths)
            
            # 打开菜单项（只在单选时显示）
            if not is_multiple:
                if is_dir:
                    open_action = QAction("打开", parent)
                    open_action.setIcon(qta.icon('fa5s.folder-open', color='#f57c00'))
                    open_action.triggered.connect(lambda: parent.open_folder(file_path))
                else:
                    open_action = QAction("打开", parent)
                    open_action.setIcon(qta.icon('fa5s.file', color='#2196f3'))
                    open_action.triggered.connect(lambda: parent.open_file(file_path))
                menu.addAction(open_action)
                menu.addSeparator()
            
            # 剪切、复制菜单项（支持多选）
            cut_action = QAction("剪切", parent)
            cut_action.setIcon(qta.icon('fa5s.cut', color='#ff9800'))
            copy_action = QAction("复制", parent)
            copy_action.setIcon(qta.icon('fa5s.copy', color='#2196f3'))
                
            cut_action.triggered.connect(lambda: parent.cut_items(selected_paths))
            copy_action.triggered.connect(lambda: parent.copy_items(selected_paths))
            menu.addAction(cut_action)
            menu.addAction(copy_action)
            
            # 粘贴菜单项（只在单选文件夹时显示）
            if not is_multiple and is_dir and parent.clipboard_items:
                paste_action = QAction("粘贴", parent)
                paste_action.setIcon(qta.icon('fa5s.paste', color='#4caf50'))
                paste_action.triggered.connect(lambda: parent.paste_items(file_path))
                menu.addAction(paste_action)
            
            menu.addSeparator()
            
            # 重命名菜单项（只在单选时显示）
            if not is_multiple:
                rename_action = QAction("重命名", parent)
                rename_action.setIcon(qta.icon('fa5s.edit', color='#ff9800'))
                rename_action.triggered.connect(lambda: parent.rename_file(file_path))
                menu.addAction(rename_action)
            
            # 删除菜单项（支持多选）
            delete_action = QAction("删除", parent)
            delete_action.setIcon(qta.icon('fa5s.trash', color='#f44336'))
            delete_action.triggered.connect(lambda: parent.delete_files(selected_paths))
            menu.addAction(delete_action)
            
            # 只在单选文件夹时显示新建选项
            if not is_multiple and is_dir:
                menu.addSeparator()
                new_folder_action = QAction("新建文件夹", parent)
                new_folder_action.setIcon(qta.icon('fa5s.folder', color='#4caf50'))
                new_folder_action.triggered.connect(lambda: parent.create_folder(file_path))
                menu.addAction(new_folder_action)
                
                new_file_action = QAction("新建文件", parent)
                new_file_action.setIcon(qta.icon('fa5s.file-alt', color='#4caf50'))
                new_file_action.triggered.connect(lambda: parent.create_file(file_path))
                menu.addAction(new_file_action)
            
            # 刷新选项
            refresh_action = QAction("刷新", parent)
            refresh_action.setIcon(qta.icon('fa5s.sync-alt', color='#2196f3'))
            refresh_action.triggered.connect(parent.refresh_view)
            menu.addAction(refresh_action)
            
        else:
            # 在空白处右键，在当前目录操作
            current_dir = parent.get_current_root_path()
            print(f"📂 空白处右键，当前目录: {current_dir}")
            if current_dir and os.path.exists(current_dir):
                # 粘贴选项
                if parent.clipboard_items:
                    paste_action = QAction("粘贴", parent)
                    paste_action.setIcon(qta.icon('fa5s.paste', color='#4caf50'))
                    paste_action.triggered.connect(lambda: parent.paste_items(current_dir))
                    menu.addAction(paste_action)
                    menu.addSeparator()
                
                # 新建选项
                new_folder_action = QAction("新建文件夹", parent)
                new_folder_action.setIcon(qta.icon('fa5s.folder', color='#4caf50'))
                new_folder_action.triggered.connect(lambda: parent.create_folder(current_dir))
                menu.addAction(new_folder_action)
                
                new_file_action = QAction("新建文件", parent)
                new_file_action.setIcon(qta.icon('fa5s.file-alt', color='#4caf50'))
                new_file_action.triggered.connect(lambda: parent.create_file(current_dir))
                menu.addAction(new_file_action)
                
                menu.addSeparator()
                
                # 在资源管理器中打开当前目录
                open_explorer_action = QAction("在资源管理器中打开", parent)
                open_explorer_action.setIcon(qta.icon('fa5s.external-link-alt', color='#2196f3'))
                open_explorer_action.triggered.connect(lambda: parent.open_in_explorer(current_dir))
                menu.addAction(open_explorer_action)
                
                # 刷新选项
                refresh_action = QAction("刷新", parent)
                refresh_action.setIcon(qta.icon('fa5s.sync-alt', color='#2196f3'))
                refresh_action.triggered.connect(parent.refresh_view)
                menu.addAction(refresh_action) 