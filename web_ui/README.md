# 松瓷机电AI助手 WEB UI

松瓷机电AI助手的WEB版用户界面，提供与桌面版完全相同的功能，支持局域网访问。

## 功能特性

- **智能对话**: 与松瓷机电AI助手进行自然对话，支持多轮对话、知识库对话和实时响应
- **多语言翻译**: 支持多种语言之间的智能翻译，集成术语库和占位符处理
- **术语库管理**: 专业术语管理，支持术语增删改查、导入导出和分类管理
- **知识库管理**: 管理和检索知识条目，支持文档导入、向量搜索和分类管理
- **语音功能**: 文本转语音、语音转文本、自定义语音训练和语音克隆
- **系统设置**: 配置AI模型参数和系统设置
- **实时通信**: 基于WebSocket的实时消息推送
- **响应式设计**: 支持桌面、平板、手机等多种设备
- **局域网支持**: 可配置为局域网服务，支持多用户访问

## 快速开始

### 1. 安装依赖

```bash
# 安装WEB UI依赖
pip install -r web_ui/requirements.txt
```

### 2. 启动服务

#### 方法一：使用启动脚本（推荐）

**Windows:**
```bash
start_web_ui.bat
```

**Linux/macOS:**
```bash
bash start_web_ui.sh
```

#### 方法二：直接运行

```bash
python web_ui/app.py
```

### 3. 访问界面

- **本地访问**: http://localhost:5000
- **局域网访问**: http://[服务器IP]:5000

## 配置说明

### 环境配置

通过环境变量配置运行环境：

```bash
# 开发环境（默认）
export FLASK_ENV=development

# 生产环境
export FLASK_ENV=production

# 测试环境
export FLASK_ENV=testing
```

### 服务器配置

在 `web_ui/config/web_config.py` 中修改配置：

```python
# 服务器配置
HOST = '0.0.0.0'  # 监听所有网络接口
PORT = 5000       # 服务端口
DEBUG = False     # 调试模式

# 安全配置
SECRET_KEY = 'your-secret-key'
ENABLE_AUTH = True  # 启用用户认证
```

### 局域网访问配置

1. 确保防火墙允许端口5000的访问
2. 设置 `HOST = '0.0.0.0'` 监听所有网络接口
3. 获取服务器IP地址，其他设备通过 `http://[服务器IP]:5000` 访问

## 功能模块

### 1. 智能对话 (/chat)

- 实时对话界面
- 消息历史记录
- 多轮对话支持
- 对话导出功能
- 快捷消息模板

### 2. 多语言翻译 (/translation)

- 支持多种语言翻译
- 自动语言检测
- 术语库集成翻译
- 术语占位符处理
- 翻译历史记录
- 批量翻译功能
- 语言交换功能
- 术语匹配显示

### 3. 术语库管理 (/terminology)

- 术语条目增删改查
- 术语分类管理
- 术语导入导出 (CSV/JSON/TXT)
- 术语搜索和过滤
- 多语言术语对管理
- 术语使用统计
- 术语库状态监控

### 4. 知识库管理 (/knowledge)

- 知识条目管理
- 文档导入功能
- 向量化搜索
- 标签分类
- 文件上传支持

### 5. 语音功能 (/voice)

- 文本转语音 (TTS)
- 语音转文本 (STT)
- 自定义语音训练
- 音频文件处理
- 实时录音功能

### 6. 系统设置 (/settings)

- AI模型参数配置
- 系统信息监控
- 模型管理
- 性能监控

## API接口

### 聊天API

- `POST /api/chat/send` - 发送消息
- `GET /api/chat/history` - 获取历史记录
- `DELETE /api/chat/clear` - 清空历史

### 翻译API

- `POST /api/translation/translate` - 执行翻译
- `POST /api/translation/match_terms` - 匹配术语
- `GET /api/translation/history` - 翻译历史
- `GET /api/translation/languages` - 支持语言列表

### 术语库API

- `GET /api/terminology/terms` - 获取术语列表
- `POST /api/terminology/add` - 添加术语
- `PUT /api/terminology/update/<id>` - 更新术语
- `DELETE /api/terminology/delete/<id>` - 删除术语
- `POST /api/terminology/search` - 搜索术语
- `POST /api/terminology/import` - 导入术语库
- `GET /api/terminology/export` - 导出术语库
- `GET /api/terminology/categories` - 获取分类列表
- `GET /api/terminology/statistics` - 获取统计信息

