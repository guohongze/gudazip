#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GudaZip 卸载模块
用于完全清理程序的所有痕迹，包括环境变量、配置文件、文件关联和右键菜单
"""

import os
import sys
import shutil
from typing import Dict, List, Any
from pathlib import Path

from .environment_manager import get_environment_manager
from .file_association_manager import FileAssociationManager
from .config_manager import get_config_manager


class Uninstaller:
    """GudaZip卸载器"""
    
    def __init__(self):
        self.env_manager = get_environment_manager()
        self.file_assoc_manager = FileAssociationManager()
        self.results = {
            "environment_variables": {"success": False, "details": []},
            "file_associations": {"success": False, "details": []},
            "context_menus": {"success": False, "details": []},
            "config_files": {"success": False, "details": []},
            "install_directory": {"success": False, "details": []}
        }
    
    def uninstall_complete(self, remove_install_dir: bool = True) -> Dict[str, Any]:
        """完整卸载GudaZip"""
        print("=" * 60)
        print("开始卸载 GudaZip")
        print("=" * 60)
        
        # 1. 移除环境变量
        print("\n1. 清理环境变量...")
        self._remove_environment_variables()
        
        # 2. 取消文件关联
        print("\n2. 取消文件关联...")
        self._remove_file_associations()
        
        # 3. 移除右键菜单
        print("\n3. 移除右键菜单...")
        self._remove_context_menus()
        
        # 4. 删除配置文件
        print("\n4. 删除配置文件...")
        self._remove_config_files()
        
        # 5. 删除安装目录（可选）
        if remove_install_dir:
            print("\n5. 清理安装目录...")
            self._remove_install_directory()
        
        # 生成卸载报告
        return self._generate_uninstall_report()
    
    def _remove_environment_variables(self):
        """移除环境变量"""
        try:
            if self.env_manager.remove_environment_variables():
                self.results["environment_variables"]["success"] = True
                self.results["environment_variables"]["details"].append("✅ 环境变量清理成功")
            else:
                self.results["environment_variables"]["details"].append("❌ 环境变量清理失败")
        except Exception as e:
            self.results["environment_variables"]["details"].append(f"❌ 环境变量清理异常: {e}")
    
    def _remove_file_associations(self):
        """取消文件关联"""
        try:
            # 获取所有支持的扩展名
            extensions = self.file_assoc_manager.supported_extensions
            
            result = self.file_assoc_manager.unregister_file_association(extensions)
            
            if result["success"]:
                self.results["file_associations"]["success"] = True
                self.results["file_associations"]["details"].append(
                    f"✅ 文件关联清理成功: {result['success_count']}/{result['total_operations']} 个格式"
                )
            else:
                self.results["file_associations"]["details"].append(
                    f"❌ 文件关联清理失败: {result.get('message', '未知错误')}"
                )
            
            # 添加详细信息
            for ext, detail in result.get("details", {}).items():
                if detail["success"]:
                    self.results["file_associations"]["details"].append(f"  ✅ {ext}")
                else:
                    self.results["file_associations"]["details"].append(
                        f"  ❌ {ext}: {detail.get('error', '未知错误')}"
                    )
                    
        except Exception as e:
            self.results["file_associations"]["details"].append(f"❌ 文件关联清理异常: {e}")
    
    def _remove_context_menus(self):
        """移除右键菜单"""
        try:
            # 移除普通右键菜单
            result = self.file_assoc_manager.uninstall_context_menu()
            
            if result["success"]:
                self.results["context_menus"]["details"].append(
                    f"✅ 右键菜单清理成功: {result['success_count']} 个菜单项"
                )
            else:
                self.results["context_menus"]["details"].append(
                    f"❌ 右键菜单清理失败: {result.get('message', '未知错误')}"
                )
            
            # 清理桌面空白处菜单（如果存在）
            desktop_result = self.file_assoc_manager.clean_desktop_background_menu()
            
            if desktop_result["success"]:
                self.results["context_menus"]["details"].append(
                    f"✅ 桌面空白处菜单清理成功: {desktop_result['success_count']} 个菜单项"
                )
                self.results["context_menus"]["success"] = True
            else:
                self.results["context_menus"]["details"].append(
                    f"⚠️ 桌面空白处菜单清理: {desktop_result.get('message', '无需清理')}"
                )
                # 如果普通菜单清理成功，整体仍然算成功
                if result["success"]:
                    self.results["context_menus"]["success"] = True
                    
        except Exception as e:
            self.results["context_menus"]["details"].append(f"❌ 右键菜单清理异常: {e}")
    
    def _remove_config_files(self):
        """删除配置文件"""
        try:
            config_path = self.env_manager.get_config_path()
            config_dir = Path(config_path)
            
            if config_dir.exists():
                # 备份重要配置（可选）
                backup_created = False
                try:
                    backup_dir = config_dir.parent / f"{config_dir.name}_backup_{int(time.time())}"
                    shutil.copytree(config_dir, backup_dir)
                    backup_created = True
                    self.results["config_files"]["details"].append(f"✅ 配置文件已备份到: {backup_dir}")
                except Exception as e:
                    self.results["config_files"]["details"].append(f"⚠️ 配置文件备份失败: {e}")
                
                # 删除配置目录
                try:
                    shutil.rmtree(config_dir)
                    self.results["config_files"]["success"] = True
                    self.results["config_files"]["details"].append(f"✅ 配置文件删除成功: {config_dir}")
                except Exception as e:
                    self.results["config_files"]["details"].append(f"❌ 配置文件删除失败: {e}")
            else:
                self.results["config_files"]["success"] = True
                self.results["config_files"]["details"].append("✅ 配置文件不存在，无需删除")
                
        except Exception as e:
            self.results["config_files"]["details"].append(f"❌ 配置文件清理异常: {e}")
    
    def _remove_install_directory(self):
        """删除安装目录"""
        try:
            install_path = self.env_manager.get_install_path()
            install_dir = Path(install_path)
            
            # 检查是否是开发环境
            if not getattr(sys, 'frozen', False):
                self.results["install_directory"]["success"] = True
                self.results["install_directory"]["details"].append(
                    "✅ 开发环境，跳过安装目录删除"
                )
                return
            
            # 检查当前程序是否在安装目录中运行
            current_exe = Path(sys.executable)
            if current_exe.parent == install_dir:
                self.results["install_directory"]["details"].append(
                    "⚠️ 程序正在安装目录中运行，无法删除安装目录"
                )
                self.results["install_directory"]["details"].append(
                    "💡 请在程序退出后手动删除安装目录"
                )
                return
            
            if install_dir.exists():
                # 删除安装目录
                try:
                    shutil.rmtree(install_dir)
                    self.results["install_directory"]["success"] = True
                    self.results["install_directory"]["details"].append(f"✅ 安装目录删除成功: {install_dir}")
                except Exception as e:
                    self.results["install_directory"]["details"].append(f"❌ 安装目录删除失败: {e}")
            else:
                self.results["install_directory"]["success"] = True
                self.results["install_directory"]["details"].append("✅ 安装目录不存在，无需删除")
                
        except Exception as e:
            self.results["install_directory"]["details"].append(f"❌ 安装目录清理异常: {e}")
    
    def _generate_uninstall_report(self) -> Dict[str, Any]:
        """生成卸载报告"""
        total_success = sum(1 for result in self.results.values() if result["success"])
        total_operations = len(self.results)
        
        report = {
            "overall_success": total_success == total_operations,
            "success_count": total_success,
            "total_operations": total_operations,
            "details": self.results,
            "summary": []
        }
        
        print("\n" + "=" * 60)
        print("卸载完成报告")
        print("=" * 60)
        
        for operation, result in self.results.items():
            status_icon = "✅" if result["success"] else "❌"
            operation_name = {
                "environment_variables": "环境变量清理",
                "file_associations": "文件关联清理",
                "context_menus": "右键菜单清理",
                "config_files": "配置文件清理",
                "install_directory": "安装目录清理"
            }.get(operation, operation)
            
            print(f"\n{status_icon} {operation_name}:")
            for detail in result["details"]:
                print(f"  {detail}")
            
            report["summary"].append(f"{status_icon} {operation_name}")
        
        print(f"\n总体结果: {total_success}/{total_operations} 项操作成功")
        
        if report["overall_success"]:
            print("\n🎉 GudaZip 卸载完成！")
        else:
            print("\n⚠️ 卸载过程中遇到一些问题，请查看上述详细信息")
        
        return report
    
    def check_uninstall_status(self) -> Dict[str, Any]:
        """检查卸载状态（用于验证是否完全卸载）"""
        status = {
            "environment_variables": self._check_env_vars_status(),
            "file_associations": self._check_file_assoc_status(),
            "context_menus": self._check_context_menu_status(),
            "config_files": self._check_config_files_status(),
            "install_directory": self._check_install_dir_status()
        }
        
        # 计算总体状态
        all_clean = all(not status[key]["exists"] for key in status)
        
        return {
            "all_clean": all_clean,
            "details": status
        }
    
    def _check_env_vars_status(self) -> Dict[str, Any]:
        """检查环境变量状态"""
        env_status = self.env_manager.check_environment_variables()
        return {
            "exists": env_status["all_set"],
            "details": env_status["variables"]
        }
    
    def _check_file_assoc_status(self) -> Dict[str, Any]:
        """检查文件关联状态"""
        extensions = self.file_assoc_manager.supported_extensions
        assoc_status = self.file_assoc_manager.check_association_status(extensions)
        
        has_associations = any(assoc_status.values())
        
        return {
            "exists": has_associations,
            "details": assoc_status
        }
    
    def _check_context_menu_status(self) -> Dict[str, Any]:
        """检查右键菜单状态"""
        menu_status = self.file_assoc_manager.check_context_menu_status()
        
        has_menus = False
        for category in menu_status.values():
            for ext_menus in category.values():
                if any(ext_menus.values()):
                    has_menus = True
                    break
            if has_menus:
                break
        
        return {
            "exists": has_menus,
            "details": menu_status
        }
    
    def _check_config_files_status(self) -> Dict[str, Any]:
        """检查配置文件状态"""
        config_path = Path(self.env_manager.get_config_path())
        
        return {
            "exists": config_path.exists(),
            "path": str(config_path),
            "size": config_path.stat().st_size if config_path.exists() else 0
        }
    
    def _check_install_dir_status(self) -> Dict[str, Any]:
        """检查安装目录状态"""
        install_path = Path(self.env_manager.get_install_path())
        
        # 在开发环境中，安装目录就是项目目录，不应该被删除
        if not getattr(sys, 'frozen', False):
            return {
                "exists": False,  # 开发环境不算"存在"需要清理的安装目录
                "path": str(install_path),
                "is_dev_env": True
            }
        
        return {
            "exists": install_path.exists(),
            "path": str(install_path),
            "is_dev_env": False
        }


# 导入time模块
import time


def create_uninstaller() -> Uninstaller:
    """创建卸载器实例"""
    return Uninstaller()