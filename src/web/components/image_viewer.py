"""
图片展示组件模块
提供Gradio UI组件用于图片画廊和卡片展示
"""

import gradio as gr
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any


def image_gallery(
    images: List[str],
    titles: List[str] = None,
    columns: int = 4,
    height: str = "auto",
    preview: bool = True,
) -> gr.Gallery:
    """
    创建图片画廊组件
    
    用于展示多张图片的网格画廊，支持预览功能
    
    Args:
        images: 图片路径列表
        titles: 图片标题列表（可选）
        columns: 网格列数，默认4列
        height: 画廊高度，默认"auto"自适应
        preview: 是否启用预览功能，默认True
        
    Returns:
        gr.Gallery: Gradio画廊组件
    """
    if not images:
        return gr.Markdown("**暂无图片**")
    
    # 构建画廊数据
    gallery_data = []
    for i, img_path in enumerate(images):
        # 检查图片是否存在
        if img_path and Path(img_path).exists():
            title = titles[i] if titles and i < len(titles) else f"图片 {i+1}"
            # 格式：(标题, 图片路径)
            gallery_data.append((str(img_path), title))
        else:
            print(f"警告：图片不存在: {img_path}")
    
    if not gallery_data:
        return gr.Markdown("**暂无有效图片**")
    
    return gr.Gallery(
        value=gallery_data,
        columns=columns,
        preview=preview,
        height=height,
        object_fit="contain",
        show_label=True,
    )


def image_card(
    image_path: str,
    title: str,
    entity_type: str,
    show_regenerate: bool = True,
    height: int = 200,
) -> gr.Column:
    """
    创建单张图片卡片组件
    
    包含图片展示、标题和操作按钮
    
    Args:
        image_path: 图片路径
        title: 卡片标题
        entity_type: 实体类型（character/scene/item）
        show_regenerate: 是否显示重新生成按钮，默认True
        height: 图片高度，默认200
        
    Returns:
        gr.Column: Gradio列组件容器
    """
    with gr.Column():
        # 图片展示
        if image_path and Path(image_path).exists():
            gr.Image(
                value=image_path,
                label=title,
                height=height,
                show_fullscreen_button=True,
                show_download_button=True,
            )
        else:
            gr.Image(
                label=title,
                height=height,
                show_fullscreen_button=True,
            )
        
        # 实体类型标签
        type_emoji = {
            "character": "👤",
            "scene": "🏞️",
            "item": "📦",
            "creature": "🐉",
        }.get(entity_type, "📄")
        
        gr.Label(
            label=f"类型",
            value={f"{type_emoji} {entity_type}": 1},
            show_label=True,
        )
        
        # 操作按钮
        if show_regenerate:
            regenerate_btn = gr.Button(
                f"🔄 重新生成",
                size="sm",
                variant="secondary",
            )


def image_detail_view(
    entity_name: str,
    face_anchor_path: str = None,
    main_image_path: str = None,
    entity_type: str = "character",
) -> gr.Column:
    """
    创建图片详情视图组件
    
    包含面部锚定图（如果有）和主图的对比展示
    
    Args:
        entity_name: 实体名称
        face_anchor_path: 面部锚定图路径
        main_image_path: 主图路径
        entity_type: 实体类型
        
    Returns:
        gr.Column: Gradio列组件容器
    """
    with gr.Column():
        # 标题
        gr.Markdown(f"## 🎨 {entity_name}")
        
        with gr.Row():
            # 面部锚定图（如果有）
            if face_anchor_path and Path(face_anchor_path).exists():
                with gr.Column():
                    gr.Markdown("**📌 面部锚定图**")
                    gr.Image(
                        value=face_anchor_path,
                        height=300,
                        show_fullscreen_button=True,
                    )
            
            # 主图
            if main_image_path and Path(main_image_path).exists():
                with gr.Column():
                    gr.Markdown("**🖼️ 生成图片**")
                    gr.Image(
                        value=main_image_path,
                        height=400,
                        show_fullscreen_button=True,
                        show_download_button=True,
                    )


