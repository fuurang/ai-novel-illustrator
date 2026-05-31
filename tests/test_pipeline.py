import pytest
import sys
from pathlib import Path
import tempfile
import json
from unittest.mock import Mock, AsyncMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.pipeline import Pipeline, PipelineContext, StageResult
from src.core.cli_integration import (
    create_pipeline,
    create_pipeline_with_config,
    load_project_context,
    PipelineRunner,
)
from src.models.project import Project, ProjectStatus
from src.models.chapter import Chapter
from src.models.entity import Entity, EntityType
from src.models.world_bible import WorldBible, WorldFramework, VisualAnchoring, ColorPalette
from src.models.prompt import Prompt, PromptParameters
from src.storage.project_store import ProjectStore
from src.api.routers.chapters import next_scene_start_chapter


class TestPipelineContext:
    """PipelineContext 测试"""

    def test_create_context(self):
        """测试创建上下文"""
        project = Project(
            id="test_001",
            novel_title="测试小说",
            input_path="./test.txt",
        )
        context = PipelineContext(project=project)

        assert context.project.id == "test_001"
        assert context.chapters == []
        assert context.entities == []
        assert context.prompts == []
        assert len(context.stage_results) == 0

    def test_context_defaults(self):
        """测试上下文默认值"""
        project = Project(id="test_001")
        context = PipelineContext(project=project)

        assert context.text == ""
        assert context.world_bible is None
        assert len(context.processed_chapters) == 0


class TestStageResult:
    """StageResult 测试"""

    def test_create_result(self):
        """测试创建阶段结果"""
        result = StageResult(
            stage="preprocess",
            success=True,
            data={"chapter_count": 10},
            duration=1.5,
        )

        assert result.stage == "preprocess"
        assert result.success == True
        assert result.data["chapter_count"] == 10
        assert result.duration == 1.5
        assert result.error is None

    def test_result_with_error(self):
        """测试带错误的阶段结果"""
        result = StageResult(
            stage="extract",
            success=False,
            error="LLM调用失败",
            duration=0.5,
        )

        assert result.success == False
        assert result.error == "LLM调用失败"


class TestPipelineCreation:
    """Pipeline 创建测试"""

    def test_create_pipeline_with_config(self):
        """测试使用配置创建 Pipeline"""
        config = {
            "llm": {
                "provider": "deepseek",
                "model": "deepseek-chat",
                "api_key": "test_key",
            },
            "extraction": {
                "max_chapters_parallel": 3,
            },
        }
        pipeline = create_pipeline_with_config(config)

        assert pipeline.config == config
        assert pipeline.project_store is not None

    def test_create_pipeline_with_empty_config(self):
        """测试使用空配置创建 Pipeline"""
        pipeline = create_pipeline_with_config({})

        assert pipeline.config == {}
        assert pipeline.project_store is not None


