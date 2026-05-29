# LLM Prompt 模板库

> 本文档集中管理 AI拆书生图 项目中所有 LLM 调用的 Prompt 模板。
> 每个模板包含：用途说明、输入变量、System Prompt、User Prompt、期望输出格式。

---

## 模板索引

| 编号 | 模板名称 | 阶段 | 使用时机 |
|------|---------|------|---------|
| P01 | 世界观宏观分析 | Stage 0 | 首次分析小说，提取世界观框架 |
| P02 | 视觉锚定生成 | Stage 0 | 基于世界观框架生成视觉规范 |
| P03 | 章节实体发现 | Stage 2 | 逐章提取人物/场景/物品 |
| P04 | 实体消歧判断 | Stage 2 | 判断两个实体是否为同一实体 |
| P05 | 角色属性深度提取 | Stage 2 | 提取角色完整视觉属性 |
| P06 | 场景属性深度提取 | Stage 2 | 提取场景完整视觉属性 |
| P07 | 物品属性深度提取 | Stage 2 | 提取物品完整视觉属性 |
| P08 | 关系图谱提取 | Stage 2 | 提取实体间关系 |
| P09 | 角色提示词生成 | Stage 3 | 生成角色中文+英文生图提示词 |
| P10 | 场景提示词生成 | Stage 3 | 生成场景中文+英文生图提示词 |
| P11 | 物品提示词生成 | Stage 3 | 生成物品中文+英文生图提示词 |
| P12 | 分镜提示词生成 | Stage 3 | 生成关键情节分镜提示词 |
| P13 | 面部锚定图提示词生成 | Stage 4 | 生成面部锚定图专用提示词 |
| P14 | 生图结果验证 | Stage 4 | 验证生成图是否符合预期 |

---

## P01 世界观宏观分析

### 用途

从小说前 N 章中提取世界观框架，为后续所有步骤提供约束基准。

### 输入变量

| 变量 | 类型 | 说明 |
|------|------|------|
| `{novel_title}` | string | 小说标题 |
| `{text_content}` | string | 前 N 章文本 + 目录 + 简介 |

### System Prompt

```
你是一位资深文学评论家和世界观架构师，精通各类小说类型的世界观分析。
你擅长从文本中提炼出小说的核心设定、时代背景、力量体系和社会结构。
你的分析必须客观、准确，严格基于原文内容，不得臆造。
```

### User Prompt

```
请分析以下小说内容，提取其世界观框架。

小说标题：{novel_title}

小说内容：
{text_content}

请按以下 JSON 格式输出分析结果：

```json
{
  "genre": "小说类型（仙侠/都市/玄幻/科幻/历史/悬疑/言情/其他）",
  "sub_genre": "子类型，可多个，用+连接",
  "era_setting": "时代背景描述",
  "technology_level": "科技/技术发展水平描述",
  "power_system": "力量/能力体系描述，无则填'无超自然力量体系'",
  "social_structure": "社会结构描述",
  "geography_overview": "地理环境概览",
  "key_concepts": ["核心概念1", "核心概念2", "核心概念3"],
  "tone_and_mood": "整体基调与氛围"
}
```

要求：
1. 严格基于原文内容分析，不得臆造
2. 如果原文信息不足某项，填写"原文未明确"
3. genre 必须从给定选项中选择最匹配的
4. key_concepts 列出 3-5 个最核心的世界观概念
```

### 期望输出

JSON 格式的世界观框架，对应 WorldBible.world_framework。

---

## P02 视觉锚定生成

### 用途

基于世界观框架，生成统一的视觉规范，包括画风、色彩、光影、材质、氛围、禁止元素等。

### 输入变量

| 变量 | 类型 | 说明 |
|------|------|------|
| `{world_framework}` | JSON | P01 输出的世界观框架 |
| `{novel_title}` | string | 小说标题 |

### System Prompt

