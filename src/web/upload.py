"""
文件上传处理模块

提供Web UI文件上传的支持功能，包括：
- 临时文件管理
- 文件类型验证
- 编码处理
"""
import tempfile
import shutil
import hashlib
import time
from pathlib import Path
from typing import Optional, List, Tuple
import os


SUPPORTED_EXTENSIONS = {
    '.txt', '.md', '.html', '.htm',
    '.epub', '.pdf', '.docx',
}


class FileUploadHandler:
    """
    文件上传处理器
    
    负责处理Web框架（如Gradio）上传的文件，提供：
    - 临时文件存储
    - 文件验证
    - 自动清理
    """
    
    def __init__(self, temp_dir: Optional[str] = None):
        """
        初始化文件上传处理器
        
        Args:
            temp_dir: 临时目录路径（可选，默认使用系统临时目录）
        """
        self.temp_dir = Path(temp_dir) if temp_dir else Path(tempfile.gettempdir())
        self.upload_dir = self.temp_dir / "ai_book_upload"
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        
        self._uploaded_files: List[Path] = []
    
    def handle_upload(self, file_obj) -> Optional[str]:
        """
        处理上传的文件
        
        Args:
            file_obj: Gradio上传的文件对象
        
        Returns:
            str: 临时文件路径，失败返回None
        """
        if file_obj is None:
            return None
        
        try:
            if hasattr(file_obj, 'name'):
                src = Path(file_obj.name)
            elif hasattr(file_obj, 'path'):
                src = Path(file_obj.path)
            else:
                src = Path(str(file_obj))
            
            if not src.exists():
                return None
            
            extension = src.suffix.lower()
            if extension not in SUPPORTED_EXTENSIONS and not extension:
                return None
            
            unique_name = self._generate_unique_name(src)
            dst = self.upload_dir / unique_name
            
            shutil.copy(src, dst)
            self._uploaded_files.append(dst)
            
            return str(dst)
            
        except Exception as e:
            print(f"文件上传处理失败: {e}")
            return None
    
    def handle_multiple_uploads(self, file_objs) -> List[str]:
        """
        处理多个上传的文件
        
        Args:
            file_objs: 文件对象列表
        
        Returns:
            List[str]: 成功上传的文件路径列表
        """
        if not file_objs:
            return []
        
        result = []
        for file_obj in file_objs:
            path = self.handle_upload(file_obj)
            if path:
                result.append(path)
        
        return result
    
    def validate_file(self, file_path: str) -> Tuple[bool, str]:
        """
        验证文件
        
        Args:
            file_path: 文件路径
        
        Returns:
            Tuple[bool, str]: (是否有效, 错误消息)
        """
        path = Path(file_path)
        
        if not path.exists():
            return False, "文件不存在"
        
        if not path.is_file():
            return False, "不是有效的文件"
        
        if path.stat().st_size == 0:
            return False, "文件为空"
        
        extension = path.suffix.lower()
        if extension not in SUPPORTED_EXTENSIONS:
            return False, f"不支持的文件类型: {extension}"
        
        max_size = 100 * 1024 * 1024
        if path.stat().st_size > max_size:
            return False, f"文件过大，最大支持 {max_size // (1024*1024)}MB"
        
        return True, ""
    
    def _generate_unique_name(self, src: Path) -> str:
        """
        生成唯一文件名
        
        Args:
            src: 源文件路径
        
        Returns:
            str: 唯一文件名
        """
        timestamp = int(time.time() * 1000)
        hash_value = hashlib.md5(f"{src.name}_{timestamp}".encode()).hexdigest()[:8]
        return f"{src.stem}_{timestamp}_{hash_value}{src.suffix}"
    
    def cleanup_uploaded_files(self):
        """
        清理已上传的临时文件
        """
        for file_path in self._uploaded_files:
            try:
                if file_path.exists():
                    file_path.unlink()
            except Exception as e:
                print(f"清理文件失败 {file_path}: {e}")
        
        self._uploaded_files.clear()
    
    def get_upload_dir(self) -> str:
        """
        获取上传目录路径
        
        Returns:
            str: 上传目录路径
        """
        return str(self.upload_dir)
    
    def list_uploaded_files(self) -> List[Dict[str, str]]:
        """
        列出已上传的文件
        
        Returns:
            List[Dict[str, str]]: 文件信息列表
        """
        files = []
        for file_path in self.upload_dir.iterdir():
            if file_path.is_file():
                stat = file_path.stat()
                files.append({
                    "name": file_path.name,
                    "path": str(file_path),
                    "size": stat.st_size,
                    "modified": stat.st_mtime,
                })
        return files
    
    def delete_file(self, file_path: str) -> bool:
        """
        删除指定的文件
        
        Args:
            file_path: 文件路径
        
        Returns:
            bool: 是否删除成功
        """
        try:
            path = Path(file_path)
            if path.exists():
                path.unlink()
                if path in self._uploaded_files:
                    self._uploaded_files.remove(path)
                return True
            return False
        except Exception as e:
            print(f"删除文件失败: {e}")
            return False


