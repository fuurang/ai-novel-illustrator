import asyncio
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Awaitable, Callable, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.api.routers.ai_workspace import AiRunRequest, run_ai_task
from src.api.routers.chapters import (
    group_end_chapter,
    group_start_chapter,
    last_chapter_number as _last_chapter_number,
    load_scene_groups,
    next_scene_start_chapter,
    parse_chapter_range,
    save_scene_groups,
    scene_chapters as _scene_chapters,
)
from src.api.routers.images import _entity_image_path, _generate_single_entity_image
from src.storage.project_store import ProjectStore

router = APIRouter()
store = ProjectStore()

_auto_tasks: dict[str, asyncio.Task] = {}


class AutoIllustrationStartRequest(BaseModel):
    scene_granularity: str = "medium"
    extraction_level: str = "balanced"
    skip_locked: bool = True


def _now() -> str:
    return datetime.now().isoformat()


def _state_path(project_id: str) -> Path:
    path = store.get_project_dir(project_id) / "data" / "auto_illustration_state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _default_state() -> dict[str, Any]:
    return {
        "status": "idle",
        "scene_granularity": "medium",
        "extraction_level": "balanced",
        "skip_locked": True,
        "current_scene_id": "",
        "current_scene_name": "",
        "current_phase": "done",
        "current_chapter": 1,
        "last_completed_chapter": 0,
        "total_chapters": 0,
        "completed_scene_ids": [],
        "skipped_scene_ids": [],
        "failed_steps": [],
        "retry_counts": {},
        "pause_requested": False,
        "stop_requested": False,
        "message": "",
        "progress": 0,
        "updated_at": _now(),
    }


def _load_state(project_id: str) -> dict[str, Any]:
    state = _default_state()
    path = _state_path(project_id)
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                state.update(loaded)
        except Exception:
            pass

    state.setdefault("completed_scene_ids", [])
    state.setdefault("skipped_scene_ids", [])
    state.setdefault("failed_steps", [])
    state.setdefault("retry_counts", {})
    state.setdefault("skip_locked", True)
    return state


