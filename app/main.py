from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import auth, products, orders, custom_orders, shipments, payments

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
    contact={
        "name": "LizzieMade Technical Team",
        "url": "https://lizziemade.com/tech",
        "email": "dev@lizziemade.com",
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


@app.get("/", tags=["Health"])
async def root():
    return {"status": "ok", "service": settings.app_name, "version": "1.0.0"}


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "healthy"}