class TestProjectStore:
    """项目存储测试"""

    def setup_method(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()
        self.store = ProjectStore(base_dir=self.temp_dir)

    def teardown_method(self):
        """清理测试环境"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_create_project(self):
        """测试创建项目"""
        project_id = "test_project_001"
        project_dir = self.store.create_project(
            project_id,
            "测试项目",
            {"test": True}
        )

        assert project_dir.exists()
        assert (project_dir / "data").exists()
        assert (project_dir / "prompts").exists()
        assert (project_dir / "images").exists()

    def test_project_exists(self):
        """测试项目存在检查"""
        project_id = "test_project_002"
        self.store.create_project(project_id, "测试项目")

        assert self.store.project_exists(project_id) == True
        assert self.store.project_exists("nonexistent") == False

    def test_save_and_load_chapters(self):
        """测试保存和加载章节"""
        project_id = "test_project_003"
        self.store.create_project(project_id, "测试项目")

        chapters = [
            {"id": "ch_001", "title": "第一章", "number": 1, "text": "内容1"},
            {"id": "ch_002", "title": "第二章", "number": 2, "text": "内容2"},
        ]
        self.store.save_chapters(project_id, chapters)
        loaded = self.store.load_chapters(project_id)

        assert len(loaded) == 2
        assert loaded[0]["title"] == "第一章"

    def test_save_and_load_entities(self):
        """测试保存和加载实体"""
        project_id = "test_project_004"
        self.store.create_project(project_id, "测试项目")

        entities = [
            {"id": "char_001", "name": "张三", "type": "character"},
            {"id": "scene_001", "name": "神秘森林", "type": "scene"},
        ]
        self.store.save_entities(project_id, entities)
        loaded = self.store.load_entities(project_id)

        assert len(loaded) == 2
        assert loaded[0]["name"] == "张三"

    def test_save_and_load_world_bible(self):
        """测试保存和加载世界观"""
        project_id = "test_project_005"
        self.store.create_project(project_id, "测试项目")

        world_bible = {
            "id": "wb_001",
            "novel_title": "测试小说",
            "world_framework": {
                "genre": "仙侠",
            },
        }
        self.store.save_world_bible(project_id, world_bible)
        loaded = self.store.load_world_bible(project_id)

        assert loaded["novel_title"] == "测试小说"
        assert loaded["world_framework"]["genre"] == "仙侠"

    def test_save_and_load_prompts(self):
        """测试保存和加载提示词"""
        project_id = "test_project_006"
        self.store.create_project(project_id, "测试项目")

        prompts = [
            {
                "id": "prompt_001",
                "entity_id": "char_001",
                "type": "character",
                "chinese_prompt": "测试提示词",
                "parameters": {},
            }
        ]
        self.store.save_prompts(project_id, prompts)
        loaded = self.store.load_prompts(project_id)

        assert len(loaded) == 1
        assert loaded[0]["chinese_prompt"] == "测试提示词"

    def test_list_projects(self):
        """测试列出项目"""
        self.store.create_project("proj_001", "项目1")
        self.store.create_project("proj_002", "项目2")

        projects = self.store.list_projects()

        assert len(projects) == 2

    def test_delete_project(self):
        """测试删除项目"""
        project_id = "test_project_007"
        self.store.create_project(project_id, "测试项目")

        assert self.store.project_exists(project_id) == True
        self.store.delete_project(project_id)
        assert self.store.project_exists(project_id) == False


class TestSceneSegmentationProgress:
    def test_next_scene_start_ignores_quick_groups(self):
        chapters = [{"number": number} for number in range(1, 9)]
        groups = [
            {"source": "quick", "chapters": [1, 2, 3, 4, 5], "chapter_range": "1-5"},
        ]

        assert next_scene_start_chapter(chapters, groups) == 1

    def test_next_scene_start_uses_confirmed_groups(self):
        chapters = [{"number": number} for number in range(1, 9)]
        groups = [
            {"source": "quick", "chapters": [1, 2, 3, 4, 5], "chapter_range": "1-5"},
            {"source": "ai", "chapters": [1, 2], "chapter_range": "1-2"},
            {"source": "manual", "chapters": [3], "chapter_range": "3"},
        ]

        assert next_scene_start_chapter(chapters, groups) == 4


class TestLoadProjectContext:
    """加载项目上下文测试"""

    def setup_method(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()
        self.store = ProjectStore(base_dir=self.temp_dir)

    def teardown_method(self):
        """清理测试环境"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_load_complete_context(self):
        """测试加载完整上下文"""
        project_id = "test_001"
        self.store.create_project(project_id, "测试项目")

        chapters = [{"id": "ch_001", "title": "第一章"}]
        entities = [{"id": "char_001", "name": "张三"}]
        world_bible = {"id": "wb_001", "novel_title": "测试"}
        prompts = [{"id": "prompt_001", "entity_id": "char_001"}]

        self.store.save_chapters(project_id, chapters)
        self.store.save_entities(project_id, entities)
        self.store.save_world_bible(project_id, world_bible)
        self.store.save_prompts(project_id, prompts)

        context = load_project_context(project_id, self.store)

        assert context is not None
        assert len(context['chapters']) == 1
        assert len(context['entities']) == 1
        assert context['world_bible'] is not None
        assert len(context['prompts']) == 1

    def test_load_nonexistent_context(self):
        """测试加载不存在的项目"""
        context = load_project_context("nonexistent", self.store)
        assert context is None


class TestPipelineRunner:
    """PipelineRunner 测试"""

    def test_create_runner(self):
        """测试创建 Runner"""
        runner = PipelineRunner(config={}, output_dir="./test_output")

        assert runner.config == {}
        assert runner.pipeline is not None

    def test_get_project_status_new(self):
        """测试获取新项目状态"""
        runner = PipelineRunner(config={})

        status = runner.get_project_status("nonexistent_project")

        assert status["exists"] == False

    def test_get_project_status_existing(self):
        """测试获取已有项目状态"""
        temp_dir = tempfile.mkdtemp()
        try:
            store = ProjectStore(base_dir=temp_dir)
            project_id = "test_001"
            store.create_project(project_id, "测试项目")

            chapters = [{"id": "ch_001", "title": "第一章"}]
            entities = [{"id": "char_001", "name": "张三", "type": "character"}]
            world_bible = {"id": "wb_001"}
            prompts = [{"id": "prompt_001"}]

            store.save_chapters(project_id, chapters)
            store.save_entities(project_id, entities)
            store.save_world_bible(project_id, world_bible)
            store.save_prompts(project_id, prompts)

            runner = PipelineRunner(config={}, output_dir=temp_dir)
            status = runner.get_project_status(project_id)

            assert status["exists"] == True
            assert status["has_chapters"] == True
            assert status["has_entities"] == True
            assert status["has_world_bible"] == True
            assert status["has_prompts"] == True
            assert status["completion"] == 100

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
