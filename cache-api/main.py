"""
FastAPI Cache API Service
Provides normalized cache lookups for sports betting markets, teams, and players.
Includes Redis caching layer for improved performance.
"""

from fastapi import FastAPI, Query, HTTPException, Body, Security, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
import uvicorn
import os
from dotenv import load_dotenv
from cache_db import get_cache_entry, get_batch_cache_entries, get_precision_batch_cache_entries
from redis_cache import get_cache_stats, clear_all_cache, invalidate_cache
from uuid_tracking import track_uuid_login, get_uuid_login_logs

# Load environment variables
load_dotenv()

# Security configuration
security = HTTPBearer()

# Non-admin key (read-only access to cache endpoints)
NON_ADMIN_KEY = "12345"

# Admin key (full access to all endpoints)
ADMIN_KEY = "eternitylabsadmin"

# All valid tokens (admin + non-admin)
VALID_API_TOKENS = {ADMIN_KEY, NON_ADMIN_KEY}

# Debug: Print loaded tokens
print(f"🔑 Loaded API Tokens:")
print(f"   Admin Key: {ADMIN_KEY}")
print(f"   Non-Admin Key: {NON_ADMIN_KEY}")
print(f"   Valid Tokens Set: {VALID_API_TOKENS}")

def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> str:
    """
    Verify the API token from the Authorization header.
    Allows both admin and non-admin tokens.
    
    Raises:
        HTTPException: If token is invalid or missing
    
    Returns:
        The validated token
    """
    if not VALID_API_TOKENS:
        raise HTTPException(
            status_code=500,
            detail="No API tokens configured. Please set API_TOKEN in environment variables."
        )
    
    token = credentials.credentials
    
    # Debug: Log received token
    print(f"🔍 Received token: '{token}' (length: {len(token)})")
    print(f"🔍 Token in VALID_API_TOKENS: {token in VALID_API_TOKENS}")
    print(f"🔍 Valid tokens: {VALID_API_TOKENS}")
    
    if token not in VALID_API_TOKENS:
        print(f"❌ Token '{token}' not found in valid tokens")
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired API token"
        )
    
    print(f"✅ Token '{token}' validated successfully")
    return token

def verify_admin_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> str:
    """
    Verify the API token is an admin token.
    Restricts access to admin-only endpoints.
    
    Raises:
        HTTPException: If token is invalid, missing, or not an admin token
    
    Returns:
        The validated admin token
    """
    token = credentials.credentials
    if token != ADMIN_KEY:
        raise HTTPException(
            status_code=403,
            detail="Admin access required. This endpoint requires an admin API token."
        )
    
    return token

app = FastAPI(
    title="Cache API",
    description="Sports betting cache normalization service with Redis caching",
    version="2.0.0"
)

# Add CORS middleware to allow cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods (GET, POST, DELETE, etc.)
    allow_headers=["*"],  # Allow all headers
)

# Mount static files (CSS, JS) for the dashboard
dashboard_path = os.path.join(os.path.dirname(__file__), "dashboard")
if os.path.exists(dashboard_path):
    # Mount CSS directory
    css_path = os.path.join(dashboard_path, "css")
    if os.path.exists(css_path):
        app.mount("/css", StaticFiles(directory=css_path), name="css")
    
    # Mount JS directory
    js_path = os.path.join(dashboard_path, "js")
    if os.path.exists(js_path):
        app.mount("/js", StaticFiles(directory=js_path), name="js")
    
    print(f"📁 Dashboard static files mounted from: {dashboard_path}")


# Request models for batch endpoints
class BatchQueryRequest(BaseModel):
    """Request model for batch cache queries"""
    team: Optional[List[str]] = None
    player: Optional[List[str]] = None
    market: Optional[List[str]] = None
    sport: Optional[str] = None  # Sport context for team/league queries
    league: Optional[List[str]] = None

class PrecisionBatchItem(BaseModel):
    """Single precision query item"""
    team: Optional[str] = None
    player: Optional[str] = None
    market: Optional[str] = None
    sport: Optional[str] = None
    league: Optional[str] = None

class PrecisionBatchRequest(BaseModel):
    """Request model for precision batch queries"""
    queries: List[PrecisionBatchItem]

class UUIDLoginRequest(BaseModel):
    """Request model for UUID-based login"""
    uuid: str

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "service": "Cache API",
        "version": "2.0.0",
        "features": ["Redis caching", "SQLite database", "Alias normalization"]
    }

@app.get("/index.html")
async def dashboard():
    """Serve the dashboard HTML interface"""
    dashboard_file = os.path.join(os.path.dirname(__file__), "dashboard", "index.html")
    print(dashboard_file)
    if os.path.exists(dashboard_file):
        return FileResponse(dashboard_file)
    else:
        raise HTTPException(status_code=404, detail="Dashboard not found")

@app.get("/dashboard")
async def dashboard_redirect():
    """Redirect /dashboard to /index.html"""
    dashboard_file = os.path.join(os.path.dirname(__file__), "dashboard", "index.html")
    if os.path.exists(dashboard_file):
        return FileResponse(dashboard_file)
    else:
        raise HTTPException(status_code=404, detail="Dashboard not found")

