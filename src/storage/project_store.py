from typing import Dict, Any, List, Optional
from pathlib import Path
import json
import shutil
from datetime import datetime


class ProjectStore:
    """项目存储管理器"""

    def __init__(self, base_dir: str = "./projects"):
        """初始化存储管理器
        
        Args:
            base_dir: 项目根目录
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def create_project(
        self,
        project_id: str,
        project_name: str,
        config: Optional[Dict[str, Any]] = None
    ) -> Path:
        """创建项目目录结构
        
        Args:
            project_id: 项目ID
            project_name: 项目名称
            config: 项目配置
            
        Returns:
            项目根目录路径
        """
        project_dir = self.base_dir / project_id
        project_dir.mkdir(parents=True, exist_ok=True)
        
        (project_dir / "data").mkdir(exist_ok=True)
        (project_dir / "output").mkdir(exist_ok=True)
        (project_dir / "prompts").mkdir(exist_ok=True)
        (project_dir / "images").mkdir(exist_ok=True)
        
        project_info = {
            "id": project_id,
            "name": project_name,
            "created_at": datetime.now().isoformat(),
            "config": config or {}
        }
        
        info_file = project_dir / "project.json"
        with open(info_file, 'w', encoding='utf-8') as f:
            json.dump(project_info, f, ensure_ascii=False, indent=2)
        
        return project_dir

    def get_project_dir(self, project_id: str) -> Path:
        """获取项目目录
        
        Args:
            project_id: 项目ID
            
        Returns:
            项目目录路径
        """
        return self.base_dir / project_id

    def project_exists(self, project_id: str) -> bool:
        """检查项目是否存在
        
        Args:
            project_id: 项目ID
            
        Returns:
            是否存在
        """
        return (self.base_dir / project_id).exists()

    def load_project_info(self, project_id: str) -> Dict[str, Any]:
        """加载项目信息
        
        Args:
            project_id: 项目ID
            
        Returns:
            项目信息字典
        """
        info_file = self.base_dir / project_id / "project.json"
        
        if not info_file.exists():
            raise FileNotFoundError(f"项目不存在: {project_id}")
        
        with open(info_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def save_world_bible(
        self,
        project_id: str,
        world_bible: Dict[str, Any]
    ) -> None:
        """保存世界观圣经
        
        Args:
            project_id: 项目ID
            world_bible: 世界观圣经数据
        """
        wb_file = self.base_dir / project_id / "data" / "world_bible.json"
        
        with open(wb_file, 'w', encoding='utf-8') as f:
            json.dump(world_bible, f, ensure_ascii=False, indent=2)

    def load_world_bible(self, project_id: str) -> Dict[str, Any]:
        """加载世界观圣经
        
        Args:
            project_id: 项目ID
            
        Returns:
            世界观圣经数据
        """
        wb_file = self.base_dir / project_id / "data" / "world_bible.json"
        
        if not wb_file.exists():
            raise FileNotFoundError(f"世界观圣经不存在: {project_id}")
        
        with open(wb_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def save_ai_runs(self, project_id: str, runs: List[Dict[str, Any]]) -> None:
        """保存 AI 交互记录"""
        runs_file = self.base_dir / project_id / "data" / "ai_runs.json"
        runs_file.parent.mkdir(parents=True, exist_ok=True)

        with open(runs_file, 'w', encoding='utf-8') as f:
            json.dump(runs, f, ensure_ascii=False, indent=2)

    def load_ai_runs(self, project_id: str) -> List[Dict[str, Any]]:
        """加载 AI 交互记录"""
        runs_file = self.base_dir / project_id / "data" / "ai_runs.json"

        if not runs_file.exists():
            return []

        with open(runs_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def append_ai_run(self, project_id: str, run: Dict[str, Any]) -> Dict[str, Any]:
        """追加一条 AI 交互记录"""
        runs = self.load_ai_runs(project_id)
        runs.insert(0, run)
        self.save_ai_runs(project_id, runs[:200])
        return run

    def save_chapters(
        self,
        project_id: str,
        chapters: List[Dict[str, Any]]
    ) -> None:
        """保存章节
        
        Args:
            project_id: 项目ID
            chapters: 章节列表
        """
        chapters_file = self.base_dir / project_id / "data" / "chapters.json"
        
        with open(chapters_file, 'w', encoding='utf-8') as f:
            json.dump(chapters, f, ensure_ascii=False, indent=2)

    def load_chapters(self, project_id: str) -> List[Dict[str, Any]]:
        """加载章节
        
        Args:
            project_id: 项目ID
            
        Returns:
            章节列表
        """
        chapters_file = self.base_dir / project_id / "data" / "chapters.json"
        
        if not chapters_file.exists():
            return []
        
        with open(chapters_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def save_entities(
        self,
        project_id: str,
        entities: List[Dict[str, Any]]
    ) -> None:
        """保存实体
        
        Args:
            project_id: 项目ID
            entities: 实体列表
        """
        entities_file = self.base_dir / project_id / "data" / "entities.json"
        
        with open(entities_file, 'w', encoding='utf-8') as f:
            json.dump(entities, f, ensure_ascii=False, indent=2)

    def load_entities(self, project_id: str) -> List[Dict[str, Any]]:
        """加载实体
        
        Args:
            project_id: 项目ID
            
        Returns:
            实体列表
        """
        entities_file = self.base_dir / project_id / "data" / "entities.json"
        
        if not entities_file.exists():
            return []
        
        with open(entities_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def save_prompts(
        self,
        project_id: str,
        prompts: List[Dict[str, Any]]
    ) -> None:
        """保存提示词
        
        Args:
            project_id: 项目ID
            prompts: 提示词列表
        """
        prompts_file = self.base_dir / project_id / "prompts" / "prompts.json"
        
        prompts_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(prompts_file, 'w', encoding='utf-8') as f:
            json.dump(prompts, f, ensure_ascii=False, indent=2)

    def load_prompts(self, project_id: str) -> List[Dict[str, Any]]:
        """加载提示词
        
        Args:
            project_id: 项目ID
            
        Returns:
            提示词列表
        """
        prompts_file = self.base_dir / project_id / "prompts" / "prompts.json"
        
        if not prompts_file.exists():
            return []
        
        with open(prompts_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def save_prompts_md(
        self,
        project_id: str,
        prompts: List[Dict[str, Any]],
        output_name: str = "prompts.md"
    ) -> Path:
        """将提示词输出为Markdown格式
        
        Args:
            project_id: 项目ID
            prompts: 提示词列表
            output_name: 输出文件名
            
        Returns:
            输出的Markdown文件路径
        """
        prompts_file = self.base_dir / project_id / "prompts" / output_name
        
        prompts_file.parent.mkdir(parents=True, exist_ok=True)
        
        lines = ["# 图片生成提示词\n"]
        lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        lines.append("---\n\n")
        
        current_type = None
        
        for i, prompt in enumerate(prompts, 1):
            prompt_type = prompt.get('type', 'unknown')
            
            if prompt_type != current_type:
                lines.append(f"\n## {prompt_type.capitalize()} Prompts\n\n")
                current_type = prompt_type
            
            lines.append(f"### {i}. {prompt.get('id', f'prompt_{i}')}\n\n")
            
            if prompt.get('character_id'):
                lines.append(f"**角色ID**: {prompt['character_id']}\n\n")
            if prompt.get('scene_id'):
                lines.append(f"**场景ID**: {prompt['scene_id']}\n\n")
            if prompt.get('chapter_number'):
                lines.append(f"**章节**: 第{prompt['chapter_number']}章\n\n")
            
            lines.append("**Parameters**:\n")
            params = prompt.get('parameters', {})
            lines.append(f"- Style: {params.get('style', 'auto')}\n")
            lines.append(f"- Size: {params.get('width', 1024)}x{params.get('height', 1024)}\n")
            lines.append(f"- Steps: {params.get('steps', 30)}\n")
            lines.append(f"- CFG Scale: {params.get('cfg_scale', 7.0)}\n\n")
            
            lines.append("**Positive Prompt**:\n")
            lines.append(f"```\n{prompt.get('positive_prompt', '')}\n```\n\n")
            
            if prompt.get('negative_prompt'):
                lines.append("**Negative Prompt**:\n")
                lines.append(f"```\n{prompt['negative_prompt']}\n```\n\n")
            
            lines.append("---\n\n")
        
        with open(prompts_file, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        
        return prompts_file

    def save_entity_image(
        self,
        project_id: str,
        entity_id: str,
        image_data: bytes,
        filename: str
    ) -> Path:
        """保存实体图像
        
        Args:
            project_id: 项目ID
            entity_id: 实体ID
            image_data: 图像数据
            filename: 文件名
            
        Returns:
            保存的文件路径
        """
        entity_images_dir = self.base_dir / project_id / "images" / "entities" / entity_id
        entity_images_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = entity_images_dir / filename
        
        with open(file_path, 'wb') as f:
            f.write(image_data)
        
        return file_path

    def list_projects(self) -> List[Dict[str, Any]]:
        """列出所有项目
        
        Returns:
            项目信息列表
        """
        projects = []
        
        for project_dir in self.base_dir.iterdir():
            if project_dir.is_dir():
                info_file = project_dir / "project.json"
                if info_file.exists():
                    with open(info_file, 'r', encoding='utf-8') as f:
                        projects.append(json.load(f))
        
        return sorted(projects, key=lambda x: x.get('created_at', ''), reverse=True)

    def delete_project(self, project_id: str) -> None:
        """删除项目
        
        Args:
            project_id: 项目ID
        """
        project_dir = self.base_dir / project_id
        
        if project_dir.exists():
            shutil.rmtree(project_dir)

    def export_project(
        self,
        project_id: str,
        export_path: str
    ) -> Path:
        """导出项目
        
        Args:
            project_id: 项目ID
            export_path: 导出路径
            
        Returns:
            导出文件路径
        """
        import zipfile
        
        project_dir = self.base_dir / project_id
        zip_path = Path(export_path)
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in project_dir.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to(project_dir)
                    zipf.write(file_path, arcname)
        
        return zip_path

    def import_project(self, zip_path: str) -> str:
        """导入项目
        
        Args:
            zip_path: ZIP文件路径
            
        Returns:
            导入的项目ID
        """
        import zipfile
        
        zip_path = Path(zip_path)
        
        with zipfile.ZipFile(zip_path, 'r') as zipf:
            zipf.extractall(self.base_dir)
        
        info_file = self.base_dir / "project.json"
        if info_file.exists():
            with open(info_file, 'r', encoding='utf-8') as f:
                info = json.load(f)
                return info['id']
        
        return zip_path.stem
