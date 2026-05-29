"""
AI拆书生图 - 生图模块验证脚本

验证所有生图相关模块的导入和基本功能
"""

import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

async def test_imports():
    """测试所有模块能否正确导入"""
    print("=" * 60)
    print("开始验证模块导入...")
    print("=" * 60)
    
    try:
        from src.render.chatgpt2api_backend import ChatGPT2APIBackend
        print("✓ ChatGPT2APIBackend 导入成功")
        
        from src.render.face_consistency import FaceConsistencyChecker
        print("✓ FaceConsistencyChecker 导入成功")
        
        from src.core.face_anchor import FaceAnchorGenerator
        print("✓ FaceAnchorGenerator 导入成功")
        
        from src.core.image_generator import ImageGenerator
        print("✓ ImageGenerator 导入成功")
        
        from src.models import WorldBible, Entity, EntityType, Prompt, Chapter, Project
        print("✓ 数据模型导入成功")
        
        from src.llm import LLMAdapter, PromptLoader
        print("✓ LLM适配器导入成功")
        
        print("\n" + "=" * 60)
        print("所有模块导入验证通过！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ 模块导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

async def test_backend_initialization():
    """测试后端初始化"""
    print("\n" + "=" * 60)
    print("测试 ChatGPT2APIBackend 初始化...")
    print("=" * 60)
    
    try:
        from src.render.chatgpt2api_backend import ChatGPT2APIBackend
        
        config = {
            "base_url": "http://localhost:3000/v1",
            "api_key": "biaooo",
            "model": "gpt-image-2",
        }
        
        backend = ChatGPT2APIBackend(config)
        
        print(f"✓ 后端初始化成功")
        print(f"  - base_url: {backend.base_url}")
        print(f"  - api_key: {backend.api_key}")
        print(f"  - model: {backend.model}")
        
        return True
        
    except Exception as e:
        print(f"\n✗ 后端初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_face_consistency_checker():
    """测试面部一致性检查器"""
    print("\n" + "=" * 60)
    print("测试 FaceConsistencyChecker 初始化...")
    print("=" * 60)
    
    try:
        from src.render.face_consistency import FaceConsistencyChecker
        from src.llm.adapter import LLMAdapter
        
        llm_config = {
            "provider": "deepseek",
            "model": "deepseek-chat",
            "api_key": "test-key",
        }
        llm = LLMAdapter(llm_config)
        
        config = {
            "similarity_threshold": 0.7,
            "max_retries": 3,
        }
        
        checker = FaceConsistencyChecker(llm, config)
        
        print(f"✓ 面部一致性检查器初始化成功")
        print(f"  - 相似度阈值: {checker.similarity_threshold}")
        print(f"  - 最大重试次数: {checker.max_retries}")
        
        return True
        
    except Exception as e:
        print(f"\n✗ 面部一致性检查器初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_image_generator():
    """测试图片生成器"""
    print("\n" + "=" * 60)
    print("测试 ImageGenerator 初始化...")
    print("=" * 60)
    
    try:
        from src.core.image_generator import ImageGenerator
        from src.render.chatgpt2api_backend import ChatGPT2APIBackend
        
        backend_config = {
            "base_url": "http://localhost:3000/v1",
            "api_key": "biaooo",
            "model": "gpt-image-2",
        }
        backend = ChatGPT2APIBackend(backend_config)
        
        config = {
            "default_sizes": {
                "character": "1024x1536",
                "scene": "1536x1024",
                "item": "1024x1024",
                "face_anchor": "1024x1024",
            }
        }
        
        generator = ImageGenerator(backend, config)
        
        print(f"✓ 图片生成器初始化成功")
        print(f"  - 默认角色图尺寸: {generator.default_sizes['character']}")
        print(f"  - 默认场景图尺寸: {generator.default_sizes['scene']}")
        print(f"  - 默认物品图尺寸: {generator.default_sizes['item']}")
        
        return True
        
    except Exception as e:
        print(f"\n✗ 图片生成器初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_data_models():
    """测试数据模型"""
    print("\n" + "=" * 60)
    print("测试数据模型...")
    print("=" * 60)
    
    try:
        from src.models import WorldBible, Entity, EntityType, Prompt, Chapter, Project
        
        from src.models.world_bible import WorldFramework, VisualAnchoring
        wb = WorldBible(
            id="test_001",
            novel_title="测试小说",
            world_framework=WorldFramework(genre="仙侠"),
            visual_anchoring=VisualAnchoring(art_style="古风"),
        )
        print(f"✓ WorldBible 创建成功: {wb.novel_title}")
        
        entity = Entity(
            id="char_001",
            name="林婉儿",
            type=EntityType.CHARACTER,
        )
        print(f"✓ Entity 创建成功: {entity.name} ({entity.type.value})")
        
        prompt = Prompt(
            id="prompt_001",
            entity_id="char_001",
            type="character",
            english_prompt="A beautiful Chinese ancient style woman",
        )
        print(f"✓ Prompt 创建成功: {prompt.type}")
        
        project = Project(
            id="proj_001",
            novel_title="测试项目",
            input_path="test.txt",
        )
        print(f"✓ Project 创建成功: {project.novel_title}")
        
        return True
        
    except Exception as e:
        print(f"\n✗ 数据模型测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """主函数"""
    import sys
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    print("\n")
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 15 + "AI拆书生图 - 模块验证" + " " * 17 + "║")
    print("╚" + "═" * 58 + "╝")
    print()
    
    tests = [
        ("模块导入", test_imports),
        ("后端初始化", test_backend_initialization),
        ("面部一致性检查器", test_face_consistency_checker),
        ("图片生成器", test_image_generator),
        ("数据模型", test_data_models),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = await test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ {name} 测试异常: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 60)
    print("验证结果汇总")
    print("=" * 60)
    
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{name}: {status}")
    
    all_passed = all(result for _, result in results)
    
    print("\n" + "=" * 60)
    if all_passed:
        print("所有验证测试通过！")
    else:
        print("部分测试失败，请检查错误信息。")
    print("=" * 60)
    
    return all_passed

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
