"""
FastAPI Cache API Service
Provides normalized cache lookups for sports betting markets, teams, and players.
Includes Redis caching layer for improved performance.
"""

from fastapi import FastAPI, Query, HTTPException, Body
from fastapi.responses import JSONResponse
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
import uvicorn
from cache_db import get_cache_entry, get_batch_cache_entries, get_precision_batch_cache_entries
from redis_cache import get_cache_stats, clear_all_cache, invalidate_cache

app = FastAPI(
    title="Cache API",
    description="Sports betting cache normalization service with Redis caching",
    version="2.0.0"
)

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

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "service": "Cache API",
        "version": "2.0.0",
        "features": ["Redis caching", "SQLite database", "Alias normalization"]
    }

@app.get("/health")
async def health_check():
    """Health check for monitoring"""
    stats = get_cache_stats()
    return {
        "status": "healthy",
        "cache": stats
    }

@app.get("/cache/stats")
async def cache_statistics():
    """Get detailed cache statistics"""
    stats = get_cache_stats()
    return JSONResponse(
        status_code=200,
        content=stats
    )

@app.delete("/cache/clear")
async def clear_cache():
    """Clear all cache entries"""
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
    league: Optional[str] = Query(None)
):
    """Invalidate specific cache entry"""
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
    league: Optional[str] = Query(None, description="League name to look up")
) -> JSONResponse:
    """
    Get normalized cache entry for market, team, player, or league.
    
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
async def get_batch_cache(request: BatchQueryRequest = Body(...)) -> JSONResponse:
    """
    Batch cache query endpoint - independent searches for multiple items per category.
    
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
async def get_precision_batch_cache(request: PrecisionBatchRequest = Body(...)) -> JSONResponse:
    """
    Precision batch cache query endpoint - combined parameter searches in batch.
    
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


if __name__ == "__main__":
    # Run the server on port 8001
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=False,
        log_level="info"
    )
