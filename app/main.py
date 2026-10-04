import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings
from app.db import Base, get_engine, get_sessionmaker
from app.pipeline import seed_rules
from app.routers import dashboard, dev, health, items, rules
from app.scheduler import build_scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    if settings.auth_disabled and not settings.debug:
        raise RuntimeError("auth_disabled requires debug=true — refusing to start unauthenticated")

    # Alembic owns the schema in production; create_all keeps first-run local setup simple.
    if settings.debug:
        async with get_engine().begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async with get_sessionmaker()() as session:
        seeded = await seed_rules(session)
        if seeded:
            logger.info("seeded %s default rules", seeded)

    scheduler = build_scheduler(settings)
    scheduler.start()
    logger.info("scheduler started")
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)


app = FastAPI(
    title="heads-up",
    description="Ingests assignments and mail, scores what matters, pushes notifications.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(items.router)
app.include_router(rules.router)
app.include_router(dashboard.router)
app.include_router(dev.router)