```
你是一位资深的AI绘画提示词工程师和视觉艺术总监。
你精通各类绘画风格、色彩理论、光影设计和视觉叙事。
你的任务是为小说建立统一的视觉规范，确保所有后续生成的图片风格一致。
你必须同时提供中文和英文的视觉描述。
```

### User Prompt

```
基于以下小说的世界观框架，为其建立统一的视觉规范。

小说标题：{novel_title}

世界观框架：
{world_framework}

请按以下 JSON 格式输出视觉锚定规范：

```json
{
  "visual_anchoring": {
    "art_style": "中文画风描述",
    "art_style_en": "英文画风描述",
    "color_palette": {
      "primary": "主色调（中文）",
      "secondary": "辅助色（中文）",
      "accent": "点缀色（中文）",
      "mood": "情绪色彩描述",
      "specific_colors": ["具体颜色1", "具体颜色2", "具体颜色3", "具体颜色4", "具体颜色5", "具体颜色6"]
    },
    "lighting_style": "光影风格描述",
    "texture_style": "材质风格描述",
    "atmosphere_keywords": ["氛围关键词1", "氛围关键词2", "氛围关键词3", "氛围关键词4"],
    "atmosphere_keywords_en": ["英文氛围关键词1", "英文氛围关键词2", "英文氛围关键词3", "英文氛围关键词4"],
    "forbidden_elements": ["禁止元素1", "禁止元素2", "禁止元素3", "禁止元素4"]
  },
  "character_visual_rules": {
    "face_style": "角色面部风格描述（中文）",
    "face_style_en": "角色面部风格描述（英文）",
    "body_proportion": "身体比例风格",
    "clothing_system": "服饰体系描述",
    "clothing_materials": "服饰材质",
    "hair_style_rules": "发型规则",
    "accessory_rules": "配饰规则"
  },
  "scene_visual_rules": {
    "architecture_style": "建筑风格描述",
    "landscape_style": "景观风格描述",
    "interior_style": "室内风格描述",
    "weather_patterns": "天气模式描述"
  },
  "item_visual_rules": {
    "weapon_style": "武器风格描述",
    "material_system": "材质体系描述",
    "craftsmanship": "工艺纹饰描述"
  }
}
```

要求：
1. 画风必须与小说类型高度匹配（仙侠→古风，都市→写实，科幻→赛博朋克，等）
2. 色彩体系要具体到可用的颜色名称，不能笼统
3. forbidden_elements 必须列出 4-6 个与该世界观不符的视觉元素
4. 中英文描述必须语义对齐
5. character_visual_rules 中的 face_style 是面部一致性的关键，必须精确
6. 所有描述必须为 AI 绘画可理解的语言
```

### 期望输出

JSON 格式的视觉锚定规范，对应 WorldBible.visual_anchoring + 各 visual_rules。

---

## P03 章节实体发现

### 用途

从单个章节中提取所有出现的人物、场景、物品实体。

### 输入变量

| 叏量 | 类型 | 说明 |
|------|------|------|
| `{chapter_number}` | int | 章节序号 |
| `{chapter_title}` | string | 章节标题 |
| `{chapter_text}` | string | 章节正文 |
| `{world_bible_summary}` | string | WorldBible 摘要（genre + era + forbidden_elements） |
| `{existing_entities}` | string | 已有实体列表（避免重复提取） |

### System Prompt

```
你是一位专业的小说文本分析师，擅长从文学作品中提取人物、场景和物品。
你的提取必须严格基于原文，不得遗漏重要实体，也不得臆造不存在的实体。
所有提取结果必须符合小说的世界观设定。
```

### User Prompt

