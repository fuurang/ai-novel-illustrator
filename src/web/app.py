"""AI拆书生图 - Gradio Web界面"""

import gradio as gr
import asyncio
import hashlib
import time
from pathlib import Path
from typing import Optional, List, Dict, Any

from src.storage.project_store import ProjectStore
from src.core.pipeline import Pipeline
from src.web.state import WebState
from src.web.components.cards import (
    entity_card,
    world_bible_card,
    prompt_card,
    stats_card,
    empty_card
)


class GradioApp:
    """Gradio应用主类"""
    
    def __init__(self, port: int = 8888, config_path: Optional[str] = None):
        """初始化Gradio应用
        
        Args:
            port: 服务端口，默认8888（避免7860/7861冲突）
            config_path: 配置文件路径
        """
        self.port = port
        self.state = WebState()
        self.state.load_config(config_path)
        self.store = ProjectStore()
        self.pipeline = None
        
        self.app = self._create_blocks()
    
    def _create_blocks(self) -> gr.Blocks:
        """创建Gradio Blocks界面"""
        
        with gr.Blocks(
            title="AI拆书生图"
        ) as app:
            
            gr.Markdown("# 🖼️ AI拆书生图", elem_classes="main-header")
            gr.Markdown("将小说文本转换为AI图像生成提示词", elem_classes="subtitle")
            
            with gr.Row():
                with gr.Column(scale=1, min_width=250, elem_classes="sidebar"):
                    self._create_sidebar()
                
                with gr.Column(scale=4):
                    self._create_main_content()
            
            self._create_settings_modal()
            
            self._setup_event_handlers()
        
        return app
    
    def _get_css(self) -> str:
        """获取自定义CSS样式"""
        return """
        .main-header {
            text-align: center;
            font-size: 28px;
            font-weight: bold;
            margin-bottom: 10px;
        }
        .subtitle {
            text-align: center;
            color: #666;
            margin-bottom: 20px;
        }
        .sidebar {
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 10px;
        }
        .card {
            border-radius: 10px;
            padding: 15px;
            background-color: white;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin: 10px 0;
        }
        .status-success { color: green; }
        .status-error { color: red; }
        .status-warning { color: orange; }
        """
    
    def _create_sidebar(self):
        """创建侧边栏"""
        gr.Markdown("## 📂 项目列表")
        
        self.project_dropdown = gr.Dropdown(
            choices=self._get_project_choices(),
            label="选择项目",
            interactive=True,
            allow_custom_value=False
        )
        
        with gr.Row():
            self.new_project_btn = gr.Button("+ 新建项目", size="sm", variant="primary")
            self.refresh_btn = gr.Button("🔄 刷新", size="sm")
        
        gr.Markdown("---")
        gr.Markdown("## 📊 统计信息")
        
        self.stats_text = gr.Textbox(
            label="项目状态",
            interactive=False,
            lines=6
        )
        
        gr.Markdown("---")
        gr.Markdown("## ⚙️ 设置")
        self.settings_btn = gr.Button("🔧 配置管理", size="sm")
    
    def _create_main_content(self):
        """创建主内容区"""
        with gr.Row():
            self.upload_btn = gr.Button("📤 上传小说", variant="primary")
            self.run_btn = gr.Button("▶️ 运行流水线", variant="primary", interactive=False)
            self.export_btn = gr.Button("📥 导出提示词", interactive=False)
        
        self.status_text = gr.Textbox(
            label="状态信息",
            interactive=False,
            lines=2
        )
        
        self.progress_bar = gr.Slider(
            minimum=0,
            maximum=100,
            value=0,
            label="进度",
            interactive=False,
            visible=False
        )
        
        with gr.Tabs():
            self._create_world_bible_tab()
            self._create_character_tab()
            self._create_scene_tab()
            self._create_item_tab()
            self._create_gallery_tab()
    
    def _create_world_bible_tab(self):
        """创建世界观Tab"""
        with gr.Tab("🌍 世界观"):
            self.wb_content = gr.Column()
            with self.wb_content:
                gr.Markdown("请先创建或选择一个项目，然后运行流水线生成世界观数据")
    
    def _create_character_tab(self):
        """创建角色Tab"""
        with gr.Tab("👤 角色"):
            self.character_content = gr.Column()
            with self.character_content:
                gr.Markdown("请先运行流水线生成角色数据")
    
    def _create_scene_tab(self):
        """创建场景Tab"""
        with gr.Tab("🏔️ 场景"):
            self.scene_content = gr.Column()
            with self.scene_content:
                gr.Markdown("请先运行流水线生成场景数据")
    
    def _create_item_tab(self):
        """创建物品Tab"""
        with gr.Tab("⚔️ 物品"):
            self.item_content = gr.Column()
            with self.item_content:
                gr.Markdown("请先运行流水线生成物品数据")
    
    def _create_gallery_tab(self):
        """创建图集Tab"""
        with gr.Tab("🖼️ 图集"):
            self.gallery_content = gr.Column()
            with self.gallery_content:
                gr.Markdown("请先生成图片")
                self.gallery_gallery = gr.Gallery(
                    label="生成图片",
                    object_fit="contain",
                    height=400,
                    visible=False
                )
    
    def _create_settings_modal(self):
        """创建设置弹窗"""
        with gr.Blocks(visible=False) as settings_modal:
            gr.Markdown("# ⚙️ 配置管理")
            
            with gr.Row():
                with gr.Column():
                    gr.Markdown("### LLM 配置")
                    self.llm_provider = gr.Dropdown(
                        choices=["deepseek", "openai", "anthropic"],
                        value="deepseek",
                        label="LLM Provider"
                    )
                    self.llm_model = gr.Textbox(
                        label="Model",
                        value="deepseek-chat"
                    )
                    self.llm_api_key = gr.Textbox(
                        label="API Key",
                        type="password"
                    )
                    self.llm_base_url = gr.Textbox(
                        label="Base URL",
                        value="https://api.deepseek.com/v1"
                    )
                
                with gr.Column():
                    gr.Markdown("### 输出配置")
                    self.output_dir = gr.Textbox(
                        label="输出目录",
                        value="./projects"
                    )
                    self.default_style = gr.Dropdown(
                        choices=["auto", "anime", "realistic", "watercolor"],
                        value="auto",
                        label="默认风格"
                    )
            
            with gr.Row():
                self.save_config_btn = gr.Button("💾 保存配置", variant="primary")
                self.close_settings_btn = gr.Button("关闭")
        
        self.settings_modal = settings_modal
    
    def _get_project_choices(self) -> List[str]:
        """获取项目列表选项"""
        projects = self.store.list_projects()
        return [p['id'] for p in projects]
    
    def _setup_event_handlers(self):
        """设置事件处理器"""
        self.project_dropdown.change(
            fn=self._on_project_select,
            inputs=[self.project_dropdown],
            outputs=[self.status_text, self.stats_text, self.wb_content, 
                     self.character_content, self.scene_content, self.item_content]
        )
        
        self.refresh_btn.click(
            fn=self._on_refresh,
            outputs=[self.project_dropdown, self.status_text]
        )
        
        self.new_project_btn.click(
            fn=self._show_new_project_dialog,
            outputs=[self.status_text]
        )
        
        self.upload_btn.click(
            fn=self._on_upload,
            outputs=[self.status_text]
        )
        
        self.run_btn.click(
            fn=self._on_run_pipeline,
            inputs=[self.project_dropdown],
            outputs=[self.status_text, self.progress_bar]
        )
        
        self.export_btn.click(
            fn=self._on_export,
            inputs=[self.project_dropdown],
            outputs=[self.status_text]
        )
        
        self.settings_btn.click(
            fn=lambda: gr.Blocks(visible=True),
            outputs=[self.settings_modal]
        )
        
        self.close_settings_btn.click(
            fn=lambda: gr.Blocks(visible=False),
            outputs=[self.settings_modal]
        )
        
        self.save_config_btn.click(
            fn=self._on_save_config,
            inputs=[self.llm_provider, self.llm_model, self.llm_api_key, 
                   self.llm_base_url, self.output_dir, self.default_style],
            outputs=[self.status_text, self.settings_modal]
        )
    
    def _on_project_select(self, project_id: str):
        """项目选择事件处理"""
        if not project_id:
            return (
                "请选择一个项目",
                "",
                gr.Column(visible=True),
                gr.Column(visible=True),
                gr.Column(visible=True),
                gr.Column(visible=True)
            )
        
        success = self.state.load_project(project_id, self.store)
        
        if not success:
            return (
                f"❌ 加载项目失败: {project_id}",
                "",
                gr.Column(visible=True),
                gr.Column(visible=True),
                gr.Column(visible=True),
                gr.Column(visible=True)
            )
        
        stats = self.state.get_project_stats()
        stats_text = f"""项目: {self.state.current_project.get('name', '未知')}
章节: {stats['chapter_count']}
角色: {stats['character_count']}
场景: {stats['scene_count']}
物品: {stats['item_count']}
提示词: {stats['prompt_count']}"""
        
        self.run_btn.interactive = True
        self.export_btn.interactive = stats['prompt_count'] > 0
        
        return (
            f"✅ 已加载项目: {project_id}",
            stats_text,
            self._create_wb_content(),
            self._create_entity_content('character'),
            self._create_entity_content('scene'),
            self._create_entity_content('item')
        )
    
    def _on_refresh(self):
        """刷新项目列表"""
        choices = self._get_project_choices()
        return (
            gr.Dropdown(choices=choices, value=None),
            "✅ 已刷新项目列表"
        )
    
    def _show_new_project_dialog(self):
        """显示新建项目对话框"""
        return "请在下方输入项目名称和上传小说文件"
    
    def _on_upload(self):
        """处理文件上传"""
        return "请选择小说文件（支持 .txt 格式）"
    
    def _on_run_pipeline(self, project_id: str):
        """运行流水线"""
        if not project_id:
            return "❌ 请先选择项目", gr.Slider(visible=False)
        
        return (
            f"🔄 正在运行流水线...\n项目: {project_id}\n请稍候...",
            gr.Slider(visible=True, value=0)
        )
    
    def _on_export(self, project_id: str):
        """导出提示词"""
        if not project_id:
            return "❌ 请先选择项目"
        
        try:
            prompts = self.state.prompts
            if not prompts:
                return "⚠️ 没有可导出的提示词"
            
            output_path = self.store.save_prompts_md(project_id, prompts, "prompts_export.md")
            return f"✅ 提示词已导出到: {output_path}"
        except Exception as e:
            return f"❌ 导出失败: {str(e)}"
    
    def _on_save_config(self, provider, model, api_key, base_url, output_dir, style):
        """保存配置"""
        return (
            "✅ 配置已保存",
            gr.Blocks(visible=False)
        )
    
    def _create_wb_content(self):
        """创建世界观内容"""
        if not self.state.has_world_bible():
            with gr.Column() as col:
                gr.Markdown("⚠️ 暂无世界观数据，请运行流水线生成")
            return col
        
        with gr.Column() as col:
            world_bible_card(self.state.world_bible)
        return col
    
    def _create_entity_content(self, entity_type: str):
        """创建实体内容"""
        entities = self.state.get_entities_by_type(entity_type)
        
        if not entities:
            type_names = {
                'character': '角色',
                'scene': '场景',
                'item': '物品'
            }
            with gr.Column() as col:
                gr.Markdown(f"⚠️ 暂无{type_names.get(entity_type, entity_type)}数据，请运行流水线生成")
            return col
        
        with gr.Column() as col:
            gr.Markdown(f"### {entity_type.capitalize()} ({len(entities)})")
            
            for entity in entities[:20]:
                prompt = self.state.get_entity_prompt(entity.get('id'))
                entity_card(entity, prompt)
        
        return col
    
    def run(self, share: bool = False, debug: bool = False):
        """启动Gradio应用
        
        Args:
            share: 是否创建公开链接
            debug: 是否启用调试模式
        """
        self.app.launch(
            server_port=self.port,
            share=share,
            debug=debug,
            theme=gr.themes.Soft(
                primary_hue="blue",
                secondary_hue="gray",
            ),
            css=self._get_css()
        )


