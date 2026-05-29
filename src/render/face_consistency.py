from typing import Dict, Any, Optional, List
from pathlib import Path
import json


class FaceConsistencyChecker:
    """面部一致性维护模块"""

    def __init__(self, llm_adapter, config: Dict[str, Any] = None):
        """初始化面部一致性模块
        
        Args:
            llm_adapter: LLM适配器实例
            config: 配置字典
        """
        self.llm_adapter = llm_adapter
        self.config = config or {}
        self.similarity_threshold = self.config.get("similarity_threshold", 0.7)
        self.max_retries = self.config.get("max_retries", 3)

    def store_face_anchor(
        self,
        character_id: str,
        face_data: Dict[str, Any]
    ) -> None:
        """存储面部锚点
        
        Args:
            character_id: 角色ID
            face_data: 面部数据
        """
        self._face_cache[character_id] = face_data

    def get_face_anchor(self, character_id: str) -> Optional[Dict[str, Any]]:
        """获取面部锚点
        
        Args:
            character_id: 角色ID
            
        Returns:
            面部数据
        """
        return self._face_cache.get(character_id)

    def load_face_anchors(self, project_path: str) -> None:
        """从项目加载面部锚点
        
        Args:
            project_path: 项目路径
        """
        anchors_file = Path(project_path) / 'face_anchors.json'
        
        if anchors_file.exists():
            with open(anchors_file, 'r', encoding='utf-8') as f:
                self._face_cache = json.load(f)

    def save_face_anchors(self, project_path: str) -> None:
        """保存面部锚点到项目
        
        Args:
            project_path: 项目路径
        """
        anchors_file = Path(project_path) / 'face_anchors.json'
        
        with open(anchors_file, 'w', encoding='utf-8') as f:
            json.dump(self._face_cache, f, ensure_ascii=False, indent=2)

    def create_face_description(
        self,
        character: Dict[str, Any],
        world_bible: Optional[Dict[str, Any]] = None
    ) -> str:
        """创建面部描述
        
        Args:
            character: 角色字典
            world_bible: 世界观圣经
            
        Returns:
            面部描述文本
        """
        appearance = character.get('appearance', {})
        parts = []
        
        if 'gender' in appearance:
            parts.append(appearance['gender'])
        
        if 'age_appearance' in appearance:
            parts.append(appearance['age_appearance'])
        
        if 'face_shape' in appearance:
            parts.append(f"{appearance['face_shape']} face")
        
        if 'skin_tone' in appearance:
            parts.append(f"{appearance['skin_tone']} skin")
        
        if 'eyes' in appearance:
            parts.append(f"eyes: {appearance['eyes']}")
        
        if 'hair' in appearance:
            parts.append(f"hair: {appearance['hair']}")
        
        if 'distinctive_features' in appearance:
            features = appearance['distinctive_features']
            if isinstance(features, list):
                parts.extend(features)
            else:
                parts.append(str(features))
        
        return ', '.join(parts)

    def generate_face_prompt(
        self,
        character: Dict[str, Any],
        scene_context: str,
        world_bible: Optional[Dict[str, Any]] = None
    ) -> str:
        """生成面部提示词
        
        Args:
            character: 角色字典
            scene_context: 场景上下文
            world_bible: 世界观圣经
            
        Returns:
            面部提示词
        """
        face_description = self.create_face_description(character, world_bible)
        
        prompt_parts = [face_description]
        
        if scene_context:
            prompt_parts.append(f"context: {scene_context}")
        
        art_style = "portrait style"
        if world_bible and 'visual_rules' in world_bible:
            vr = world_bible['visual_rules']
            if 'character_rules' in vr:
                cr = vr['character_rules']
                if 'art_style' in cr:
                    art_style = cr['art_style']
        
        prompt_parts.append(art_style)
        
        return ', '.join(prompt_parts)

    def maintain_face_consistency(
        self,
        base_image_path: str,
        new_scene_prompt: str,
        character: Dict[str, Any],
        face_anchor: Dict[str, Any],
        backend
    ) -> Dict[str, Any]:
        """在新场景中保持面部一致性
        
        Args:
            base_image_path: 基础图像路径
            new_scene_prompt: 新场景提示词
            character: 角色字典
            face_anchor: 面部锚点
            backend: 图像后端
            
        Returns:
            生成结果
        """
        if self.method == 'edit_image':
            combined_prompt = self._build_edit_prompt(
                face_anchor, new_scene_prompt, character
            )
            
            return backend.edit(base_image_path, combined_prompt)
        
        elif self.method == 'img2img':
            return self._img2img_consistency(
                base_image_path, new_scene_prompt, face_anchor, backend
            )
        
        else:
            return {'success': False, 'error': f'Unknown method: {self.method}'}

    def _build_edit_prompt(
        self,
        face_anchor: Dict[str, Any],
        scene_prompt: str,
        character: Dict[str, Any]
    ) -> str:
        """构建编辑提示词
        
        Args:
            face_anchor: 面部锚点
            scene_prompt: 场景提示词
            character: 角色字典
            
        Returns:
            组合后的提示词
        """
        parts = []
        
        if 'description' in face_anchor:
            parts.append(face_anchor['description'])
        
        parts.append(scene_prompt)
        
        if 'preserve_features' in face_anchor:
            preserve = face_anchor['preserve_features']
            if isinstance(preserve, list):
                parts.append(f"Preserve: {', '.join(preserve)}")
        
        return ', '.join(parts)

    def _img2img_consistency(
        self,
        base_image_path: str,
        new_scene_prompt: str,
        face_anchor: Dict[str, Any],
        backend
    ) -> Dict[str, Any]:
        """使用img2img保持一致性
        
        Args:
            base_image_path: 基础图像路径
            new_scene_prompt: 新场景提示词
            face_anchor: 面部锚点
            backend: 图像后端
            
        Returns:
            生成结果
        """
        raise NotImplementedError("img2img一致性方法尚未实现")

    def verify_similarity(
        self,
        image1_path: str,
        image2_path: str,
        character: Dict[str, Any]
    ) -> float:
        """验证两张图像的面部相似度
        
        Args:
            image1_path: 图像1路径
            image2_path: 图像2路径
            character: 角色字典
            
        Returns:
            相似度分数
        """
        if self.verify_with_llm and self.llm_adapter:
            return self._llm_verify_similarity(image1_path, image2_path, character)
        
        return self._simple_similarity_check(image1_path, image2_path)

    def _llm_verify_similarity(
        self,
        image1_path: str,
        image2_path: str,
        character: Dict[str, Any]
    ) -> float:
        """使用LLM验证相似度
        
        Args:
            image1_path: 图像1路径
            image2_path: 图像2路径
            character: 角色字典
            
        Returns:
            相似度分数
        """
        face_description = self.create_face_description(character)
        
        system_prompt = f"""You are an expert at comparing character faces for consistency.
The character should look like: {face_description}

Compare the two images and rate the facial similarity from 0.0 to 1.0.
Respond with only a single number between 0.0 and 1.0."""

        user_prompt = "Compare these two images and rate the facial similarity."

        raise NotImplementedError("LLM验证相似度尚未实现")

    def _simple_similarity_check(
        self,
        image1_path: str,
        image2_path: str
    ) -> float:
        """简单的相似度检查
        
        Args:
            image1_path: 图像1路径
            image2_path: 图像2路径
            
        Returns:
            相似度分数
        """
        from PIL import Image
        import math
        
        try:
            img1 = Image.open(image1_path).convert('RGB')
            img2 = Image.open(image2_path).convert('RGB')
            
            if img1.size != img2.size:
                img2 = img2.resize(img1.size)
            
            img1_data = list(img1.getdata())
            img2_data = list(img2.getdata())
            
            total_diff = 0
            for p1, p2 in zip(img1_data, img2_data):
                diff = sum(abs(a - b) for a, b in zip(p1, p2))
                total_diff += diff / (255 * 3)
            
            avg_diff = total_diff / len(img1_data)
            similarity = 1.0 - (avg_diff / 255)
            
            return max(0.0, min(1.0, similarity))
            
        except Exception:
            return 0.5

    def batch_maintain_consistency(
        self,
        base_image_path: str,
        scenes: List[Dict[str, Any]],
        character: Dict[str, Any],
        face_anchor: Dict[str, Any],
        backend
    ) -> List[Dict[str, Any]]:
        """批量保持面部一致性
        
        Args:
            base_image_path: 基础图像路径
            scenes: 场景列表
            character: 角色字典
            face_anchor: 面部锚点
            backend: 图像后端
            
        Returns:
            生成结果列表
        """
        results = []
        
        for scene in scenes:
            result = self.maintain_face_consistency(
                base_image_path=base_image_path,
                new_scene_prompt=scene.get('prompt', ''),
                character=character,
                face_anchor=face_anchor,
                backend=backend
            )
            results.append({
                'scene_id': scene.get('id', ''),
                'result': result
            })
        
        return results