```
请从以下小说章节中提取所有出现的实体。

【世界观约束】
{world_bible_summary}

【章节信息】
第{chapter_number}章 {chapter_title}

【章节正文】
{chapter_text}

【已有实体（无需重复提取，但如有新描述请补充）】
{existing_entities}

请按以下 JSON 格式输出：

```json
{
  "characters": [
    {
      "name": "角色名称",
      "aliases": ["别名1", "别名2"],
      "brief_description": "首次出现时的简要描述（直接引用原文）",
      "source_quote": "原文引用",
      "confidence": 0.95,
      "is_new": true
    }
  ],
  "scenes": [
    {
      "name": "场景名称",
      "brief_description": "场景的简要视觉描述（直接引用原文）",
      "source_quote": "原文引用",
      "confidence": 0.9,
      "is_new": true
    }
  ],
  "items": [
    {
      "name": "物品名称",
      "category": "武器/服饰/道具/药物/其他",
      "brief_description": "物品的简要视觉描述（直接引用原文）",
      "source_quote": "原文引用",
      "confidence": 0.85,
      "is_new": true
    }
  ]
}
```

要求：
1. 提取所有有名字的实体，也包括仅以代词出现但可推断身份的角色
2. 同一角色在本章可能有多个称呼（如"林婉儿"="婉儿"="林家大小姐"），都列入 aliases
3. brief_description 必须直接引用或紧贴原文，不得自行发挥
4. confidence 为 0-1 的置信度，1.0 表示完全确定
5. is_new 标记该实体是否为新发现（不在已有实体列表中）
6. 如果某已有实体在本章有新的外貌/服饰描述，也请列出并标记 is_new: false
7. 所有描述必须符合世界观约束，不得出现与设定矛盾的内容
```

### 期望输出

JSON 格式的实体列表，包含 characters / scenes / items 三个数组。

---

## P04 实体消歧判断

### 用途

判断两个名称不同的实体是否为同一实体（如"婉儿"和"林家大小姐"）。

### 输入变量

| 变量 | 类型 | 说明 |
|------|------|------|
| `{entity_a}` | JSON | 实体A的信息 |
| `{entity_b}` | JSON | 实体B的信息 |
| `{context_quotes}` | string | 相关上下文原文 |

### System Prompt

```
你是一位小说文本分析专家，擅长通过上下文判断不同称呼是否指向同一角色/场景/物品。
你的判断必须基于原文证据，而非主观推测。
```

### User Prompt

```
请判断以下两个实体是否为同一实体。

【实体A】
{entity_a}

【实体B】
{entity_b}

【相关上下文】
{context_quotes}

请按以下 JSON 格式输出：

```json
{
  "is_same": true/false,
  "confidence": 0.0-1.0,
  "reasoning": "判断理由，引用原文证据",
  "merged_name": "合并后的首选名称（如果 is_same 为 true）",
  "merged_aliases": ["合并后的别名列表"]
}
```

要求：
1. 只有在原文有明确证据时才判断为同一实体
2. confidence 低于 0.6 时建议保留为独立实体，由人工确认
3. merged_name 选择正式名称（全名 > 称号 > 昵称）
```

### 期望输出

JSON 格式的消歧判断结果。

---

## P05 角色属性深度提取

### 用途

基于角色的所有原文引用，提取完整的视觉属性档案。

### 输入变量

| 变量 | 类型 | 说明 |
|------|------|------|
| `{character_name}` | string | 角色名称 |
| `{source_quotes}` | string | 该角色所有相关原文引用 |
| `{world_bible_visual_rules}` | string | WorldBible 中的角色视觉规范 |

### System Prompt

```
你是一位专业的角色视觉设计师，擅长从文学描述中提取角色的完整视觉属性。
你的提取必须严格基于原文引用，将文学描述转化为可用于AI绘画的视觉属性。
所有属性必须符合小说的世界观视觉规范。
面部特征必须单独、精确地描述，因为面部需要在多张图中保持一致。
```

### User Prompt

