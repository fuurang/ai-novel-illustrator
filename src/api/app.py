from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from src.api.routers import projects, pipeline, entities, world_bible, images, settings, chapters, prompts


def create_app() -> FastAPI:
    app = FastAPI(title="AI拆书生图 API", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:8888"],
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
    app.include_router(settings.router, prefix="/api/settings", tags=["settings"])
    app.include_router(prompts.router, prefix="/api/prompts", tags=["prompts"])

    output_dir = Path("./output")
    output_dir.mkdir(exist_ok=True)
    app.mount("/output", StaticFiles(directory=str(output_dir)), name="output")

    @app.get("/api/health")
    async def health_check():
        return {"status": "ok"}

    return app


app = create_app()