def image_batch_grid(
    image_dict: Dict[str, List[str]],
    show_titles: bool = True,
) -> Dict[str, gr.Gallery]:
    """
    创建批量图片网格组件
    
    将不同类型的图片分组展示
    
    Args:
        image_dict: 图片字典，格式：{"类型": [图片路径列表]}
        show_titles: 是否显示类型标题
        
    Returns:
        dict: 类型到画廊组件的映射
    """
    components = {}
    
    type_labels = {
        "characters": "👤 角色图",
        "scenes": "🏞️ 场景图",
        "items": "📦 物品图",
        "face_anchors": "📌 面部锚定图",
    }
    
    for img_type, images in image_dict.items():
        if not images:
            continue
            
        label = type_labels.get(img_type, img_type)
        
        with gr.Column():
            if show_titles:
                gr.Markdown(f"### {label}")
            
            gallery = image_gallery(
                images=images,
                columns=4 if len(images) > 1 else 1,
                height="auto",
            )
            
            components[img_type] = gallery
    
    return components


def create_image_upload_zone(
    label: str = "上传图片",
    file_types: List[str] = ["image"],
) -> gr.File:
    """
    创建图片上传区域组件
    
    Args:
        label: 上传区域标签
        file_types: 允许的文件类型列表
        
    Returns:
        gr.File: Gradio文件上传组件
    """
    return gr.File(
        label=label,
        file_count="single",
        file_types=file_types,
        type="filepath",
    )


def image_comparison_slider(
    image_before: str,
    image_after: str,
    labels: Tuple[str, str] = ("原图", "新图"),
) -> gr.Gallery:
    """
    创建图片对比滑块组件
    
    暂时使用画廊展示，未来可以扩展为滑块对比
    
    Args:
        image_before: 原图路径
        image_after: 新图路径
        labels: 两个图片的标签
        
    Returns:
        gr.Gallery: 包含两张图片的画廊
    """
    gallery_data = []
    
    if image_before and Path(image_before).exists():
        gallery_data.append((str(image_before), labels[0]))
    
    if image_after and Path(image_after).exists():
        gallery_data.append((str(image_after), labels[1]))
    
    if not gallery_data:
        return gr.Markdown("**暂无对比图片**")
    
    return gr.Gallery(
        value=gallery_data,
        columns=2,
        preview=False,
        height="auto",
    )


def progress_indicator(current: int, total: int, status: str) -> gr.HTML:
    """
    创建进度指示器组件
    
    显示当前生成进度
    
    Args:
        current: 当前进度
        total: 总数
        status: 状态文本
        
    Returns:
        gr.HTML: HTML进度条组件
    """
    percentage = (current / total * 100) if total > 0 else 0
    
    html = f"""
    <div style="width: 100%; margin: 10px 0;">
        <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
            <span>{status}</span>
            <span>{current}/{total} ({percentage:.1f}%)</span>
        </div>
        <div style="width: 100%; height: 20px; background-color: #f0f0f0; border-radius: 10px; overflow: hidden;">
            <div style="width: {percentage}%; height: 100%; background-color: #4CAF50; transition: width 0.3s ease;"></div>
        </div>
    </div>
    """
    
    return gr.HTML(value=html)


def image_status_badge(
    status: str,
    message: str = "",
) -> gr.Label:
    """
    创建图片状态徽章组件
    
    显示生成状态（成功、失败、生成中）
    
    Args:
        status: 状态（success/error/processing）
        message: 状态消息
        
    Returns:
        gr.Label: Gradio标签组件
    """
    status_config = {
        "success": ("✅ 成功", {"success": 1}),
        "error": ("❌ 失败", {"error": 1}),
        "processing": ("⏳ 生成中", {"processing": 1}),
        "pending": ("⏸️ 等待中", {"pending": 1}),
    }
    
    config = status_config.get(status, ("❓ 未知", {"unknown": 1}))
    display_message = f"{config[0]} {message}" if message else config[0]
    
    return gr.Label(
        label="状态",
        value={display_message: 1},
    )
