"""Web UI卡片组件"""

import gradio as gr
from typing import Dict, Any, Optional


def entity_card(entity: Dict[str, Any], prompt: Optional[Dict[str, Any]] = None) -> None:
    """渲染实体卡片组件
    
    Args:
        entity: 实体数据字典
        prompt: 关联的提示词数据（可选）
    """
    entity_name = entity.get('name', '未知')
    entity_type = entity.get('type', 'unknown')
    entity_id = entity.get('id', '')
    
    has_prompt = prompt is not None
    has_image = False
    
    attributes = entity.get('attributes', {})
    
    with gr.Column(elem_classes="card"):
        if has_image and entity_type == 'character':
            gr.Image(
                label=f"{entity_name} 形象",
                value=None,
                height=200
            )
        
        gr.Markdown(f"### {entity_name}")
        
        type_labels = {
            'character': '角色',
            'scene': '场景',
            'item': '物品',
            'creature': '生物'
        }
        type_label = type_labels.get(entity_type, entity_type)
        gr.Markdown(f"**类型**: {type_label}")
        
        if entity_type == 'character' and attributes:
            appearance = attributes.get('appearance', {})
            if appearance:
                hair = appearance.get('hair', '')
                if hair:
                    gr.Markdown(f"**发色**: {hair}")
        
        if entity_type == 'scene' and attributes:
            env_type = attributes.get('environment_type', '')
            if env_type:
                gr.Markdown(f"**环境**: {env_type}")
        
        if entity_type == 'item' and attributes:
            category = attributes.get('category', '')
            if category:
                gr.Markdown(f"**分类**: {category}")
        
        aliases = entity.get('aliases', [])
        if aliases:
            alias_text = ', '.join(aliases[:3])
            if len(aliases) > 3:
                alias_text += '...'
            gr.Markdown(f"**别名**: {alias_text}")
        
        first_chapter = entity.get('first_appearance_chapter')
        if first_chapter:
            gr.Markdown(f"**首次出现**: 第{first_chapter}章")
        
        with gr.Row():
            prompt_btn = gr.Button("📝 查看提示词" if has_prompt else "✨ 生成提示词", size="sm")
            if has_prompt:
                copy_btn = gr.Button("📋 复制", size="sm")
            else:
                generate_btn = gr.Button("🖼️ 生成图片", size="sm", interactive=False)


def world_bible_card(world_bible: Dict[str, Any]) -> None:
    """渲染世界观卡片组件
    
    Args:
        world_bible: 世界观数据字典
    """
    framework = world_bible.get('world_framework', {})
    visual = world_bible.get('visual_anchoring', {})
    
    with gr.Column(elem_classes="card"):
        gr.Markdown("### 🌍 世界观概要")
        
        genre = framework.get('genre', '未知')
        sub_genre = framework.get('sub_genre', '')
        gr.Markdown(f"**类型**: {genre} {f'/ {sub_genre}' if sub_genre else ''}")
        
        era = framework.get('era_setting', '未知')
        gr.Markdown(f"**时代**: {era}")
        
        power_system = framework.get('power_system', '')
        if power_system:
            gr.Markdown(f"**力量体系**: {power_system}")
        
        gr.Markdown("---")
        
        art_style = visual.get('art_style', '未知')
        gr.Markdown(f"**艺术风格**: {art_style}")
        
        color_palette = visual.get('color_palette', {})
        if color_palette:
            primary = color_palette.get('primary', '')
            secondary = color_palette.get('secondary', '')
            if primary:
                gr.Markdown(f"**主色调**: {primary}")
            if secondary:
                gr.Markdown(f"**辅色调**: {secondary}")
        
        gr.Markdown("---")
        
        forbidden = visual.get('forbidden_elements', [])
        if forbidden:
            forbidden_text = ', '.join(forbidden[:5])
            gr.Markdown(f"**禁忌元素**: {forbidden_text}")


def prompt_card(prompt: Dict[str, Any]) -> None:
    """渲染提示词卡片组件
    
    Args:
        prompt: 提示词数据字典
    """
    prompt_id = prompt.get('id', '')[:8]
    prompt_type = prompt.get('type', 'unknown')
    
    params = prompt.get('parameters', {})
    aspect_ratio = params.get('aspect_ratio', '1:1')
    steps = params.get('steps', 30)
    cfg_scale = params.get('cfg_scale', 7.0)
    
    with gr.Column(elem_classes="card"):
        gr.Markdown(f"### 提示词 #{prompt_id}")
        
        type_labels = {
            'character': '角色',
            'scene': '场景',
            'item': '物品'
        }
        gr.Markdown(f"**类型**: {type_labels.get(prompt_type, prompt_type)}")
        gr.Markdown(f"**参数**: {aspect_ratio} | {steps}步 | CFG {cfg_scale}")
        
        chinese_prompt = prompt.get('chinese_prompt', '')
        if chinese_prompt:
            with gr.Accordion("📜 中文提示词", open=False):
                gr.Code(chinese_prompt, language="text", lines=5)
        
        world_prefix = prompt.get('world_prefix_chinese', '')
        if world_prefix:
            with gr.Accordion("🌍 世界观前缀", open=False):
                gr.Textbox(world_prefix, lines=3, interactive=False)
        
        negative = prompt.get('negative_prompt', '')
        if negative:
            with gr.Accordion("⚠️ 负向提示词", open=False):
                gr.Code(negative, language="text", lines=3)
        
        face_block = prompt.get('face_block_chinese', '')
        if face_block:
            with gr.Accordion("🔒 面容锁定", open=False):
                gr.Code(face_block, language="text", lines=3)
        
        with gr.Row():
            copy_btn = gr.Button("📋 复制", size="sm")
            download_btn = gr.Button("💾 导出", size="sm")


def stats_card(stats: Dict[str, int]) -> None:
    """渲染统计卡片组件
    
    Args:
        stats: 统计数据字典
    """
    with gr.Column(elem_classes="card"):
        gr.Markdown("### 📊 项目统计")
        
        gr.Markdown(f"**章节数**: {stats.get('chapter_count', 0)}")
        gr.Markdown(f"**实体总数**: {stats.get('entity_count', 0)}")
        
        gr.Markdown(f"- 角色: {stats.get('character_count', 0)}")
        gr.Markdown(f"- 场景: {stats.get('scene_count', 0)}")
        gr.Markdown(f"- 物品: {stats.get('item_count', 0)}")
        
        gr.Markdown(f"**提示词数**: {stats.get('prompt_count', 0)}")


def empty_card(message: str) -> None:
    """渲染空状态卡片
    
    Args:
        message: 提示信息
    """
    with gr.Column():
        gr.Markdown(f"⚠️ {message}")
