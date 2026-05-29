"""
进度状态管理模块

提供流水线执行过程中的进度跟踪和管理功能，包括：
- 实时进度更新
- 线程安全的进度访问
- 状态持久化
"""
import threading
import time
from typing import Optional, Callable, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum


class PipelineState(Enum):
    """流水线状态枚举"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class StageStatus:
    """阶段状态"""
    name: str
    display_name: str
    progress: float
    status: str
    message: str
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    details: Dict[str, Any] = field(default_factory=dict)


class ProgressManager:
    """
    进度管理器
    
    线程安全的进度状态管理，用于：
    - 跟踪流水线执行进度
    - 管理多个阶段的状态
    - 提供状态查询接口
    """
    
    STAGE_ORDER = [
        "init",
        "preprocess",
        "world_bible",
        "extract",
        "merge",
        "attribute",
        "prompt",
        "illustrate",
        "complete",
    ]
    
    STAGE_NAMES = {
        "init": "初始化",
        "preprocess": "预处理",
        "world_bible": "世界观构建",
        "extract": "实体提取",
        "merge": "实体合并",
        "attribute": "属性构建",
        "prompt": "提示词生成",
        "illustrate": "图片生成",
        "complete": "完成",
        "error": "错误",
        "stopping": "停止中",
    }
    
    def __init__(self):
        """初始化进度管理器"""
        self._lock = threading.Lock()
        self._state = PipelineState.IDLE
        self._current_stage = ""
        self._current_progress = 0.0
        self._current_message = ""
        self._is_running = False
        self._start_time: Optional[float] = None
        self._end_time: Optional[float] = None
        self._stages: Dict[str, StageStatus] = {}
        self._errors: List[str] = []
        self._warnings: List[str] = []
        self._result_data: Dict[str, Any] = {}
    
    def update(
        self,
        stage: str,
        progress: float,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        更新进度
        
        Args:
            stage: 阶段标识
            progress: 整体进度 (0.0 - 1.0)
            message: 进度消息
            details: 额外详情
        """
        with self._lock:
            self._current_stage = stage
            self._current_progress = progress
            self._current_message = message
            
            display_name = self.STAGE_NAMES.get(stage, stage)
            
            if stage not in self._stages:
                self._stages[stage] = StageStatus(
                    name=stage,
                    display_name=display_name,
                    progress=progress,
                    status="running",
                    message=message,
                    start_time=time.time(),
                )
            else:
                self._stages[stage].progress = progress
                self._stages[stage].message = message
                self._stages[stage].details.update(details or {})
            
            if progress >= 1.0:
                self._stages[stage].status = "completed"
                self._stages[stage].end_time = time.time()
            
            if details:
                self._stages[stage].details.update(details)
    
    def set_state(self, state: PipelineState):
        """
        设置流水线状态
        
        Args:
            state: 流水线状态
        """
        with self._lock:
            self._state = state
            
            if state == PipelineState.RUNNING:
                self._is_running = True
                if self._start_time is None:
                    self._start_time = time.time()
            elif state in [PipelineState.COMPLETED, PipelineState.FAILED]:
                self._is_running = False
                self._end_time = time.time()
    
    def add_error(self, error: str):
        """
        添加错误信息
        
        Args:
            error: 错误消息
        """
        with self._lock:
            self._errors.append(error)
            self._state = PipelineState.FAILED
            self._is_running = False
            self._end_time = time.time()
    
    def add_warning(self, warning: str):
        """
        添加警告信息
        
        Args:
            warning: 警告消息
        """
        with self._lock:
            self._warnings.append(warning)
    
    def set_result(self, key: str, value: Any):
        """
        设置结果数据
        
        Args:
            key: 结果键
            value: 结果值
        """
        with self._lock:
            self._result_data[key] = value
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取当前状态
        
        Returns:
            dict: 状态信息字典
        """
        with self._lock:
            return {
                "state": self._state.value,
                "stage": self._current_stage,
                "stage_name": self.STAGE_NAMES.get(self._current_stage, self._current_stage),
                "progress": self._current_progress,
                "message": self._current_message,
                "is_running": self._is_running,
                "start_time": self._start_time,
                "end_time": self._end_time,
                "elapsed_time": (
                    (time.time() - self._start_time) if self._start_time else 0
                ),
                "stages": {
                    stage: {
                        "progress": status.progress,
                        "status": status.status,
                        "message": status.message,
                        "details": status.details,
                    }
                    for stage, status in self._stages.items()
                },
                "errors": self._errors.copy(),
                "warnings": self._warnings.copy(),
                "result": self._result_data.copy(),
            }
    
    def get_current_stage_progress(self) -> Optional[StageStatus]:
        """
        获取当前阶段的详细进度
        
        Returns:
            StageStatus: 当前阶段状态
        """
        with self._lock:
            if self._current_stage and self._current_stage in self._stages:
                return self._stages[self._current_stage]
            return None
    
    def get_stage_progress(self, stage: str) -> Optional[StageStatus]:
        """
        获取指定阶段的进度
        
        Args:
            stage: 阶段标识
        
        Returns:
            StageStatus: 阶段状态
        """
        with self._lock:
            return self._stages.get(stage)
    
    def get_all_stages(self) -> List[StageStatus]:
        """
        获取所有阶段的列表
        
        Returns:
            List[StageStatus]: 阶段状态列表
        """
        with self._lock:
            result = []
            for stage_name in self.STAGE_ORDER:
                if stage_name in self._stages:
                    result.append(self._stages[stage_name])
            return result
    
    def reset(self):
        """重置所有状态"""
        with self._lock:
            self._state = PipelineState.IDLE
            self._current_stage = ""
            self._current_progress = 0.0
            self._current_message = ""
            self._is_running = False
            self._start_time = None
            self._end_time = None
            self._stages.clear()
            self._errors.clear()
            self._warnings.clear()
            self._result_data.clear()
    
    def is_running(self) -> bool:
        """
        检查是否正在运行
        
        Returns:
            bool: 是否正在运行
        """
        with self._lock:
            return self._is_running
    
    def get_elapsed_time(self) -> float:
        """
        获取已用时间
        
        Returns:
            float: 已用时间（秒）
        """
        with self._lock:
            if self._start_time:
                end = self._end_time if self._end_time else time.time()
                return end - self._start_time
            return 0.0
    
    def get_estimated_remaining_time(self) -> Optional[float]:
        """
        估算剩余时间
        
        Returns:
            float: 估算的剩余时间（秒）
        """
        with self._lock:
            if not self._start_time or self._current_progress <= 0:
                return None
            
            elapsed = time.time() - self._start_time
            if self._current_progress >= 1.0:
                return 0.0
            
            total_estimated = elapsed / self._current_progress
            return total_estimated - elapsed


class ProgressCallbackAdapter:
    """
    进度回调适配器
    
    将ProgressManager转换为可调用对象，用于Pipeline的进度回调
    """
    
    def __init__(self, progress_manager: Optional[ProgressManager] = None):
        """
        初始化适配器
        
        Args:
            progress_manager: ProgressManager实例
        """
        self.progress_manager = progress_manager or ProgressManager()
    
    def __call__(
        self,
        stage: str,
        progress: float,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        处理进度更新
        
        Args:
            stage: 阶段标识
            progress: 进度值
            message: 进度消息
            details: 额外详情
        """
        self.progress_manager.update(stage, progress, message, details)
    
    def get_progress_manager(self) -> ProgressManager:
        """
        获取ProgressManager
        
        Returns:
            ProgressManager: 进度管理器实例
        """
        return self.progress_manager