@app.get("/health")
async def health_check(token: str = Depends(verify_admin_token)):
    """Health check for monitoring (requires admin authentication)"""
    stats = get_cache_stats()
    return {
        "status": "healthy",
        "cache": stats
    }

@app.get("/cache/stats")
async def cache_statistics(token: str = Depends(verify_admin_token)):
    """Get detailed cache statistics (requires admin authentication)"""
    stats = get_cache_stats()
    return JSONResponse(
        status_code=200,
        content=stats
    )

@app.delete("/cache/clear")
async def clear_cache(token: str = Depends(verify_admin_token)):
    """Clear all cache entries (requires admin authentication)"""
    success = clear_all_cache()
    
    if success:
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "All cache entries cleared"
            }
        )
    else:
        raise HTTPException(
            status_code=500,
            detail="Failed to clear cache"
        )

@app.delete("/cache/invalidate")
async def invalidate_specific_cache(
    market: Optional[str] = Query(None),
    team: Optional[str] = Query(None),
    player: Optional[str] = Query(None),
    sport: Optional[str] = Query(None),
    league: Optional[str] = Query(None),
    token: str = Depends(verify_admin_token)
):
    """Invalidate specific cache entry (requires admin authentication)"""
    if not any([market, team, player, league]):
        raise HTTPException(
            status_code=400,
            detail="At least one parameter must be provided"
        )
    
    success = invalidate_cache(market=market, team=team, player=player, sport=sport, league=league)
    
    if success:
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "Cache entry invalidated"
            }
        )
    else:
        return JSONResponse(
            status_code=404,
            content={
                "status": "not_found",
                "message": "Cache entry not found"
            }
        )