def _save_state(project_id: str, state: dict[str, Any]) -> dict[str, Any]:
    state["updated_at"] = _now()
    with open(_state_path(project_id), "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    return state


def _update_state(project_id: str, **patch: Any) -> dict[str, Any]:
    state = _load_state(project_id)
    state.update(patch)
    return _save_state(project_id, state)


def _active_task(project_id: str) -> Optional[asyncio.Task]:
    task = _auto_tasks.get(project_id)
    if task and not task.done():
        return task
    if task and task.done():
        _auto_tasks.pop(project_id, None)
    return None


def _http_error_message(error: Exception) -> str:
    if isinstance(error, HTTPException):
        return str(error.detail)
    return str(error)


def _state_for_response(project_id: str) -> dict[str, Any]:
    state = _load_state(project_id)
    if state.get("status") == "running" and not _active_task(project_id):
        state = _save_state(project_id, {
            **state,
            "status": "paused",
            "pause_requested": True,
            "message": "服务进程里没有正在运行的任务，已保留进度；点击继续可从 checkpoint 恢复。",
        })
    return state


def _append_failed_step(
    project_id: str,
    *,
    phase: str,
    step: str,
    message: str,
    attempts: int = 1,
    scene: Optional[dict[str, Any]] = None,
    entity: Optional[dict[str, Any]] = None,
    skipped: bool = True,
) -> dict[str, Any]:
    state = _load_state(project_id)
    failed_steps = list(state.get("failed_steps") or [])
    failed_steps.insert(0, {
        "id": str(uuid.uuid4())[:8],
        "phase": phase,
        "step": step,
        "message": message,
        "attempts": attempts,
        "skipped": skipped,
        "scene_id": (scene or {}).get("id", state.get("current_scene_id", "")),
        "scene_name": (scene or {}).get("name", state.get("current_scene_name", "")),
        "entity_id": (entity or {}).get("id", ""),
        "entity_name": (entity or {}).get("name", ""),
        "created_at": _now(),
    })
    state["failed_steps"] = failed_steps[:200]
    state["message"] = message
    return _save_state(project_id, state)


def _record_retry(project_id: str, key: str, retries: int) -> None:
    state = _load_state(project_id)
    retry_counts = dict(state.get("retry_counts") or {})
    retry_counts[key] = retries
    state["retry_counts"] = retry_counts
    _save_state(project_id, state)


async def _with_retries(
    project_id: str,
    key: str,
    phase: str,
    work: Callable[[], Awaitable[Any]],
    *,
    attempts: int = 3,
    scene: Optional[dict[str, Any]] = None,
    entity: Optional[dict[str, Any]] = None,
) -> Any:
    last_error: Optional[Exception] = None
    for attempt in range(1, attempts + 1):
        try:
            if attempt > 1:
                _record_retry(project_id, key, attempt - 1)
                _update_state(project_id, message=f"{phase} 失败后重试 {attempt - 1}/{attempts - 1}")
            return await work()
        except Exception as error:
            last_error = error
            if attempt < attempts:
                await asyncio.sleep(min(2 * attempt, 5))
                continue

    message = _http_error_message(last_error or RuntimeError("未知错误"))
    _append_failed_step(
        project_id,
        phase=phase,
        step=key,
        message=message,
        attempts=attempts,
        scene=scene,
        entity=entity,
        skipped=True,
    )
    raise RuntimeError(message)


def _entity_chapter_numbers(entity: dict[str, Any]) -> set[int]:
    chapters: set[int] = set()

    def add(value: Any) -> None:
        try:
            number = int(value)
        except Exception:
            return
        if number > 0:
            chapters.add(number)

    for item in entity.get("source_quotes") or []:
        add(item if isinstance(item, int) else item.get("chapter") if isinstance(item, dict) else None)
    for item in entity.get("chapter_appearances") or []:
        add(item if isinstance(item, int) else item.get("chapter") if isinstance(item, dict) else None)
    for item in entity.get("source_chapters") or []:
        add(item)
    add(entity.get("first_appearance_chapter"))
    for chapter in parse_chapter_range(entity.get("chapter_range", "")):
        add(chapter)

    return chapters


def _entity_in_scene(entity: dict[str, Any], scene: dict[str, Any]) -> bool:
    scene_chapter_numbers = _scene_chapters(scene)
    if not scene_chapter_numbers:
        return True
    entity_chapters = _entity_chapter_numbers(entity)
    if not entity_chapters:
        return False
    return bool(entity_chapters & scene_chapter_numbers)


def _scene_entities(project_id: str, scene: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        entity for entity in store.load_entities(project_id)
        if _entity_in_scene(entity, scene)
    ]


def _has_visual_attributes(entity: dict[str, Any]) -> bool:
    attrs = entity.get("attributes")
    if not isinstance(attrs, dict) or not attrs:
        return False
    compact = json.dumps(attrs, ensure_ascii=False).translate(str.maketrans("", "", '{}[]":, \n\r\t'))
    return len(compact) > 8


def _task_prefix(entity: dict[str, Any]) -> str:
    if entity.get("type") == "scene":
        return "scene"
    if entity.get("type") == "item":
        return "item"
    return "character"


def _prompt_entity_ids(project_id: str) -> set[str]:
    return {
        prompt.get("entity_id", "")
        for prompt in store.load_prompts(project_id)
        if prompt.get("entity_id")
    }


def _chapter_range_label(scene: dict[str, Any]) -> str:
    if scene.get("chapter_range"):
        return str(scene["chapter_range"])
    chapters = sorted(_scene_chapters(scene))
    if not chapters:
        return ""
    return f"{chapters[0]}-{chapters[-1]}"


def _overall_progress(last_completed_chapter: int, total_chapters: int) -> int:
    if total_chapters <= 0:
        return 0
    return max(0, min(99, round(last_completed_chapter / total_chapters * 100)))


async def _run_ai_and_apply(project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    request = AiRunRequest(**payload, apply_result=True)
    result = await run_ai_task(project_id, request)
    return result.get("run", {})


async def _generate_image_or_raise(project_id: str, entity_id: str) -> dict[str, Any]:
    result = await _generate_single_entity_image(project_id, entity_id)
    if isinstance(result, dict) and result.get("error"):
        raise RuntimeError(result["error"])
    return result


async def _check_control(project_id: str) -> bool:
    state = _load_state(project_id)
    if state.get("stop_requested"):
        _update_state(project_id, status="stopped", current_phase="done", message="已停止")
        return True
    if state.get("pause_requested"):
        _update_state(project_id, status="paused", message="已暂停，点击继续可从当前 checkpoint 恢复。")
        return True
    return False


def _create_fallback_scene(project_id: str, start_chapter: int, granularity: str, reason: str) -> dict[str, Any]:
    groups = load_scene_groups(project_id)
    group = {
        "id": f"scene_skip_{start_chapter}_{str(uuid.uuid4())[:4]}",
        "name": f"待人工检查场景 第{start_chapter}章",
        "chapter_range": f"{start_chapter}-{start_chapter}",
        "chapters": [start_chapter],
        "description": "AI 自动分场景失败后创建的单章占位场景，建议后续人工检查。",
        "confidence": 0.1,
        "granularity": granularity,
        "reasoning": reason,
        "source": "ai",
        "auto_skip": True,
    }
    groups.append(group)
    save_scene_groups(project_id, groups)
    return group


async def _segment_next_scene(project_id: str, start_chapter: int, granularity: str) -> dict[str, Any]:
    run = await _run_ai_and_apply(project_id, {
        "task": "scene_segmentation",
        "start_chapter": start_chapter,
        "scene_granularity": granularity,
        "attachment_refs": ["data:world_bible", "data:scene_groups"],
    })
    applied = run.get("applied") or {}
    group_id = applied.get("group_id")
    if not group_id:
        raise RuntimeError(applied.get("message") or "AI 未写入场景分组")

    for group in load_scene_groups(project_id):
        if str(group.get("id", "")) == str(group_id):
            return group
    raise RuntimeError(f"场景已生成但无法重新读取: {group_id}")


async def _run_scene_illustration(project_id: str, scene: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    scene_id = str(scene.get("id", ""))
    scene_ref = f"scene:{scene_id}"
    extraction_level = state.get("extraction_level", "balanced")
    skip_locked = bool(state.get("skip_locked", True))
    base_refs = ["data:world_bible", "data:scene_groups", "data:entities"]
    refs_with_scene = ["data:world_bible", "data:scene_groups", scene_ref, "data:entities", "data:prompts"]

    _update_state(
        project_id,
        current_scene_id=scene_id,
        current_scene_name=scene.get("name", ""),
        current_phase="extract",
        message=f"识别当前场景出图对象：{scene.get('name', '')}",
    )

    scene_entities = _scene_entities(project_id, scene)
    if not scene_entities:
        try:
            await _with_retries(
                project_id,
                f"extract:{scene_id}",
                "extract",
                lambda: _run_ai_and_apply(project_id, {
                    "task": "entity_extraction",
                    "extraction_level": extraction_level,
                    "attachment_refs": ["data:world_bible", "data:scene_groups", scene_ref, "data:entities"],
                }),
                scene=scene,
            )
        except Exception:
            return {"skipped": True, "entities": 0, "images": 0}
        scene_entities = _scene_entities(project_id, scene)

    if not scene_entities:
        _append_failed_step(
            project_id,
            phase="extract",
            step=f"extract:{scene_id}",
            message="当前场景没有识别到可出图对象，已跳过。",
            attempts=3,
            scene=scene,
            skipped=True,
        )
        return {"skipped": True, "entities": 0, "images": 0}

    if await _check_control(project_id):
        return {"stopped": True}

    attribute_targets = [entity for entity in scene_entities if not _has_visual_attributes(entity)]
    for index, entity in enumerate(attribute_targets, start=1):
        if await _check_control(project_id):
            return {"stopped": True}
        prefix = _task_prefix(entity)
        _update_state(
            project_id,
            current_phase="attribute",
            message=f"整理视觉设定 {index}/{len(attribute_targets)}：{entity.get('name', entity.get('id', ''))}",
        )
        try:
            await _with_retries(
                project_id,
                f"attribute:{entity.get('id', '')}",
                "attribute",
                lambda entity=entity, prefix=prefix: _run_ai_and_apply(project_id, {
                    "task": f"{prefix}_attribute",
                    "entity_id": entity.get("id"),
                    "attachment_refs": refs_with_scene if prefix == "character" else [*base_refs, scene_ref, "data:prompts"],
                }),
                scene=scene,
                entity=entity,
            )
        except Exception:
            continue

    if await _check_control(project_id):
        return {"stopped": True}

    scene_entities = _scene_entities(project_id, scene)
    prompt_entity_ids = _prompt_entity_ids(project_id)
    prompt_targets = [entity for entity in scene_entities if entity.get("id") not in prompt_entity_ids]
    for index, entity in enumerate(prompt_targets, start=1):
        if await _check_control(project_id):
            return {"stopped": True}
        prefix = _task_prefix(entity)
        _update_state(
            project_id,
            current_phase="prompt",
            message=f"生成绘图指令 {index}/{len(prompt_targets)}：{entity.get('name', entity.get('id', ''))}",
        )
        try:
            await _with_retries(
                project_id,
                f"prompt:{entity.get('id', '')}",
                "prompt",
                lambda entity=entity, prefix=prefix: _run_ai_and_apply(project_id, {
                    "task": f"{prefix}_prompt",
                    "entity_id": entity.get("id"),
                    "attachment_refs": [*base_refs, scene_ref],
                }),
                scene=scene,
                entity=entity,
            )
        except Exception:
            continue

    if await _check_control(project_id):
        return {"stopped": True}

    prompt_entity_ids = _prompt_entity_ids(project_id)
    scene_entities = _scene_entities(project_id, scene)
    image_targets = []
    for entity in scene_entities:
        if entity.get("id") not in prompt_entity_ids:
            continue
        if skip_locked and entity.get("image_locked") and entity.get("locked_image_path"):
            continue
        if _entity_image_path(project_id, entity):
            continue
        image_targets.append(entity)

    generated_images = 0
    consecutive_failures = 0
    for index, entity in enumerate(image_targets, start=1):
        if await _check_control(project_id):
            return {"stopped": True}
        if consecutive_failures >= 3:
            _append_failed_step(
                project_id,
                phase="image",
                step=f"image:scene:{scene_id}",
                message="本场景图片连续失败达到 3 个对象，已跳过剩余图片。",
                attempts=1,
                scene=scene,
                skipped=True,
            )
            break

        _update_state(
            project_id,
            current_phase="image",
            message=f"生成图片 {index}/{len(image_targets)}：{entity.get('name', entity.get('id', ''))}",
        )
        try:
            result = await _with_retries(
                project_id,
                f"image:{entity.get('id', '')}",
                "image",
                lambda entity=entity: _generate_image_or_raise(project_id, entity.get("id", "")),
                scene=scene,
                entity=entity,
            )
            if not result:
                raise RuntimeError("图片生成接口未返回结果")
            generated_images += 1
            consecutive_failures = 0
        except Exception:
            consecutive_failures += 1
            continue

    return {"skipped": False, "entities": len(scene_entities), "images": generated_images}


async def _run_auto_workflow(project_id: str) -> None:
    try:
        while True:
            if await _check_control(project_id):
                return

            chapters = store.load_chapters(project_id)
            total_chapters = _last_chapter_number(chapters)
            if total_chapters <= 0:
                _update_state(project_id, status="failed", current_phase="done", message="项目没有章节数据，无法启动全书自动出图。")
                return

            groups = load_scene_groups(project_id)
            start_chapter = next_scene_start_chapter(chapters, groups)
            state = _load_state(project_id)
            progress = _overall_progress(max(0, start_chapter - 1), total_chapters)
            _update_state(
                project_id,
                status="running",
                current_phase="segment",
                current_chapter=start_chapter,
                total_chapters=total_chapters,
                progress=progress,
                message=f"从第 {start_chapter} 章开始识别下一个场景",
            )

            if start_chapter > total_chapters:
                _update_state(
                    project_id,
                    status="completed",
                    current_phase="done",
                    progress=100,
                    current_scene_id="",
                    current_scene_name="",
                    pause_requested=False,
                    stop_requested=False,
                    message="全书自动分场景出图已完成。",
                )
                return

            try:
                scene = await _with_retries(
                    project_id,
                    f"segment:{start_chapter}",
                    "segment",
                    lambda: _segment_next_scene(project_id, start_chapter, state.get("scene_granularity", "medium")),
                )
            except Exception as error:
                message = _http_error_message(error)
                scene = _create_fallback_scene(
                    project_id,
                    start_chapter,
                    state.get("scene_granularity", "medium"),
                    message,
                )
                skipped_ids = list(_load_state(project_id).get("skipped_scene_ids") or [])
                if scene["id"] not in skipped_ids:
                    skipped_ids.append(scene["id"])
                _update_state(
                    project_id,
                    current_phase="skip",
                    current_scene_id=scene["id"],
                    current_scene_name=scene["name"],
                    last_completed_chapter=start_chapter,
                    progress=_overall_progress(start_chapter, total_chapters),
                    skipped_scene_ids=skipped_ids,
                    message=f"场景分段失败，已创建单章待检查场景并跳过：第 {start_chapter} 章",
                )
                continue

            if await _check_control(project_id):
                return

            scene_start = group_start_chapter(scene) or start_chapter
            scene_end = group_end_chapter(scene) or scene_start
            _update_state(
                project_id,
                current_scene_id=scene.get("id", ""),
                current_scene_name=scene.get("name", ""),
                current_chapter=scene_start,
                message=f"处理场景：{scene.get('name', '')}（第 {_chapter_range_label(scene)} 章）",
            )

            result = await _run_scene_illustration(project_id, scene, _load_state(project_id))
            if result.get("stopped"):
                return

            state = _load_state(project_id)
            completed_ids = list(state.get("completed_scene_ids") or [])
            skipped_ids = list(state.get("skipped_scene_ids") or [])
            scene_id = str(scene.get("id", ""))
            if scene_id and scene_id not in completed_ids:
                completed_ids.append(scene_id)
            if result.get("skipped") and scene_id and scene_id not in skipped_ids:
                skipped_ids.append(scene_id)

            _update_state(
                project_id,
                current_phase="done",
                last_completed_chapter=max(scene_end, state.get("last_completed_chapter", 0)),
                progress=_overall_progress(max(scene_end, state.get("last_completed_chapter", 0)), total_chapters),
                completed_scene_ids=completed_ids,
                skipped_scene_ids=skipped_ids,
                message=(
                    f"场景完成：{scene.get('name', '')}；"
                    f"处理对象 {result.get('entities', 0)} 个，生成图片 {result.get('images', 0)} 张。"
                ),
            )
    except Exception as error:
        _append_failed_step(
            project_id,
            phase="workflow",
            step="auto_workflow",
            message=_http_error_message(error),
            attempts=1,
            skipped=False,
        )
        _update_state(project_id, status="failed", current_phase="done", message=f"全书自动出图任务异常：{_http_error_message(error)}")
    finally:
        _auto_tasks.pop(project_id, None)


def _launch_task(project_id: str) -> dict[str, Any]:
    if _active_task(project_id):
        raise HTTPException(status_code=409, detail="当前项目已有全书自动出图任务正在运行。")
    task = asyncio.create_task(_run_auto_workflow(project_id))
    _auto_tasks[project_id] = task
    return _state_for_response(project_id)


@router.post("/{project_id}/auto-illustration/start")
async def start_auto_illustration(project_id: str, request: AutoIllustrationStartRequest):
    if not store.project_exists(project_id):
        raise HTTPException(status_code=404, detail=f"项目不存在: {project_id}")
    if _active_task(project_id):
        raise HTTPException(status_code=409, detail="当前项目已有全书自动出图任务正在运行。")

    state = _load_state(project_id)
    state.update({
        "status": "running",
        "scene_granularity": request.scene_granularity,
        "extraction_level": request.extraction_level,
        "skip_locked": request.skip_locked,
        "pause_requested": False,
        "stop_requested": False,
        "message": "全书自动出图任务已启动。",
    })
    _save_state(project_id, state)
    return _launch_task(project_id)


@router.post("/{project_id}/auto-illustration/pause")
async def pause_auto_illustration(project_id: str):
    if not store.project_exists(project_id):
        raise HTTPException(status_code=404, detail=f"项目不存在: {project_id}")
    state = _load_state(project_id)
    state["pause_requested"] = True
    state["message"] = "已请求暂停，当前 AI/API 小步骤结束后生效。"
    if not _active_task(project_id):
        state["status"] = "paused"
    return _save_state(project_id, state)


@router.post("/{project_id}/auto-illustration/resume")
async def resume_auto_illustration(project_id: str):
    if not store.project_exists(project_id):
        raise HTTPException(status_code=404, detail=f"项目不存在: {project_id}")
    if _active_task(project_id):
        raise HTTPException(status_code=409, detail="当前项目已有全书自动出图任务正在运行。")
    state = _load_state(project_id)
    state.update({
        "status": "running",
        "pause_requested": False,
        "stop_requested": False,
        "message": "已从 checkpoint 继续全书自动出图任务。",
    })
    _save_state(project_id, state)
    return _launch_task(project_id)


@router.post("/{project_id}/auto-illustration/stop")
async def stop_auto_illustration(project_id: str):
    if not store.project_exists(project_id):
        raise HTTPException(status_code=404, detail=f"项目不存在: {project_id}")
    state = _load_state(project_id)
    state["stop_requested"] = True
    state["message"] = "已请求停止，当前 AI/API 小步骤结束后生效。"
    if not _active_task(project_id):
        state["status"] = "stopped"
        state["current_phase"] = "done"
    return _save_state(project_id, state)


@router.get("/{project_id}/auto-illustration/status")
async def get_auto_illustration_status(project_id: str):
    if not store.project_exists(project_id):
        raise HTTPException(status_code=404, detail=f"项目不存在: {project_id}")
    return _state_for_response(project_id)


@router.get("/{project_id}/auto-illustration/events")
async def auto_illustration_events(project_id: str, request: Request):
    if not store.project_exists(project_id):
        raise HTTPException(status_code=404, detail=f"项目不存在: {project_id}")

    async def event_stream():
        while True:
            if await request.is_disconnected():
                break
            state = _state_for_response(project_id)
            yield f"data: {json.dumps(state, ensure_ascii=False)}\n\n"
            await asyncio.sleep(1)

    return StreamingResponse(event_stream(), media_type="text/event-stream")