```
请根据以下原文引用，提取角色「{character_name}」的完整视觉属性。

【世界观视觉规范】
{world_bible_visual_rules}

【原文引用】
{source_quotes}

请按以下 JSON 格式输出：

```json
{
  "name": "{character_name}",
  "attributes": {
    "gender": "性别",
    "age_range": "年龄段描述",
    "appearance": {
      "face": "面部描述（脸型、肤色、眉眼、标志性特征，必须精确）",
      "hair": "发型发色描述",
      "body": "身材体型描述",
      "distinguishing_features": "标志性特征（痣、疤、胎记等，无则填'无特别标志'）"
    },
    "clothing": {
      "default": "默认/最常见的服饰描述",
      "variations": [
        {"context": "换装场景描述", "description": "对应服饰描述"}
      ]
    },
    "personality": "性格气质描述（影响表情和姿态）",
    "abilities": ["能力/技能1", "能力/技能2"],
    "relationships": [
      {"target_name": "关联角色名", "relation": "关系描述"}
    ]
  },
  "missing_info": ["原文未提及但重要的视觉属性1", "原文未提及但重要的视觉属性2"]
}
```

要求：
1. appearance 中的每个字段都必须基于原文，原文未提及的标注"原文未提及"
2. face 字段是面部一致性的关键，必须尽可能精确和完整
3. distinguishing_features 是面部锁定的核心依据，必须逐一列出
4. clothing.variations 记录角色在不同场景的换装
5. missing_info 列出原文未提及但对生图重要的属性（如未描写发色等）
6. 所有描述必须符合世界观视觉规范，不得出现与设定矛盾的内容
7. personality 会影响角色的默认表情和姿态，需要提取
```

### 期望输出

JSON 格式的角色完整属性档案。

---

## P06 场景属性深度提取

### 用途

基于场景的所有原文引用，提取完整的视觉属性档案。

### 输入变量

| 变量 | 类型 | 说明 |
|------|------|------|
| `{scene_name}` | string | 场景名称 |
| `{source_quotes}` | string | 该场景所有相关原文引用 |
| `{world_bible_scene_rules}` | string | WorldBible 中的场景视觉规范 |

### System Prompt

```
你是一位专业的场景概念设计师，擅长从文学描述中提取场景的完整视觉属性。
你的提取必须严格基于原文引用，将文学描述转化为可用于AI绘画的视觉属性。
所有属性必须符合小说的世界观场景视觉规范。
```

### User Prompt

```
请根据以下原文引用，提取场景「{scene_name}」的完整视觉属性。

【世界观场景规范】
{world_bible_scene_rules}

【原文引用】
{source_quotes}

请按以下 JSON 格式输出：

```json
{
  "name": "{scene_name}",
  "attributes": {
    "environment_type": "环境类型（高山/平原/城市/室内/水下/等）",
    "time_of_day": "典型时段",
    "weather": "典型天气",
    "visual_description": "完整视觉描述（200字以内，包含所有视觉要素）",
    "atmosphere": "氛围描述（3-5个关键词）",
    "key_landmarks": ["标志性元素1", "标志性元素2", "标志性元素3"],
    "color_palette": "色彩描述（3-5个具体颜色）"
  },
  "missing_info": ["原文未提及但重要的视觉属性"]
}
```

要求：
1. visual_description 必须完整到可以直接用于生成场景图
2. key_landmarks 是场景的标志性元素，必须出现在每张该场景的图中
3. color_palette 必须与世界观色彩体系协调
4. 所有描述必须符合世界观场景规范
```

### 期望输出

JSON 格式的场景完整属性档案。

---

## P07 物品属性深度提取

### 用途

基于物品的所有原文引用，提取完整的视觉属性档案。

### 输入变量

| 变量 | 类型 | 说明 |
|------|------|------|
| `{item_name}` | string | 物品名称 |
| `{source_quotes}` | string | 该物品所有相关原文引用 |
| `{world_bible_item_rules}` | string | WorldBible 中的物品视觉规范 |

### System Prompt

```
你是一位专业的道具/器物概念设计师，擅长从文学描述中提取物品的完整视觉属性。
你的提取必须严格基于原文引用，将文学描述转化为可用于AI绘画的视觉属性。
所有属性必须符合小说的世界观物品视觉规范。
```

### User Prompt

