import asyncio
import json
from typing import Optional, List

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.storage.project_store import ProjectStore
from src.core.pipeline import Pipeline
from src.api.routers.settings import load_config

router = APIRouter()

_pipeline_tasks: dict = {}
_pipeline_status: dict = {}

store = ProjectStore()


class PipelineRequest(BaseModel):
    stages: Optional[List[str]] = None
    enable_image: bool = False
    chapter_range: Optional[str] = None
    chapter_indices: Optional[List[int]] = None


def _get_project_input_file(project_id: str) -> str:
    info = store.load_project_info(project_id)
    input_file = info.get("input_file", "")
    if not input_file:
        raise ValueError(f"项目 {project_id} 没有关联的输入文件")
    return input_file


def _parse_chapter_range(chapter_range: str) -> List[int]:
    result = []
    for part in chapter_range.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            result.extend(range(int(start), int(end) + 1))
        else:
            result.append(int(part))
    return result


async def _run_pipeline_task(project_id: str, config: dict, request: PipelineRequest):
    try:
        chapter_indices = None
        if request.chapter_indices:
            chapter_indices = request.chapter_indices
        elif request.chapter_range:
            chapter_indices = _parse_chapter_range(request.chapter_range)

        _pipeline_status[project_id] = {
            "is_running": True,
            "current_stage": "初始化",
            "current_stage_key": "init",
            "progress": 0,
            "stages_completed": [],
            "error": None,
        }

        input_file = _get_project_input_file(project_id)
        pipeline = Pipeline(config, store)

        stages = request.stages
        if stages is None:
            stages = ["preprocess", "world_bible", "extract", "merge", "attribute", "prompt"]

        stage_names = {
            "preprocess": "预处理",
            "world_bible": "世界观构建",
            "extract": "实体提取",
            "merge": "实体合并",
            "attribute": "属性构建",
            "prompt": "提示词生成",
            "illustrate": "图片生成",
            "face_anchor": "面部锚定图",
            "character_image": "角色全身图",
            "scene_image": "场景图",
            "item_image": "物品图",
        }

        total_stages = len(stages)
        completed = []

        for i, stage in enumerate(stages):
            chapter_info = ""
            if chapter_indices and stage in ("extract", "attribute", "prompt"):
                chapter_info = f" (第{min(chapter_indices)}-{max(chapter_indices)}章)" if len(chapter_indices) > 1 else f" (第{chapter_indices[0]}章)"

            _pipeline_status[project_id] = {
                "is_running": True,
                "current_stage": stage_names.get(stage, stage) + chapter_info,
                "current_stage_key": stage,
                "progress": int(i / total_stages * 100),
                "stages_completed": list(completed),
                "error": None,
            }

            context = await pipeline.run(
                input_path=input_file,
                output_dir="",
                stages=[stage],
                enable_image=stage in ("illustrate", "face_anchor", "character_image", "scene_image", "item_image") and request.enable_image,
                project_id=project_id,
                project_name=store.load_project_info(project_id).get("name", ""),
                chapter_indices=chapter_indices,
            )

            if context is None:
                _pipeline_status[project_id] = {
                    "is_running": False,
                    "current_stage": stage_names.get(stage, stage),
                    "current_stage_key": stage,
                    "progress": int(i / total_stages * 100),
                    "stages_completed": list(completed),
                    "error": f"阶段 {stage_names.get(stage, stage)} 执行失败",
                }
                return

            completed.append(stage)

        _pipeline_status[project_id] = {
            "is_running": False,
            "current_stage": "完成",
            "current_stage_key": "done",
            "progress": 100,
            "stages_completed": list(completed),
            "error": None,
        }

    except Exception as e:
        _pipeline_status[project_id] = {
            "is_running": False,
            "current_stage": "失败",
            "current_stage_key": "error",
            "progress": 0,
            "stages_completed": [],
            "error": str(e),
        }


@router.post("/{project_id}/pipeline")
async def run_pipeline(project_id: str, request: PipelineRequest = None):
    if not store.project_exists(project_id):
        raise HTTPException(status_code=404, detail=f"项目不存在: {project_id}")

    if project_id in _pipeline_tasks and not _pipeline_tasks[project_id].done():
        raise HTTPException(status_code=409, detail="流水线正在运行中，请等待完成")

    if request is None:
        request = PipelineRequest()

    config = load_config()
    task = asyncio.create_task(_run_pipeline_task(project_id, config, request))
    _pipeline_tasks[project_id] = task

    return {"message": "流水线已启动", "project_id": project_id}


@router.get("/{project_id}/pipeline/status")
async def pipeline_status(project_id: str):
    async def event_generator():
        while True:
            status = _pipeline_status.get(project_id, {
                "is_running": False,
                "current_stage": "未启动",
                "progress": 0,
                "stages_completed": [],
                "error": None,
            })
            yield f"data: {json.dumps(status, ensure_ascii=False)}\n\n"
            if not status.get("is_running", False):
                break
            await asyncio.sleep(1)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
