# 多Agent并行开发方案

## 一、任务依赖与并行分析

### 依赖关系图

```
┌─────────────────────────────────────────────────────────────┐
│ 阶段0: 项目骨架 (T01-T06)                                    │
│  T01(目录) → T02(依赖) → T03(模型) → T04(LLM) → T05(存储) → T06(CLI)│
│  (线性串行，每步依赖前一步产出)                                │
└────────────────────────────┬────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        ▼                    ▼                    ▼
┌───────────────┐  ┌────────────────┐  ┌──────────────────┐
│ Agent-2       │  │ Agent-3        │  │ Agent-4          │
│ Prompt模板库   │  │ 核心逻辑        │  │ 生图后端          │
│               │  │                │  │ (不依赖Phase0-5)  │
│ T07(独立)     │  │ T09(T07+T08)   │  │                  │
│ T08(独立)     │  │ T15(T14)       │  │ T25(独立)        │
│ T14(T07+T08)  │  │ T16(T14)       │  │ T26(T25)         │
│ T19(T07+T08)  │  │ T17(T14)       │  │ T27(T25)         │
│               │  │ T18(T14)       │  │ T28(T25)         │
│               │  │ T20(T14)       │  │                  │
│               │  │ T21(T14)       │  │                  │
└───────┬───────┘  └───────┬────────┘  └────────┬─────────┘
        │                  │                    │
        └──────────┬───────┘                    │
                   ▼                            │
        ┌──────────────────────┐                │
        │ Agent-5              │                │
        │ Pipeline集成          │                │
        │                      │                │
        │ T22(T03+T04+T05+     │                │
        │      T06+T09+T20)    │                │
        │ T23(T22)             │                │
        │ T24(T22+T23)         │                │
        │ T29(T24+T25)         │                │
        └──────────────────────┘                │
```

### 并行策略

| Agent | 任务 | 依赖前置 | 启动时机 |
|-------|------|---------|---------|
| **Agent-1** | T01-T06 | 无 | 第1批并行 |
| **Agent-2** | T07, T08 | 无 | 第1批并行 |
| **Agent-3** | T09, T15-T18, T20-T21 | T07, T08, T14 | 第2批（第1批完成后） |
| **Agent-4** | T25-T28 | 无 | 第1批并行（独立于其他阶段） |
| **Agent-5** | T22-T24, T29 | T03+T04+T05+T06+T09+T20+T24 | 第3批（核心逻辑完成后） |

### 执行时序

```
时间 ──────────────────────────────────────────────────────────────►

批次1: ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
       │ Agent-1    │  │ Agent-2    │  │ Agent-4    │
       │ T01-T06   │  │ T07,T08    │  │ T25-T28   │
       │ 项目骨架    │  │ Prompt模板  │  │ 生图后端   │
       └─────┬───────┘  └─────┬───────┘  └─────┬───────┘
             │                │                │
批次2:       │         ┌──────▼──────┐        │
             │         │ Agent-3    │        │
             │         │ T09,T15-21 │        │
             │         │ 核心逻辑    │        │
             │         └──────┬──────┘        │
批次3:       │                │                │
             │         ┌──────▼──────┐        │
             │         │ Agent-5    │        │
             │         │ T22-T24,T29│        │
             │         │ Pipeline   │        │
             │         └──────┬──────┘        │
批次4:       │                │                │
             ▼                ▼                ▼
           全部完成

最大并行度: 3个Agent同时工作 (Agent-1 + Agent-2 + Agent-4)
预计总工期: ~3天 (vs 串行的 ~6天)
```

---

## 二、Agent任务分配详情

### Agent-1: 项目骨架工程师

**职责**：创建项目基础结构和基础设施代码