```
请根据以下原文引用，提取物品「{item_name}」的完整视觉属性。

【世界观物品规范】
{world_bible_item_rules}

【原文引用】
{source_quotes}

请按以下 JSON 格式输出：

```json
{
  "name": "{item_name}",
  "attributes": {
    "category": "武器/服饰/道具/药物/交通工具/其他",
    "visual_description": "完整视觉描述（150字以内，包含所有视觉要素）",
    "material": "材质描述",
    "size": "尺寸描述",
    "special_effects": "特殊视觉效果（光华、纹路等）",
    "owner": "持有者（如有）"
  },
  "missing_info": ["原文未提及但重要的视觉属性"]
}
```

要求：
1. visual_description 必须完整到可以直接用于生成物品设定图
2. special_effects 是灵器/法宝等的关键视觉特征，必须精确描述
3. 所有描述必须符合世界观物品规范
```

### 期望输出

JSON 格式的物品完整属性档案。

---

## P08 关系图谱提取

### 用途

从章节文本中提取实体间的关系。

### 输入变量

| 变量 | 类型 | 说明 |
|------|------|------|
| `{chapter_text}` | string | 章节正文 |
| `{entity_list}` | string | 本章出现的实体列表 |

### System Prompt

```
你是一位小说文本分析专家，擅长从文本中提取人物关系、物品归属和场景关联。
```

### User Prompt

```
请从以下章节中提取实体间的关系。

【章节正文】
{chapter_text}

【本章实体列表】
{entity_list}

请按以下 JSON 格式输出：

```json
{
  "character_relationships": [
    {"source": "角色A", "target": "角色B", "relation": "关系类型（师徒/恋人/敌对/朋友/主从/同门/亲属/其他）", "evidence": "原文证据"}
  ],
  "item_ownership": [
    {"item": "物品名", "owner": "持有者", "evidence": "原文证据"}
  ],
  "character_scene_association": [
    {"character": "角色名", "scene": "场景名", "association": "常驻/途径/居住/修炼/其他"}
  ]
}
```

要求：
1. 每条关系必须有原文证据
2. relation 使用标准化关系类型
3. 只提取明确的关系，不推测
```

### 期望输出

JSON 格式的关系列表。

---

## P09 角色提示词生成

### 用途

基于角色属性档案和 WorldBible，生成中文+英文生图提示词。

### 输入变量

| 变量 | 类型 | 说明 |
|------|------|------|
| `{entity_json}` | JSON | 角色完整属性档案 |
| `{world_bible_visual_anchoring}` | JSON | WorldBible 视觉锚定部分 |
| `{source_quotes}` | string | 原文引用 |

### System Prompt

```
你是一位专业的AI绘画提示词工程师，同时精通中文文学和视觉艺术。
你擅长将文学描述转化为高质量的AI绘画提示词，同时保持对原著的忠实。
你必须同时生成中文和英文版本的提示词。
面部描述必须独立成块，与服饰/姿态解耦，以便于面部一致性控制。
```

### User Prompt

```
请根据以下角色属性档案，生成AI绘画提示词。

【世界观视觉约束】（必须严格遵守）
{world_bible_visual_anchoring}

【角色属性档案】
{entity_json}

【原文引用】
{source_quotes}

请按以下 JSON 格式输出：

```json
{
  "world_prefix_chinese": "中文世界观前缀（从 visual_anchoring 提取，所有提示词共享）",
  "world_prefix_english": "英文世界观前缀",
  "face_block_chinese": "中文面容独立块（仅面部特征，用于面部锁定）",
  "face_block_english": "英文面容独立块",
  "chinese_prompt": "完整中文提示词，按 [世界观][质量][面容][服饰][姿态][氛围][风格][参数] 结构组织",
  "english_prompt": "完整英文提示词，使用 SD/MJ 语法（逗号分隔tag，括号加权）",
  "negative_prompt": "反向提示词（中文+英文混合）",
  "style_tags": ["风格标签1", "风格标签2"],
  "parameters": {
    "aspect_ratio": "3:4",
    "steps": 30,
    "cfg_scale": 7,
    "sampler": "DPM++ 2M Karras"
  }
}
```

要求：
1. 世界观前缀必须包含：画风、色彩体系、氛围关键词、禁止元素
2. 面容独立块必须精确包含：脸型、肤色、眉眼、标志性特征、发色发型
3. 面容独立块末尾标注"（面容锁定：此面容在所有图中保持一致）"
4. 英文面容块使用 (face locked: this face must remain consistent across all images:1.3) 加权
5. 服饰描述必须与属性档案 clothing.default 一致
6. 所有视觉描述必须忠实于原文，不得凭空捏造
7. 禁止出现 WorldBible 中的 forbidden_elements
8. negative_prompt 必须包含 forbidden_elements 的英文翻译
9. parameters 中的 aspect_ratio：角色用 3:4，场景用 16:9，物品用 1:1
```

