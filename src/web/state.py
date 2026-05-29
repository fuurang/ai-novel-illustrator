"""Web UI全局状态管理"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from pathlib import Path
import yaml


@dataclass
class WebState:
    """Web UI全局状态管理类"""
    
    current_project_id: Optional[str] = None
    current_project: Optional[Dict[str, Any]] = None
    world_bible: Optional[Dict[str, Any]] = None
    entities: List[Dict[str, Any]] = field(default_factory=list)
    prompts: List[Dict[str, Any]] = field(default_factory=list)
    chapters: List[Dict[str, Any]] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)
    
    def load_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """加载配置文件
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            配置字典
        """
        if config_path:
            config_file = Path(config_path)
        else:
            config_file = Path(__file__).parent.parent.parent / 'config' / 'default.yaml'
        
        if not config_file.exists():
            return {}
        
        with open(config_file, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f) or {}
            return self.config
    
    def load_project(self, project_id: str, store) -> bool:
        """从存储加载项目数据
        
        Args:
            project_id: 项目ID
            store: ProjectStore实例
            
        Returns:
            是否加载成功
        """
        try:
            self.current_project_id = project_id
            self.current_project = store.load_project_info(project_id)
            self.chapters = store.load_chapters(project_id)
            
            try:
                self.world_bible = store.load_world_bible(project_id)
            except FileNotFoundError:
                self.world_bible = None
            
            self.entities = store.load_entities(project_id)
            self.prompts = store.load_prompts(project_id)
            
            return True
        except Exception as e:
            print(f"加载项目失败: {e}")
            return False
    
    def get_entities_by_type(self, entity_type: str) -> List[Dict[str, Any]]:
        """获取指定类型的实体列表
        
        Args:
            entity_type: 实体类型 (character/scene/item)
            
        Returns:
            实体列表
        """
        return [e for e in self.entities if e.get('type') == entity_type]
    
    def get_prompts_by_type(self, prompt_type: str) -> List[Dict[str, Any]]:
        """获取指定类型的提示词列表
        
        Args:
            prompt_type: 提示词类型
            
        Returns:
            提示词列表
        """
        return [p for p in self.prompts if p.get('type') == prompt_type]
    
    def get_entity_prompt(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """获取实体的提示词
        
        Args:
            entity_id: 实体ID
            
        Returns:
            提示词字典
        """
        for prompt in self.prompts:
            if prompt.get('entity_id') == entity_id or prompt.get('character_id') == entity_id:
                return prompt
        return None
    
    def get_project_stats(self) -> Dict[str, int]:
        """获取项目统计信息
        
        Returns:
            统计信息字典
        """
        character_count = len(self.get_entities_by_type('character'))
        scene_count = len(self.get_entities_by_type('scene'))
        item_count = len(self.get_entities_by_type('item'))
        
        return {
            'chapter_count': len(self.chapters),
            'entity_count': len(self.entities),
            'character_count': character_count,
            'scene_count': scene_count,
            'item_count': item_count,
            'prompt_count': len(self.prompts),
        }
    
    def clear(self):
        """清空所有状态"""
        self.current_project_id = None
        self.current_project = None
        self.world_bible = None
        self.entities = []
        self.prompts = []
        self.chapters = []
    
    def has_world_bible(self) -> bool:
        """检查是否有世界观圣经"""
        return self.world_bible is not None
    
    def has_entities(self) -> bool:
        """检查是否有实体数据"""
        return len(self.entities) > 0
    
    def has_prompts(self) -> bool:
        """检查是否有提示词"""
        return len(self.prompts) > 0
    
    def get_world_bible_summary(self) -> str:
        """获取世界观概要文本"""
        if not self.world_bible:
            return "暂无世界观数据"
        
        framework = self.world_bible.get('world_framework', {})
        visual = self.world_bible.get('visual_anchoring', {})
        
        summary = f"""**类型**: {framework.get('genre', '未知')} / {framework.get('sub_genre', '未知')}
**时代**: {framework.get('era_setting', '未知')}
**力量体系**: {framework.get('power_system', '未知')}
**艺术风格**: {visual.get('art_style', '未知')}
**色调**: {visual.get('color_palette', {}).get('primary', '未知')}"""
        
        return summary
