from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from src.llm.prompt_loader import PromptLoader

router = APIRouter()


class PromptTemplate(BaseModel):
    """提示词模板"""
    name: str
    system_prompt: str
    user_prompt: str
    description: Optional[str] = None


class PromptUpdate(BaseModel):
    """提示词更新请求"""
    system_prompt: str
    user_prompt: str


def get_prompt_description(name: str) -> str:
    """获取提示词的描述"""
    descriptions = {
        "world_bible_analyze": "世界观分析 - 从小说文本中提取世界观框架",
        "visual_anchoring": "视觉锚定 - 生成视觉风格和色彩体系",
        "entity_extraction": "实体提取 - 从章节中提取角色、场景、物品",
        "character_attribute": "角色属性 - 提取角色的完整视觉属性",
        "scene_attribute": "场景属性 - 提取场景的完整视觉属性",
        "item_attribute": "物品属性 - 提取物品的完整视觉属性",
        "character_prompt": "角色图像提示词生成",
        "scene_prompt": "场景图像提示词生成",
        "item_prompt": "物品图像提示词生成",
        "face_anchor_prompt": "面部锚定 - 确保角色面部一致性",
        "image_verify": "图像验证 - 验证生成图像的质量",
    }
    return descriptions.get(name, "")


# 全局的 prompt loader 实例
_prompt_loader: Optional[PromptLoader] = None


def get_prompt_loader() -> PromptLoader:
    """获取提示词加载器单例"""
    global _prompt_loader
    if _prompt_loader is None:
        _prompt_loader = PromptLoader()
    return _prompt_loader


@router.get("", response_model=List[Dict[str, Any]])
async def list_prompts():
    """列出所有可用的提示词模板"""
    loader = get_prompt_loader()
    template_names = loader.list_templates()
    
    prompts = []
    for name in sorted(template_names):
        try:
            data = loader.load(name)
            prompts.append({
                "name": name,
                "description": get_prompt_description(name),
                "has_system": "system_prompt" in data,
                "has_user": "user_prompt" in data,
            })
        except Exception as e:
            continue
    
    return prompts


@router.get("/{name}", response_model=PromptTemplate)
async def get_prompt(name: str):
    """获取指定的提示词模板"""
    loader = get_prompt_loader()
    
    if not loader.has_template(name):
        raise HTTPException(status_code=404, detail=f"提示词模板不存在: {name}")
    
    try:
        data = loader.load(name)
        return PromptTemplate(
            name=name,
            system_prompt=data.get("system_prompt", ""),
            user_prompt=data.get("user_prompt", ""),
            description=get_prompt_description(name),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取提示词失败: {str(e)}")


@router.put("/{name}")
async def update_prompt(name: str, prompt: PromptUpdate):
    """更新提示词模板"""
    loader = get_prompt_loader()
    
    if not loader.has_template(name):
        raise HTTPException(status_code=404, detail=f"提示词模板不存在: {name}")
    
    try:
        # 先读取现有数据，保留其他可能的字段
        existing_data = loader.load(name)
        
        # 更新提示词
        existing_data["system_prompt"] = prompt.system_prompt
        existing_data["user_prompt"] = prompt.user_prompt
        
        # 保存
        loader.save_template(name, existing_data)
        
        return {"success": True, "message": "提示词更新成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存提示词失败: {str(e)}")


@router.post("/{name}/reset")
async def reset_prompt(name: str):
    """重置提示词模板（暂未实现，需要备份原始提示词）"""
    # TODO: 实现提示词备份和重置功能
    raise HTTPException(status_code=501, detail="重置功能暂未实现")