### 期望输出

JSON 格式的完整提示词，包含中英文版本、面容独立块、反向提示词、生图参数。

---

## P10 场景提示词生成

### 用途

基于场景属性档案和 WorldBible，生成中文+英文生图提示词。

### 输入变量

| 变量 | 类型 | 说明 |
|------|------|------|
| `{entity_json}` | JSON | 场景完整属性档案 |
| `{world_bible_visual_anchoring}` | JSON | WorldBible 视觉锚定部分 |
| `{world_bible_scene_rules}` | JSON | WorldBible 场景视觉规范 |
| `{source_quotes}` | string | 原文引用 |

### System Prompt

```
你是一位专业的AI绘画提示词工程师，专精场景概念图提示词。
你擅长将文学场景描述转化为高质量的场景概念图提示词。
场景图不包含人物，仅展示环境和氛围。
```

### User Prompt

```
请根据以下场景属性档案，生成AI绘画提示词。

【世界观视觉约束】
{world_bible_visual_anchoring}

【场景视觉规范】
{world_bible_scene_rules}

【场景属性档案】
{entity_json}

【原文引用】
{source_quotes}

请按以下 JSON 格式输出：

```json
{
  "world_prefix_chinese": "中文世界观前缀",
  "world_prefix_english": "英文世界观前缀",
  "chinese_prompt": "完整中文提示词，按 [世界观][质量][主体][环境][氛围][色调][风格][参数] 结构组织",
  "english_prompt": "完整英文提示词",
  "negative_prompt": "反向提示词",
  "style_tags": ["风格标签1", "风格标签2"],
  "parameters": {
    "aspect_ratio": "16:9",
    "steps": 30,
    "cfg_scale": 7
  }
}
```

要求：
1. 场景图不包含任何人物，仅展示环境
2. 世界观前缀中的场景部分需替换为场景专属规范
3. 必须包含 key_landmarks 中的所有标志性元素
4. 色调必须与 color_palette 一致
5. 禁止出现 WorldBible 中的 forbidden_elements
```

### 期望输出

JSON 格式的场景提示词。

---

## P11 物品提示词生成

### 用途

基于物品属性档案和 WorldBible，生成中文+英文生图提示词。

### 输入变量

| 变量 | 类型 | 说明 |
|------|------|------|
| `{entity_json}` | JSON | 物品完整属性档案 |
| `{world_bible_visual_anchoring}` | JSON | WorldBible 视觉锚定部分 |
| `{world_bible_item_rules}` | JSON | WorldBible 物品视觉规范 |
| `{source_quotes}` | string | 原文引用 |

### System Prompt

```
你是一位专业的AI绘画提示词工程师，专精道具/器物设定图提示词。
你擅长将文学物品描述转化为高质量的器物设定图提示词。
物品图通常使用暗色背景、聚光照射，突出物品细节。
```

### User Prompt

