# AI 拆书生图

分析中文小说原文，自动提取人物、场景、物品，生成 AI 绘画提示词，并支持一致性插画生成。

## 功能特性

- 📖 **智能文本分析** — 自动拆分章节，提取角色/场景/物品实体
- 🌍 **世界观锚定** — 分析小说建立统一视觉风格，确保全局一致
- 🎨 **中文提示词生成** — 生成中文+英文双语提示词，可直接用于 Midjourney / Stable Diffusion
- 👤 **面部一致性** — 通过面部锚定图 + edit_image 接口，保证角色面部跨图不变
- 📝 **章节级可控** — 逐章分析，选择哪章分析哪章，精确控制消耗
- 🌓 **暗色/亮色主题** — 支持深色和浅色界面切换

## 技术架构

```
中文小说原文 → [文本预处理] → [世界观构建] → [实体提取] → [实体消歧] → [属性构建] → [提示词生成] → [一致性生图]
```

- **后端**: Python + FastAPI
- **前端**: React + TypeScript + Vite + TailwindCSS
- **LLM**: 支持任何 OpenAI 兼容 API（DeepSeek / GPT / 本地模型）
- **生图**: 支持 ChatGPT2API / ComfyUI / SD WebUI / DALL-E

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- 一个 OpenAI 兼容的 LLM API

### 安装

```bash
# 克隆仓库
git clone https://github.com/fuurang/ai-novel-illustrator.git
cd ai-novel-illustrator

# 安装后端依赖
pip install -r requirements.txt

# 安装前端依赖
cd web
npm install
```

### 配置

复制默认配置并填入你的 API Key：

```bash
cp config/default.yaml config/user.yaml
```

编辑 `config/user.yaml`：

```yaml
llm:
  provider: "openai_compatible"
  model: "your-model-name"        # 如 deepseek-chat
  api_key: "your-api-key"
  base_url: "your-api-base-url"   # 如 https://api.deepseek.com/v1

image:
  enabled: true
  backend: "chatgpt2api"          # 或 comfyui / sd_webui / dall_e
  chatgpt2api:
    base_url: "http://localhost:5000/v1"
    api_key: "your-image-api-key"
    model: "gpt-image-2"
```

### 启动

```bash
# 启动后端 API
uvicorn src.api.app:app --port 8000 --reload

# 启动前端界面（新终端）
cd web
npm run dev
```

打开浏览器访问 http://localhost:8888

### CLI 使用

```bash
# 运行完整流水线
python -m src.cli run -i 小说.txt -n "项目名称"

# 查看项目信息
python -m src.cli info -p 项目ID

# 导出提示词
python -m src.cli export -p 项目ID -f md
```

## 使用流程

1. **新建项目** — 上传 TXT 小说文件
2. **文本预处理** — 自动拆分章节（免费，不消耗 API）
3. **章节选择** — 选择要分析的章节（不选则分析全部）
4. **逐步执行** — 按需执行：世界观构建 → 实体提取 → 消歧 → 属性构建 → 提示词生成
5. **查看结果** — 浏览提取的实体和生成的提示词
6. **生成图片** — 按需生成面部锚定图、角色图、场景图、物品图

## 项目结构

```
├── src/                        # 后端源码
│   ├── api/                    # FastAPI 路由
│   ├── core/                   # 核心逻辑（流水线、实体提取、提示词生成等）
│   ├── llm/                    # LLM 适配层
│   ├── models/                 # Pydantic 数据模型
│   ├── render/                 # 生图后端
│   ├── storage/                # 存储层
│   └── cli.py                  # CLI 入口
├── web/                        # 前端源码
│   └── src/
│       ├── api/                # API 客户端
│       ├── components/         # UI 组件
│       ├── hooks/              # React Hooks
│       ├── pages/              # 页面
│       └── stores/             # Zustand 状态管理
├── config/                     # 配置文件
│   ├── default.yaml            # 默认配置
│   └── prompts/                # LLM Prompt 模板
├── tests/                      # 测试
└── output/                     # 输出目录（gitignore）
```

## 交流

- **QQ 交流群**: [297144575](https://qm.qq.com/q/297144575)
- **Issues**: [GitHub Issues](https://github.com/fuurang/ai-novel-illustrator/issues)

## 开源协议

[MIT License](LICENSE)
