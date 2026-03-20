# Video Generator

YouTube 内容重新制作流水线 —— 自动从字幕到视频的端到端处理。

## 功能

- 🔍 **YouTube 订阅监控** - 自动检测新视频
- 📝 **字幕提取与分析** - 提取字幕并用 AI 分析核心观点
- ✍️ **风格重写** - 以不同风格重写文案
- 🎬 **分镜生成** - 自动规划视觉分镜
- 🖼️ **图像生成** - 风格一致的图像生成
- 🎙️ **语音合成** - 文案转语音
- 🎥 **视频渲染** - 使用 MoviePy 合成最终视频

## 快速开始

### 安装

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# 安装依赖
pip install -e ".[dev]"
```

### 配置

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 填入你的 API keys
nano .env
```

### 运行

```bash
# 监控 YouTube 频道
video-generator watch --channel-id <CHANNEL_ID>

# 处理单个视频
video-generator process --video-id <VIDEO_ID> --style dramatic

# 列出可用风格模板
video-generator styles list
```

## 项目结构

```
video-generator/
├── src/
│   ├── main.py          # CLI 入口
│   ├── config/          # 配置管理
│   ├── core/            # 核心业务逻辑
│   ├── stages/          # 8 个处理阶段
│   ├── api/             # 外部 API 封装
│   ├── templates/       # 风格模板
│   ├── utils/           # 工具函数
│   └── storage/         # 存储层
├── tests/               # 测试
├── docs/                # 文档
└── scripts/             # 脚本
```

## 文档

- [架构文档](docs/ARCHITECTURE.md) - 系统架构设计
- [产品设计](docs/design/product-design.md) - 产品需求文档
- [测试计划](docs/design/test-plan.md) - 测试策略
- [CEO 计划](docs/design/ceo-plan.md) - 战略规划

## 开发

```bash
# 运行测试
pytest

# 代码格式化
black src/ tests/
ruff check src/ tests/

# 类型检查
mypy src/
```

## 许可证

MIT
