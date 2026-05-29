"""
文本预处理器 - 负责文件读取和章节识别
"""
import re
import uuid
from pathlib import Path
from typing import Optional

import chardet

from src.models.chapter import Chapter


CHAPTER_PATTERNS = [
    re.compile(r"^第[一二三四五六七八九十百千万零\d]+[章节回卷集部].*$", re.MULTILINE),
    re.compile(r"^Chapter\s+\d+.*$", re.MULTILINE | re.IGNORECASE),
    re.compile(r"^第\d+章.*$", re.MULTILINE),
    re.compile(r"^\d{1,4}[\.、]\s.*$", re.MULTILINE),
    re.compile(r"^【[^】]+】$", re.MULTILINE),
]


class Preprocessor:
    """
    文本预处理器，用于读取小说文件并识别章节结构
    
    支持的章节格式：
    - 中文：第X章、第X节、第X回、第X卷、第X集、第X部
    - 英文：Chapter X
    - 数字：X. 或 X、开头
    - 括号：【标题】
    """
    
    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}
        self.sliding_window_size = self.config.get("sliding_window_size", 50000)
        self.sliding_window_overlap = self.config.get("sliding_window_overlap", 5000)
    
    def read_file(self, file_path: str) -> str:
        """
        读取文件内容，自动检测编码
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件文本内容
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        raw = path.read_bytes()
        detected = chardet.detect(raw)
        encoding = detected.get("encoding", "utf-8") or "utf-8"
        
        try:
            return raw.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            for fallback in ["utf-8", "gbk", "gb2312", "gb18030"]:
                try:
                    return raw.decode(fallback)
                except (UnicodeDecodeError, LookupError):
                    continue
            return raw.decode("utf-8", errors="replace")
    
    def split_chapters(self, text: str, project_id: str = "") -> list[Chapter]:
        """
        识别章节结构，使用正则优先+滑动窗口兜底
        
        Args:
            text: 小说全文
            project_id: 项目ID
            
        Returns:
            章节列表
        """
        for pattern in CHAPTER_PATTERNS:
            matches = list(pattern.finditer(text))
            if len(matches) >= 2:
                return self._split_by_matches(text, matches, project_id)
        
        return self._split_by_window(text, project_id)
    
    def _split_by_matches(self, text: str, matches: list, project_id: str) -> list[Chapter]:
        """
        基于正则匹配结果切分章节
        
        Args:
            text: 小说全文
            matches: 正则匹配列表
            project_id: 项目ID
            
        Returns:
            章节列表
        """
        chapters = []
        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            title = match.group().strip()
            body = text[start:end].replace(title, "", 1).strip()

            if body.strip():
                chapters.append(Chapter(
                    id=str(uuid.uuid4())[:8],
                    project_id=project_id,
                    number=i + 1,
                    title=title,
                    text=body,
                ))

        return chapters
    
    def split_chapters_with_extra_fields(self, text: str, project_id: str = "") -> list[dict]:
        """
        切分章节，并同时添加额外的字段用于兼容API
        """
        chapters = self.split_chapters(text, project_id)
        result = []
        for ch in chapters:
            ch_dict = ch.model_dump()
            # 添加兼容字段，同时有index和chapter_number，方便前后端使用
            ch_dict["index"] = ch_dict["number"]
            ch_dict["chapter_number"] = ch_dict["number"]
            result.append(ch_dict)
        return result
    
    def _split_by_window(self, text: str, project_id: str) -> list[Chapter]:
        """
        使用滑动窗口切分章节（兜底方案）
        
        Args:
            text: 小说全文
            project_id: 项目ID
            
        Returns:
            章节列表
        """
        chapters = []
        chars = list(text)
        total_len = len(chars)
        
        for i in range(0, total_len, self.sliding_window_size - self.sliding_window_overlap):
            if i >= total_len:
                break
            end = min(i + self.sliding_window_size, total_len)
            chunk = "".join(chars[i:end])
            
            first_line = chunk.split("\n")[0] if "\n" in chunk else chunk[:50]
            title = first_line.strip() if first_line.strip() else f"段落{len(chapters) + 1}"
            
            chapters.append(Chapter(
                id=str(uuid.uuid4())[:8],
                project_id=project_id,
                number=len(chapters) + 1,
                title=title[:100],
                text=chunk,
            ))
            
            if end >= total_len:
                break
        
        return chapters
    
    def clean_text(self, text: str) -> str:
        """
        清洗文本，去除多余空行和特殊字符
        
        Args:
            text: 原始文本
            
        Returns:
            清洗后的文本
        """
        text = re.sub(r"\r\n", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]+\n", "\n", text)
        text = re.sub(r"\n[ \t]+", "\n", text)
        return text.strip()