**任务列表**：
- T01: 初始化项目结构（目录、__init__.py）
- T02: 配置依赖和基础设置（requirements.txt、pyproject.toml、config/default.yaml）
- T03: 数据模型定义（src/models/ 下所有 Pydantic 模型）
- T04: LLM 适配器（src/llm/adapter.py、src/llm/prompt_loader.py）
- T05: 存储层（src/storage/project_store.py）
- T06: CLI 骨架（src/cli.py）

**产出目录**：
```
src/
├── __init__.py
├── cli.py
├── core/
├── models/
│   ├── __init__.py
│   ├── world_bible.py
│   ├── entity.py
│   ├── chapter.py
│   ├── prompt.py
│   └── project.py
├── llm/
│   ├── __init__.py
│   ├── adapter.py
│   └── prompt_loader.py
├── storage/
│   ├── __init__.py
│   └── project_store.py
└── render/
    ├── __init__.py
config/
├── default.yaml
└── prompts/
```

**验证标准**：每个任务完成后运行验证命令，确保无报错。

---

### Agent-2: Prompt工程师

**职责**：设计和编写所有LLM Prompt模板

**任务列表**：
- T07: 世界观分析 Prompt（config/prompts/world_bible_analyze.yaml）
- T08: 视觉锚定 Prompt（config/prompts/visual_anchoring.yaml）
- T14: 实体提取 + 属性提取 Prompt
  - config/prompts/entity_extraction.yaml
  - config/prompts/character_attribute.yaml
  - config/prompts/scene_attribute.yaml
  - config/prompts/item_attribute.yaml
- T19: 提示词生成 Prompt
  - config/prompts/character_prompt.yaml
  - config/prompts/scene_prompt.yaml
  - config/prompts/item_prompt.yaml
  - config/prompts/face_anchor_prompt.yaml（面部锚定图）
  - config/prompts/image_verify.yaml（图片验证）

**参考文档**：[Prompt模板库.md](Prompt模板库.md) 中的所有模板内容

**验证标准**：每个 YAML 文件能被 jinja2 正确加载和渲染。

---

### Agent-3: 核心逻辑工程师

**职责**：实现所有核心业务逻辑模块

**任务列表**：
- T09: WorldBibleBuilder（src/core/world_bible_builder.py）
- T15: EntityExtractor（src/core/entity_extractor.py）
- T16: EntityMerger（src/core/entity_merger.py）
- T17: AttributeBuilder（src/core/attribute_builder.py）
- T18: 集成测试：实体提取端到端
- T20: PromptGenerator（src/core/prompt_generator.py）
- T21: 集成测试：提示词生成端到端

**前置依赖**：
- T07, T08（Prompt模板）
- T14（实体+属性 Prompt）
- T19（提示词生成 Prompt）

**产出文件**：
```
src/core/
├── world_bible_builder.py
├── entity_extractor.py
├── entity_merger.py
├── attribute_builder.py
├── prompt_generator.py
├── preprocessor.py (T11-T12)
```

**验证标准**：T18 和 T21 的集成测试清单全部通过。

---

### Agent-4: 生图后端工程师

**职责**：实现生图相关功能，独立的模块，不依赖 Phase 0-5

**任务列表**：
- T25: ChatGPT2API 后端（src/render/chatgpt2api_backend.py）
- T26: 面部锚定图生成（src/core/face_anchor.py）
- T27: 角色全身图生成（src/core/image_generator.py）
- T28: 面部一致性验证（src/render/face_consistency.py）
- T29: 生图端到端集成测试

**前置依赖**：无（完全独立于其他阶段）

**产出文件**：
```
src/render/
├── chatgpt2api_backend.py
└── face_consistency.py
src/core/
├── face_anchor.py
└── image_generator.py
```

**验证标准**：T29 的集成测试清单全部通过。

---

### Agent-5: Pipeline集成工程师

**职责**：实现流水线编排、CLI完善、端到端测试

**任务列表**：
- T22: Pipeline 编排（src/core/pipeline.py）
- T23: CLI完善（src/cli.py 与 Pipeline 对接）
- T24: 端到端测试（完整流程验证）
- T29: 生图端到端测试（与 Agent-4 协作）

