# 松瓷机电AI助手自动更新器

本文档介绍松瓷机电AI助手程序的自动更新功能，包括自动更新器的使用方法和配置选项。

## 功能概述

松瓷机电AI助手自动更新器(`auto_updater.py`)提供以下功能：

1. **版本检查**：自动检查是否有新版本可用
2. **增量更新**：只下载和更新已变更的文件，减小更新包大小
3. **全量更新**：支持完全替换应用程序文件的更新方式
4. **后台更新**：支持在后台下载更新，不影响应用程序使用
5. **更新提示**：以图形界面方式提示用户更新
6. **强制更新**：支持强制用户更新到最新版本
7. **自动重启**：更新完成后可自动重启应用程序

## 使用方法

### 图形界面模式

最简单的使用方式是直接运行自动更新器：

```bash
python auto_updater.py --gui
```

这将启动一个图形界面，用户可以通过界面检查更新、下载和应用更新。

### 命令行模式

自动更新器也支持命令行操作：

1. **检查更新**：
   ```bash
   python auto_updater.py --check --url https://example.com/updates.json
   ```

2. **下载并应用更新**：
   ```bash
   python auto_updater.py --check --url https://example.com/updates.json --download
   ```

3. **下载、应用更新并重启应用**：
   ```bash
   python auto_updater.py --check --url https://example.com/updates.json --download --restart
   ```

### 在应用程序中集成

在松瓷机电AI助手程序中集成自动更新功能：

```python
from auto_updater import AutoUpdater

# 创建更新器实例
updater = AutoUpdater(
    app_name="松瓷机电AI助手",
    check_url="https://example.com/updates.json",
    on_progress=lambda progress, message: print(f"更新进度: {progress:.1%} - {message}")
)

# 检查更新
has_update, current_version, latest_version = updater.check_for_updates()

if has_update:
    # 提示用户更新
    print(f"发现新版本: {latest_version} (当前版本: {current_version})")
    
    # 下载并应用更新
    updater.download_updates()
    
    # 更新完成后重启应用
    # updater.restart_application()
```

## 更新服务器配置

自动更新器需要连接到更新服务器获取更新信息。更新信息文件(`updates.json`)格式如下：

```json
{
  "app_name": "松瓷机电AI助手",
  "old_version": "1.0.0",
  "new_version": "1.0.1",
  "update_date": "2023-01-01 12:00:00",
  "update_timestamp": 1672531200,
  "update_url": "https://example.com/downloads/松瓷机电AI助手_update_1.0.0_to_1.0.1.zip",
  "check_url": "https://example.com/updates.json",
  "release_notes": "修复了若干问题，提升了性能",
  "required_update": false,
  "update_size": 1048576,
  "file_updates": [
    {
      "path": "main.exe",
      "action": "update",
      "size": 1048576
    },
    {
      "path": "config/settings.json",
      "action": "add",
      "size": 1024
    },
    {
      "path": "data/temp.dat",
      "action": "delete",
      "size": 0
    }
  ]
}
```

## 生成更新包

使用版本管理工具(`version_manager.py`)生成更新包：

1. **更新版本号**：
   ```bash
   python version_manager.py update 1.0.1 --notes "修复了若干问题，提升了性能"
   ```

2. **扫描文件变更**：
   ```bash
   python version_manager.py scan dist
   ```

3. **创建更新包**：
   ```bash
   python version_manager.py package old_version.json --output packages
   ```

4. **发布更新**：
   ```bash
   python version_manager.py publish https://example.com/api/updates --api-key YOUR_API_KEY
   ```

## 安全性考虑

自动更新功能涉及下载和执行代码，需注意以下安全事项：

1. **更新包验证**：自动更新器会验证下载的更新包完整性
2. **HTTPS传输**：确保使用HTTPS协议传输更新包，防止中间人攻击
3. **备份机制**：更新前自动备份关键文件，支持更新失败时回滚
4. **错误处理**：完善的错误处理机制，确保更新过程中的问题不会导致应用程序崩溃

## 自定义配置

`auto_updater.py`支持以下配置选项：

- `VERSION_FILE`: 版本信息文件路径
- `UPDATE_INFO_FILE`: 更新信息文件路径
- `TEMP_DIR`: 临时目录路径
- `BACKUP_DIR`: 备份目录路径
- `MAX_RETRY_COUNT`: 最大重试次数
- `DEFAULT_TIMEOUT`: 默认超时时间（秒）

可以通过修改`auto_updater.py`文件开头的常量来自定义这些配置。

## 常见问题

### 更新后应用程序无法启动

可能原因：
- 更新文件不完整或损坏
- 关键文件被占用，无法更新
- 应用程序依赖项发生变化

解决方法：
1. 检查日志文件，查看详细错误信息
2. 尝试手动替换更新文件
3. 恢复备份（位于`%TEMP%/ai_assistant_backup`目录）

### 无法连接到更新服务器

可能原因：
- 网络连接问题
- 更新服务器地址配置错误
- 更新服务器暂时不可用

解决方法：
1. 检查网络连接
2. 验证更新服务器URL配置
3. 稍后重试或联系管理员

### 更新过程中断

可能原因：
- 网络连接中断
- 磁盘空间不足
- 应用程序异常退出

解决方法：
1. 重新启动应用程序，自动继续更新
2. 清理磁盘空间
3. 手动删除临时文件（位于`%TEMP%/ai_assistant_update`目录）

## 最佳实践

1. **定期更新**：设置定期检查更新，确保应用程序始终为最新版本
2. **增量更新**：尽可能使用增量更新，减小更新包大小
3. **更新提示**：在非关键操作时提示用户更新，避免中断用户工作
4. **详细日志**：保留详细的更新日志，方便排查问题
5. **版本回滚**：提供版本回滚功能，允许用户在遇到问题时回退到旧版本 