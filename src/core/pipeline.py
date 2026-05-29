"""
Pipeline 编排器 - 负责串联所有模块形成完整的流水线
"""
import asyncio
import hashlib
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn
from rich.console import Console
from rich.table import Table

from src.models.project import Project, ProjectStatus
from src.models.chapter import Chapter
from src.models.entity import Entity, EntityType
from src.models.world_bible import WorldBible
from src.models.prompt import Prompt

from src.core.preprocessor import Preprocessor
from src.core.world_bible_builder import WorldBibleBuilder
from src.core.entity_extractor import EntityExtractor
from src.core.entity_merger import EntityMerger
from src.core.attribute_builder import AttributeBuilder
from src.core.prompt_generator import PromptGenerator
from src.core.face_anchor import FaceAnchorGenerator
from src.core.image_generator import ImageGenerator

from src.storage.project_store import ProjectStore
from src.llm.adapter import LLMAdapter
from src.llm.prompt_loader import PromptLoader

console = Console()


@dataclass
class StageResult:
    """阶段执行结果"""
    stage: str
    success: bool
    data: Any = None
    error: Optional[str] = None
    duration: float = 0.0


@dataclass
class PipelineContext:
    """流水线上下文"""
    project: Project
    text: str = ""
    chapters: List[Chapter] = field(default_factory=list)
    world_bible: Optional[WorldBible] = None
    entities: List[Entity] = field(default_factory=list)
    prompts: List[Prompt] = field(default_factory=list)
    stage_results: Dict[str, StageResult] = field(default_factory=dict)
    processed_chapters: set = field(default_factory=set)