class WebProgressTracker:
    """
    Web进度跟踪器
    
    为Web UI优化的进度跟踪器，提供实时状态更新
    """
    
    def __init__(self):
        """初始化Web进度跟踪器"""
        self._progress_manager = ProgressManager()
        self._subscribers: List[Callable] = []
        self._lock = threading.Lock()
    
    def subscribe(self, callback: Callable[[Dict[str, Any]], None]):
        """
        订阅进度更新
        
        Args:
            callback: 回调函数
        """
        with self._lock:
            self._subscribers.append(callback)
    
    def unsubscribe(self, callback: Callable):
        """
        取消订阅
        
        Args:
            callback: 回调函数
        """
        with self._lock:
            if callback in self._subscribers:
                self._subscribers.remove(callback)
    
    def _notify_subscribers(self, status: Dict[str, Any]):
        """
        通知所有订阅者
        
        Args:
            status: 状态信息
        """
        with self._lock:
            for callback in self._subscribers:
                try:
                    callback(status)
                except Exception as e:
                    print(f"通知订阅者失败: {e}")
    
    def update(
        self,
        stage: str,
        progress: float,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        更新进度并通知订阅者
        
        Args:
            stage: 阶段标识
            progress: 进度值
            message: 进度消息
            details: 额外详情
        """
        self._progress_manager.update(stage, progress, message, details)
        status = self._progress_manager.get_status()
        self._notify_subscribers(status)
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取当前状态
        
        Returns:
            dict: 状态信息
        """
        return self._progress_manager.get_status()
    
    def reset(self):
        """重置状态"""
        self._progress_manager.reset()


def create_progress_callback(
    on_progress: Optional[Callable] = None
) -> tuple:
    """
    创建进度回调的便捷函数
    
    Args:
        on_progress: 进度更新回调函数
    
    Returns:
        tuple: (callback函数, ProgressManager实例)
    """
    progress_manager = ProgressManager()
    callback_adapter = ProgressCallbackAdapter(progress_manager)
    
    def callback(
        stage: str,
        progress: float,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        callback_adapter(stage, progress, message, details)
        if on_progress:
            on_progress(progress_manager.get_status())
    
    return callback, progress_manager
