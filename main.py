"""
Trade Opportunities API
FastAPI service that analyzes market data and provides trade opportunity insights
for specific sectors in India.
"""

import time
import uuid
import logging
from datetime import datetime
from typing import Optional
from collections import defaultdict

from fastapi import FastAPI, HTTPException, Depends, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from auth import verify_token, create_guest_token
from data_collector import DataCollector
from ai_analyzer import AIAnalyzer
from models import TokenResponse, HealthResponse
from config import settings

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("trade_api")

# ── In-memory stores ────────────────────────────────────────────────────────────
sessions: dict[str, dict] = {}          # session_id → metadata
rate_store: dict[str, list] = defaultdict(list)   # token → [timestamps]

# ── Rate-limit helper ───────────────────────────────────────────────────────────
def check_rate_limit(token: str) -> None:
    """Sliding-window rate limiter: max N requests per minute per token."""
    now = time.time()
    window = settings.RATE_LIMIT_WINDOW_SECONDS
    max_req = settings.RATE_LIMIT_MAX_REQUESTS

    # Purge old timestamps
    rate_store[token] = [t for t in rate_store[token] if now - t < window]

    if len(rate_store[token]) >= max_req:
        wait = int(window - (now - rate_store[token][0])) + 1
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Try again in {wait}s.",
            headers={"Retry-After": str(wait)},
        )

    rate_store[token].append(now)

# ── App setup ───────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Trade Opportunities API",
    description="Analyzes market data and returns sector-specific trade opportunity reports for India.",
    version="1.0.0",
    contact={"name": "API Support"},
    license_info={"name": "MIT"},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

data_collector = DataCollector()
ai_analyzer    = AIAnalyzer()

# ── Endpoints ───────────────────────────────────────────────────────────────────

@app.get("/", response_model=HealthResponse, tags=["Health"])
async def root():
    """Health check."""
    return HealthResponse(status="ok", message="Trade Opportunities API is running.")


@app.post("/auth/guest-token", response_model=TokenResponse, tags=["Auth"])
async def get_guest_token(request: Request):
    """
    Issue a short-lived guest JWT.  
    No credentials required — suitable for demo / evaluation use.
    """
    client_ip = request.client.host if request.client else "unknown"
    token, expires_at = create_guest_token(client_ip)
    session_id = str(uuid.uuid4())
    sessions[session_id] = {
        "created_at": datetime.utcnow().isoformat(),
        "client_ip": client_ip,
        "requests": 0,
    }
    logger.info("Guest token issued for IP=%s session=%s", client_ip, session_id)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_at=expires_at,
        session_id=session_id,
    )


@app.get(
    "/analyze/{sector}",
    response_class=PlainTextResponse,
    tags=["Analysis"],
    summary="Analyze trade opportunities for a given sector",
    responses={
        200: {"description": "Markdown report", "content": {"text/plain": {}}},
        400: {"description": "Invalid sector name"},
        401: {"description": "Missing or invalid token"},
        429: {"description": "Rate limit exceeded"},
        502: {"description": "External API error"},
    },
)
async def analyze_sector(
    sector: str,
    authorization: Optional[str] = Header(None),
):
    """
    **Core endpoint** – accepts a sector name and returns a structured Markdown
    market-analysis report with current trade opportunities for India.

    ### Supported sectors (examples)
    `pharmaceuticals`, `technology`, `agriculture`, `textiles`, `automotive`,
    `renewable-energy`, `fintech`, `electronics`, `chemicals`, `food-processing`

    ### Authentication
    Pass your guest token in the `Authorization: Bearer <token>` header.  
    Obtain a token from `POST /auth/guest-token`.
    """
    # ── Auth ────────────────────────────────────────────────────────────────────
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Authorization header missing. Use: Authorization: Bearer <token>",
        )
    token = authorization.split(" ", 1)[1]
    payload = verify_token(token)          # raises 401 on failure

    # ── Rate limit ──────────────────────────────────────────────────────────────
    check_rate_limit(token)

    # ── Input validation ────────────────────────────────────────────────────────
    sector = sector.strip().lower().replace("-", " ")
    if not sector or len(sector) < 2 or len(sector) > 60:
        raise HTTPException(status_code=400, detail="Sector name must be 2–60 characters.")
    if not all(c.isalpha() or c.isspace() for c in sector):
        raise HTTPException(status_code=400, detail="Sector name may only contain letters and spaces.")

    logger.info("Analysis requested | sector=%s | sub=%s", sector, payload.get("sub"))

    # ── Data collection ─────────────────────────────────────────────────────────
    try:
        raw_data = await data_collector.collect(sector)
    except Exception as exc:
        logger.error("Data collection failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"Data collection error: {exc}")

    # ── AI analysis ─────────────────────────────────────────────────────────────
    try:
        report = await ai_analyzer.analyze(sector, raw_data)
    except Exception as exc:
        logger.error("AI analysis failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"AI analysis error: {exc}")

    logger.info("Report generated | sector=%s | length=%d chars", sector, len(report))
    return PlainTextResponse(content=report, media_type="text/plain; charset=utf-8")


@app.get("/session/stats", tags=["Session"], summary="View current session usage stats")
async def session_stats(authorization: Optional[str] = Header(None)):
    """Returns request-count and rate-limit status for the current token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header missing.")
    token = authorization.split(" ", 1)[1]
    verify_token(token)

    now = time.time()
    window = settings.RATE_LIMIT_WINDOW_SECONDS
    recent = [t for t in rate_store.get(token, []) if now - t < window]
    return {
        "requests_in_current_window": len(recent),
        "max_requests_per_window": settings.RATE_LIMIT_MAX_REQUESTS,
        "window_seconds": window,
        "remaining": settings.RATE_LIMIT_MAX_REQUESTS - len(recent),
    }
