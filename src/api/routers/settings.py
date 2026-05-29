import yaml
import httpx
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

CONFIG_PATH = Path("./config/default.yaml")
USER_CONFIG_PATH = Path("./config/user.yaml")


def _deep_merge(base: dict, override: dict) -> dict:
    """深度合并两个字典，override 覆盖 base"""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config() -> dict:
    """加载配置，合并默认配置和用户配置"""
    config = {}

    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

    if USER_CONFIG_PATH.exists():
        with open(USER_CONFIG_PATH, "r", encoding="utf-8") as f:
            user_config = yaml.safe_load(f) or {}
        config = _deep_merge(config, user_config)

    return config


def save_config(config: dict) -> None:
    """保存用户配置"""
    USER_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(USER_CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False)


class SettingsUpdate(BaseModel):
    """设置更新请求"""
    llm: Optional[dict] = None
    world_bible: Optional[dict] = None
    extraction: Optional[dict] = None
    prompt: Optional[dict] = None
    image: Optional[dict] = None
    face_consistency: Optional[dict] = None


class TestConnectionRequest(BaseModel):
    """测试连接请求"""
    provider: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None


@router.get("")
async def get_settings():
    """获取设置"""
    config = load_config()
    if "llm" in config and "api_key" in config["llm"]:
        key = config["llm"]["api_key"]
        if key:
            config["llm"]["api_key"] = key[:8] + "****" + key[-4:] if len(key) > 12 else "****"
    return config


@router.put("")
async def update_settings(request: SettingsUpdate):
    """更新设置"""
    user_config = {}
    if request.llm is not None:
        user_config["llm"] = request.llm
    if request.world_bible is not None:
        user_config["world_bible"] = request.world_bible
    if request.extraction is not None:
        user_config["extraction"] = request.extraction
    if request.prompt is not None:
        user_config["prompt"] = request.prompt
    if request.image is not None:
        user_config["image"] = request.image
    if request.face_consistency is not None:
        user_config["face_consistency"] = request.face_consistency

    existing = {}
    if USER_CONFIG_PATH.exists():
        with open(USER_CONFIG_PATH, "r", encoding="utf-8") as f:
            existing = yaml.safe_load(f) or {}

    merged = _deep_merge(existing, user_config)
    save_config(merged)

    return {"message": "设置已更新"}


@router.post("/test-connection")
async def test_connection(request: TestConnectionRequest):
    """测试API连接"""
    config = load_config()
    llm_config = config.get("llm", {})

    provider = request.provider or llm_config.get("provider", "deepseek")
    api_key = request.api_key or llm_config.get("api_key", "")
    base_url = request.base_url or llm_config.get("base_url", "")
    model = request.model or llm_config.get("model", "deepseek-chat")

    if not api_key:
        raise HTTPException(status_code=400, detail="未提供API Key")

    if not base_url:
        raise HTTPException(status_code=400, detail="未提供Base URL")

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 5,
            }
            response = await client.post(
                f"{base_url}/chat/completions",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            return {"success": True, "message": "连接成功", "model": model}
    except httpx.HTTPStatusError as e:
        return {"success": False, "message": f"HTTP错误: {e.response.status_code}", "detail": str(e)}
    except httpx.ConnectError:
        return {"success": False, "message": f"无法连接到 {base_url}"}
    except Exception as e:
        return {"success": False, "message": f"连接失败: {str(e)}"}
