"""
画风匹配器 - 根据小说类型和基调匹配相应的绘画风格
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class StylePreset:
    """画风预设数据类"""
    art_style_cn: str
    art_style_en: str
    color_primary: str
    color_secondary: str
    color_accent: str
    lighting: str
    texture: str
    keywords_cn: list[str]
    keywords_en: list[str]
    forbidden: list[str]


class StyleMatcher:
    """
    画风匹配器，根据小说类型和基调匹配合适的绘画风格
    
    预置风格库：
    - 仙侠：古风水墨、工笔重彩
    - 玄幻：奇幻写实、哥特暗黑
    - 都市：现代写实、日系清新
    - 科幻：赛博朋克、蒸汽朋克
    - 历史：古典写实、水墨丹青
    - 言情：小清新、唯美梦幻
    - 悬疑：暗黑悬疑、电影质感
    """
    
    PRESETS: dict[str, StylePreset] = {
        "仙侠": StylePreset(
            art_style_cn="古风水墨",
            art_style_en="Ancient Chinese ink painting style",
            color_primary="青色",
            color_secondary="墨色",
            color_accent="金色",
            lighting="柔光、雾气",
            texture="宣纸、水墨晕染",
            keywords_cn=["飘逸", "空灵", "仙气", "古韵"],
            keywords_en=["ethereal", "elegant", "mystical", "classical"],
            forbidden=["现代建筑", "高科技", "西方奇幻", "写实摄影"],
        ),
        "玄幻": StylePreset(
            art_style_cn="奇幻写实",
            art_style_en="Fantasy realistic style",
            color_primary="紫色",
            color_secondary="深蓝",
            color_accent="金色、银色",
            lighting="戏剧光、魔法光效",
            texture="细腻质感、魔法粒子",
            keywords_cn=["神秘", "宏大", "奇幻", "史诗"],
            keywords_en=["mysterious", "epic", "magical", "fantasy"],
            forbidden=["现代建筑", "日常物品", "写实摄影"],
        ),
        "都市": StylePreset(
            art_style_cn="现代写实",
            art_style_en="Modern realistic photography style",
            color_primary="蓝色",
            color_secondary="灰色",
            color_accent="暖色点缀",
            lighting="自然光、城市灯光",
            texture="高清质感",
            keywords_cn=["都市", "时尚", "生活", "真实"],
            keywords_en=["urban", "modern", "realistic", "fashionable"],
            forbidden=["古风建筑", "魔法效果", "奇幻元素"],
        ),
        "科幻": StylePreset(
            art_style_cn="赛博朋克",
            art_style_en="Cyberpunk style",
            color_primary="霓虹蓝",
            color_secondary="暗紫",
            color_accent="霓虹粉、霓虹绿",
            lighting="霓虹灯、LED",
            texture="金属、光滑表面",
            keywords_cn=["科技", "赛博", "未来", "数字"],
            keywords_en=["cyber", "futuristic", "neon", "digital"],
            forbidden=["古风", "中世纪", "魔法"],
        ),
        "历史": StylePreset(
            art_style_cn="古典写实",
            art_style_en="Classical realistic style",
            color_primary="棕褐",
            color_secondary="暗红",
            color_accent="金色",
            lighting="自然光、烛光",
            texture="油画质感、古典笔触",
            keywords_cn=["古典", "历史", "庄重", "典雅"],
            keywords_en=["classical", "historical", "elegant", "refined"],
            forbidden=["现代元素", "高科技", "奇幻元素"],
        ),
        "言情": StylePreset(
            art_style_cn="小清新",
            art_style_en="Soft pastel illustration style",
            color_primary="粉色",
            color_secondary="浅蓝",
            color_accent="暖黄",
            lighting="柔光、逆光",
            texture="水彩、手绘",
            keywords_cn=["唯美", "浪漫", "清新", "梦幻"],
            keywords_en=["romantic", "soft", "dreamy", "pastel"],
            forbidden=["暗黑", "血腥", "赛博朋克"],
        ),
        "悬疑": StylePreset(
            art_style_cn="暗黑悬疑",
            art_style_en="Dark noir cinematic style",
            color_primary="深灰",
            color_secondary="暗蓝",
            color_accent="红色点缀",
            lighting="明暗对比、阴影",
            texture="电影质感、颗粒感",
            keywords_cn=["悬疑", "紧张", "神秘", "压抑"],
            keywords_en=["noir", "suspenseful", "mysterious", "cinematic"],
            forbidden=["明亮色调", "卡通风格", "可爱元素"],
        ),
        "恐怖": StylePreset(
            art_style_cn="暗黑恐怖",
            art_style_en="Dark horror style",
            color_primary="黑色",
            color_secondary="暗红",
            color_accent="惨白",
            lighting="极端明暗、诡异光源",
            texture="粗糙质感",
            keywords_cn=["恐怖", "诡异", "阴森", "惊悚"],
            keywords_en=["horror", "gloomy", "eerie", "macabre"],
            forbidden=["明亮", "可爱", "卡通"],
        ),
        "武侠": StylePreset(
            art_style_cn="武侠水墨",
            art_style_en="Wuxia ink painting style",
            color_primary="墨色",
            color_secondary="灰白",
            color_accent="血红",
            lighting="自然光、山水光影",
            texture="水墨、宣纸",
            keywords_cn=["武侠", "江湖", "侠义", "飘逸"],
            keywords_en=["wuxia", "martial", "heroic", "fluid"],
            forbidden=["高科技", "西方奇幻", "现代都市"],
        ),
        "游戏": StylePreset(
            art_style_cn="游戏CG",
            art_style_en="Game CG illustration style",
            color_primary="鲜艳多彩",
            color_secondary="暗色背景",
            color_accent="特效色",
            lighting="游戏光效、RPG风格",
            texture="CG渲染质感",
            keywords_cn=["游戏", "CG", "特效", "奇幻"],
            keywords_en=["game art", "CG", "fantasy", "vibrant"],
            forbidden=["照片质感", "过于写实"],
        ),
    }
    
    TONE_MODIFIERS: dict[str, dict] = {
        "轻松": {"add_keywords": ["happy", "bright"], "remove_forbidden": ["dark"]},
        "沉重": {"add_keywords": ["serious", "dramatic"], "add_forbidden": ["bright", "cartoon"]},
        "黑暗": {"add_keywords": ["dark", "gloomy"], "add_forbidden": ["bright", "pastel"]},
        "浪漫": {"add_keywords": ["romantic", "warm"], "add_forbidden": ["horror", "gloomy"]},
        "热血": {"add_keywords": ["dynamic", "energetic"], "add_forbidden": ["calm", "soft"]},
    }
    
    def __init__(self):
        pass
    
    def match(self, genre: str, tone: str = "") -> StylePreset:
        """
        根据小说类型和基调匹配画风预设
        
        Args:
            genre: 小说类型（如"仙侠"、"都市"等）
            tone: 小说基调（如"轻松"、"黑暗"等）
            
        Returns:
            匹配的画风预设
        """
        preset = self.PRESETS.get(genre)
        if not preset:
            preset = self.PRESETS["都市"]
        
        if tone:
            preset = self._apply_tone_modifier(preset, tone)
        
        return preset
    
    def _apply_tone_modifier(self, preset: StylePreset, tone: str) -> StylePreset:
        """
        应用基调修饰符到预设
        
        Args:
            preset: 原始预设
            tone: 基调
            
        Returns:
            修改后的预设
        """
        modifier = self.TONE_MODIFIERS.get(tone)
        if not modifier:
            return preset
        
        new_keywords_en = preset.keywords_en.copy()
        new_keywords_cn = preset.keywords_cn.copy()
        new_forbidden = preset.forbidden.copy()
        
        for kw in modifier.get("add_keywords", []):
            if kw not in new_keywords_en:
                new_keywords_en.append(kw)
        
        for kw in modifier.get("add_forbidden", []):
            if kw not in new_forbidden:
                new_forbidden.append(kw)
        
        return StylePreset(
            art_style_cn=preset.art_style_cn,
            art_style_en=preset.art_style_en,
            color_primary=preset.color_primary,
            color_secondary=preset.color_secondary,
            color_accent=preset.color_accent,
            lighting=preset.lighting,
            texture=preset.texture,
            keywords_cn=new_keywords_cn,
            keywords_en=new_keywords_en,
            forbidden=new_forbidden,
        )
    
    def get_style_keywords(self, genre: str, tone: str = "") -> dict:
        """
        获取风格关键词
        
        Args:
            genre: 小说类型
            tone: 小说基调
            
        Returns:
            包含中英文关键词的字典
        """
        preset = self.match(genre, tone)
        return {
            "chinese": preset.keywords_cn,
            "english": preset.keywords_en,
        }
    
    def get_art_style(self, genre: str, tone: str = "") -> tuple[str, str]:
        """
        获取画风描述
        
        Args:
            genre: 小说类型
            tone: 小说基调
            
        Returns:
            (中文画风, 英文画风) 元组
        """
        preset = self.match(genre, tone)
        return preset.art_style_cn, preset.art_style_en
    
    def get_forbidden_elements(self, genre: str, tone: str = "") -> list[str]:
        """
        获取禁止元素列表
        
        Args:
            genre: 小说类型
            tone: 小说基调
            
        Returns:
            禁止元素列表
        """
        preset = self.match(genre, tone)
        return preset.forbidden
    
    def list_available_genres(self) -> list[str]:
        """
        获取所有可用的类型列表
        
        Returns:
            类型名称列表
        """
        return list(self.PRESETS.keys())
    
    def list_available_tones(self) -> list[str]:
        """
        获取所有可用的基调列表
        
        Returns:
            基调名称列表
        """
        return list(self.TONE_MODIFIERS.keys())
