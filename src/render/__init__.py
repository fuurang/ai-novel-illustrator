"""
AI拆书生图 - 生图模块包
提供基于ChatGPT2API的图片生成功能
"""

from .chatgpt2api_backend import ChatGPT2APIBackend
from .face_consistency import FaceConsistencyChecker

__all__ = ["ChatGPT2APIBackend", "FaceConsistencyChecker"]
