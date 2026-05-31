from pathlib import Path


PROJECT_ROOT = Path("./projects")
LEGACY_IMAGE_OUTPUT_ROOT = Path("./output")


def get_project_output_dir(project_id: str) -> Path:
    path = PROJECT_ROOT / project_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_project_images_dir(project_id: str) -> Path:
    path = get_project_output_dir(project_id) / "images"
    path.mkdir(parents=True, exist_ok=True)
    return path


def image_url(project_id: str, image_path: Path) -> str:
    image_path = Path(image_path)
    try:
        relative = image_path.relative_to(get_project_output_dir(project_id))
        return f"/output/{project_id}/{str(relative).replace(chr(92), '/')}"
    except ValueError:
        relative = image_path.relative_to(LEGACY_IMAGE_OUTPUT_ROOT / project_id)
        return f"/legacy-output/{project_id}/{str(relative).replace(chr(92), '/')}"


def candidate_image_paths(project_id: str, *parts: str) -> list[Path]:
    return [
        PROJECT_ROOT / project_id / "images" / Path(*parts),
        LEGACY_IMAGE_OUTPUT_ROOT / project_id / "images" / Path(*parts),
    ]
