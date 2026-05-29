"""
Web UI模块

提供Web界面与后端Pipeline的集成功能
"""
from src.web.pipeline_integration import (
    WebPipelineRunner,
    PipelineResult,
    StageProgress,
    ProgressCallback,
)
from src.web.upload import (
    FileUploadHandler,
    handle_file_upload,
    handle_multiple_file_uploads,
    validate_uploaded_file,
    cleanup_temp_files,
    read_file_content,
    get_file_info,
)
from src.web.progress import (
    ProgressManager,
    PipelineState,
    StageStatus,
    ProgressCallbackAdapter,
    WebProgressTracker,
    create_progress_callback,
)

__all__ = [
    "WebPipelineRunner",
    "PipelineResult",
    "StageProgress",
    "ProgressCallback",
    "FileUploadHandler",
    "handle_file_upload",
    "handle_multiple_file_uploads",
    "validate_uploaded_file",
    "cleanup_temp_files",
    "read_file_content",
    "get_file_info",
    "ProgressManager",
    "PipelineState",
    "StageStatus",
    "ProgressCallbackAdapter",
    "WebProgressTracker",
    "create_progress_callback",
]
