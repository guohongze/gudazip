# GudaZip - Python桌面压缩管理器

## 项目简介

GudaZip是一个基于Python和PySide6开发的桌面压缩文件管理器，提供类似资源管理器的界面，支持多种压缩格式的浏览、解压、压缩等操作。

## 功能特性

### 当前版本 (v0.1.0)
- ✅ 资源管理器风格的用户界面
- ✅ 左侧文件系统导航树
- ✅ 右侧多标签文件查看器
- ✅ ZIP文件的完整支持（读写）
- ✅ RAR文件的只读支持
- ✅ 基础的菜单和工具栏

### 支持的压缩格式
- **ZIP** - 完整支持（创建、解压、添加、删除文件）
- **RAR** - 只读支持（需要unrar工具）
- **7Z** - 计划支持
- **TAR/GZ** - 计划支持

## 安装和运行

### 1. 环境要求
- Python 3.12+
- Windows 10+

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

### 3. 运行程序
```bash
python main.py
```

## 项目结构

```
GudaZip/
├── main.py                 # 主入口文件
├── requirements.txt        # 依赖包列表
├── README.md              # 项目说明
├── doc/                   # 文档目录
│   └── gudazip.md        # 开发文档
└── src/                   # 源代码目录
    └── gudazip/           # 主包
        ├── __init__.py
        ├── main_window.py # 主窗口
        ├── ui/            # 用户界面组件
        │   ├── __init__.py
        │   ├── file_browser.py      # 文件浏览器
        │   └── archive_viewer.py    # 压缩包查看器
        └── core/          # 核心功能
            ├── __init__.py
            ├── archive_manager.py   # 压缩包管理器
            ├── zip_handler.py       # ZIP处理器
            └── rar_handler.py       # RAR处理器
```

## 开发状态

按照开发文档的6周计划：

- ✅ **第1周**: 需求确认 + UI草图设计 + 文件浏览器实现
- 🔄 **第2周**: 实现 ZIP/RAR/GZ 支持 (进行中)
- ⏳ **第3周**: 实现压缩包查看、添加/删除、密码
- ⏳ **第4周**: 整合工具栏、菜单、状态栏功能
- ⏳ **第5周**: 主题切换、设置面板
- ⏳ **第6周**: 测试 + 打包 + 文档编写

## 技术栈

- **GUI框架**: PySide6
- **压缩库**: zipfile (内置), rarfile, py7zr, patool
- **图标**: qtawesome
- **多语言**: QTranslator
- **打包**: cx_Freeze

## 开发者注意事项

### RAR支持说明
RAR格式支持需要：
1. 安装`rarfile`库: `pip install rarfile`
2. 安装WinRAR或unrar命令行工具
3. 确保unrar.exe在系统PATH中或在标准安装位置

### 代码规范
- 使用UTF-8编码
- 遵循PEP8代码规范
- 类和函数需要中文注释
- 采用Model-View架构

## 许可证

该项目遵循MIT许可证。

## 贡献

欢迎提交Issue和Pull Request！

## 更新日志

### v0.1.0 (当前版本)
- 初始版本发布
- 实现基础的文件浏览和压缩包查看功能
- 支持ZIP和RAR格式的基本操作 