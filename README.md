# GudaZip - Python桌面压缩管理器

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![PySide6](https://img.shields.io/badge/PySide6-6.5+-green.svg)](https://doc.qt.io/qtforpython/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

GudaZip是一个基于Python和PySide6开发的现代化桌面压缩文件管理器，提供直观的图形界面来管理各种压缩格式的文件。

## 🚀 主要功能

### 📦 压缩格式支持
- **ZIP**: 完整的ZIP文件创建、解压和管理
- **RAR**: RAR文件解压和查看（需要RAR工具）
- **7Z**: 7-Zip格式支持，包括创建和解压
- **通用格式**: 通过patool支持更多压缩格式

### 🖥️ 用户界面特性
- **现代化界面**: 基于PySide6的响应式设计
- **文件浏览器**: 直观的文件和文件夹浏览
- **拖拽支持**: 支持文件拖拽操作
- **右键菜单**: 集成到Windows资源管理器的右键菜单
- **多语言支持**: 支持中文界面

### 🔧 高级功能
- **异步操作**: 后台处理大文件，不阻塞界面
- **进度显示**: 实时显示压缩/解压进度
- **错误处理**: 完善的错误提示和恢复机制
- **文件关联**: 自动关联压缩文件格式
- **权限管理**: 智能处理管理员权限需求

## 📋 系统要求

- **操作系统**: Windows 10/11
- **Python**: 3.8 或更高版本
- **内存**: 建议 4GB 以上
- **磁盘空间**: 至少 100MB 可用空间

## 🛠️ 安装说明

### 方法一：从源码安装

1. **克隆仓库**
   ```bash
   git clone https://github.com/your-username/gudazip.git
   cd gudazip
   ```

2. **创建虚拟环境**
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # Linux/macOS
   source venv/bin/activate
   ```

3. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

4. **运行程序**
   ```bash
   python main.py
   ```

### 方法二：使用安装包

1. 下载最新的MSI安装包
2. 双击运行安装程序
3. 按照向导完成安装

## 🚀 快速开始

### 启动程序
```bash
python main.py
```

### 基本操作
1. **创建压缩文件**: 选择文件/文件夹 → 右键 → "添加到压缩文件"
2. **解压文件**: 双击压缩文件或右键选择"解压到..."
3. **浏览压缩文件**: 双击压缩文件查看内容
4. **设置默认程序**: 在设置中配置文件关联

## 📁 项目结构

```
gudazip/
├── main.py                 # 程序入口
├── build.py               # 打包脚本
├── requirements.txt       # 依赖包列表
├── src/                  # 源代码目录
│   └── gudazip/
│       ├── core/         # 核心功能模块
│       ├── ui/           # 用户界面组件
│       └── main_window.py # 主窗口
├── resources/            # 资源文件
│   └── icons/           # 图标文件
├── docs/                # 文档目录
└── venv/                # 虚拟环境
```

## 🔧 开发指南

### 环境设置
1. 确保安装了Python 3.8+
2. 安装PySide6: `pip install PySide6`
3. 安装其他依赖: `pip install -r requirements.txt`

### 代码风格
- 使用Python PEP 8代码规范
- 所有字符串使用UTF-8编码
- 添加适当的类型注解

### 构建发布版本
```bash
python build.py --optimized
```

## 📚 文档

更多详细信息请查看 `docs/` 目录：

- [安装指南](docs/安装PyWin32指南.md)
- [MSI打包说明](docs/MSI打包PyWin32问题解决方案.md)
- [性能优化](docs/第三阶段性能优化-3.1-异步文件操作.md)
- [重构报告](docs/REFACTORING_SUMMARY.md)

## 🤝 贡献指南

我们欢迎所有形式的贡献！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

- [PySide6](https://doc.qt.io/qtforpython/) - Qt for Python
- [patool](https://wummel.github.io/patool/) - 通用压缩工具接口
- [py7zr](https://github.com/miurahr/py7zr) - 7-Zip Python库
- [rarfile](https://github.com/markokr/rarfile) - RAR文件支持

## 📞 联系方式

- 项目主页: [GitHub Repository](https://github.com/your-username/gudazip)
- 问题反馈: [Issues](https://github.com/your-username/gudazip/issues)
- 功能建议: [Discussions](https://github.com/your-username/gudazip/discussions)

---

**GudaZip** - 让压缩文件管理变得简单高效！ 🎉 