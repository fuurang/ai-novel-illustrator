# Web UI集成模块使用说明

## 概述

本模块提供了Web UI与AI拆书生图Pipeline的集成功能，支持异步执行、进度跟踪和文件上传处理。

## 核心组件

### 1. Pipeline Web集成 (`pipeline_integration.py`)

**WebPipelineRunner** - Pipeline的Web运行器

```python
from src.web import WebPipelineRunner, create_progress_callback

# 创建运行器
runner = WebPipelineRunner()

# 设置进度回调
callback, progress_manager = create_progress_callback(
    on_progress=lambda status: print(f"进度: {status['progress']:.2%}")
)
runner.set_progress_callback(callback)

# 运行流水线
result = await runner.run_full_pipeline(
    input_path="path/to/novel.txt",
    project_name="我的项目",
)
```

**主要功能**:
- `run_full_pipeline()` - 运行完整流水线
- `run_pipeline_with_stages()` - 运行指定阶段
- `get_project_info()` - 获取项目信息
- `load_project_prompts()` - 加载项目提示词

### 2. 文件上传处理 (`upload.py`)

**FileUploadHandler** - 文件上传处理器

```python
from src.web import FileUploadHandler

handler = FileUploadHandler()

# 处理上传
file_path = handler.handle_upload(file_obj)

# 验证文件
is_valid, error_msg = handler.validate_file(file_path)

# 获取文件信息
file_info = handler.get_file_info(file_path)
```

**便捷函数**:
- `handle_file_upload()` - 处理单个文件上传
- `handle_multiple_file_uploads()` - 处理多个文件
- `validate_uploaded_file()` - 验证文件
- `read_file_content()` - 读取文件内容

### 3. 进度状态管理 (`progress.py`)

**ProgressManager** - 进度管理器

```python
from src.web import ProgressManager, PipelineState

manager = ProgressManager()

# 更新进度
manager.update("preprocess", 0.5, "正在读取文件...")

# 获取状态
status = manager.get_status()
print(f"进度: {status['progress']:.2%}")
print(f"阶段: {status['stage_name']}")

# 检查是否运行中
if manager.is_running():
    print("流水线正在执行...")
```

**WebProgressTracker** - Web进度跟踪器（支持订阅模式）

```python
from src.web import WebProgressTracker

tracker = WebProgressTracker()

# 订阅进度更新
def on_update(status):
    print(f"更新: {status['message']}")

tracker.subscribe(on_update)

# 更新进度（会自动通知所有订阅者）
tracker.update("preprocess", 0.3, "正在处理...")
```

## 使用示例

### 基本使用流程

```python
import asyncio
from src.web import (
    WebPipelineRunner,
    FileUploadHandler,
    ProgressManager,
    create_progress_callback,
)

async def main():
    # 1. 初始化组件
    upload_handler = FileUploadHandler()
    runner = WebPipelineRunner()
    
    # 2. 设置进度回调
    def on_progress(status):
        print(f"[{status['stage_name']}] {status['progress']:.1%} - {status['message']}")
    
    callback, _ = create_progress_callback(on_progress)
    runner.set_progress_callback(callback)
    
    # 3. 处理文件上传
    file_path = upload_handler.handle_upload(file_obj)
    if not file_path:
        print("文件上传失败")
        return
    
    # 4. 运行流水线
    result = await runner.run_full_pipeline(
        input_path=file_path,
        project_name="我的小说项目",
    )
    
    # 5. 处理结果
    if result.success:
        print(f"✅ 成功! 项目ID: {result.project_id}")
        print(f"生成提示词数: {result.summary['prompt_count']}")
    else:
        print(f"❌ 失败: {result.error}")

asyncio.run(main())
```

### 启动Web界面

运行简化版示例应用：

```bash
python -m src.web.simple_app
```

访问 `http://localhost:7861` 查看界面。

## 进度回调机制

进度回调函数签名：

```python
def progress_callback(stage: str, progress: float, message: str, details: dict):
    """
    Args:
        stage: 阶段标识 (preprocess, world_bible, extract, etc.)
        progress: 整体进度 (0.0 - 1.0)
        message: 进度描述消息
        details: 额外详情字典
    """
    pass
```

## 流水线阶段

| 阶段标识 | 显示名称 | 说明 |
|---------|---------|------|
| init | 初始化 | 初始化组件 |
| preprocess | 预处理 | 读取并分割章节 |
| world_bible | 世界观构建 | 分析并构建世界观 |
| extract | 实体提取 | 提取角色、场景、物品 |
| merge | 实体合并 | 去重和归一化 |
| attribute | 属性构建 | 构建视觉属性 |
| prompt | 提示词生成 | 生成AI绘画提示词 |
| complete | 完成 | 执行完成 |

## 注意事项

1. **异步执行**: `run_full_pipeline()` 是异步方法，需要使用 `await` 或 `asyncio.run()`
2. **文件清理**: 使用 `cleanup_uploaded_files()` 定期清理临时文件
3. **线程安全**: ProgressManager 使用线程锁，可在多线程环境安全使用
4. **错误处理**: 建议捕获异常并提供用户友好的错误提示

## 项目结构

```
src/web/
├── __init__.py           # 包初始化，导出主要接口
├── pipeline_integration.py # Pipeline Web集成
├── upload.py             # 文件上传处理
├── progress.py           # 进度状态管理
├── simple_app.py         # 简化版示例应用
└── example.py            # 使用示例
```

## 下一步

1. 根据需要扩展 `simple_app.py` 添加更多功能
2. 集成到现有的Gradio应用 (`app.py`)
3. 添加用户认证和项目管理功能
4. 实现实时进度更新的WebSocket支持
