# -*- coding: utf-8 -*-
"""
程序健康检查器
检查程序运行环境和依赖是否正常
"""

import os
import sys
import tempfile
import shutil
import logging
from typing import List, Dict, Tuple, Any
from pathlib import Path

from .error_manager import ErrorManager, ErrorCategory, ErrorSeverity, get_error_manager

logger = logging.getLogger(__name__)

class HealthChecker:
    """程序健康检查器"""
    
    def __init__(self, parent=None):
        """初始化健康检查器"""
        self.parent = parent
        self.error_manager = get_error_manager(parent)
        self.check_results = {}
        
    @staticmethod
    def check_all() -> Tuple[bool, List[str]]:
        """执行全面健康检查"""
        issues = []
        
        # 检查Python版本
        python_issues = HealthChecker.check_python_version()
        issues.extend(python_issues)
        
        # 检查必需的模块
        module_issues = HealthChecker.check_required_modules()
        issues.extend(module_issues)
        
        # 检查文件系统权限
        permission_issues = HealthChecker.check_filesystem_permissions()
        issues.extend(permission_issues)
        
        # 检查临时目录
        temp_issues = HealthChecker.check_temp_directory()
        issues.extend(temp_issues)
        
        # 检查资源文件
        resource_issues = HealthChecker.check_resources()
        issues.extend(resource_issues)
        
        return len(issues) == 0, issues
    
    @staticmethod
    def check_python_version() -> List[str]:
        """检查Python版本"""
        issues = []
        
        if sys.version_info < (3, 8):
            issues.append(f"Python版本过低 ({sys.version_info.major}.{sys.version_info.minor})，建议使用Python 3.8或更高版本")
        
        return issues
    
    @staticmethod
    def check_required_modules() -> List[str]:
        """检查必需的模块"""
        issues = []
        
        required_modules = [
            ('PySide6', 'PySide6'),
            ('qtawesome', 'qtawesome'),
            ('zipfile', 'zipfile'),
            ('os', 'os'),
            ('sys', 'sys'),
        ]
        
        for module_name, import_name in required_modules:
            try:
                __import__(import_name)
            except ImportError:
                issues.append(f"缺少必需模块：{module_name}")
        
        # 检查可选模块
        optional_modules = [
            ('rarfile', 'rarfile'),
            ('py7zr', 'py7zr'),
        ]
        
        missing_optional = []
        for module_name, import_name in optional_modules:
            try:
                __import__(import_name)
            except ImportError:
                missing_optional.append(module_name)
        
        if missing_optional:
            issues.append(f"缺少可选模块（功能可能受限）：{', '.join(missing_optional)}")
        
        return issues
    
    @staticmethod
    def check_filesystem_permissions() -> List[str]:
        """检查文件系统权限"""
        issues = []
        
        # 检查当前目录写权限
        try:
            current_dir = os.getcwd()
            test_file = os.path.join(current_dir, '.gudazip_test')
            
            with open(test_file, 'w') as f:
                f.write('test')
            
            os.remove(test_file)
            
        except Exception:
            issues.append("当前目录没有写权限，某些功能可能无法正常使用")
        
        return issues
    
    @staticmethod
    def check_temp_directory() -> List[str]:
        """检查临时目录"""
        issues = []
        
        try:
            temp_dir = tempfile.gettempdir()
            
            # 检查临时目录是否存在且可写
            if not os.path.exists(temp_dir):
                issues.append("系统临时目录不存在")
            elif not os.access(temp_dir, os.W_OK):
                issues.append("系统临时目录没有写权限")
            else:
                # 尝试在临时目录创建测试文件
                try:
                    test_file = os.path.join(temp_dir, 'gudazip_temp_test')
                    with open(test_file, 'w') as f:
                        f.write('test')
                    os.remove(test_file)
                except Exception:
                    issues.append("无法在临时目录创建文件")
        
        except Exception:
            issues.append("无法访问系统临时目录")
        
        return issues
    
    @staticmethod
    def check_resources() -> List[str]:
        """检查资源文件"""
        issues = []
        
        # 获取程序根目录
        try:
            current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            resources_dir = os.path.join(current_dir, 'resources')
            
            # 检查资源目录是否存在
            if not os.path.exists(resources_dir):
                issues.append("资源目录不存在，某些功能可能受影响")
            else:
                # 检查图标目录
                icons_dir = os.path.join(resources_dir, 'icons')
                if not os.path.exists(icons_dir):
                    issues.append("图标资源目录不存在，界面可能显示异常")
        
        except Exception:
            issues.append("无法检查资源文件状态")
        
        return issues
    
    @staticmethod
    def check_disk_space(min_space_mb: int = 100) -> List[str]:
        """检查磁盘空间"""
        issues = []
        
        try:
            if os.name == 'nt':  # Windows
                import shutil
                total, used, free = shutil.disk_usage(os.getcwd())
                free_mb = free // (1024 * 1024)
            else:  # Unix/Linux
                statvfs = os.statvfs(os.getcwd())
                free_mb = (statvfs.f_bavail * statvfs.f_frsize) // (1024 * 1024)
            
            if free_mb < min_space_mb:
                issues.append(f"磁盘可用空间不足 ({free_mb}MB)，建议至少保留{min_space_mb}MB")
        
        except Exception:
            issues.append("无法检查磁盘空间")
        
        return issues
    
    @staticmethod
    def generate_report() -> Dict[str, any]:
        """生成详细的健康检查报告"""
        is_healthy, issues = HealthChecker.check_all()
        
        # 获取系统信息
        system_info = {
            'platform': sys.platform,
            'python_version': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            'python_executable': sys.executable,
            'current_directory': os.getcwd(),
            'temp_directory': tempfile.gettempdir(),
        }
        
        # 检查可用模块
        available_modules = {}
        test_modules = ['PySide6', 'qtawesome', 'rarfile', 'py7zr']
        for module in test_modules:
            try:
                __import__(module)
                available_modules[module] = True
            except ImportError:
                available_modules[module] = False
        
        return {
            'is_healthy': is_healthy,
            'issues': issues,
            'system_info': system_info,
            'available_modules': available_modules,
            'timestamp': __import__('datetime').datetime.now().isoformat()
        }

    def check_dependencies(self) -> Tuple[bool, str]:
        """检查依赖库"""
        try:
            missing_deps = []
            
            # 检查Qt相关库
            try:
                import PySide6
                import PySide6.QtWidgets
                import PySide6.QtCore
                import PySide6.QtGui
            except ImportError as e:
                missing_deps.append(f"PySide6: {str(e)}")
                self.error_manager.handle_error(
                    ErrorCategory.APP_DEPENDENCY,
                    ErrorSeverity.CRITICAL,
                    "PySide6依赖缺失",
                    details=str(e),
                    show_dialog=False
                )
            
            # 检查其他必要依赖
            optional_deps = [
                ("qtawesome", "图标库"),
                ("Pillow", "图像处理"),
                ("win32com.client", "Windows系统集成"),
                ("py7zr", "7Z压缩包支持"),
                ("rarfile", "RAR压缩包支持")
            ]
            
            for dep_name, description in optional_deps:
                try:
                    __import__(dep_name)
                except ImportError:
                    # 对于可选依赖，只记录警告
                    self.error_manager.handle_error(
                        ErrorCategory.APP_DEPENDENCY,
                        ErrorSeverity.WARNING,
                        f"可选依赖缺失: {description}",
                        details=f"模块 {dep_name} 未安装，某些功能可能不可用",
                        show_dialog=False
                    )
            
            if missing_deps:
                return False, f"缺少必要依赖: {', '.join(missing_deps)}"
            
            return True, "所有依赖项检查通过"
            
        except Exception as e:
            self.error_manager.handle_exception(
                e,
                context={"operation": "check_dependencies"},
                category=ErrorCategory.APP_DEPENDENCY,
                show_dialog=False
            )
            return False, f"依赖检查失败: {str(e)}"

    def check_file_permissions(self) -> Tuple[bool, str]:
        """检查文件权限"""
        try:
            # 获取用户目录
            user_dir = Path.home()
            temp_dir = Path.cwd()
            
            # 测试读写权限
            test_locations = [
                (user_dir, "用户目录"),
                (temp_dir, "当前目录"),
            ]
            
            permission_issues = []
            
            for location, desc in test_locations:
                try:
                    # 测试写入权限
                    test_file = location / "gudazip_test.tmp"
                    test_file.write_text("test")
                    test_file.unlink()
                except Exception as e:
                    issue = f"{desc}写入权限不足: {str(e)}"
                    permission_issues.append(issue)
                    self.error_manager.handle_error(
                        ErrorCategory.FILE_PERMISSION,
                        ErrorSeverity.WARNING,
                        f"{desc}权限检查失败",
                        details=str(e),
                        show_dialog=False
                    )
            
            if permission_issues:
                return False, "权限检查发现问题: " + "; ".join(permission_issues)
            
            return True, "文件权限检查通过"
            
        except Exception as e:
            self.error_manager.handle_exception(
                e,
                context={"operation": "check_file_permissions"},
                category=ErrorCategory.FILE_PERMISSION,
                show_dialog=False
            )
            return False, f"权限检查失败: {str(e)}"

    def check_system_resources(self) -> Tuple[bool, str]:
        """检查系统资源"""
        try:
            import psutil
            
            # 检查内存使用情况
            memory = psutil.virtual_memory()
            if memory.percent > 90:
                self.error_manager.handle_error(
                    ErrorCategory.SYSTEM_RESOURCE,
                    ErrorSeverity.WARNING,
                    "系统内存使用率过高",
                    details=f"内存使用率: {memory.percent}%",
                    show_dialog=False
                )
                return False, f"内存使用率过高: {memory.percent}%"
            
            # 检查磁盘空间
            disk = psutil.disk_usage('/')
            if disk.percent > 95:
                self.error_manager.handle_error(
                    ErrorCategory.SYSTEM_RESOURCE,
                    ErrorSeverity.WARNING,
                    "磁盘空间不足",
                    details=f"磁盘使用率: {disk.percent}%",
                    show_dialog=False
                )
                return False, f"磁盘空间不足: {disk.percent}%"
            
            return True, "系统资源检查通过"
            
        except ImportError:
            # psutil未安装，跳过系统资源检查
            return True, "系统资源检查跳过（psutil未安装）"
        except Exception as e:
            self.error_manager.handle_exception(
                e,
                context={"operation": "check_system_resources"},
                category=ErrorCategory.SYSTEM_RESOURCE,
                show_dialog=False
            )
            return True, f"系统资源检查出现问题但继续: {str(e)}" 