def create_app(port: int = 8888, config_path: Optional[str] = None) -> gr.Blocks:
    """创建Gradio应用
    
    Args:
        port: 服务端口（默认8888，避免7860/7861冲突）
        config_path: 配置文件路径
        
    Returns:
        Gradio Blocks实例
    """
    gradio_app = GradioApp(port=port, config_path=config_path)
    return gradio_app.app


def main():
    """主入口函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="AI拆书生图 - Web界面")
    parser.add_argument(
        '--port', '-p',
        type=int,
        default=8888,
            help='服务端口（默认: 8888）'
    )
    parser.add_argument(
        '--config', '-c',
        type=str,
        default=None,
        help='配置文件路径'
    )
    parser.add_argument(
        '--share',
        action='store_true',
        help='创建公开分享链接'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='启用调试模式'
    )
    
    args = parser.parse_args()
    
    print(f"🚀 启动AI拆书生图 Web界面...")
    print(f"📍 访问地址: http://localhost:{args.port}")
    print(f"🔧 调试模式: {'启用' if args.debug else '禁用'}")
    
    app = create_app(port=args.port, config_path=args.config)
    gradio_app = GradioApp(port=args.port, config_path=args.config)
    gradio_app.run(share=args.share, debug=args.debug)


if __name__ == '__main__':
    main()