class Pipeline:
    """
    图片生成流水线编排器

    完整流程：
    1. 预处理 - 读取文件并分割章节
    2. 世界观构建 - 分析文本构建 WorldBible
    3. 实体提取 - 从章节中提取角色、场景、物品
    4. 实体合并 - 去重和归一化实体
    5. 属性构建 - 为实体构建视觉属性
    6. 提示词生成 - 生成 AI 绘画提示词
    7. 图片生成 - 生成实体插画（可选）
    """

    def __init__(self, config: Dict[str, Any], project_store: Optional[ProjectStore] = None):
        """
        初始化流水线

        Args:
            config: 配置字典
            project_store: 项目存储实例
        """
        self.config = config
        self.project_store = project_store or ProjectStore()
        self._components: Dict[str, Any] = {}

        self._preprocessor: Optional[Preprocessor] = None
        self._world_bible_builder: Optional[WorldBibleBuilder] = None
        self._entity_extractor: Optional[EntityExtractor] = None
        self._entity_merger: Optional[EntityMerger] = None
        self._attribute_builder: Optional[AttributeBuilder] = None
        self._prompt_generator: Optional[PromptGenerator] = None
        self._face_anchor_generator: Optional[FaceAnchorGenerator] = None
        self._image_generator: Optional[ImageGenerator] = None

        self._llm_adapter: Optional[LLMAdapter] = None
        self._prompt_loader: Optional[PromptLoader] = None

    def _init_components(self) -> None:
        """初始化所有组件"""
        if self._llm_adapter is None:
            self._llm_adapter = LLMAdapter(self.config)

        if self._prompt_loader is None:
            prompts_dir = self.config.get("prompts_dir")
            if prompts_dir:
                self._prompt_loader = PromptLoader(prompts_dir)
            else:
                self._prompt_loader = PromptLoader()

        extraction_config = self.config.get("extraction", {})

        if self._preprocessor is None:
            self._preprocessor = Preprocessor(self.config)

        if self._world_bible_builder is None and self._llm_adapter and self._prompt_loader:
            self._world_bible_builder = WorldBibleBuilder(
                self._llm_adapter,
                self._prompt_loader,
                max_retries=extraction_config.get("max_retries", 3)
            )

        if self._entity_extractor is None and self._llm_adapter and self._prompt_loader:
            self._entity_extractor = EntityExtractor(
                self._llm_adapter,
                self._prompt_loader,
                config=extraction_config
            )

        if self._entity_merger is None:
            self._entity_merger = EntityMerger(extraction_config)

        if self._attribute_builder is None and self._llm_adapter and self._prompt_loader:
            self._attribute_builder = AttributeBuilder(
                self._llm_adapter,
                self._prompt_loader,
                max_retries=extraction_config.get("max_retries", 3)
            )

        if self._prompt_generator is None and self._llm_adapter and self._prompt_loader:
            prompt_config = self.config.get("prompt", {})
            self._prompt_generator = PromptGenerator(
                self._llm_adapter,
                self._prompt_loader,
                config=prompt_config
            )

    def add_component(self, name: str, component: Any) -> None:
        """
        添加组件到流水线

        Args:
            name: 组件名称
            component: 组件实例
        """
        self._components[name] = component

        component_map = {
            "preprocessor": Preprocessor,
            "world_bible_builder": WorldBibleBuilder,
            "entity_extractor": EntityExtractor,
            "entity_merger": EntityMerger,
            "attribute_builder": AttributeBuilder,
            "prompt_generator": PromptGenerator,
            "face_anchor_generator": FaceAnchorGenerator,
            "image_generator": ImageGenerator,
        }

        if name in component_map:
            attr_name = f"_{name}"
            setattr(self, attr_name, component)

    async def run(
        self,
        input_path: str,
        output_dir: str = "",
        stages: List[str] = None,
        enable_image: bool = False,
        project_id: str = None,
        project_name: str = None,
    ) -> PipelineContext:
        """
        运行完整的流水线

        Args:
            input_path: 小说文件路径
            output_dir: 输出目录
            stages: 执行的阶段，None 表示全部
            enable_image: 是否启用图片生成
            project_id: 项目ID（可选）
            project_name: 项目名称（可选）

        Returns:
            PipelineContext 对象
        """
        self._init_components()

        if stages is None:
            stages = ["preprocess", "world_bible", "extract", "merge", "prompt"]
            if enable_image:
                stages.append("illustrate")

        if project_id is None:
            project_id = hashlib.md5(f"{input_path}_{time.time()}".encode()).hexdigest()[:12]

        if project_name is None:
            project_name = Path(input_path).stem

        project = Project(
            id=project_id,
            novel_title=project_name,
            input_path=input_path,
            status=ProjectStatus.CREATED,
        )

        if not self.project_store.project_exists(project_id):
            self.project_store.create_project(project_id, project_name, self.config)

        context = PipelineContext(project=project)

        console.print(Panel.fit(
            f"[bold cyan]AI拆书生图流水线[/bold cyan]\n"
            f"项目: {project_name} ({project_id})",
            border_style="cyan"
        ))

        stage_descriptions = {
            "preprocess": "预处理：读取文件并分割章节",
            "world_bible": "构建世界观圣经",
            "extract": "提取实体",
            "merge": "合并实体",
            "attribute": "构建属性",
            "prompt": "生成提示词",
            "illustrate": "生成图片",
        }

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            main_task = progress.add_task("[cyan]流水线执行中...", total=None)

            if "preprocess" in stages:
                progress.update(main_task, description=f"[cyan]阶段 1/6: {stage_descriptions.get('preprocess', '预处理')}")
                context = await self._stage_preprocess(context, input_path, progress)
                if context is None:
                    return None
                progress.advance(main_task)

            if "world_bible" in stages and context:
                progress.update(main_task, description=f"[cyan]阶段 2/6: {stage_descriptions.get('world_bible', '世界观构建')}")
                context = await self._stage_world_bible(context, progress)
                if context is None:
                    return None
                progress.advance(main_task)

            if "extract" in stages and context:
                progress.update(main_task, description=f"[cyan]阶段 3/6: {stage_descriptions.get('extract', '实体提取')}")
                context = await self._stage_extract(context, progress)
                if context is None:
                    return None
                progress.advance(main_task)

            if "merge" in stages and context:
                progress.update(main_task, description=f"[cyan]阶段 4/6: {stage_descriptions.get('merge', '实体合并')}")
                context = await self._stage_merge(context, progress)
                if context is None:
                    return None
                progress.advance(main_task)

            if "attribute" in stages and context:
                progress.update(main_task, description=f"[cyan]阶段 5/6: {stage_descriptions.get('attribute', '属性构建')}")
                context = await self._stage_attribute(context, progress)
                if context is None:
                    return None
                progress.advance(main_task)

            if "prompt" in stages and context:
                progress.update(main_task, description=f"[cyan]阶段 6/6: {stage_descriptions.get('prompt', '提示词生成')}")
                context = await self._stage_prompt(context, progress)
                if context is None:
                    return None
                progress.advance(main_task)

            if "illustrate" in stages and context and enable_image:
                progress.update(main_task, description=f"[cyan]图片生成: {stage_descriptions.get('illustrate', '生成图片')}")
                await self._stage_illustrate(context, progress)
                progress.advance(main_task)

        self._display_summary(context)
        return context

    async def _stage_preprocess(
        self,
        context: PipelineContext,
        input_path: str,
        progress: Progress = None,
    ) -> PipelineContext:
        """阶段1：预处理 - 读取文件并分割章节"""
        start_time = time.time()
        task_desc = f"[cyan]预处理章节...[/cyan]" if progress else None

        try:
            if task_desc:
                progress.update(progress.task_ids[0] if progress.task_ids else 0, description=task_desc)

            text = self._preprocessor.read_file(input_path)
            text = self._preprocessor.clean_text(text)
            context.text = text

            chapters = self._preprocessor.split_chapters(text, context.project.id)
            context.chapters = chapters

            self.project_store.save_chapters(
                context.project.id,
                [c.model_dump() for c in chapters]
            )

            context.project.status = ProjectStatus.EXTRACTING

            result = StageResult(
                stage="preprocess",
                success=True,
                data={"chapter_count": len(chapters)},
                duration=time.time() - start_time,
            )
            context.stage_results["preprocess"] = result

            console.print(f"[green]✓[/green] 预处理完成: {len(chapters)} 个章节")

            return context

        except Exception as e:
            console.print(f"[red]✗[/red] 预处理失败: {str(e)}")
            result = StageResult(
                stage="preprocess",
                success=False,
                error=str(e),
                duration=time.time() - start_time,
            )
            context.stage_results["preprocess"] = result
            return None

    async def _stage_world_bible(
        self,
        context: PipelineContext,
        progress: Progress = None,
    ) -> PipelineContext:
        """阶段2：构建世界观圣经"""
        start_time = time.time()
        task_desc = f"[cyan]构建世界观圣经...[/cyan]" if progress else None

        if self._world_bible_builder is None:
            console.print("[yellow]![/yellow] WorldBibleBuilder 未初始化，跳过")
            return context

        try:
            if task_desc and progress.task_ids:
                progress.update(progress.task_ids[0], description=task_desc)

            wb_config = self.config.get("world_bible", {})
            analysis_chapters = wb_config.get("analysis_chapters", 5)

            analysis_text = "\n".join([c.text for c in context.chapters[:analysis_chapters]])

            world_bible = await self._world_bible_builder.analyze(
                text=analysis_text,
                novel_title=context.project.novel_title,
                project_id=context.project.id,
            )

            context.world_bible = world_bible
            context.project.world_bible_id = world_bible.id
            context.project.status = ProjectStatus.WORLD_BIBLE_DONE

            self.project_store.save_world_bible(
                context.project.id,
                world_bible.model_dump()
            )

            result = StageResult(
                stage="world_bible",
                success=True,
                data={"world_bible_id": world_bible.id},
                duration=time.time() - start_time,
            )
            context.stage_results["world_bible"] = result

            console.print(f"[green]✓[/green] 世界观构建完成: {world_bible.world_framework.genre} / {world_bible.world_framework.era_setting}")

            return context

        except Exception as e:
            console.print(f"[red]✗[/red] 世界观构建失败: {str(e)}")
            result = StageResult(
                stage="world_bible",
                success=False,
                error=str(e),
                duration=time.time() - start_time,
            )
            context.stage_results["world_bible"] = result
            return context

    async def _stage_extract(
        self,
        context: PipelineContext,
        progress: Progress = None,
    ) -> PipelineContext:
        """阶段3：提取实体"""
        start_time = time.time()

        if self._entity_extractor is None:
            console.print("[yellow]![/yellow] EntityExtractor 未初始化，跳过")
            return context

        try:
            chapters_to_process = [
                c for c in context.chapters
                if c.id not in context.processed_chapters
            ]

            if not chapters_to_process:
                console.print("[yellow]![/yellow] 没有需要处理的章节")
                return context

            extraction_config = self.config.get("extraction", {})
            max_parallel = extraction_config.get("max_chapters_parallel", 3)

            semaphore = asyncio.Semaphore(max_parallel)
            all_candidates = []

            async def extract_from_chapter(chapter: Chapter) -> List[dict]:
                async with semaphore:
                    if context.world_bible:
                        candidates = await self._entity_extractor.extract_from_chapter(
                            chapter=chapter,
                            world_bible=context.world_bible,
                            existing_entities=context.entities,
                        )
                        return candidates
                    return []

            tasks = [extract_from_chapter(c) for c in chapters_to_process]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for r in results:
                if isinstance(r, list):
                    all_candidates.extend(r)
                elif isinstance(r, Exception):
                    console.print(f"[yellow]章节处理异常: {r}[/yellow]")

            context.processed_chapters.update(c.id for c in chapters_to_process)

            result = StageResult(
                stage="extract",
                success=True,
                data={"candidates": len(all_candidates)},
                duration=time.time() - start_time,
            )
            context.stage_results["extract"] = result

            console.print(f"[green]✓[/green] 实体提取完成: {len(all_candidates)} 个候选实体")

            if all_candidates and context._components.get("_pending_candidates"):
                context._components["_pending_candidates"].extend(all_candidates)
            else:
                context._components["_pending_candidates"] = all_candidates

            return context

        except Exception as e:
            console.print(f"[red]✗[/red] 实体提取失败: {str(e)}")
            result = StageResult(
                stage="extract",
                success=False,
                error=str(e),
                duration=time.time() - start_time,
            )
            context.stage_results["extract"] = result
            return context

    async def _stage_merge(
        self,
        context: PipelineContext,
        progress: Progress = None,
    ) -> PipelineContext:
        """阶段4：合并实体"""
        start_time = time.time()

        if self._entity_merger is None:
            console.print("[yellow]![/yellow] EntityMerger 未初始化，跳过")
            return context

        try:
            pending_candidates = context._components.get("_pending_candidates", [])

            if not pending_candidates:
                console.print("[yellow]![/yellow] 没有待合并的候选实体")
                return context

            merged_entities = self._entity_merger.merge(
                candidates=pending_candidates,
                existing=context.entities,
                project_id=context.project.id,
            )

            context.entities = merged_entities
            context._components["_pending_candidates"] = []

            self.project_store.save_entities(
                context.project.id,
                [e.model_dump() for e in merged_entities]
            )

            result = StageResult(
                stage="merge",
                success=True,
                data={"entity_count": len(merged_entities)},
                duration=time.time() - start_time,
            )
            context.stage_results["merge"] = result

            entity_stats = {}
            for e in merged_entities:
                type_str = e.type.value
                entity_stats[type_str] = entity_stats.get(type_str, 0) + 1

            stats_str = ", ".join([f"{k}: {v}" for k, v in entity_stats.items()])
            console.print(f"[green]✓[/green] 实体合并完成: {len(merged_entities)} 个实体 ({stats_str})")

            return context

        except Exception as e:
            console.print(f"[red]✗[/red] 实体合并失败: {str(e)}")
            result = StageResult(
                stage="merge",
                success=False,
                error=str(e),
                duration=time.time() - start_time,
            )
            context.stage_results["merge"] = result
            return context

    async def _stage_attribute(
        self,
        context: PipelineContext,
        progress: Progress = None,
    ) -> PipelineContext:
        """阶段5：构建属性"""
        start_time = time.time()

        if self._attribute_builder is None:
            console.print("[yellow]![/yellow] AttributeBuilder 未初始化，跳过")
            return context

        if not context.world_bible:
            console.print("[yellow]![/yellow] 没有 WorldBible，跳过属性构建")
            return context

        try:
            entities_to_process = [
                e for e in context.entities
                if not e.attributes
            ]

            if not entities_to_process:
                console.print("[yellow]![/yellow] 所有实体已有属性")
                return context

            semaphore = asyncio.Semaphore(3)
            updated_entities = []

            async def build_entity_attribute(entity: Entity) -> Entity:
                async with semaphore:
                    return await self._attribute_builder.build_attributes(
                        entity=entity,
                        world_bible=context.world_bible,
                    )

            tasks = [build_entity_attribute(e) for e in entities_to_process]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for i, r in enumerate(results):
                if isinstance(r, Entity):
                    updated_entities.append(r)
                else:
                    updated_entities.append(entities_to_process[i])

            for i, e in enumerate(entities_to_process):
                for u in updated_entities:
                    if u.id == e.id:
                        idx = context.entities.index(e)
                        context.entities[idx] = u
                        break

            self.project_store.save_entities(
                context.project.id,
                [e.model_dump() for e in context.entities]
            )

            result = StageResult(
                stage="attribute",
                success=True,
                data={"processed": len(updated_entities)},
                duration=time.time() - start_time,
            )
            context.stage_results["attribute"] = result

            console.print(f"[green]✓[/green] 属性构建完成: {len(updated_entities)} 个实体")

            return context

        except Exception as e:
            console.print(f"[red]✗[/red] 属性构建失败: {str(e)}")
            result = StageResult(
                stage="attribute",
                success=False,
                error=str(e),
                duration=time.time() - start_time,
            )
            context.stage_results["attribute"] = result
            return context

    async def _stage_prompt(
        self,
        context: PipelineContext,
        progress: Progress = None,
    ) -> PipelineContext:
        """阶段6：生成提示词"""
        start_time = time.time()

        if self._prompt_generator is None:
            console.print("[yellow]![/yellow] PromptGenerator 未初始化，跳过")
            return context

        if not context.world_bible:
            console.print("[yellow]![/yellow] 没有 WorldBible，跳过提示词生成")
            return context

        try:
            entities_to_process = context.entities

            if not entities_to_process:
                console.print("[yellow]![/yellow] 没有可生成提示词的实体")
                return context

            semaphore = asyncio.Semaphore(3)
            generated_prompts = []

            async def generate_entity_prompt(entity: Entity) -> Prompt:
                async with semaphore:
                    return await self._prompt_generator.generate(
                        entity=entity,
                        world_bible=context.world_bible,
                    )

            tasks = [generate_entity_prompt(e) for e in entities_to_process]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for r in results:
                if isinstance(r, Prompt):
                    generated_prompts.append(r)

            context.prompts = generated_prompts

            self.project_store.save_prompts(
                context.project.id,
                [p.model_dump() for p in generated_prompts]
            )

            self.project_store.save_prompts_md(
                context.project.id,
                [p.model_dump() for p in generated_prompts],
                "prompts.md"
            )

            result = StageResult(
                stage="prompt",
                success=True,
                data={"prompt_count": len(generated_prompts)},
                duration=time.time() - start_time,
            )
            context.stage_results["prompt"] = result

            console.print(f"[green]✓[/green] 提示词生成完成: {len(generated_prompts)} 个提示词")

            return context

        except Exception as e:
            console.print(f"[red]✗[/red] 提示词生成失败: {str(e)}")
            result = StageResult(
                stage="prompt",
                success=False,
                error=str(e),
                duration=time.time() - start_time,
            )
            context.stage_results["prompt"] = result
            return context

    async def _stage_illustrate(
        self,
        context: PipelineContext,
        progress: Progress = None,
    ) -> Dict[str, Any]:
        """阶段7：生成图片"""
        start_time = time.time()

        console.print("[yellow]![/yellow] 图片生成需要配置后端，当前跳过")

        result = StageResult(
            stage="illustrate",
            success=True,
            data={"message": "图片生成跳过（未配置后端）"},
            duration=time.time() - start_time,
        )
        context.stage_results["illustrate"] = result

        return {"message": "图片生成跳过"}

    def _display_summary(self, context: PipelineContext) -> None:
        """显示流水线执行摘要"""
        console.print("\n[bold green]流水线执行完成！[/bold green]\n")

        table = Table(title="执行摘要", box=box.ROUNDED)
        table.add_column("阶段", style="cyan")
        table.add_column("状态", style="white")
        table.add_column("耗时", style="green")

        stage_names = {
            "preprocess": "预处理",
            "world_bible": "世界观构建",
            "extract": "实体提取",
            "merge": "实体合并",
            "attribute": "属性构建",
            "prompt": "提示词生成",
            "illustrate": "图片生成",
        }

        total_duration = 0.0
        for stage, stage_result in context.stage_results.items():
            status = "[green]✓ 成功[/green]" if stage_result.success else f"[red]✗ 失败[/red]"
            duration_str = f"{stage_result.duration:.2f}s"
            table.add_row(stage_names.get(stage, stage), status, duration_str)
            total_duration += stage_result.duration

        table.add_row("[bold]总计[/bold]", "", f"[bold]{total_duration:.2f}s[/bold]")
        console.print(table)

        console.print(f"\n项目ID: [cyan]{context.project.id}[/cyan]")
        console.print(f"章节数: {len(context.chapters)}")
        console.print(f"实体数: {len(context.entities)}")
        console.print(f"提示词数: {len(context.prompts)}")


from rich import box


async def run_pipeline(
    input_path: str,
    config: Dict[str, Any],
    output_dir: str = "",
    stages: List[str] = None,
    enable_image: bool = False,
) -> PipelineContext:
    """
    运行流水线的便捷函数

    Args:
        input_path: 小说文件路径
        config: 配置字典
        output_dir: 输出目录
        stages: 执行的阶段
        enable_image: 是否启用图片生成

    Returns:
        PipelineContext 对象
    """
    project_store = ProjectStore(base_dir=output_dir) if output_dir else None
    pipeline = Pipeline(config, project_store)
    return await pipeline.run(
        input_path=input_path,
        output_dir=output_dir,
        stages=stages,
        enable_image=enable_image,
    )
