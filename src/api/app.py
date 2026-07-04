from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from src.api.routers import projects, pipeline, entities, world_bible, images, settings, chapters, prompts, ai_workspace, auto_illustration


def create_app() -> FastAPI:
    app = FastAPI(title="AI拆书生图 API", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:8888",
            "http://127.0.0.1:8888",
            "http://localhost:7861",
            "http://127.0.0.1:7861",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(projects.router, prefix="/api/projects", tags=["projects"])
    app.include_router(pipeline.router, prefix="/api/projects", tags=["pipeline"])
    app.include_router(entities.router, prefix="/api/projects", tags=["entities"])
    app.include_router(world_bible.router, prefix="/api/projects", tags=["world_bible"])
    app.include_router(images.router, prefix="/api/projects", tags=["images"])
    app.include_router(chapters.router, prefix="/api/projects", tags=["chapters"])
    app.include_router(ai_workspace.router, prefix="/api/projects", tags=["ai_workspace"])
    app.include_router(auto_illustration.router, prefix="/api/projects", tags=["auto_illustration"])
    app.include_router(settings.router, prefix="/api/settings", tags=["settings"])
    app.include_router(prompts.router, prefix="/api/prompts", tags=["prompts"])

    output_dir = Path("./projects")
    output_dir.mkdir(exist_ok=True)
    app.mount("/output", StaticFiles(directory=str(output_dir)), name="output")
    legacy_output_dir = Path("./output")
    legacy_output_dir.mkdir(exist_ok=True)
    app.mount("/legacy-output", StaticFiles(directory=str(legacy_output_dir)), name="legacy_output")

    @app.get("/api/health")
    async def health_check():
        return {"status": "ok"}

    return app


app = create_app()