### 知识库API

- `GET /api/knowledge/items` - 获取知识条目
- `POST /api/knowledge/add` - 添加知识条目
- `POST /api/knowledge/search` - 搜索知识
- `POST /api/knowledge/upload` - 上传文档

### 语音API

- `POST /api/voice/tts` - 文本转语音
- `POST /api/voice/stt` - 语音转文本
- `GET /api/voice/voices` - 获取可用语音

### 设置API

- `GET /api/settings/config` - 获取配置
- `POST /api/settings/update` - 更新配置
- `GET /api/settings/models` - 获取模型列表
- `GET /api/settings/system_info` - 获取系统信息

## 开发说明

### 项目结构

```
web_ui/
├── app.py                  # Flask主应用
├── config/                 # 配置模块
│   ├── __init__.py
│   └── web_config.py      # WEB服务配置
├── api/                    # API接口模块
│   ├── __init__.py
│   ├── chat_api.py         # 聊天API
│   ├── translation_api.py  # 翻译API
│   ├── knowledge_api.py    # 知识库API
│   ├── settings_api.py     # 设置API
│   └── voice_api.py        # 语音API
├── websocket/             # WebSocket处理
│   ├── __init__.py
│   └── handlers.py        # WebSocket事件处理
├── templates/             # HTML模板
│   ├── base.html          # 基础模板
│   ├── index.html         # 主页面
│   ├── chat.html          # 聊天界面
│   ├── translation.html   # 翻译界面
│   ├── knowledge.html     # 知识库界面
│   ├── settings.html      # 设置界面
│   ├── voice.html         # 语音界面
│   └── error.html         # 错误页面
├── static/                # 静态资源
│   ├── css/               # 样式文件
│   │   └── style.css
│   └── js/                # JavaScript文件
│       └── app.js
└── requirements.txt       # 依赖包列表
```

### 技术栈

- **后端**: Flask + Flask-SocketIO
- **前端**: HTML5 + CSS3 + JavaScript (ES6+)
- **UI框架**: Bootstrap 5 + Font Awesome
- **实时通信**: WebSocket (Socket.IO)
- **API设计**: RESTful API

### 扩展开发

1. **添加新功能模块**:
   - 在 `api/` 目录下创建新的API文件
   - 在 `templates/` 目录下创建对应的HTML模板
   - 在 `api/__init__.py` 中注册新的蓝图

2. **自定义样式**:
   - 修改 `static/css/style.css`
   - 添加自定义CSS类和样式

3. **扩展JavaScript功能**:
   - 修改 `static/js/app.js`
   - 添加页面特定的JavaScript代码

## 故障排除

### 常见问题

1. **端口被占用**:
   ```bash
   # 查找占用端口的进程
   netstat -ano | findstr :5000  # Windows
   lsof -i :5000                 # Linux/macOS

   # 修改配置文件中的端口号
   ```

2. **依赖包安装失败**:
   ```bash
   # 升级pip
   python -m pip install --upgrade pip

   # 使用国内镜像源
   pip install -r web_ui/requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/
   ```

3. **松瓷机电AI助手未初始化**:
   - 确保主项目的松瓷机电AI助手模块正常工作
   - 检查模型文件是否存在
   - 查看控制台错误信息

4. **局域网无法访问**:
   - 检查防火墙设置
   - 确保HOST配置为 '0.0.0.0'
   - 验证网络连接

### 日志查看

日志文件位置: `logs/web_ui.log`

```bash
# 实时查看日志
tail -f logs/web_ui.log
```

## 测试

运行测试脚本验证功能：

```bash
python test_web_ui.py
```

## 更新日志

### 2025-05-26 v2
- **修复Ollama模型超时问题**：
  - 针对知识库问答增加超时时间（180秒）
  - 普通对话使用90秒超时
  - 添加重试机制（最多重试2次）
  - 增加连接错误处理和详细日志
- **优化知识库问答API**：
  - 支持多模型选择（本地/Ollama/OpenAI兼容API）
  - 统一知识库问答策略，保持与PC端一致
  - 改进错误处理和用户反馈

### 2025-05-26 v1
- 优化知识库问答功能，提高回答严谨度和markdown格式支持
- 增强WEB端与PC端的功能一致性
- 改进思维链折叠显示功能
- 优化模型选择和GPU资源管理

## 许可证

本项目遵循与主项目相同的许可证。
