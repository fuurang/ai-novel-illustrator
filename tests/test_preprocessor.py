import pytest
import sys
from pathlib import Path
import tempfile
import os

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.preprocessor import Preprocessor
from src.models.chapter import Chapter


class TestPreprocessor:
    """预处理模块测试"""

    def setup_method(self):
        """设置测试环境"""
        self.config = {
            'extraction': {
                'sliding_window_size': 80000,
                'sliding_window_overlap': 2000
            }
        }
        self.preprocessor = Preprocessor(self.config)

    def test_clean_text(self):
        """测试文本清理"""
        text = "这是    一段   包含多余   空格的文本"
        cleaned = self.preprocessor.clean_text(text)
        assert cleaned.strip() == text.strip()
        assert cleaned.startswith("这是")
        assert cleaned.endswith("文本")

    def test_clean_text_multiple_newlines(self):
        """测试清理多余换行"""
        text = "第一行\n\n\n第二行\n\n\n\n第三行"
        cleaned = self.preprocessor.clean_text(text)
        assert cleaned.count("\n\n\n") == 0

    def test_split_chapters_by_chapter(self):
        """测试章节分割 - 章节格式"""
        text = """第一章 穿越
这是第一章的内容，有些长。

第二章 新世界
这是第二章的内容。

第三章 冒险开始
这是第三章的内容。"""
        chapters = self.preprocessor.split_chapters(text, "test_project")
        assert len(chapters) == 3
        assert "第一章" in chapters[0].title or "穿越" in chapters[0].title

    def test_split_chapters_by_chapter_with_number(self):
        """测试章节分割 - 数字格式"""
        text = """第1章 测试
这是第1章的内容。

第2章 测试2
这是第2章的内容。"""
        chapters = self.preprocessor.split_chapters(text, "test_project")
        assert len(chapters) == 2

    def test_split_chapters_dedupes_repeated_titles(self):
        """测试重复章节标题不会导致编号变成 2/4/6"""
        text = """第一章 太阳消失
第一章 太阳消失()
这是第一章的内容。

第二章 全球恐慌
第二章 全球恐慌()
这是第二章的内容。

第三章 黑暗时代
第三章 黑暗时代()
这是第三章的内容。"""
        chapters = self.preprocessor.split_chapters(text, "test_project")
        assert len(chapters) == 3
        assert [chapter.number for chapter in chapters] == [1, 2, 3]
        assert chapters[0].title == "太阳消失"

    def test_split_chapters_by_chapter_patten_chinese(self):
        """测试章节分割 - 中文章节格式"""
        text = """第一章 穿越异世
主角张三意外穿越到异世界。

第二章 新世界
张三在新世界开始了新生活。

第三章 第一次冒险
他遇到了第一个伙伴。"""
        chapters = self.preprocessor.split_chapters(text, "test_project")
        assert len(chapters) >= 2

    def test_split_chapters_by_window(self):
        """测试滑动窗口分割"""
        text = "这是一段没有章节标记的长文本。" * 1000
        chapters = self.preprocessor.split_chapters(text, "test_project")
        assert len(chapters) >= 1

    def test_read_file(self):
        """测试文件读取"""
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', suffix='.txt', delete=False) as f:
            f.write("测试内容\n第二行")
            temp_path = f.name

        try:
            content = self.preprocessor.read_file(temp_path)
            assert "测试内容" in content
            assert "第二行" in content
        finally:
            os.unlink(temp_path)

    def test_read_file_gbk(self):
        """测试GBK编码文件读取"""
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.txt', delete=False) as f:
            f.write("测试内容\n第二行".encode('gbk'))
            temp_path = f.name

        try:
            content = self.preprocessor.read_file(temp_path)
            assert "测试内容" in content
        finally:
            os.unlink(temp_path)

    def test_split_chapters_empty(self):
        """测试空文本分割"""
        chapters = self.preprocessor.split_chapters("", "test_project")
        assert len(chapters) == 0

    def test_split_chapters_single_chapter(self):
        """测试单章节分割"""
        text = """第一章 唯一章节
这是唯一章节的内容。"""
        chapters = self.preprocessor.split_chapters(text, "test_project")
        assert len(chapters) >= 1


class TestChapterModel:
    """章节模型测试"""

    def test_create_chapter(self):
        """测试创建章节"""
        chapter = Chapter(
            id="ch_001",
            project_id="proj_001",
            number=1,
            title="第一章 测试",
            text="这是测试内容"
        )
        assert chapter.id == "ch_001"
        assert chapter.number == 1
        assert chapter.title == "第一章 测试"
        assert chapter.text == "这是测试内容"

    def test_chapter_defaults(self):
        """测试章节默认值"""
        chapter = Chapter()
        assert chapter.id == ""
        assert chapter.number == 0
        assert chapter.is_processed == False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