@app.get("/cache")
async def get_cache(
    market: Optional[str] = Query(None, description="Market type (e.g., 'moneyline', 'spread', 'total')"),
    team: Optional[str] = Query(None, description="Team name to look up"),
    player: Optional[str] = Query(None, description="Player name to look up"),
    sport: Optional[str] = Query(None, description="Sport name (required when searching by team or league)"),
    league: Optional[str] = Query(None, description="League name to look up"),
    token: str = Depends(verify_token)
) -> JSONResponse:
    """
    Get normalized cache entry for market, team, player, or league (requires authentication).
    
    Parameters:
    - market: Market type to look up
    - team: Team name to normalize
    - player: Player name to normalize
    - sport: Sport name (required when searching by team or league only)
    - league: League name to normalize
    
    Returns:
    - Mapped/normalized entry from cache database
    
    Examples:
    - /cache?team=Lakers&sport=Basketball
    - /cache?league=Premier League&sport=Soccer
    - /cache?player=LeBron James
    - /cache?market=moneyline
    """
    
    # Validate that at least one parameter is provided
    if not any([market, team, player, league]):
        raise HTTPException(
            status_code=400,
            detail="At least one parameter (market, team, player, or league) must be provided"
        )
    
    # Validate that sport is provided when searching by team or league (unless both team and player provided)
    if team and not player and not sport:
        raise HTTPException(
            status_code=400,
            detail="Sport parameter is required when searching by team only"
        )
    
    if league and not sport:
        raise HTTPException(
            status_code=400,
            detail="Sport parameter is required when searching by league"
        )
    
    # Get the cache entry
    try:
        result = get_cache_entry(market=market, team=team, player=player, sport=sport, league=league)
        
        if result is None:
            return JSONResponse(
                status_code=404,
                content={
                    "found": False,
                    "message": "No cache entry found",
                    "query": {
                        "market": market,
                        "team": team,
                        "player": player,
                        "sport": sport,
                        "league": league
                    }
                }
            )
        
        return JSONResponse(
            status_code=200,
            content={
                "found": True,
                "data": result,
                "query": {
                    "market": market,
                    "team": team,
                    "player": player,
                    "sport": sport,
                    "league": league
                }
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving cache entry: {str(e)}"
        )

@app.post("/cache/batch")
async def get_batch_cache(request: BatchQueryRequest = Body(...), token: str = Depends(verify_token)) -> JSONResponse:
    """
    Batch cache query endpoint - independent searches for multiple items per category (requires authentication).
    
    Queries multiple teams, players, markets, and leagues in a single request.
    Each item is searched independently (not combined for precision).
    
    Request body:
    {
        "team": ["Lakers", "Warriors", "Bulls"],
        "player": ["LeBron James", "Stephen Curry"],
        "market": ["moneyline", "spread", "total"],
        "sport": "Basketball",  // Optional: context for team/league searches
        "league": ["NBA", "EuroLeague"]
    }
    
    Response:
    {
        "team": {
            "Lakers": {...},
            "Warriors": {...},
            "Bulls": null  // if not found
        },
        "player": {
            "LeBron James": {...},
            "Stephen Curry": {...}
        },
        "market": {
            "moneyline": {...},
            "spread": {...},
            "total": {...}
        },
        "league": {
            "NBA": {...},
            "EuroLeague": null
        }
    }
    """
    try:
        result = get_batch_cache_entries(
            teams=request.team,
            players=request.player,
            markets=request.market,
            sport=request.sport,
            leagues=request.league
        )
        
        return JSONResponse(
            status_code=200,
            content=result
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing batch query: {str(e)}"
        )

@app.post("/cache/batch/precision")
async def get_precision_batch_cache(request: PrecisionBatchRequest = Body(...), token: str = Depends(verify_token)) -> JSONResponse:
    """
    Precision batch cache query endpoint - combined parameter searches in batch (requires authentication).
    
    Allows multiple precise queries where parameters can be combined for specificity.
    Each query item can have multiple parameters that narrow the search.
    
    Request body:
    {
        "queries": [
            {"team": "Lakers", "player": "LeBron James", "sport": "Basketball"},
            {"team": "Warriors", "sport": "Basketball"},
            {"player": "Messi", "sport": "Soccer"},
            {"market": "moneyline"},
            {"league": "Premier League", "sport": "Soccer"}
        ]
    }
    
    Response:
    {
        "results": [
            {
                "query": {"team": "Lakers", "player": "LeBron James", "sport": "Basketball"},
                "found": true,
                "data": {...}
            },
            {
                "query": {"team": "Warriors", "sport": "Basketball"},
                "found": true,
                "data": {...}
            },
            {
                "query": {"player": "Messi", "sport": "Soccer"},
                "found": true,
                "data": {...}
            },
            {
                "query": {"market": "moneyline"},
                "found": true,
                "data": {...}
            },
            {
                "query": {"league": "Premier League", "sport": "Soccer"},
                "found": false,
                "data": null
            }
        ],
        "total_queries": 5,
        "successful": 4,
        "failed": 1
    }
    """
    try:
        result = get_precision_batch_cache_entries(request.queries)
        
        return JSONResponse(
            status_code=200,
            content=result
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing precision batch query: {str(e)}"
        )


@app.post("/auth/uuid")
async def uuid_login(request: Request, login_data: UUIDLoginRequest = Body(...)):
    """
    UUID-based authentication endpoint.
    Tracks login attempts with UUID and geo-location data.
    
    This endpoint does not require prior authentication - it IS the authentication endpoint.
    All UUID login attempts are tracked with:
    - UUID
    - IP address
    - Geo-location (country, region, city, coordinates)
    - Timestamp
    - User agent
    
    Request body:
    {
        "uuid": "550e8400-e29b-41d4-a716-446655440000"
    }
    
    Response:
    {
        "authenticated": true,
        "message": "Login successful",
        "tracking": {
            "status": "success",
            "record_id": 123,
            "geo_location": {...}
        }
    }
    """
    # Get client IP address with improved proxy support
    client_ip = request.client.host if request.client else "unknown"
    
    # Check multiple headers for real IP (when behind proxy/load balancer/CDN)
    # Priority: X-Real-IP > X-Forwarded-For > CF-Connecting-IP > client.host
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        client_ip = real_ip.strip()
    else:
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # X-Forwarded-For can contain multiple IPs, get the first one (original client)
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            # Check for Cloudflare's connecting IP header
            cf_ip = request.headers.get("CF-Connecting-IP")
            if cf_ip:
                client_ip = cf_ip.strip()
    
    # Get user agent
    user_agent = request.headers.get("User-Agent", "unknown")
    
    # Track the UUID login attempt
    tracking_result = track_uuid_login(
        uuid=login_data.uuid,
        ip_address=client_ip,
        user_agent=user_agent
    )
    
    # For now, all UUID logins are accepted (you can add validation logic here)
    return JSONResponse(
        status_code=200,
        content={
            "authenticated": True,
            "message": "Login successful - UUID authenticated",
            "uuid": login_data.uuid,
            "tracking": tracking_result
        }
    )


@app.get("/admin/uuid-logs")
async def get_uuid_logs(
    uuid: Optional[str] = Query(None, description="Filter by specific UUID"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    token: str = Depends(verify_admin_token)
):
    """
    Admin-only endpoint to retrieve UUID login tracking logs.
    
    Query parameters:
    - uuid: Optional UUID to filter logs
    - limit: Maximum number of records (1-1000, default 100)
    - offset: Number of records to skip (for pagination)
    
    Returns:
    {
        "total": 500,
        "limit": 100,
        "offset": 0,
        "count": 100,
        "logs": [
            {
                "id": 123,
                "uuid": "550e8400-e29b-41d4-a716-446655440000",
                "ip_address": "203.0.113.42",
                "timestamp": "2026-01-20 10:30:15",
                "geo_location": {
                    "country": "United States",
                    "region": "California",
                    "city": "San Francisco",
                    "latitude": 37.7749,
                    "longitude": -122.4194
                },
                "user_agent": "Mozilla/5.0..."
            }
        ]
    }
    """
    logs = get_uuid_login_logs(uuid=uuid, limit=limit, offset=offset)
    
    return JSONResponse(
        status_code=200,
        content=logs
    )


if __name__ == "__main__":
    # Run the server on port 8001
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=False,
        log_level="info"
    )