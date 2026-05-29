"""
简单的Gradio应用示例

演示如何使用Web集成模块创建一个基本的AI拆书生图界面
"""
import gradio as gr
import asyncio
from pathlib import Path
from typing import Optional

from src.web import (
    WebPipelineRunner,
    FileUploadHandler,
    ProgressManager,
    create_progress_callback,
)
from src.storage.project_store import ProjectStore


class SimpleGradioApp:
    """简化版Gradio应用"""
    
    def __init__(self):
        """初始化应用"""
        self.runner = WebPipelineRunner()
        self.upload_handler = FileUploadHandler()
        self.store = ProjectStore()
        self.progress_manager = ProgressManager()
        
        self.current_project_id: Optional[str] = None
        self.current_file_path: Optional[str] = None
    
    def create_interface(self):
        """创建Gradio界面"""
        
        with gr.Blocks(
            title="AI拆书生图",
            theme=gr.themes.Soft()
        ) as app:
            
            gr.Markdown("# 🖼️ AI拆书生图 - Web演示")
            gr.Markdown("将小说文本转换为AI图像生成提示词")
            
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("## 📤 文件上传")
                    
                    file_input = gr.File(
                        label="上传小说文件",
                        file_types=[".txt", ".md", ".html"],
                    )
                    
                    project_name = gr.Textbox(
                        label="项目名称",
                        placeholder="输入项目名称（可选）",
                    )
                    
                    run_btn = gr.Button(
                        "🚀 开始处理",
                        variant="primary",
                    )
                    
                    gr.Markdown("---")
                    gr.Markdown("## ⚙️ 进度跟踪")
                    
                    progress_output = gr.Textbox(
                        label="当前状态",
                        interactive=False,
                        lines=3,
                    )
                    
                    progress_bar = gr.Slider(
                        minimum=0,
                        maximum=1,
                        value=0,
                        label="完成进度",
                        interactive=False,
                    )
                
                with gr.Column(scale=2):
                    gr.Markdown("## 📊 结果展示")
                    
                    status_output = gr.JSON(
                        label="执行结果",
                    )
            
            run_btn.click(
                fn=self._on_run,
                inputs=[file_input, project_name],
                outputs=[progress_output, progress_bar, status_output],
            )
        
        return app
    
    def _on_run(self, file_obj, project_name: str):
        """
        处理运行按钮点击
        
        Args:
            file_obj: 上传的文件对象
            project_name: 项目名称
        
        Returns:
            进度消息，进度条值，结果字典
        """
        if file_obj is None:
            return "❌ 请先上传文件", gr.Slider(value=0, visible=False), {}
        
        file_path = self.upload_handler.handle_upload(file_obj)
        if not file_path:
            return "❌ 文件处理失败", gr.Slider(value=0, visible=False), {}
        
        self.current_file_path = file_path
        
        progress_messages = []
        
        def on_progress(status):
            """进度回调"""
            progress_messages.append(f"[{status['stage_name']}] {status['message']}")
            return "\n".join(progress_messages[-5:])
        
        callback, progress_mgr = create_progress_callback(on_progress)
        self.runner.set_progress_callback(callback)
        
        result = asyncio.run(
            self.runner.run_full_pipeline(
                input_path=file_path,
                project_name=project_name or None,
            )
        )
        
        if result.success:
            self.current_project_id = result.project_id
            
            final_message = f"✅ 处理完成！\n项目ID: {result.project_id}\n"
            final_message += f"章节数: {result.summary.get('chapter_count', 0)}\n"
            final_message += f"实体数: {result.summary.get('entity_count', 0)}\n"
            final_message += f"提示词数: {result.summary.get('prompt_count', 0)}"
            
            return final_message, gr.Slider(value=1.0), result.summary
        else:
            return f"❌ 处理失败: {result.error}", gr.Slider(value=0), {"error": result.error}
    
    def get_project_info(self, project_id: str):
        """
        获取项目信息
        
        Args:
            project_id: 项目ID
        
        Returns:
            项目信息字典
        """
        return self.runner.get_project_info(project_id)
    
    def load_project_prompts(self, project_id: str):
        """
        加载项目提示词
        
        Args:
            project_id: 项目ID
        
        Returns:
            提示词列表
        """
        return self.runner.load_project_prompts(project_id)


def main(port: int = 7861):
    """
    启动应用
    
    Args:
        port: 服务端口
    """
    print(f"🚀 启动AI拆书生图 Web界面...")
    print(f"📍 访问地址: http://localhost:{port}")
    
    app = SimpleGradioApp()
    interface = app.create_interface()
    
    interface.launch(
        server_port=port,
        share=False,
        debug=False,
    )


if __name__ == "__main__":
    main()
