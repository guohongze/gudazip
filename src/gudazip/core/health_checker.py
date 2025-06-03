# -*- coding: utf-8 -*-
"""
程序健康检查器
检查程序运行环境和依赖是否正常
"""

import os
import sys
import tempfile
import shutil
from typing import List, Dict, Tuple


class HealthChecker:
    """程序健康检查器"""
    
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