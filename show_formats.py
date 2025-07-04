from src.gudazip.core.file_association_manager import FileAssociationManager

# 创建文件关联管理器实例
fam = FileAssociationManager()

print("✅ 文件关联管理器支持格式数量:", len(fam.supported_extensions))
print("📋 完整格式列表:")
for i, ext in enumerate(fam.supported_extensions, 1):
    print(f"  {i:2d}. {ext}")

print("🎯 按类别分组:")
print("• 基础格式: .zip, .rar, .7z")
print("• tar系列: .tar, .tgz, .tar.gz, .tbz, .tbz2, .tar.bz2, .txz, .tar.xz, .taz")
print("• 压缩格式: .gz, .gzip, .bz2, .bzip2, .xz, .lzma, .z")
print("• 其他格式: .cab, .arj, .lzh, .cpio, .iso")

print("\n📐 界面布局信息:")
print("• 文件关联设置已优化为6列并列显示")
print("• 更好地利用界面空间，减少垂直滚动")
print("• 支持的格式总数:", len(fam.supported_extensions))
print("• 预计显示行数:", (len(fam.supported_extensions) + 5) // 6)  # 向上取整