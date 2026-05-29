"""
Web集成模块使用示例

演示如何使用Web UI模块来运行流水线
"""
import asyncio
from pathlib import Path
from src.web import (
    WebPipelineRunner,
    FileUploadHandler,
    ProgressManager,
    create_progress_callback,
)


async def example_basic_usage():
    """
    基本使用示例
    """
    print("=" * 50)
    print("基本使用示例")
    print("=" * 50)
    
    runner = WebPipelineRunner()
    
    progress_manager = ProgressManager()
    callback, _ = create_progress_callback(
        on_progress=lambda status: print(f"进度: {status['progress']:.2%} - {status['message']}")
    )
    
    runner.set_progress_callback(callback)
    
    print("WebPipelineRunner 初始化完成")
    print(f"是否运行中: {runner.is_running}")
    print()


async def example_with_file_upload():
    """
    带文件上传的使用示例
    """
    print("=" * 50)
    print("文件上传示例")
    print("=" * 50)
    
    upload_handler = FileUploadHandler()
    
    print(f"上传目录: {upload_handler.get_upload_dir()}")
    
    print("已上传文件:")
    for file_info in upload_handler.list_uploaded_files():
        print(f"  - {file_info['name']} ({file_info['size']} bytes)")
    
    print()


def example_progress_tracking():
    """
    进度跟踪示例
    """
    print("=" * 50)
    print("进度跟踪示例")
    print("=" * 50)
    
    progress_manager = ProgressManager()
    
    progress_manager.update("preprocess", 0.1, "正在读取文件...")
    print(f"阶段: {progress_manager.get_status()['stage_name']}")
    print(f"进度: {progress_manager.get_status()['progress']:.2%}")
    print(f"消息: {progress_manager.get_status()['message']}")
    
    progress_manager.update("preprocess", 0.5, "文件读取完成")
    progress_manager.update("world_bible", 0.6, "正在构建世界观...")
    
    print("\n所有阶段:")
    for stage in progress_manager.get_all_stages():
        print(f"  - {stage.display_name}: {stage.progress:.2%} ({stage.status})")
    
    print()


async def main():
    """
    主函数
    """
    print("\n" + "=" * 50)
    print("Web集成模块演示")
    print("=" * 50 + "\n")
    
    await example_basic_usage()
    example_progress_tracking()
    await example_with_file_upload()
    
    print("=" * 50)
    print("演示完成！")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
