#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GudaZip cx-freeze 打包脚本
生成MSI安装包，支持用户选择安装路径和文件关联
"""

import sys
import os
from pathlib import Path
from cx_Freeze import setup, Executable

# 项目信息
APP_NAME = "GudaZip"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "Python桌面压缩管理器"
APP_AUTHOR = "GudaZip Team"
APP_COPYRIGHT = "Copyright © 2024 GudaZip Team"

# cx-freeze构建选项
build_exe_options = {
    "build_exe": "build/exe",
    "include_files": [
        ("resources/", "resources/"),
        ("src/gudazip/", "gudazip/")
    ],
    "packages": [
        # GUI框架
        "PySide6",
        # 图标库
        "qtawesome",
        # 压缩格式支持
        "rarfile",
        "py7zr",
        # 图像处理
        "PIL"
    ],
    "excludes": ["tkinter", "unittest", "email", "xml"]
}

# MSI构建选项
bdist_msi_options = {
    "upgrade_code": "{12345678-1234-5678-9ABC-123456789012}",  # 固定的升级代码
    "add_to_path": False,
    "initial_target_dir": r"[ProgramFilesFolder]\GudaZip",
    "install_icon": "resources/icons/app.ico",
    "summary_data": {
        "author": APP_AUTHOR,
        "comments": APP_DESCRIPTION,
        "keywords": "压缩;解压;归档;zip;rar;7z"
    },
    "target_name": f"GudaZip-{APP_VERSION}-Setup.msi"
}

# 可执行文件配置
executables = [
    Executable(
        "main.py",
        base="Win32GUI" if sys.platform == "win32" else None,
        target_name="GudaZip.exe",
        icon="resources/icons/app.ico",
        shortcut_name="GudaZip",
        shortcut_dir="DesktopFolder",  # 在桌面创建快捷方式
        copyright=APP_COPYRIGHT
    )
]


def create_custom_msi_script():
    """创建自定义MSI安装脚本"""
    script_content = '''
<?xml version="1.0" encoding="UTF-8"?>
<Wix xmlns="http://schemas.microsoft.com/wix/2006/wi">
  <Product Id="*" 
           Name="GudaZip" 
           Language="2052" 
           Version="1.0.0" 
           Manufacturer="GudaZip Team" 
           UpgradeCode="{12345678-1234-5678-9ABC-123456789012}">
    
    <Package InstallerVersion="200" Compressed="yes" InstallScope="perUser" />
    
    <!-- 升级规则 -->
    <MajorUpgrade DowngradeErrorMessage="已安装更新版本的 [ProductName]。" />
    
    <!-- 媒体定义 -->
    <MediaTemplate EmbedCab="yes" />
    
    <!-- 功能定义 -->
    <Feature Id="ProductFeature" Title="GudaZip" Level="1">
      <ComponentGroupRef Id="ProductComponents" />
      <ComponentRef Id="ContextMenus" />
      <ComponentRef Id="EnvironmentVariables" />
      <ComponentRef Id="UninstallComponent" />
    </Feature>
    
    <!-- 文件关联功能（用户可选，默认启用） -->
    <Feature Id="FileAssociationFeature" Title="文件关联" Description="将压缩文件格式关联到 GudaZip（推荐）" Level="1" Display="expand">
      <Condition Level="1">SET_AS_DEFAULT="1"</Condition>
      <Condition Level="0">SET_AS_DEFAULT&lt;&gt;"1"</Condition>
      <ComponentRef Id="BasicFormats" />
      <ComponentRef Id="TarFormats" />
      <ComponentRef Id="CompressionFormats" />
      <ComponentRef Id="OtherFormats" />
    </Feature>
    
    <!-- 目录结构 -->
    <Directory Id="TARGETDIR" Name="SourceDir">
      <Directory Id="LocalAppDataFolder">
        <Directory Id="INSTALLFOLDER" Name="GudaZip" />
      </Directory>
      <Directory Id="ProgramMenuFolder">
        <Directory Id="ApplicationProgramsFolder" Name="GudaZip" />
      </Directory>
      <Directory Id="DesktopFolder" Name="Desktop" />
    </Directory>
    
    <!-- 环境变量组件 -->
    <Component Id="EnvironmentVariables" Directory="INSTALLFOLDER" Guid="{87654321-4321-8765-CBA9-876543210987}">
      <Environment Id="GudaZipInstallPath" 
                   Name="GUDAZIP_INSTALL_PATH" 
                   Value="[INSTALLFOLDER]" 
                   Permanent="no" 
                   Part="all" 
                   Action="set" 
                   System="no" />
      <Environment Id="GudaZipResourcesPath" 
                   Name="GUDAZIP_RESOURCES_PATH" 
                   Value="[INSTALLFOLDER]resources" 
                   Permanent="no" 
                   Part="all" 
                   Action="set" 
                   System="no" />
      <Environment Id="GudaZipIconsPath" 
                   Name="GUDAZIP_ICONS_PATH" 
                   Value="[INSTALLFOLDER]resources\\icons" 
                   Permanent="no" 
                   Part="all" 
                   Action="set" 
                   System="no" />
    </Component>
    
    <!-- 基础格式文件关联组件 -->
    <Component Id="BasicFormats" Directory="INSTALLFOLDER" Guid="{11111111-2222-3333-4444-555555555555}">
      <RegistryValue Root="HKCU" Key="Software\\Classes\\.zip" Value="GudaZip.Archive" Type="string" />
      <RegistryValue Root="HKCU" Key="Software\\Classes\\.rar" Value="GudaZip.Archive" Type="string" />
      <RegistryValue Root="HKCU" Key="Software\\Classes\\.7z" Value="GudaZip.Archive" Type="string" />
      <RegistryValue Root="HKCU" Key="Software\\Classes\\GudaZip.Archive" Value="GudaZip压缩文件" Type="string" />
      <RegistryValue Root="HKCU" Key="Software\\Classes\\GudaZip.Archive\\DefaultIcon" Value="[INSTALLFOLDER]resources\\icons\\app.ico" Type="string" />
      <RegistryValue Root="HKCU" Key="Software\\Classes\\GudaZip.Archive\\shell\\open\\command" Value='"[INSTALLFOLDER]GudaZip.exe" "%1"' Type="string" KeyPath="yes" />
    </Component>
    
    <!-- TAR系列格式文件关联组件 -->
    <Component Id="TarFormats" Directory="INSTALLFOLDER" Guid="{11111111-2222-3333-4444-555555555556}">
      <RegistryValue Root="HKCU" Key="Software\\Classes\\.tar" Value="GudaZip.Archive" Type="string" />
      <RegistryValue Root="HKCU" Key="Software\\Classes\\.tgz" Value="GudaZip.Archive" Type="string" />
      <RegistryValue Root="HKCU" Key="Software\\Classes\\.tar.gz" Value="GudaZip.Archive" Type="string" />
      <RegistryValue Root="HKCU" Key="Software\\Classes\\.tbz" Value="GudaZip.Archive" Type="string" />
      <RegistryValue Root="HKCU" Key="Software\\Classes\\.tbz2" Value="GudaZip.Archive" Type="string" />
      <RegistryValue Root="HKCU" Key="Software\\Classes\\.tar.bz2" Value="GudaZip.Archive" Type="string" />
      <RegistryValue Root="HKCU" Key="Software\\Classes\\.txz" Value="GudaZip.Archive" Type="string" />
      <RegistryValue Root="HKCU" Key="Software\\Classes\\.tar.xz" Value="GudaZip.Archive" Type="string" />
      <RegistryValue Root="HKCU" Key="Software\\Classes\\.taz" Value="GudaZip.Archive" Type="string" KeyPath="yes" />
    </Component>
    
    <!-- 压缩格式文件关联组件 -->
    <Component Id="CompressionFormats" Directory="INSTALLFOLDER" Guid="{11111111-2222-3333-4444-555555555557}">
      <RegistryValue Root="HKCU" Key="Software\\Classes\\.gz" Value="GudaZip.Archive" Type="string" />
      <RegistryValue Root="HKCU" Key="Software\\Classes\\.gzip" Value="GudaZip.Archive" Type="string" />
      <RegistryValue Root="HKCU" Key="Software\\Classes\\.bz2" Value="GudaZip.Archive" Type="string" />
      <RegistryValue Root="HKCU" Key="Software\\Classes\\.bzip2" Value="GudaZip.Archive" Type="string" />
      <RegistryValue Root="HKCU" Key="Software\\Classes\\.xz" Value="GudaZip.Archive" Type="string" />
      <RegistryValue Root="HKCU" Key="Software\\Classes\\.lzma" Value="GudaZip.Archive" Type="string" />
      <RegistryValue Root="HKCU" Key="Software\\Classes\\.z" Value="GudaZip.Archive" Type="string" KeyPath="yes" />
    </Component>
    
    <!-- 其他格式文件关联组件 -->
    <Component Id="OtherFormats" Directory="INSTALLFOLDER" Guid="{11111111-2222-3333-4444-555555555558}">
      <RegistryValue Root="HKCU" Key="Software\\Classes\\.cab" Value="GudaZip.Archive" Type="string" />
      <RegistryValue Root="HKCU" Key="Software\\Classes\\.arj" Value="GudaZip.Archive" Type="string" />
      <RegistryValue Root="HKCU" Key="Software\\Classes\\.lzh" Value="GudaZip.Archive" Type="string" />
      <RegistryValue Root="HKCU" Key="Software\\Classes\\.cpio" Value="GudaZip.Archive" Type="string" />
      <RegistryValue Root="HKCU" Key="Software\\Classes\\.iso" Value="GudaZip.Archive" Type="string" KeyPath="yes" />
    </Component>
    
    <!-- 右键菜单组件 -->
    <Component Id="ContextMenus" Directory="INSTALLFOLDER" Guid="{22222222-3333-4444-5555-666666666666}">
      <RegistryValue Root="HKCU" Key="Software\\Classes\\*\\shell\\GudaZip.Compress" Value="使用 GudaZip 压缩" Type="string" />
      <RegistryValue Root="HKCU" Key="Software\\Classes\\*\\shell\\GudaZip.Compress\\command" Value='"[INSTALLFOLDER]GudaZip.exe" --add "%1"' Type="string" />
      <RegistryValue Root="HKCU" Key="Software\\Classes\\Directory\\shell\\GudaZip.Compress" Value="使用 GudaZip 压缩" Type="string" />
      <RegistryValue Root="HKCU" Key="Software\\Classes\\Directory\\shell\\GudaZip.Compress\\command" Value='"[INSTALLFOLDER]GudaZip.exe" --add "%1"' Type="string" KeyPath="yes" />
    </Component>
    
    <!-- 卸载组件 -->
    <Component Id="UninstallComponent" Directory="INSTALLFOLDER" Guid="{99999999-8888-7777-6666-555555555555}">
      <!-- 卸载时清理环境变量 -->
      <Environment Id="RemoveGudaZipInstallPath" Name="GUDAZIP_INSTALL_PATH" Action="remove" System="no" />
      <Environment Id="RemoveGudaZipResourcesPath" Name="GUDAZIP_RESOURCES_PATH" Action="remove" System="no" />
      <Environment Id="RemoveGudaZipIconsPath" Name="GUDAZIP_ICONS_PATH" Action="remove" System="no" />
      
      <!-- 卸载时清理注册表 -->
      <!-- 基础格式 -->
      <RemoveRegistryKey Root="HKCU" Key="Software\\Classes\\.zip" Action="removeOnUninstall" />
      <RemoveRegistryKey Root="HKCU" Key="Software\\Classes\\.rar" Action="removeOnUninstall" />
      <RemoveRegistryKey Root="HKCU" Key="Software\\Classes\\.7z" Action="removeOnUninstall" />
      <!-- TAR系列格式 -->
      <RemoveRegistryKey Root="HKCU" Key="Software\\Classes\\.tar" Action="removeOnUninstall" />
      <RemoveRegistryKey Root="HKCU" Key="Software\\Classes\\.tgz" Action="removeOnUninstall" />
      <RemoveRegistryKey Root="HKCU" Key="Software\\Classes\\.tar.gz" Action="removeOnUninstall" />
      <RemoveRegistryKey Root="HKCU" Key="Software\\Classes\\.tbz" Action="removeOnUninstall" />
      <RemoveRegistryKey Root="HKCU" Key="Software\\Classes\\.tbz2" Action="removeOnUninstall" />
      <RemoveRegistryKey Root="HKCU" Key="Software\\Classes\\.tar.bz2" Action="removeOnUninstall" />
      <RemoveRegistryKey Root="HKCU" Key="Software\\Classes\\.txz" Action="removeOnUninstall" />
      <RemoveRegistryKey Root="HKCU" Key="Software\\Classes\\.tar.xz" Action="removeOnUninstall" />
      <RemoveRegistryKey Root="HKCU" Key="Software\\Classes\\.taz" Action="removeOnUninstall" />
      <!-- 压缩格式 -->
      <RemoveRegistryKey Root="HKCU" Key="Software\\Classes\\.gz" Action="removeOnUninstall" />
      <RemoveRegistryKey Root="HKCU" Key="Software\\Classes\\.gzip" Action="removeOnUninstall" />
      <RemoveRegistryKey Root="HKCU" Key="Software\\Classes\\.bz2" Action="removeOnUninstall" />
      <RemoveRegistryKey Root="HKCU" Key="Software\\Classes\\.bzip2" Action="removeOnUninstall" />
      <RemoveRegistryKey Root="HKCU" Key="Software\\Classes\\.xz" Action="removeOnUninstall" />
      <RemoveRegistryKey Root="HKCU" Key="Software\\Classes\\.lzma" Action="removeOnUninstall" />
      <RemoveRegistryKey Root="HKCU" Key="Software\\Classes\\.z" Action="removeOnUninstall" />
      <!-- 其他格式 -->
      <RemoveRegistryKey Root="HKCU" Key="Software\\Classes\\.cab" Action="removeOnUninstall" />
      <RemoveRegistryKey Root="HKCU" Key="Software\\Classes\\.arj" Action="removeOnUninstall" />
      <RemoveRegistryKey Root="HKCU" Key="Software\\Classes\\.lzh" Action="removeOnUninstall" />
      <RemoveRegistryKey Root="HKCU" Key="Software\\Classes\\.cpio" Action="removeOnUninstall" />
      <RemoveRegistryKey Root="HKCU" Key="Software\\Classes\\.iso" Action="removeOnUninstall" />
      <!-- 通用清理 -->
      <RemoveRegistryKey Root="HKCU" Key="Software\\Classes\\GudaZip.Archive" Action="removeOnUninstall" />
      <RemoveRegistryKey Root="HKCU" Key="Software\\Classes\\*\\shell\\GudaZip.Compress" Action="removeOnUninstall" />
      <RemoveRegistryKey Root="HKCU" Key="Software\\Classes\\Directory\\shell\\GudaZip.Compress" Action="removeOnUninstall" />
      <RemoveRegistryKey Root="HKCU" Key="Software\\GudaZip" Action="removeOnUninstall" />
      
      <!-- 卸载时清理文件和文件夹 -->
      <RemoveFile Id="RemoveConfigFiles" Directory="INSTALLFOLDER" Name="*" On="uninstall" />
      <RemoveFolder Id="RemoveInstallFolder" Directory="INSTALLFOLDER" On="uninstall" />
      
      <RegistryValue Root="HKCU" Key="Software\\GudaZip" Name="uninstall" Type="integer" Value="1" KeyPath="yes" />
    </Component>
    
    <!-- 快捷方式 -->
    <Component Id="ApplicationShortcut" Directory="ApplicationProgramsFolder" Guid="{33333333-4444-5555-6666-777777777777}">
      <Shortcut Id="ApplicationStartMenuShortcut"
                Name="GudaZip"
                Description="Python桌面压缩管理器"
                Target="[INSTALLFOLDER]GudaZip.exe"
                WorkingDirectory="INSTALLFOLDER" />
      <RemoveFolder Id="ApplicationProgramsFolder" On="uninstall" />
      <RegistryValue Root="HKCU" Key="Software\\GudaZip" Name="installed" Type="integer" Value="1" KeyPath="yes" />
    </Component>
    
    <Component Id="DesktopShortcut" Directory="DesktopFolder" Guid="{44444444-5555-6666-7777-888888888888}">
      <Shortcut Id="ApplicationDesktopShortcut"
                Name="GudaZip"
                Description="Python桌面压缩管理器"
                Target="[INSTALLFOLDER]GudaZip.exe"
                WorkingDirectory="INSTALLFOLDER" />
      <RegistryValue Root="HKCU" Key="Software\\GudaZip" Name="desktop_shortcut" Type="integer" Value="1" KeyPath="yes" />
    </Component>
    
    <!-- 组件组 -->
    <ComponentGroup Id="ProductComponents" Directory="INSTALLFOLDER">
      <ComponentRef Id="ApplicationShortcut" />
      <ComponentRef Id="DesktopShortcut" />
    </ComponentGroup>
    
    <!-- 安装UI -->
    <UI>
      <UIRef Id="WixUI_FeatureTree" />
      
      <!-- 自定义文件关联选择对话框 -->
      <Dialog Id="FileAssociationDlg" Width="370" Height="270" Title="文件关联设置">
        <Control Id="Title" Type="Text" X="15" Y="6" Width="200" Height="15" Transparent="yes" NoPrefix="yes" Text="选择要关联的文件类型" />
        <Control Id="Description" Type="Text" X="25" Y="23" Width="280" Height="15" Transparent="yes" NoPrefix="yes" Text="GudaZip 可以关联以下压缩文件格式，使其默认用 GudaZip 打开：" />
        
        <Control Id="SetAsDefaultCheck" Type="CheckBox" X="25" Y="50" Width="280" Height="17" Property="SET_AS_DEFAULT" CheckBoxValue="1" Text="设置 GudaZip 为默认压缩程序（推荐）" />
        
        <Control Id="SupportedFormatsText" Type="Text" X="25" Y="75" Width="280" Height="60" Transparent="yes" NoPrefix="yes" Text="支持的格式包括：&#xD;&#xA;• 基础格式：ZIP, RAR, 7Z&#xD;&#xA;• TAR系列：TAR, TGZ, TBZ, TXZ 等&#xD;&#xA;• 压缩格式：GZ, BZ2, XZ, LZMA 等&#xD;&#xA;• 其他格式：CAB, ARJ, LZH, CPIO, ISO" />
        
        <Control Id="WarningText" Type="Text" X="25" Y="145" Width="280" Height="30" Transparent="yes" NoPrefix="yes" Text="注意：如果取消勾选，您仍可以在安装后通过程序设置手动关联文件类型。" />
        
        <Control Id="Back" Type="PushButton" X="180" Y="243" Width="56" Height="17" Text="上一步" />
        <Control Id="Next" Type="PushButton" X="236" Y="243" Width="56" Height="17" Default="yes" Text="下一步" />
        <Control Id="Cancel" Type="PushButton" X="304" Y="243" Width="56" Height="17" Cancel="yes" Text="取消" />
      </Dialog>
      
      <!-- 对话框导航 -->
      <Publish Dialog="LicenseAgreementDlg" Control="Next" Event="NewDialog" Value="FileAssociationDlg">LicenseAccepted = "1"</Publish>
      <Publish Dialog="FileAssociationDlg" Control="Back" Event="NewDialog" Value="LicenseAgreementDlg">1</Publish>
      <Publish Dialog="FileAssociationDlg" Control="Next" Event="NewDialog" Value="CustomizeDlg">1</Publish>
      <Publish Dialog="CustomizeDlg" Control="Back" Event="NewDialog" Value="FileAssociationDlg">1</Publish>
    </UI>
    
    <!-- 属性定义 -->
    <Property Id="SET_AS_DEFAULT" Value="1" />
    <Property Id="WIXUI_INSTALLDIR" Value="INSTALLFOLDER" />
    
    <!-- 许可协议 -->
    <WixVariable Id="WixUILicenseRtf" Value="license.rtf" />
    
  </Product>
</Wix>
'''
    
    with open("installer.wxs", "w", encoding="utf-8") as f:
        f.write(script_content)
    
    print("✅ 已创建自定义MSI脚本: installer.wxs")


def create_license_file():
    """创建许可协议文件"""
    license_content = '''
{\rtf1\ansi\deff0 {\fonttbl {\f0 Times New Roman;}}\f0\fs24
GudaZip 软件许可协议\par
\par
版权所有 © 2024 GudaZip Team\par
\par
本软件按"现状"提供，不提供任何明示或暗示的保证。\par
\par
使用本软件即表示您同意以下条款：\par
\par
1. 您可以自由使用本软件进行文件压缩和解压操作。\par
2. 您不得将本软件用于任何非法目的。\par
3. 作者不对使用本软件造成的任何损失承担责任。\par
\par
如果您不同意这些条款，请不要安装或使用本软件。\par
}
'''
    
    with open("license.rtf", "w", encoding="utf-8") as f:
        f.write(license_content)
    
    print("✅ 已创建许可协议文件: license.rtf")


def prepare_build():
    """准备构建环境"""
    print("=" * 60)
    print(f"开始构建 {APP_NAME} v{APP_VERSION}")
    print("=" * 60)
    
    # 检查必要文件
    if not os.path.exists("main.py"):
        print("❌ 找不到 main.py 文件")
        sys.exit(1)
    
    if not os.path.exists("resources/icons/app.ico"):
        print("❌ 找不到应用程序图标文件")
        sys.exit(1)
    
    # 创建构建目录
    build_dir = Path("build")
    build_dir.mkdir(exist_ok=True)
    
    # 创建自定义文件
    create_license_file()
    
    print("\n开始cx-freeze构建...")


def main():
    """主函数 - 处理命令行参数和构建流程"""
    import subprocess
    
    # 如果没有命令行参数，默认执行完整构建
    if len(sys.argv) == 1:
        print("未指定构建命令，将执行完整构建流程...")
        print("\n步骤 1/2: 构建可执行文件...")
        
        # 执行 build_exe
        try:
            result = subprocess.run([sys.executable, __file__, "build_exe"], 
                                   capture_output=False, check=True)
            print("✅ 可执行文件构建完成")
        except subprocess.CalledProcessError as e:
            print(f"❌ 可执行文件构建失败: {e}")
            return 1
        
        print("\n步骤 2/2: 构建MSI安装包...")
        
        # 执行 bdist_msi
        try:
            result = subprocess.run([sys.executable, __file__, "bdist_msi"], 
                                   capture_output=False, check=True)
            print("✅ MSI安装包构建完成")
        except subprocess.CalledProcessError as e:
            print(f"❌ MSI安装包构建失败: {e}")
            return 1
        
        print("\n🎉 完整构建流程完成！")
        print("输出文件:")
        print("  - 可执行文件: build/exe/")
        print("  - MSI安装包: dist/")
        return 0
    else:
        # 有参数时，执行正常的 cx-freeze 流程
        prepare_build()
        return 0

# 主程序入口
if __name__ == "__main__":
    exit_code = main()
    if exit_code != 0:
        sys.exit(exit_code)

# cx-freeze setup 调用（仅在有参数时执行）
if len(sys.argv) > 1:
    setup(
        name=APP_NAME,
        version=APP_VERSION,
        description=APP_DESCRIPTION,
        author=APP_AUTHOR,
        options={
            "build_exe": build_exe_options,
            "bdist_msi": bdist_msi_options
        },
        executables=executables
    )