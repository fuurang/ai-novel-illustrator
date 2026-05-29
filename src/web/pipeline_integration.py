"""
Pipeline Web集成模块

提供Web UI与Pipeline的集成，支持异步执行和进度报告
"""
import asyncio
import tempfile
import shutil
from pathlib import Path
from typing import Optional, Callable, Dict, Any, List
from dataclasses import dataclass, field

from src.core.pipeline import Pipeline, PipelineContext
from src.storage.project_store import ProjectStore


@dataclass
class StageProgress:
    """阶段进度信息"""
    stage: str
    stage_name: str
    progress: float
    message: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineResult:
    """流水线执行结果"""
    success: bool
    project_id: Optional[str] = None
    error: Optional[str] = None
    stage_results: Dict[str, Any] = field(default_factory=dict)
    summary: Dict[str, Any] = field(default_factory=dict)


class WebPipelineRunner:
    """
    Pipeline的Web运行器
    
    提供与Web UI集成的异步流水线执行功能，支持：
    - 异步执行流水线
    - 进度实时回调
    - 错误处理和重试
    - 项目状态管理
    """
    
    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        project_store: Optional[ProjectStore] = None
    ):
        """
        初始化Web流水线运行器
        
        Args:
            config: 配置字典
            project_store: 项目存储实例
        """
        self.config = config or {}
        self.project_store = project_store or ProjectStore()
        self.pipeline: Optional[Pipeline] = None
        self.is_running = False
        self._progress_callback: Optional[Callable] = None
        self._current_context: Optional[PipelineContext] = None
        self._stage_progress_map = {
            "preprocess": 0.15,
            "world_bible": 0.30,
            "extract": 0.50,
            "merge": 0.65,
            "attribute": 0.80,
            "prompt": 0.95,
            "illustrate": 1.0,
        }
        self._stage_names = {
            "preprocess": "预处理",
            "world_bible": "世界观构建",
            "extract": "实体提取",
            "merge": "实体合并",
            "attribute": "属性构建",
            "prompt": "提示词生成",
            "illustrate": "图片生成",
        }
    
    def set_progress_callback(
        self,
        callback: Callable[[str, float, str, Dict[str, Any]], None]
    ):
        """
        设置进度回调函数
        
        Args:
            callback: 回调函数，签名为 (stage, progress, message, details) -> None
        """
        self._progress_callback = callback
    
    def _report_progress(
        self,
        stage: str,
        progress: float,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        报告进度
        
        Args:
            stage: 阶段标识
            progress: 整体进度 (0.0 - 1.0)
            message: 进度消息
            details: 额外详情
        """
        if self._progress_callback:
            self._progress_callback(
                stage,
                progress,
                message,
                details or {}
            )
    
    async def run_full_pipeline(
        self,
        input_path: str,
        output_dir: str = "",
        project_name: Optional[str] = None,
        enable_image: bool = False,
        stages: Optional[List[str]] = None,
    ) -> PipelineResult:
        """
        运行完整流水线
        
        Args:
            input_path: 小说文件路径
            output_dir: 输出目录
            project_name: 项目名称（可选，默认使用文件名）
            enable_image: 是否启用图片生成
            stages: 执行的阶段列表（可选，默认全部）
        
        Returns:
            PipelineResult: 执行结果
        """
        self.is_running = True
        
        try:
            self._report_progress(
                "init",
                0.0,
                "正在初始化流水线..."
            )
            
            project_store = self.project_store
            if output_dir:
                project_store = ProjectStore(base_dir=output_dir)
            
            self.pipeline = Pipeline(self.config, project_store)
            
            self._report_progress(
                "preprocess",
                0.05,
                "正在创建项目..."
            )
            
            if project_name is None:
                project_name = Path(input_path).stem
            
            self._report_progress(
                "preprocess",
                0.10,
                "正在读取文件..."
            )
            
            self._current_context = await self.pipeline.run(
                input_path=input_path,
                output_dir=output_dir,
                stages=stages,
                enable_image=enable_image,
                project_name=project_name,
            )
            
            if self._current_context is None:
                return PipelineResult(
                    success=False,
                    error="流水线执行失败"
                )
            
            self._report_progress(
                "complete",
                1.0,
                "流水线执行完成！",
                {
                    "project_id": self._current_context.project.id,
                    "chapter_count": len(self._current_context.chapters),
                    "entity_count": len(self._current_context.entities),
                    "prompt_count": len(self._current_context.prompts),
                }
            )
            
            return PipelineResult(
                success=True,
                project_id=self._current_context.project.id,
                stage_results={
                    stage: result.model_dump()
                    for stage, result in self._current_context.stage_results.items()
                },
                summary={
                    "chapter_count": len(self._current_context.chapters),
                    "entity_count": len(self._current_context.entities),
                    "prompt_count": len(self._current_context.prompts),
                    "world_bible_id": self._current_context.project.world_bible_id,
                }
            )
            
        except Exception as e:
            self._report_progress(
                "error",
                0.0,
                f"执行出错: {str(e)}"
            )
            return PipelineResult(
                success=False,
                error=str(e)
            )
        finally:
            self.is_running = False
            self._current_context = None
    
    async def run_pipeline_with_stages(
        self,
        input_path: str,
        stages: List[str],
        output_dir: str = "",
        project_name: Optional[str] = None,
    ) -> PipelineResult:
        """
        运行指定阶段的流水线
        
        Args:
            input_path: 小说文件路径
            stages: 执行的阶段列表
            output_dir: 输出目录
            project_name: 项目名称
        
        Returns:
            PipelineResult: 执行结果
        """
        return await self.run_full_pipeline(
            input_path=input_path,
            output_dir=output_dir,
            project_name=project_name,
            stages=stages,
        )
    
    def get_current_progress(self) -> Optional[StageProgress]:
        """
        获取当前进度信息
        
        Returns:
            StageProgress: 当前进度，如果没有正在执行则返回None
        """
        if not self.is_running or self._current_context is None:
            return None
        
        return StageProgress(
            stage="current",
            stage_name="执行中",
            progress=0.5,
            message="流水线正在执行",
            details=self._current_context.stage_results
        )
    
    def stop(self):
        """
        停止执行
        
        注意：这是一个优雅停止的请求，实际停止需要等待当前阶段完成
        """
        if self.is_running:
            self._report_progress(
                "stopping",
                0.0,
                "正在停止流水线..."
            )
            self.is_running = False
    
    def get_project_info(self, project_id: str) -> Optional[Dict[str, Any]]:
        """
        获取项目信息
        
        Args:
            project_id: 项目ID
        
        Returns:
            项目信息字典
        """
        try:
            return self.project_store.load_project_info(project_id)
        except FileNotFoundError:
            return None
    
    def list_projects(self) -> List[Dict[str, Any]]:
        """
        列出所有项目
        
        Returns:
            项目列表
        """
        return self.project_store.list_projects()
    
    def load_project_prompts(self, project_id: str) -> List[Dict[str, Any]]:
        """
        加载项目的提示词
        
        Args:
            project_id: 项目ID
        
        Returns:
            提示词列表
        """
        return self.project_store.load_prompts(project_id)
    
    def load_project_entities(self, project_id: str) -> List[Dict[str, Any]]:
        """
        加载项目的实体
        
        Args:
            project_id: 项目ID
        
        Returns:
            实体列表
        """
        return self.project_store.load_entities(project_id)
    
    def load_project_world_bible(self, project_id: str) -> Optional[Dict[str, Any]]:
        """
        加载项目的世界观圣经
        
        Args:
            project_id: 项目ID
        
        Returns:
            世界观圣经数据
        """
        try:
            return self.project_store.load_world_bible(project_id)
        except FileNotFoundError:
            return None
    
    def export_project_prompts(self, project_id: str) -> Optional[Path]:
        """
        导出项目提示词为Markdown
        
        Args:
            project_id: 项目ID
        
        Returns:
            导出文件路径
        """
        try:
            prompts = self.project_store.load_prompts(project_id)
            if prompts:
                return self.project_store.save_prompts_md(
                    project_id,
                    prompts,
                    "prompts.md"
                )
        except Exception:
            pass
        return None


class ProgressCallback:
    """
    进度回调包装器
    
    用于将进度信息传递给Gradio等Web框架
    """
    
    def __init__(self):
        self.latest_stage = ""
        self.latest_progress = 0.0
        self.latest_message = ""
        self.latest_details = {}
    
    def __call__(
        self,
        stage: str,
        progress: float,
        message: str,
        details: Dict[str, Any] = None
    ):
        """
        更新进度信息
        
        Args:
            stage: 阶段标识
            progress: 进度值 (0.0 - 1.0)
            message: 进度消息
            details: 额外详情
        """
        self.latest_stage = stage
        self.latest_progress = progress
        self.latest_message = message
        self.latest_details = details or {}
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取当前状态
        
        Returns:
            状态字典
        """
        return {
            "stage": self.latest_stage,
            "progress": self.latest_progress,
            "message": self.latest_message,
            "details": self.latest_details,
        }
    
    def reset(self):
        """重置状态"""
        self.latest_stage = ""
        self.latest_progress = 0.0
        self.latest_message = ""
        self.latest_details = {}
