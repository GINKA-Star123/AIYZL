# AIYZL - 智能语音交互与 Live2D 展示系统

## 项目概述

AIYZL 是一个集成了语音识别、智能对话、语音合成和 Live2D 模型展示的智能交互系统。它能够实时识别用户语音，通过大语言模型生成智能回复，并通过语音合成将回复转换为语音输出，同时在屏幕上显示生动的 Live2D 角色。

## 核心功能

- **实时语音识别**：基于 Faster Whisper 模型，支持实时中文语音识别
- **智能对话**：集成 OpenAI API，生成符合角色设定的智能回复
- **语音合成**：使用 GPTSOVITS 进行高质量语音合成
- **Live2D 模型展示**：支持透明窗口、无边框显示和鼠标拖动
- **B站弹幕监听**：实时监听 B 站直播间弹幕并自动回复
- **记忆管理**：能够存储和检索用户的重要信息
- **字幕显示**：支持实时字幕输出

## 技术栈

- **后端**：Python 3.13
- **语音识别**：Faster Whisper
- **自然语言处理**：OpenAI API、SentenceTransformer
- **语音合成**：GPTSOVITS
- **Live2D 渲染**：live2d-py、PyQt5
- **B站交互**：bilibili-api
- **其他**：WebSocket、多线程编程

## 目录结构

```
AIYZL/
├── Resources/          # Live2D 模型资源
│   └── v3/
│       └── YZL10/      # 乐正绫模型文件
├── agent/              # 智能代理模块
│   ├── CAG/            # 语义相似度缓存系统
│   ├── LLM/            # 大语言模型接口
│   └── RAG/            # 检索增强生成
├── ai-streamer-chat/   # 聊天系统
├── character/          # 角色管理
├── knowledge/          # 知识库
│   └── Personal/       # 个人记忆
├── memory/             # 记忆管理模块
├── service/            # 核心服务
│   ├── ASR/            # 语音识别
│   ├── OBS/            # 字幕系统
│   ├── TTS/            # 语音合成
│   └── live2d/         # Live2D 展示
├── .env                # 环境变量
├── .gitignore          # Git 忽略文件
├── config.py           # 配置文件
├── main.py             # 主入口
└── requirements.txt    # 依赖文件
```

## 安装说明

### 1. 环境准备

- Python 3.13+
- CUDA 11.8+（推荐，用于加速语音识别）
- Git

### 2. 克隆项目

```bash
git clone https://github.com/GINKA-Star123/AIYZL.git
cd AIYZL
```

### 3. 创建虚拟环境

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux/Mac
python3 -m venv .venv
source .venv/bin/activate
```

### 4. 安装依赖

```bash
pip install -r requirements.txt
```

### 5. 配置环境变量

编辑 `.env` 文件，添加以下内容：

```
SILICONFLOW_API=your_api_key_here
```

### 6. 配置 B 站账号（可选）

编辑 `config.py` 文件，添加 B 站账号信息：

```python
SESSDATA = "your_sessdata"
bili_jct = "your_bili_jct"
BUVID3 = "your_buvid3"
BILIBILI_ROOM_ID = your_room_id
```

## 使用方法

### 启动系统

```bash
python main.py
```

系统启动后，会自动初始化以下服务：
- 语音识别服务（ASR）
- B 站弹幕监听服务

### 功能使用

1. **语音交互**：直接对着麦克风说话，系统会自动识别并回复
2. **弹幕交互**：在 B 站直播间发送弹幕，系统会自动回复
3. **Live2D 展示**：系统会在屏幕上显示 Live2D 角色

### 停止系统

按 `Ctrl+C` 停止系统运行。

## 核心模块说明

### 1. 语音识别（ASR）

位于 `service/ASR/ASR.py`，使用 Faster Whisper 模型进行实时语音识别，支持中文优化。

### 2. 大语言模型（LLM）

位于 `agent/LLM/AILLM.py`，集成 OpenAI API，生成符合角色设定的智能回复。

### 3. 语音合成（TTS）

位于 `service/TTS/GPTSOVITS.py`，使用 GPTSOVITS 进行高质量语音合成。

### 4. Live2D 展示

位于 `service/live2d/live2dDisplay.py`，支持透明窗口、无边框显示和鼠标拖动。

### 5. 记忆管理

位于 `memory/memory.py`，能够存储和检索用户的重要信息。

### 6. B 站弹幕监听

位于 `main.py`，实时监听 B 站直播间弹幕并自动回复。

## 故障排除

### 1. 语音识别失败

- 检查麦克风是否正常工作
- 确保 CUDA 环境正确配置
- 检查网络连接是否正常（用于下载模型）

### 2. 语音合成失败

- 确保 GPTSOVITS 服务正常运行
- 检查网络连接是否正常

### 3. Live2D 模型不显示

- 检查模型文件路径是否正确
- 确保 PyQt5 正确安装

### 4. B 站弹幕不响应

- 检查 B 站账号信息是否正确
- 确保直播间 ID 正确

## 性能优化

- **GPU 加速**：确保 CUDA 环境正确配置，以加速语音识别
- **内存管理**：系统会自动清理 GPU 显存，避免内存溢出
- **音频处理**：优化了音频缓冲区管理，提高识别准确率

## 安全注意事项

- 环境变量中的 API 密钥不要泄露
- 不要在公共场合使用系统的语音识别功能
- 定期清理内存文件，避免敏感信息积累

## 未来计划

- 支持更多 Live2D 模型
- 优化语音识别和合成质量
- 添加更多智能交互功能
- 支持多平台部署

## 贡献

欢迎提交 Issue 和 Pull Request，帮助改进项目。

## 许可证

本项目采用 MIT 许可证。

## 联系方式

- GitHub: [GINKA-Star123](https://github.com/GINKA-Star123)

---

**Note**: 首次运行时，系统会自动下载 Faster Whisper 模型，可能需要一些时间。请确保网络连接稳定并具有足够的磁盘空间。