```
请根据以下物品属性档案，生成AI绘画提示词。

【世界观视觉约束】
{world_bible_visual_anchoring}

【物品视觉规范】
{world_bible_item_rules}

【物品属性档案】
{entity_json}

【原文引用】
{source_quotes}

请按以下 JSON 格式输出：

```json
{
  "world_prefix_chinese": "中文世界观前缀",
  "world_prefix_english": "英文世界观前缀",
  "chinese_prompt": "完整中文提示词，按 [世界观][质量][主体][细节][特效][背景][风格][参数] 结构组织",
  "english_prompt": "完整英文提示词",
  "negative_prompt": "反向提示词",
  "style_tags": ["风格标签1", "风格标签2"],
  "parameters": {
    "aspect_ratio": "1:1",
    "steps": 30,
    "cfg_scale": 7
  }
}
```

要求：
1. 物品图使用暗色背景、聚光照射、微光粒子飘散的展示方式
2. 必须包含 special_effects 中的视觉效果
3. 必须包含 material 的材质质感
4. 禁止出现 WorldBible 中的 forbidden_elements
```

### 期望输出

JSON 格式的物品提示词。

---

## P12 分镜提示词生成

### 用途

基于章节内容和实体档案，生成关键情节的分镜提示词。

### 输入变量

| 变量 | 类型 | 说明 |
|------|------|------|
| `{chapter_text}` | string | 章节正文 |
| `{chapter_number}` | int | 章节序号 |
| `{chapter_title}` | string | 章节标题 |
| `{entity_db_summary}` | string | 本章涉及实体的属性摘要 |
| `{world_bible_visual_anchoring}` | JSON | WorldBible 视觉锚定部分 |

### System Prompt

```
你是一位专业的分镜师和AI绘画提示词工程师。
你擅长从小说情节中选取最具视觉冲击力的关键时刻，并生成对应的分镜提示词。
每个分镜必须包含所有出场角色的面容独立块，确保面部一致性。
```

### User Prompt

```
请从以下章节中选取 3-5 个最具视觉冲击力的关键时刻，生成分镜提示词。

【世界观视觉约束】
{world_bible_visual_anchoring}

【第{chapter_number}章 {chapter_title}】
{chapter_text}

【本章涉及实体】
{entity_db_summary}

请按以下 JSON 格式输出：

```json
{
  "storyboards": [
    {
      "title": "分镜标题",
      "moment_description": "关键时刻描述",
      "source_quote": "原文引用",
      "characters": ["出场角色1", "出场角色2"],
      "scene": "场景名",
      "face_blocks_chinese": {
        "角色1": "面容独立块（中文）",
        "角色2": "面容独立块（中文）"
      },
      "face_blocks_english": {
        "角色1": "面容独立块（英文）",
        "角色2": "面容独立块（英文）"
      },
      "chinese_prompt": "完整中文提示词，按 [世界观][质量][构图][面容-N][角色][动作][场景][表情][氛围][风格][参数] 结构",
      "english_prompt": "完整英文提示词",
      "negative_prompt": "反向提示词",
      "parameters": {
        "aspect_ratio": "16:9",
        "steps": 30,
        "cfg_scale": 7
      }
    }
  ]
}
```

要求：
1. 选取的关键时刻必须有强烈的视觉画面感
2. 每个出场角色必须有面容独立块，标注"面容锁定"
3. 构图描述要具体（中景/特写/远景/俯视/仰视等）
4. 多角色场景中，每个角色的面容独立块分别列出
5. 动作和表情描述要生动具体
6. 禁止出现 WorldBible 中的 forbidden_elements
```

### 期望输出

JSON 格式的分镜提示词列表。

---

## P13 面部锚定图提示词生成

### 用途

生成角色面部锚定图的专用提示词。面部锚定图是面部一致性的基石。

### 输入变量

| 变量 | 类型 | 说明 |
|------|------|------|
| `{character_name}` | string | 角色名称 |
| `{face_block_chinese}` | string | 中文面容独立块 |
| `{face_block_english}` | string | 英文面容独立块 |
| `{world_bible_face_style}` | string | WorldBible 面部风格规范 |

### System Prompt

```
你是一位专业的AI绘画提示词工程师，专精人物面部特写图。
面部锚定图的要求极其严格：正面、中性表情、纯色背景、均匀光照、高细节。
面部锚定图将作为后续所有该角色生图的面部参考，必须精确捕捉所有面部特征。
```

