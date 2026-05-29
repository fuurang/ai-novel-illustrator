"""
实体合并器 - 负责实体消歧、归一和合并
"""
import uuid
from difflib import SequenceMatcher
from typing import Optional

from src.models.entity import Entity, EntityType, SourceQuote


class EntityMerger:
    """
    实体合并器，负责实体消歧与归一
    
    核心功能：
    1. 名称精确匹配：检查候选实体是否与已有实体名称/别名相同
    2. 相似度匹配：使用 difflib.SequenceMatcher 计算名称相似度
    3. 实体合并：将匹配的候选合并到已有实体，更新别名和原文引用
    4. 新增实体：对于无法匹配的候选，创建新的实体对象
    """
    
    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}
        self.similarity_threshold = self.config.get("dedup_similarity_threshold", 0.85)
        self.min_alias_similarity = self.config.get("min_alias_similarity", 0.8)
    
    def merge(
        self,
        candidates: list[dict],
        existing: list[Entity],
        project_id: str = "",
    ) -> list[Entity]:
        """
        合并候选实体到已有实体列表
        
        Args:
            candidates: 实体候选列表
            existing: 已有的实体列表
            project_id: 项目ID
            
        Returns:
            合并后的实体列表
        """
        result = list(existing)
        
        for candidate in candidates:
            matched = self._find_match(candidate, result)
            
            if matched:
                self._merge_into(matched, candidate)
            else:
                entity = self._to_entity(candidate, project_id)
                if entity.name:
                    result.append(entity)
        
        return result
    
    def _find_match(self, candidate: dict, entities: list[Entity]) -> Optional[Entity]:
        """
        查找与候选实体匹配的已有实体
        
        Args:
            candidate: 候选实体字典
            entities: 已有实体列表
            
        Returns:
            匹配的实体对象，如果没有匹配则返回 None
        """
        cand_name = candidate.get("name", "").strip()
        cand_aliases = candidate.get("aliases", [])
        cand_type = candidate.get("type", "")
        
        if not cand_name:
            return None
        
        for entity in entities:
            if entity.type.value != cand_type:
                continue
            
            all_names = [entity.name] + entity.aliases
            all_cand_names = [cand_name] + cand_aliases
            
            for n1 in all_names:
                for n2 in all_cand_names:
                    if not n1 or not n2:
                        continue
                    
                    if n1 == n2:
                        return entity
                    
                    if self._similarity(n1, n2) >= self.similarity_threshold:
                        return entity
        
        return None
    
    def _merge_into(self, entity: Entity, candidate: dict):
        """
        将候选实体的信息合并到已有实体
        
        Args:
            entity: 目标实体（会被直接修改）
            candidate: 候选实体字典
        """
        new_aliases = [
            a for a in candidate.get("aliases", [])
            if a not in entity.aliases and a != entity.name and a.strip()
        ]
        entity.aliases.extend(new_aliases)
        
        source_quote = candidate.get("source_quote", "").strip()
        if source_quote:
            existing_quotes = [sq.text for sq in entity.source_quotes]
            if source_quote not in existing_quotes:
                chapter = candidate.get("chapter", 0)
                location = candidate.get("location", f"第{chapter}章")
                
                entity.source_quotes.append(SourceQuote(
                    chapter=chapter,
                    text=source_quote,
                    location=location,
                ))
        
        if entity.first_appearance_chapter is None:
            entity.first_appearance_chapter = candidate.get("chapter", 0)
        else:
            new_chapter = candidate.get("chapter", 0)
            if new_chapter and new_chapter < entity.first_appearance_chapter:
                entity.first_appearance_chapter = new_chapter
    
    def _to_entity(self, candidate: dict, project_id: str) -> Entity:
        """
        将候选字典转换为 Entity 对象
        
        Args:
            candidate: 候选实体字典
            project_id: 项目ID
            
        Returns:
            新的 Entity 对象
        """
        name = candidate.get("name", "").strip()
        if not name:
            return Entity()
        
        entity_type = EntityType.CHARACTER
        type_str = candidate.get("type", "character")
        try:
            entity_type = EntityType(type_str)
        except ValueError:
            pass
        
        source_quote = candidate.get("source_quote", "").strip()
        source_quotes = []
        if source_quote:
            chapter = candidate.get("chapter", 0)
            location = candidate.get("location", f"第{chapter}章")
            source_quotes.append(SourceQuote(
                chapter=chapter,
                text=source_quote,
                location=location,
            ))
        
        return Entity(
            id=f"{type_str}_{str(uuid.uuid4())[:8]}",
            project_id=project_id,
            name=name,
            aliases=[a for a in candidate.get("aliases", []) if a.strip() and a != name],
            type=entity_type,
            source_quotes=source_quotes,
            first_appearance_chapter=candidate.get("chapter", 0),
        )
    
    def _similarity(self, a: str, b: str) -> float:
        """
        计算两个字符串的相似度
        
        Args:
            a: 字符串A
            b: 字符串B
            
        Returns:
            相似度分数（0-1）
        """
        return SequenceMatcher(None, a, b).ratio()
    
    def find_duplicates(self, entities: list[Entity]) -> list[tuple[Entity, Entity]]:
        """
        查找潜在的重复实体对（用于人工确认）
        
        Args:
            entities: 实体列表
            
        Returns:
            疑似重复的实体对列表
        """
        duplicates = []
        
        for i, e1 in enumerate(entities):
            for e2 in entities[i + 1:]:
                if e1.type != e2.type:
                    continue
                
                all_names = [e1.name] + e1.aliases
                all_other = [e2.name] + e2.aliases
                
                for n1 in all_names:
                    for n2 in all_other:
                        sim = self._similarity(n1, n2)
                        if 0.6 <= sim < self.similarity_threshold:
                            duplicates.append((e1, e2))
                            break
        
        return duplicates