def handle_file_upload(file_obj) -> Optional[str]:
    """
    处理上传的文件，返回临时文件路径（便捷函数）
    
    Args:
        file_obj: Gradio上传的文件对象
    
    Returns:
        str: 临时文件路径，失败返回None
    """
    handler = FileUploadHandler()
    return handler.handle_upload(file_obj)


def handle_multiple_file_uploads(file_objs) -> List[str]:
    """
    处理多个上传的文件（便捷函数）
    
    Args:
        file_objs: 文件对象列表
    
    Returns:
        List[str]: 成功上传的文件路径列表
    """
    handler = FileUploadHandler()
    return handler.handle_multiple_uploads(file_objs)


def validate_uploaded_file(file_path: str) -> Tuple[bool, str]:
    """
    验证上传的文件（便捷函数）
    
    Args:
        file_path: 文件路径
    
    Returns:
        Tuple[bool, str]: (是否有效, 错误消息)
    """
    handler = FileUploadHandler()
    return handler.validate_file(file_path)


def cleanup_temp_files():
    """
    清理临时上传目录（便捷函数）
    """
    handler = FileUploadHandler()
    handler.cleanup_uploaded_files()


def read_file_content(file_path: str, encoding: str = 'utf-8') -> Optional[str]:
    """
    读取文件内容
    
    Args:
        file_path: 文件路径
        encoding: 文件编码（默认utf-8）
    
    Returns:
        str: 文件内容，失败返回None
    """
    path = Path(file_path)
    
    if not path.exists():
        return None
    
    try:
        with open(path, 'r', encoding=encoding) as f:
            return f.read()
    except UnicodeDecodeError:
        try:
            with open(path, 'r', encoding='gbk') as f:
                return f.read()
        except Exception:
            return None
    except Exception:
        return None


def get_file_info(file_path: str) -> Optional[dict]:
    """
    获取文件信息
    
    Args:
        file_path: 文件路径
    
    Returns:
        dict: 文件信息字典
    """
    path = Path(file_path)
    
    if not path.exists():
        return None
    
    stat = path.stat()
    
    return {
        "name": path.name,
        "path": str(path.absolute()),
        "size": stat.st_size,
        "size_mb": round(stat.st_size / (1024 * 1024), 2),
        "modified": stat.st_mtime,
        "extension": path.suffix,
        "is_text": path.suffix.lower() in {'.txt', '.md', '.html', '.htm'},
    }


def create_temp_copy(file_path: str, project_id: str) -> Optional[str]:
    """
    为项目创建临时文件副本
    
    Args:
        file_path: 原始文件路径
        project_id: 项目ID
    
    Returns:
        str: 临时副本路径
    """
    src = Path(file_path)
    
    if not src.exists():
        return None
    
    temp_dir = Path(tempfile.gettempdir()) / "ai_book_projects" / project_id
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    dst = temp_dir / src.name
    
    try:
        shutil.copy(src, dst)
        return str(dst)
    except Exception as e:
        print(f"创建临时副本失败: {e}")
        return None
