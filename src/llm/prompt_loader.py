from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
import yaml
from jinja2 import Environment, FileSystemLoader, Template


class PromptLoader:
    """提示词模板加载器"""

    def __init__(self, prompts_dir: Optional[str] = None):
        """初始化提示词加载器
        
        Args:
            prompts_dir: 提示词模板目录路径
        """
        if prompts_dir:
            self.prompts_dir = Path(prompts_dir)
        else:
            self.prompts_dir = Path(__file__).parent.parent.parent / 'config' / 'prompts'
        
        self._env = None
        self._templates: Dict[str, Dict[str, Any]] = {}
        
        if self.prompts_dir.exists():
            self._load_templates()

    def _load_templates(self) -> None:
        """加载所有模板文件"""
        if not self.prompts_dir.exists():
            return
        
        for yaml_file in self.prompts_dir.glob('*.yaml'):
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    
                    if data:
                        template_name = yaml_file.stem
                        self._templates[template_name] = data
            except Exception as e:
                print(f"加载模板 {yaml_file} 失败: {e}")

    @property
    def env(self) -> Environment:
        """获取Jinja2环境"""
        if self._env is None:
            self._env = Environment(
                loader=FileSystemLoader(str(self.prompts_dir)),
                trim_blocks=True,
                lstrip_blocks=True,
                keep_trailing_newline=True
            )
        return self._env

    def load(self, template_name: str) -> Dict[str, Any]:
        """加载指定模板
        
        Args:
            template_name: 模板名称
            
        Returns:
            模板字典
        """
        if template_name in self._templates:
            return self._templates[template_name]
        
        yaml_path = self.prompts_dir / f"{template_name}.yaml"
        
        if yaml_path.exists():
            with open(yaml_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                self._templates[template_name] = data
                return data
        
        raise FileNotFoundError(f"找不到模板: {template_name}")

    def get_template(self, template_name: str) -> Dict[str, Any]:
        """获取模板
        
        Args:
            template_name: 模板名称
            
        Returns:
            模板字典
        """
        return self.load(template_name)

    def render(
        self,
        template_name: str,
        context: Dict[str, Any],
        system_key: str = "system",
        user_key: str = "user"
    ) -> Tuple[str, str]:
        """渲染模板
        
        Args:
            template_name: 模板名称
            context: 渲染上下文
            system_key: 系统提示键名
            user_key: 用户提示键名
            
        Returns:
            (system_prompt, user_prompt) 元组
        """
        template = self.load(template_name)
        
        system_prompt = ""
        user_prompt = ""
        
        actual_system_key = system_key if system_key in template else "system_prompt"
        actual_user_key = user_key if user_key in template else "user_prompt"

        if actual_system_key in template:
            system_template = Template(template[actual_system_key])
            system_prompt = system_template.render(**context)

        if actual_user_key in template:
            user_template = Template(template[actual_user_key])
            user_prompt = user_template.render(**context)
        
        return system_prompt, user_prompt

    def render_string(
        self,
        template_str: str,
        context: Dict[str, Any]
    ) -> str:
        """渲染字符串模板
        
        Args:
            template_str: 模板字符串
            context: 渲染上下文
            
        Returns:
            渲染后的字符串
        """
        template = Template(template_str)
        return template.render(**context)

    def list_templates(self) -> List[str]:
        """列出所有可用模板
        
        Returns:
            模板名称列表
        """
        return list(self._templates.keys())

    def add_template(
        self,
        name: str,
        template_data: Dict[str, Any]
    ) -> None:
        """添加自定义模板
        
        Args:
            name: 模板名称
            template_data: 模板数据
        """
        self._templates[name] = template_data

    def save_template(
        self,
        name: str,
        template_data: Dict[str, Any]
    ) -> None:
        """保存模板到文件
        
        Args:
            name: 模板名称
            template_data: 模板数据
        """
        yaml_path = self.prompts_dir / f"{name}.yaml"
        
        yaml_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(yaml_path, 'w', encoding='utf-8') as f:
            yaml.dump(template_data, f, allow_unicode=True, default_flow_style=False)
        
        self._templates[name] = template_data

    def has_template(self, template_name: str) -> bool:
        """检查模板是否存在
        
        Args:
            template_name: 模板名称
            
        Returns:
            是否存在
        """
        if template_name in self._templates:
            return True
        
        yaml_path = self.prompts_dir / f"{template_name}.yaml"
        return yaml_path.exists()
