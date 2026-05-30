#!/usr/bin/env python3
"""
AI拆书生图 - CLI 命令行接口
"""
from typing import Optional, Dict, Any
from pathlib import Path
import shutil
import asyncio
import click
import yaml
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich import box

console = Console()


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """加载配置文件
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        配置字典
    """
    if config_path:
        config_file = Path(config_path)
    else:
        config_file = Path(__file__).parent.parent.parent / 'config' / 'default.yaml'
    
    if not config_file.exists():
        console.print(f"[yellow]配置文件不存在: {config_file}[/yellow]")
        return {}
    
    with open(config_file, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


@click.group()
@click.version_option(version="0.1.0")
@click.option(
    '--config',
    '-c',
    type=click.Path(exists=True),
    help='配置文件路径'
)
@click.pass_context
def cli(ctx, config):
    """AI拆书生图 - 小说插画生成工具
    
    用于将小说文本转换为AI图像生成提示词的工具。
    """
    ctx.ensure_object(dict)
    ctx.obj['config'] = load_config(config)
    ctx.obj['config_path'] = config


@cli.command()
@click.argument('book_path', type=click.Path(exists=True))
@click.option('--name', '-n', prompt='项目名称', help='项目名称')
@click.option('--output', '-o', default='./projects', help='输出目录')
@click.pass_context
def init(ctx, book_path: str, name: str, output: str):
    """初始化新项目
    
    BOOK_PATH: 书籍文件路径（支持.txt文件）
    """
    config = ctx.obj.get('config', {})
    
    console.print(Panel.fit(
        "[bold cyan]初始化新项目[/bold cyan]",
        border_style="cyan"
    ))
    
    from src.storage.project_store import ProjectStore
    
    import hashlib
    import time
    project_id = hashlib.md5(f"{name}_{time.time()}".encode()).hexdigest()[:12]
    
    store = ProjectStore(base_dir=output)
    
    console.print(f"\n[green]创建项目目录...[/green]")
    project_dir = store.create_project(project_id, name, config)
    console.print(f"[green]✓[/green] 项目目录: {project_dir}")
    
    book_name = Path(book_path).name
    console.print(f"\n[green]复制书籍文件...[/green]")
    data_dir = project_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(book_path, data_dir / book_name)
    console.print(f"[green]✓[/green] 书籍文件: {book_name}")
    
    console.print("\n[bold green]项目初始化完成！[/bold green]")
    console.print(f"\n项目ID: [cyan]{project_id}[/cyan]")
    console.print(f"项目路径: [cyan]{project_dir}[/cyan]")
    
    console.print("\n下一步:")
    console.print(f"  [yellow]python -m src.cli run --input {project_dir}/data/{book_name}[/yellow] - 运行流水线")
    console.print(f"  [yellow]python -m src.cli info {project_id}[/yellow] - 查看项目信息")


@cli.command()
@click.option("--input", "-i", "input_path", required=True, help="小说文件路径")
@click.option("--output", "-o", "output_dir", default=None, help="输出目录")
@click.option("--stages", "-s", default="all", help="执行阶段: all/preprocess/world_bible/extract/merge/attribute/prompt/illustrate")
@click.option("--enable-image", is_flag=True, default=False, help="启用图片生成")
@click.option("--skip-confirm", is_flag=True, default=False, help="跳过确认提示")
@click.option("--name", "-n", default=None, help="项目名称（默认使用文件名）")
@click.pass_context
def run(ctx, input_path: str, output_dir: str, stages: str, enable_image: bool, skip_confirm: bool, name: str):
    """运行完整的AI拆书生图流水线
    
    完整流程：预处理 → 世界观构建 → 实体提取 → 实体合并 → 属性构建 → 提示词生成
    
    示例:
    
        python -m src.cli run --input ./novel.txt
        
        python -m src.cli run --input ./novel.txt --stages world_bible,extract
        
        python -m src.cli run --input ./novel.txt --enable-image
    """
    config = ctx.obj.get('config', {})
    
    if not Path(input_path).exists():
        console.print(f"[red]错误: 文件不存在: {input_path}[/red]")
        return
    
    if stages == "all":
        stage_list = None
    else:
        stage_list = [s.strip() for s in stages.split(',')]
    
    project_name = name or Path(input_path).stem
    
    console.print(Panel.fit(
        f"[bold cyan]运行流水线[/bold cyan]\n"
        f"文件: {input_path}\n"
        f"项目: {project_name}",
        border_style="cyan"
    ))
    
    console.print("\n[cyan]流水线阶段:[/cyan]")
    if stage_list is None:
        console.print("  全部阶段")
    else:
        for s in stage_list:
            console.print(f"  - {s}")
    
    if enable_image:
        console.print("\n[yellow]注意: 图片生成已启用[/yellow]")
    
    if not skip_confirm:
        if not click.confirm('\n确认开始执行?'):
            console.print("[yellow]取消执行[/yellow]")
            return
    
    from src.core.pipeline import Pipeline
    from src.storage.project_store import ProjectStore
    
    store = ProjectStore(base_dir=output_dir) if output_dir else ProjectStore()
    pipeline = Pipeline(config, store)
    
    try:
        context = asyncio.run(pipeline.run(
            input_path=input_path,
            output_dir=output_dir or "./projects",
            stages=stage_list,
            enable_image=enable_image,
            project_name=project_name,
        ))
        
        if context:
            console.print(f"\n[bold green]流水线执行成功！[/bold green]")
            console.print(f"项目ID: [cyan]{context.project.id}[/cyan]")
            console.print(f"\n查看结果:")
            console.print(f"  [yellow]python -m src.cli info {context.project.id}[/yellow] - 查看项目信息")
            console.print(f"  [yellow]python -m src.cli prompt {context.project.id} <prompt_id>[/yellow] - 查看提示词详情")
    
    except Exception as e:
        console.print(f"\n[red]流水线执行失败: {str(e)}[/red]")
        import traceback
        traceback.print_exc()


@cli.command()
@click.argument('project_id')
@click.option('--book-path', '-b', type=click.Path(exists=True), help='书籍文件路径')
@click.option('--chapters', '-c', default='0', help='分析章节数量（0表示全部）')
@click.pass_context
def resume(ctx, project_id: str, book_path: Optional[str], chapters: str):
    """从断点恢复项目执行
    
    PROJECT_ID: 项目ID
    
    恢复执行中断的流水线，保留已有的处理结果。
    """
    config = ctx.obj.get('config', {})
    
    from src.storage.project_store import ProjectStore
    
    store = ProjectStore()
    
    if not store.project_exists(project_id):
        console.print(f"[red]项目不存在: {project_id}[/red]")
        return
    
    project_info = store.load_project_info(project_id)
    chapters_data = store.load_chapters(project_id)
    
    console.print(Panel.fit(
        f"[bold cyan]恢复项目: {project_id}[/bold cyan]",
        border_style="cyan"
    ))
    
    console.print(f"\n项目名称: {project_info.get('name', 'N/A')}")
    console.print(f"已处理章节: {len(chapters_data)}")
    
    try:
        from src.core.pipeline import Pipeline
        
        pipeline = Pipeline(config, store)
        
        chapters_arg = chapters if chapters != '0' else None
        
        context = asyncio.run(pipeline.run(
            input_path=project_info.get('input_path', ''),
            output_dir=str(store.base_dir),
            stages=None,
            enable_image=False,
            project_id=project_id,
        ))
        
        if context:
            console.print(f"\n[bold green]恢复执行成功！[/bold green]")
    
    except Exception as e:
        console.print(f"[red]恢复执行失败: {str(e)}[/red]")


@cli.command()
@click.argument('project_id')
@click.pass_context
def info(ctx, project_id: str):
    """查看项目信息
    
    PROJECT_ID: 项目ID
    
    显示项目的详细信息，包括：
    - 基本信息（ID、名称、创建时间）
    - 统计数据（章节数、实体数、提示词数）
    - 世界观概要
    """
    config = ctx.obj.get('config', {})
    
    from src.storage.project_store import ProjectStore
    
    store = ProjectStore()
    
    if not store.project_exists(project_id):
        console.print(f"[red]项目不存在: {project_id}[/red]")
        return
    
    project_info = store.load_project_info(project_id)
    chapters = store.load_chapters(project_id)
    entities = store.load_entities(project_id)
    prompts = store.load_prompts(project_id)
    
    try:
        world_bible = store.load_world_bible(project_id)
        has_wb = True
    except FileNotFoundError:
        world_bible = None
        has_wb = False
    
    console.print(Panel.fit(
        f"[bold cyan]项目信息: {project_id}[/bold cyan]",
        border_style="cyan"
    ))
    
    table = Table(box=box.ROUNDED)
    table.add_column("属性", style="cyan")
    table.add_column("值", style="white")
    
    table.add_row("ID", project_info.get('id', 'N/A'))
    table.add_row("名称", project_info.get('name', 'N/A'))
    table.add_row("创建时间", project_info.get('created_at', 'N/A')[:19])
    
    project_dir = store.get_project_dir(project_id)
    table.add_row("路径", str(project_dir))
    
    console.print(table)
    
    stats_table = Table(title="统计信息", box=box.ROUNDED)
    stats_table.add_column("类型", style="cyan")
    stats_table.add_column("数量", style="white")
    
    stats_table.add_row("章节", str(len(chapters)))
    stats_table.add_row("实体", str(len(entities)))
    stats_table.add_row("提示词", str(len(prompts)))
    
    console.print(stats_table)
    
    entity_stats = {}
    for e in entities:
        etype = e.get('type', 'unknown')
        entity_stats[etype] = entity_stats.get(etype, 0) + 1
    
    if entity_stats:
        entity_table = Table(title="实体分布", box=box.ROUNDED)
        entity_table.add_column("类型", style="cyan")
        entity_table.add_column("数量", style="white")
        
        for etype, count in sorted(entity_stats.items()):
            entity_table.add_row(etype, str(count))
        
        console.print(entity_table)
    
    if has_wb and world_bible:
        wb_table = Table(title="世界观概要", box=box.ROUNDED)
        wb_table.add_column("属性", style="cyan")
        wb_table.add_column("值", style="white")
        
        framework = world_bible.get('world_framework', {})
        wb_table.add_row("类型", framework.get('genre', 'N/A'))
        wb_table.add_row("时代", framework.get('era_setting', 'N/A'))
        wb_table.add_row("力量体系", framework.get('power_system', 'N/A'))
        
        visual = world_bible.get('visual_anchoring', {})
        wb_table.add_row("艺术风格", visual.get('art_style', 'N/A'))
        
        console.print(wb_table)


@cli.command()
@click.argument('project_id')
@click.argument('prompt_id', required=False)
@click.option('--type', '-t', 'filter_type', default=None, help='按类型筛选 (character/scene/item)')
@click.option('--limit', '-l', default=10, help='显示数量限制')
@click.pass_context
def prompt(ctx, project_id: str, prompt_id: str, filter_type: str, limit: int):
    """查看和筛选提示词
    
    PROJECT_ID: 项目ID
    PROMPT_ID: 提示词ID（可选，显示特定提示词详情）
    
    示例:
    
        python -m src.cli prompt myproject                    # 列出所有提示词
        python -m src.cli prompt myproject --type character   # 只显示角色提示词
        python -m src.cli prompt myproject abc123             # 显示特定提示词详情
    """
    from src.storage.project_store import ProjectStore
    
    store = ProjectStore()
    
    if not store.project_exists(project_id):
        console.print(f"[red]项目不存在: {project_id}[/red]")
        return
    
    prompts = store.load_prompts(project_id)
    
    if prompt_id:
        target_prompt = None
        for p in prompts:
            if p.get('id') == prompt_id or p.get('entity_id') == prompt_id:
                target_prompt = p
                break
        
        if not target_prompt:
            console.print(f"[red]提示词不存在: {prompt_id}[/red]")
            return
        
        console.print(Panel.fit(
            f"[bold cyan]提示词详情: {prompt_id}[/bold cyan]",
            border_style="cyan"
        ))
        
        console.print(f"\n[cyan]类型:[/cyan] {target_prompt.get('type', 'N/A')}")
        console.print(f"[cyan]实体ID:[/cyan] {target_prompt.get('entity_id', 'N/A')}")
        
        params = target_prompt.get('parameters', {})
        console.print(f"\n[cyan]参数:[/cyan]")
        console.print(f"  宽高比: {params.get('aspect_ratio', '1:1')}")
        console.print(f"  步数: {params.get('steps', 30)}")
        console.print(f"  CFG: {params.get('cfg_scale', 7.0)}")
        console.print(f"  采样器: {params.get('sampler', 'DPM++ 2M Karras')}")
        
        console.print(f"\n[cyan]世界观前缀:[/cyan]")
        console.print(Panel(
            target_prompt.get('world_prefix_chinese', ''),
            border_style="blue"
        ))
        
        console.print(f"\n[cyan]正向提示词:[/cyan]")
        console.print(Panel(
            target_prompt.get('chinese_prompt', ''),
            border_style="green"
        ))
        
        if target_prompt.get('face_block_chinese'):
            console.print(f"\n[cyan]面容锁定:[/cyan]")
            console.print(Panel(
                target_prompt.get('face_block_chinese', ''),
                border_style="yellow"
            ))
        
        if target_prompt.get('negative_prompt'):
            console.print(f"\n[cyan]负向提示词:[/cyan]")
            console.print(Panel(
                target_prompt['negative_prompt'],
                border_style="red"
            ))
        
        if target_prompt.get('source_quotes'):
            console.print(f"\n[cyan]原文引用:[/cyan]")
            for sq in target_prompt.get('source_quotes', [])[:3]:
                chapter = sq.get('chapter', 'N/A')
                text = sq.get('text', '')[:100]
                console.print(f"  [{chapter}] {text}...")
    
    else:
        if filter_type:
            prompts = [p for p in prompts if p.get('type') == filter_type]
        
        if not prompts:
            console.print("[yellow]没有找到匹配的提示词[/yellow]")
            return
        
        console.print(Panel.fit(
            f"[bold cyan]提示词列表: {project_id}[/bold cyan]\n"
            f"共 {len(prompts)} 个提示词",
            border_style="cyan"
        ))
        
        table = Table(box=box.ROUNDED)
        table.add_column("ID", style="cyan")
        table.add_column("类型", style="yellow")
        table.add_column("中文提示词", style="white")
        table.add_column("参数", style="green")
        
        for p in prompts[:limit]:
            prompt_type = p.get('type', 'unknown')
            cn_prompt = p.get('chinese_prompt', '')[:50]
            params = p.get('parameters', {})
            ar = params.get('aspect_ratio', '1:1')
            steps = params.get('steps', 30)
            
            table.add_row(
                p.get('id', 'N/A')[:8],
                prompt_type,
                cn_prompt + "..." if len(p.get('chinese_prompt', '')) > 50 else cn_prompt,
                f"{ar} @ {steps}步"
            )
        
        console.print(table)
        
        if len(prompts) > limit:
            console.print(f"\n[yellow]还有 {len(prompts) - limit} 个提示词，使用 --limit 参数查看更多[/yellow]")


@cli.command()
@click.argument('project_id')
@click.pass_context
def entities(ctx, project_id: str):
    """列出项目中的所有实体
    
    PROJECT_ID: 项目ID
    
    显示提取的所有角色、场景和物品实体。
    """
    from src.storage.project_store import ProjectStore
    
    store = ProjectStore()
    
    if not store.project_exists(project_id):
        console.print(f"[red]项目不存在: {project_id}[/red]")
        return
    
    entities = store.load_entities(project_id)
    
    if not entities:
        console.print("[yellow]项目中没有实体[/yellow]")
        return
    
    console.print(Panel.fit(
        f"[bold cyan]实体列表: {project_id}[/bold cyan]\n"
        f"共 {len(entities)} 个实体",
        border_style="cyan"
    ))
    
    character_entities = [e for e in entities if e.get('type') == 'character']
    scene_entities = [e for e in entities if e.get('type') == 'scene']
    item_entities = [e for e in entities if e.get('type') == 'item']
    
    if character_entities:
        console.print(f"\n[bold yellow]角色 ({len(character_entities)})[/bold yellow]")
        char_table = Table(box=box.SIMPLE)
        char_table.add_column("ID", style="cyan")
        char_table.add_column("名称", style="white")
        char_table.add_column("别名", style="dim")
        char_table.add_column("首次出现", style="green")
        
        for e in character_entities[:20]:
            aliases = ", ".join(e.get('aliases', [])[:3])
            if len(e.get('aliases', [])) > 3:
                aliases += "..."
            first_ch = e.get('first_appearance_chapter', 'N/A')
            char_table.add_row(
                e.get('id', 'N/A')[:8],
                e.get('name', 'N/A'),
                aliases or "-",
                f"第{first_ch}章" if first_ch else "N/A"
            )
        
        console.print(char_table)
        if len(character_entities) > 20:
            console.print(f"[dim]...还有 {len(character_entities) - 20} 个角色[/dim]")
    
    if scene_entities:
        console.print(f"\n[bold yellow]场景 ({len(scene_entities)})[/bold yellow]")
        for e in scene_entities[:10]:
            desc = e.get('attributes', {}).get('visual_description', '')[:50]
            console.print(f"  [cyan]{e.get('id', '')[:8]}[/cyan] {e.get('name', 'N/A')} - {desc}...")
        
        if len(scene_entities) > 10:
            console.print(f"[dim]...还有 {len(scene_entities) - 10} 个场景[/dim]")
    
    if item_entities:
        console.print(f"\n[bold yellow]物品 ({len(item_entities)})[/bold yellow]")
        for e in item_entities[:10]:
            cat = e.get('attributes', {}).get('category', 'N/A')
            console.print(f"  [cyan]{e.get('id', '')[:8]}[/cyan] {e.get('name', 'N/A')} [{cat}]")
        
        if len(item_entities) > 10:
            console.print(f"[dim]...还有 {len(item_entities) - 10} 个物品[/dim]")


@cli.command()
@click.argument('project_id')
@click.option('--format', '-f', default='md', type=click.Choice(['md', 'json']), help='导出格式')
@click.option('--output', '-o', default=None, help='输出文件路径')
@click.pass_context
def export(ctx, project_id: str, format: str, output: str):
    """导出项目数据
    
    PROJECT_ID: 项目ID
    
    导出提示词到指定格式。
    """
    from src.storage.project_store import ProjectStore
    
    store = ProjectStore()
    
    if not store.project_exists(project_id):
        console.print(f"[red]项目不存在: {project_id}[/red]")
        return
    
    prompts = store.load_prompts(project_id)
    
    if not prompts:
        console.print("[yellow]没有提示词可导出[/yellow]")
        return
    
    if format == 'md':
        output_path = store.save_prompts_md(project_id, prompts, "prompts_export.md")
    else:
        output_path = Path(output) if output else store.get_project_dir(project_id) / "prompts_export.json"
        import json
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(prompts, f, ensure_ascii=False, indent=2)
    
    console.print(f"[green]✓[/green] 提示词已导出到: {output_path}")


@cli.command()
@click.argument('project_id')
@click.pass_context
def validate(ctx, project_id: str):
    """验证项目完整性
    
    PROJECT_ID: 项目ID
    
    检查项目数据是否完整，报告缺失的文件。
    """
    from src.storage.project_store import ProjectStore
    
    store = ProjectStore()
    
    if not store.project_exists(project_id):
        console.print(f"[red]项目不存在: {project_id}[/red]")
        return
    
    project_dir = store.get_project_dir(project_id)
    
    console.print(Panel.fit(
        f"[bold cyan]验证项目: {project_id}[/bold cyan]",
        border_style="cyan"
    ))
    
    issues = []
    warnings = []
    
    project_json = project_dir / "project.json"
    if not project_json.exists():
        issues.append("project.json 不存在")
    
    data_dir = project_dir / "data"
    if data_dir.exists():
        chapters_file = data_dir / "chapters.json"
        if chapters_file.exists():
            chapters = store.load_chapters(project_id)
            console.print(f"[green]✓[/green] 章节: {len(chapters)} 个")
        else:
            issues.append("chapters.json 不存在")
        
        entities_file = data_dir / "entities.json"
        if entities_file.exists():
            entities = store.load_entities(project_id)
            console.print(f"[green]✓[/green] 实体: {len(entities)} 个")
        else:
            warnings.append("entities.json 不存在（尚未提取实体）")
        
        world_bible_file = data_dir / "world_bible.json"
        if world_bible_file.exists():
            console.print(f"[green]✓[/green] 世界观圣经: 已构建")
        else:
            warnings.append("world_bible.json 不存在（尚未构建世界观）")
    
    prompts_dir = project_dir / "prompts"
    if prompts_dir.exists():
        prompts_file = prompts_dir / "prompts.json"
        if prompts_file.exists():
            prompts = store.load_prompts(project_id)
            console.print(f"[green]✓[/green] 提示词: {len(prompts)} 个")
        else:
            warnings.append("prompts.json 不存在（尚未生成提示词）")
    
    console.print()
    
    if warnings:
        console.print("[yellow]警告:[/yellow]")
        for w in warnings:
            console.print(f"  [yellow]! {w}[/yellow]")
        console.print()
    
    if issues:
        console.print("[red]问题:[/red]")
        for i in issues:
            console.print(f"  [red]✗ {i}[/red]")
        console.print()
        console.print("[red]项目数据不完整[/red]")
    else:
        if not warnings:
            console.print("[bold green]项目验证通过！[/bold green]")
        else:
            console.print("[yellow]项目验证完成（有警告）[/yellow]")


@cli.command()
@click.pass_context
def list_projects(ctx):
    """列出所有项目"""
    from src.storage.project_store import ProjectStore
    
    store = ProjectStore()
    projects = store.list_projects()
    
    if not projects:
        console.print("[yellow]暂无项目[/yellow]")
        console.print("\n使用以下命令创建新项目:")
        console.print("  [cyan]python -m src.cli init <book_path> --name <project_name>[/cyan]")
        return
    
    table = Table(title="项目列表", box=box.ROUNDED)
    table.add_column("ID", style="cyan")
    table.add_column("名称", style="white")
    table.add_column("创建时间", style="green")
    
    for project in projects:
        table.add_row(
            project.get('id', 'N/A'),
            project.get('name', 'N/A'),
            project.get('created_at', 'N/A')[:19]
        )
    
    console.print(table)


@cli.command()
@click.argument('project_id')
@click.pass_context
def delete(ctx, project_id: str):
    """删除项目
    
    PROJECT_ID: 项目ID
    
    危险操作！将永久删除项目及其所有数据。
    """
    from src.storage.project_store import ProjectStore
    
    store = ProjectStore()
    
    if not store.project_exists(project_id):
        console.print(f"[red]项目不存在: {project_id}[/red]")
        return
    
    if not click.confirm(f'[red]确定要删除项目 {project_id} 吗？此操作不可恢复！[/red]'):
        console.print("[yellow]取消删除[/yellow]")
        return
    
    store.delete_project(project_id)
    console.print(f"[green]✓ 项目已删除: {project_id}[/green]")


@cli.command()
@click.pass_context
def templates(ctx):
    """列出可用的提示词模板"""
    from src.llm.prompt_loader import PromptLoader
    
    loader = PromptLoader()
    template_list = loader.list_templates()
    
    console.print(Panel.fit(
        "[bold cyan]可用模板[/bold cyan]",
        border_style="cyan"
    ))
    
    if not template_list:
        console.print("[yellow]没有找到模板文件[/yellow]")
        console.print(f"\n模板目录: {loader.prompts_dir}")
        return
    
    table = Table(box=box.ROUNDED)
    table.add_column("模板名称", style="cyan")
    
    for name in sorted(template_list):
        table.add_row(name)
    
    console.print(table)
    console.print(f"\n共 {len(template_list)} 个模板")


def main():
    """主入口函数"""
    cli(obj={})


if __name__ == '__main__':
    main()