**前置依赖**：
- T03（数据模型）
- T04（LLM适配器）
- T05（存储层）
- T06（CLI骨架）
- T09（WorldBibleBuilder）
- T20（PromptGenerator）

**产出文件**：
```
src/core/pipeline.py
src/cli.py (更新)
tests/
├── test_preprocessor.py
├── test_world_bible.py
├── test_extractor.py
└── test_prompt_generator.py
```

**验证标准**：T24 端到端测试清单全部通过。

---

## 三、Agent间协调规则

### 1. 共享上下文（通过文件传递）

| 文件 | 读取方 | 写入方 |
|------|--------|--------|
| src/models/*.py | Agent-1 写入，Agent-3,5 读取 | Agent-1 |
| src/llm/*.py | Agent-1 写入，Agent-3,5 读取 | Agent-1 |
| src/storage/*.py | Agent-1 写入，Agent-3,5 读取 | Agent-1 |
| config/prompts/*.yaml | Agent-2 写入，Agent-3 读取 | Agent-2 |
| src/core/*.py | Agent-3 写入，Agent-5 读取 | Agent-3 |
| src/render/*.py | Agent-4 写入 | Agent-4 |

### 2. 冲突避免

- **每个文件只由一个Agent写入**
- Agent-3 和 Agent-5 如果需要同时修改同一文件（如 src/cli.py），由 Agent-5 最终合并
- Prompt模板文件（Agent-2）一旦确定，Agent-3 只能读取不能修改

### 3. 依赖通知机制

- Agent-2 完成 T07/T08 后，通知 Agent-3 可以开始 T09
- Agent-2 完成 T14 后，通知 Agent-3 可以开始 T15-T18/T20-T21
- Agent-3 完成 T09+T20 后，通知 Agent-5 可以开始 T22
- Agent-1 完成 T03+T04+T05+T06 后，通知 Agent-5 可以开始准备

### 4. 命名规范

所有代码必须遵循以下规范：

**文件命名**：小写下划线 `snake_case.py`
**类命名**：大驼峰 `PascalCase`
**函数命名**：小写下划线 `snake_case()`
**常量命名**：大写下划线 `UPPER_SNAKE_CASE`
**私有成员**：单下划线前缀 `_private_method()`

---

## 四、执行流程

### Step 1: 第1批启动（立即并行）

| Agent | 任务 | 预计耗时 |
|--------|------|---------|
| Agent-1 | T01-T06 项目骨架 | 5.5h |
| Agent-2 | T07-T08 Prompt模板(世界观+视觉) | 1h |
| Agent-4 | T25-T28 生图后端(独立) | 8h |

### Step 2: 第2批启动（Step1完成后并行）

| Agent | 任务 | 预计耗时 |
|--------|------|---------|
| Agent-3 | T09, T15-T18, T20-T21 核心逻辑 | 10h |

### Step 3: 第3批启动（Step2完成后）

| Agent | 任务 | 预计耗时 |
|--------|------|---------|
| Agent-5 | T22-T24, T29 Pipeline+端到端 | 5h |

### Step 4: 最终集成

- Agent-5 连接 Agent-4 的生图后端到 Pipeline
- 运行完整端到端测试
- 修复跨Agent集成问题

---

## 五、质量标准

每个Agent完成的代码必须满足：

1. **语法正确**：`python -m py_compile src/**/*.py` 无报错
2. **类型安全**：Pydantic 模型定义完整，序列化/反序列化无报错
3. **Prompt可渲染**：`PromptLoader.load()` 无报错
4. **CLI可运行**：`python -m src.cli --help` 输出帮助信息
5. **测试覆盖**：每个核心模块至少有一个集成测试
6. **无硬编码**：所有配置从 config/default.yaml 读取，不硬编码 API Key
7. **中文注释**：关键逻辑添加中文注释
