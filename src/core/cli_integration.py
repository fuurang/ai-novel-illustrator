"""
CLI 和 Pipeline 的粘合层
提供便捷函数和工具来连接 CLI 与 Pipeline
"""
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List
import yaml
import json

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.panel import Panel
from rich import box

from src.core.pipeline import Pipeline, PipelineContext
from src.storage.project_store import ProjectStore

console = Console()


def create_pipeline(config_path: Optional[str] = None, output_dir: str = "./projects") -> Pipeline:
    """
    从配置文件创建 Pipeline 实例

    Args:
        config_path: 配置文件路径（可选）
        output_dir: 输出目录

    Returns:
        Pipeline 实例
    """
    if config_path:
        config_file = Path(config_path)
    else:
        config_file = Path(__file__).parent.parent.parent / 'config' / 'default.yaml'

    if config_file.exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
    else:
        console.print(f"[yellow]配置文件不存在: {config_file}，使用默认配置[/yellow]")
        config = {}

    project_store = ProjectStore(base_dir=output_dir)
    return Pipeline(config, project_store)


def create_pipeline_with_config(config: Dict[str, Any], output_dir: str = "./projects") -> Pipeline:
    """
    使用字典配置创建 Pipeline 实例

    Args:
        config: 配置字典
        output_dir: 输出目录

    Returns:
        Pipeline 实例
    """
    project_store = ProjectStore(base_dir=output_dir)
    return Pipeline(config, project_store)


async def run_with_progress(
    pipeline: Pipeline,
    input_path: str,
    output_dir: str = "./projects",
    stages: List[str] = None,
    enable_image: bool = False,
    project_id: str = None,
    project_name: str = None,
) -> PipelineContext:
    """
    带进度显示的 Pipeline 运行

    Args:
        pipeline: Pipeline 实例
        input_path: 输入文件路径
        output_dir: 输出目录
        stages: 执行的阶段
        enable_image: 是否启用图片生成
        project_id: 项目ID
        project_name: 项目名称

    Returns:
        PipelineContext 对象
    """
    return await pipeline.run(
        input_path=input_path,
        output_dir=output_dir,
        stages=stages,
        enable_image=enable_image,
        project_id=project_id,
        project_name=project_name,
    )


def format_results(context: PipelineContext) -> str:
    """
    格式化流水线执行结果为可读字符串

    Args:
        context: PipelineContext 对象

    Returns:
        格式化的结果字符串
    """
    lines = []
    lines.append("=" * 60)
    lines.append(f"项目: {context.project.novel_title} ({context.project.id})")
    lines.append("=" * 60)
    lines.append("")

    lines.append("[阶段执行结果]")
    stage_names = {
        "preprocess": "预处理",
        "world_bible": "世界观构建",
        "extract": "实体提取",
        "merge": "实体合并",
        "attribute": "属性构建",
        "prompt": "提示词生成",
        "illustrate": "图片生成",
    }

    for stage, result in context.stage_results.items():
        status = "✓ 成功" if result.success else "✗ 失败"
        lines.append(f"  {stage_names.get(stage, stage)}: {status} ({result.duration:.2f}s)")
        if result.error:
            lines.append(f"    错误: {result.error}")

    lines.append("")
    lines.append("[统计信息]")
    lines.append(f"  章节数: {len(context.chapters)}")
    lines.append(f"  实体数: {len(context.entities)}")
    lines.append(f"  提示词数: {len(context.prompts)}")

    if context.world_bible:
        lines.append("")
        lines.append("[世界观概要]")
        lines.append(f"  类型: {context.world_bible.world_framework.genre}")
        lines.append(f"  时代: {context.world_bible.world_framework.era_setting}")
        lines.append(f"  艺术风格: {context.world_bible.visual_anchoring.art_style}")

    lines.append("")
    lines.append("=" * 60)

    return "\n".join(lines)


def format_entity_summary(entities: List[Dict[str, Any]]) -> str:
    """
    格式化实体列表为摘要

    Args:
        entities: 实体列表

    Returns:
        格式化的摘要字符串
    """
    if not entities:
        return "无实体"

    stats = {}
    for e in entities:
        etype = e.get('type', 'unknown')
        stats[etype] = stats.get(etype, 0) + 1

    parts = []
    for etype, count in sorted(stats.items()):
        parts.append(f"{etype}: {count}")

    return ", ".join(parts)


def format_prompt_summary(prompts: List[Dict[str, Any]]) -> str:
    """
    格式化提示词列表为摘要

    Args:
        prompts: 提示词列表

    Returns:
        格式化的摘要字符串
    """
    if not prompts:
        return "无提示词"

    total = len(prompts)
    stats = {}

    for p in prompts:
        ptype = p.get('type', 'unknown')
        stats[ptype] = stats.get(ptype, 0) + 1

    parts = [f"共 {total} 个"]
    for ptype, count in sorted(stats.items()):
        parts.append(f"{ptype}: {count}")

    return " | ".join(parts)


