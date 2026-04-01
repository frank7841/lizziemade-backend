from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from mangum import Mangum
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import auth, products, orders, custom_orders, shipments, payments, admin
import traceback
import logging
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Run migrations on startup
    logger.info("Running database migrations...")
    try:
        import alembic.config
        import alembic.command
        alembic_cfg = alembic.config.Config("alembic.ini")
        # Run upgrade head synchronously (alembic is sync)
        alembic.command.upgrade(alembic_cfg, "head")
        logger.info("Migrations completed successfully.")
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        # We don't raise here to allow the app to start and show the error via debug endpoints
    yield

app = FastAPI(
    title="LizzieMade API",
    description="""
    ## LizzieMade Crochet Marketplace API
    
    The backend for the LizzieMade marketplace, a platform for artisans to sell high-quality, handmade crochet products.
    
    ### Features:
    * **Auth**: Secure JWT-based authentication
    * **Products**: Management for artisan crochet pieces
    * **Orders**: Product purchase and custom order flows
    * **Payments**: Regional payment processing via Paystack
    * **Shipments**: Comprehensive tracking for handmade goods
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    contact={
        "name": "LizzieMade Technical Team",
        "url": "https://lizziemade.com/tech",
        "email": "dev@lizziemade.com",
    },
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global error: {exc}\n{traceback.format_exc()}")
    return JSONResponse(
        status_code=500,
        content={
            "message": "Internal Server Error",
            "detail": str(exc),
            "traceback": traceback.format_exc() if settings.debug or settings.app_env != "production" else None
        },
    )

# ── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
PREFIX = "/api/v1"
app.include_router(auth.router, prefix=PREFIX)
app.include_router(products.router, prefix=PREFIX)
app.include_router(orders.router, prefix=PREFIX)
app.include_router(custom_orders.router, prefix=PREFIX)
app.include_router(shipments.router, prefix=PREFIX)
app.include_router(payments.router, prefix=PREFIX)
app.include_router(admin.router, prefix=PREFIX)


@app.get("/", tags=["Health"])
async def root():
    return {"status": "ok", "service": settings.app_name, "version": "1.0.0"}


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "healthy"}

@app.get("/debug/db")
async def debug_db():
    from sqlalchemy import text
    from app.database import engine
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            return {"status": "connected", "result": result.scalar()}
    except Exception as e:
        return {"status": "failed", "error": str(e), "traceback": traceback.format_exc()}

# Function Compute HTTP trigger handler
handler = Mangum(app, lifespan="off")