### User Prompt

```
请为角色「{character_name}」生成面部锚定图的提示词。

【世界观面部风格】
{world_bible_face_style}

【面容独立块（中文）】
{face_block_chinese}

【面容独立块（英文）】
{face_block_english}

请按以下 JSON 格式输出：

```json
{
  "chinese_prompt": "中文面部锚定图提示词",
  "english_prompt": "英文面部锚定图提示词",
  "negative_prompt": "反向提示词",
  "parameters": {
    "aspect_ratio": "1:1",
    "steps": 40,
    "cfg_scale": 7.5,
    "denoising_strength": 0.4,
    "sampler": "DPM++ 2M Karras"
  }
}
```

面部锚定图硬性要求：
1. 正面面部特写，头部占画面 60-70%
2. 中性微笑表情，眼神正视镜头
3. 纯色渐变背景（与世界观色调一致）
4. 均匀柔光，无强烈阴影
5. 仅保留面部固有特征（泪痣等），去除可变装饰（耳环等）
6. 发色必须精确，发型为自然披发（最中性）
7. 不包含任何服饰（仅露出颈部以上）
8. 分辨率要求高细节，steps 不低于 40
9. 禁止：侧脸、夸张表情、复杂背景、强阴影、饰品
```

### 期望输出

JSON 格式的面部锚定图专用提示词。

---

## P14 生图结果验证

### 用途

使用多模态 LLM 验证生成的图片是否符合提示词和世界观要求。

### 输入变量

| 变量 | 类型 | 说明 |
|------|------|------|
| `{image}` | image | 生成的图片 |
| `{prompt_used}` | string | 使用的提示词 |
| `{world_bible_summary}` | string | WorldBible 摘要 |
| `{face_anchor_image}` | image | 面部锚定图（角色图验证时使用） |

### System Prompt

```
你是一位专业的AI绘画质量审核员，擅长评估生成图片与提示词的匹配度、
角色面部一致性、以及是否符合世界观视觉规范。
你的评估必须客观、具体、可操作。
```

### User Prompt

```
请评估以下生成的图片。

【使用的提示词】
{prompt_used}

【世界观规范摘要】
{world_bible_summary}

【面部锚定图】（仅角色图验证时提供）
{face_anchor_image}

请按以下 JSON 格式输出评估结果：

```json
{
  "prompt_match_score": 0.0-1.0,
  "face_consistency_score": 0.0-1.0,
  "world_bible_compliance_score": 0.0-1.0,
  "overall_score": 0.0-1.0,
  "passed": true/false,
  "issues": [
    {
      "type": "prompt_mismatch/face_inconsistency/world_violation/quality_issue",
      "description": "问题描述",
      "severity": "critical/major/minor",
      "suggestion": "修复建议"
    }
  ],
  "forbidden_elements_detected": ["检测到的禁止元素"],
  "face_feature_comparison": {
    "face_shape_match": true/false,
    "eye_shape_match": true/false,
    "eyebrow_shape_match": true/false,
    "distinguishing_features_match": true/false,
    "hair_color_match": true/false
  }
}
```

评估标准：
1. prompt_match_score：图片内容与提示词描述的匹配度
2. face_consistency_score：面部特征与锚定图的一致性（仅角色图）
3. world_bible_compliance_score：是否符合世界观视觉规范
4. overall_score < 0.7 或存在 critical 级别问题时 passed 为 false
5. face_feature_comparison 逐项对比面部特征
6. forbidden_elements_detected 列出所有检测到的禁止元素
```

### 期望输出

JSON 格式的评估结果，包含评分、问题列表和修复建议。

---

## 附录：Prompt 迭代记录

| 版本 | 日期 | 修改内容 | 效果 |
|------|------|---------|------|
| v1.0 | 2026-05-29 | 初始版本 | 待验证 |

> 每次修改 Prompt 后，请在此记录修改内容和效果，便于持续优化。