def load_project_context(project_id: str, project_store: ProjectStore = None) -> Optional[Dict[str, Any]]:
    """
    加载项目完整上下文

    Args:
        project_id: 项目ID
        project_store: 项目存储实例

    Returns:
        包含所有项目数据的字典
    """
    if project_store is None:
        project_store = ProjectStore()

    if not project_store.project_exists(project_id):
        return None

    context = {}

    try:
        context['project_info'] = project_store.load_project_info(project_id)
    except FileNotFoundError:
        context['project_info'] = {}

    try:
        context['chapters'] = project_store.load_chapters(project_id)
    except FileNotFoundError:
        context['chapters'] = []

    try:
        context['entities'] = project_store.load_entities(project_id)
    except FileNotFoundError:
        context['entities'] = []

    try:
        context['world_bible'] = project_store.load_world_bible(project_id)
    except FileNotFoundError:
        context['world_bible'] = None

    try:
        context['prompts'] = project_store.load_prompts(project_id)
    except FileNotFoundError:
        context['prompts'] = []

    return context


def export_project_to_json(project_id: str, output_path: str = None) -> str:
    """
    导出项目完整数据到 JSON 文件

    Args:
        project_id: 项目ID
        output_path: 输出文件路径（可选）

    Returns:
        输出文件路径
    """
    context = load_project_context(project_id)

    if context is None:
        raise ValueError(f"项目不存在: {project_id}")

    if output_path is None:
        store = ProjectStore()
        project_dir = store.get_project_dir(project_id)
        output_path = str(project_dir / f"{project_id}_export.json")

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(context, f, ensure_ascii=False, indent=2)

    return output_path


def create_progress_table() -> Table:
    """
    创建进度显示表格

    Returns:
        Rich Table 实例
    """
    table = Table(box=box.ROUNDED, show_header=True)
    table.add_column("阶段", style="cyan", width=20)
    table.add_column("状态", style="white", width=10)
    table.add_column("进度", style="green")
    table.add_column("耗时", justify="right", width=10)
    return table


class PipelineRunner:
    """
    Pipeline 运行器封装

    提供更高级的 Pipeline 运行接口，支持：
    - 增量处理
    - 断点恢复
    - 结果缓存
    """

    def __init__(self, config: Dict[str, Any] = None, output_dir: str = "./projects"):
        """
        初始化 PipelineRunner

        Args:
            config: 配置字典
            output_dir: 输出目录
        """
        self.config = config or {}
        self.output_dir = output_dir
        self.project_store = ProjectStore(base_dir=output_dir)
        self.pipeline = Pipeline(self.config, self.project_store)

    async def run_full(
        self,
        input_path: str,
        project_name: str = None,
        enable_image: bool = False,
    ) -> PipelineContext:
        """
        运行完整流水线

        Args:
            input_path: 输入文件路径
            project_name: 项目名称
            enable_image: 是否启用图片生成

        Returns:
            PipelineContext 对象
        """
        console.print(Panel.fit(
            "[bold cyan]AI拆书生图流水线[/bold cyan]",
            border_style="cyan"
        ))

        return await self.pipeline.run(
            input_path=input_path,
            output_dir=self.output_dir,
            stages=None,
            enable_image=enable_image,
            project_name=project_name,
        )

    async def run_stages(
        self,
        project_id: str,
        stages: List[str],
    ) -> PipelineContext:
        """
        运行指定阶段

        Args:
            project_id: 项目ID
            stages: 要执行的阶段列表

        Returns:
            PipelineContext 对象
        """
        project_info = self.project_store.load_project_info(project_id)
        input_path = project_info.get('input_path', '')

        if not input_path or not Path(input_path).exists():
            raise FileNotFoundError(f"无法找到输入文件: {input_path}")

        context = await self.pipeline.run(
            input_path=input_path,
            output_dir=self.output_dir,
            stages=stages,
            enable_image=False,
            project_id=project_id,
        )

        return context

    async def resume(
        self,
        project_id: str,
    ) -> PipelineContext:
        """
        恢复项目执行

        Args:
            project_id: 项目ID

        Returns:
            PipelineContext 对象
        """
        context = load_project_context(project_id, self.project_store)

        if context is None:
            raise ValueError(f"项目不存在: {project_id}")

        input_path = context['project_info'].get('input_path', '')

        if not input_path or not Path(input_path).exists():
            raise FileNotFoundError(f"无法找到输入文件: {input_path}")

        existing_chapters = set(c['id'] for c in context['chapters'])

        context_obj = await self.pipeline.run(
            input_path=input_path,
            output_dir=self.output_dir,
            stages=None,
            enable_image=False,
            project_id=project_id,
        )

        return context_obj

    def get_project_status(self, project_id: str) -> Dict[str, Any]:
        """
        获取项目状态

        Args:
            project_id: 项目ID

        Returns:
            项目状态字典
        """
        context = load_project_context(project_id, self.project_store)

        if context is None:
            return {"exists": False}

        status = {
            "exists": True,
            "has_chapters": len(context['chapters']) > 0,
            "has_entities": len(context['entities']) > 0,
            "has_world_bible": context['world_bible'] is not None,
            "has_prompts": len(context['prompts']) > 0,
            "chapter_count": len(context['chapters']),
            "entity_count": len(context['entities']),
            "prompt_count": len(context['prompts']),
        }

        status["completion"] = 0
        if status["has_chapters"]:
            status["completion"] += 25
        if status["has_world_bible"]:
            status["completion"] += 25
        if status["has_entities"]:
            status["completion"] += 25
        if status["has_prompts"]:
            status["completion"] += 25

        return status
