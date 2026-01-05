"""
Redis Cache Module
Provides Redis caching layer for database queries.
"""

import redis
import json
import os
from typing import Optional, Dict, Any
import hashlib

# Redis connection settings
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_DB = int(os.getenv('REDIS_DB', 0))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', None)

# Cache TTL (Time To Live) in seconds - default 1 hour
CACHE_TTL = int(os.getenv('CACHE_TTL', 3600))

# Redis client instance
redis_client = None


def get_redis_client():
    """Get or create Redis client connection"""
    global redis_client
    
    if redis_client is None:
        try:
            redis_client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=REDIS_DB,
                password=REDIS_PASSWORD,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # Test connection
            redis_client.ping()
            print(f"✓ Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
        except redis.ConnectionError as e:
            print(f"✗ Redis connection failed: {e}")
            print("  Cache will be disabled, falling back to direct DB queries")
            redis_client = None
        except Exception as e:
            print(f"✗ Redis error: {e}")
            redis_client = None
    
    return redis_client


def generate_cache_key(market: Optional[str] = None, 
                       team: Optional[str] = None,
                       player: Optional[str] = None,
                       sport: Optional[str] = None,
                       league: Optional[str] = None) -> str:
    """
    Generate a unique cache key based on query parameters.
    
    Args:
        market: Market type
        team: Team name
        player: Player name
        sport: Sport name
        league: League name
    
    Returns:
        Unique cache key string
    """
    # Create a sorted dictionary of non-None parameters
    params = {}
    if market:
        params['market'] = market.lower().strip()
    if team:
        params['team'] = team.lower().strip()
    if player:
        params['player'] = player.lower().strip()
    if sport:
        params['sport'] = sport.lower().strip()
    if league:
        params['league'] = league.lower().strip()
    
    # Sort keys for consistency
    sorted_params = json.dumps(params, sort_keys=True)
    
    # Generate hash for cleaner keys
    key_hash = hashlib.md5(sorted_params.encode()).hexdigest()[:16]
    
    # Create human-readable prefix
    if market:
        prefix = f"market:{params.get('market', '')}"
    elif league:
        prefix = f"league:{params.get('league', '')}:{params.get('sport', '')}"
    elif team and player:
        prefix = f"team_player:{params.get('team', '')}:{params.get('player', '')}"
    elif team:
        prefix = f"team:{params.get('team', '')}:{params.get('sport', '')}"
    elif player:
        prefix = f"player:{params.get('player', '')}"
    else:
        prefix = "query"
    
    return f"cache:{prefix}:{key_hash}"


def get_cached_data(market: Optional[str] = None,
                    team: Optional[str] = None,
                    player: Optional[str] = None,
                    sport: Optional[str] = None,
                    league: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Retrieve cached data from Redis.
    
    Args:
        market: Market type
        team: Team name
        player: Player name
        sport: Sport name
        league: League name
    
    Returns:
        Cached data dictionary or None if not found or cache unavailable
    """
    client = get_redis_client()
    
    if client is None:
        return None
    
    try:
        cache_key = generate_cache_key(market, team, player, sport, league)
        cached_value = client.get(cache_key)
        
        if cached_value:
            print(f"✓ Cache HIT: {cache_key}")
            return json.loads(cached_value)
        else:
            print(f"✗ Cache MISS: {cache_key}")
            return None
            
    except Exception as e:
        print(f"Redis get error: {e}")
        return None


def set_cached_data(data: Dict[str, Any],
                    market: Optional[str] = None,
                    team: Optional[str] = None,
                    player: Optional[str] = None,
                    sport: Optional[str] = None,
                    league: Optional[str] = None,
                    ttl: Optional[int] = None) -> bool:
    """
    Store data in Redis cache.
    
    Args:
        data: Data to cache
        market: Market type
        team: Team name
        player: Player name
        sport: Sport name
        league: League name
        ttl: Time to live in seconds (default: CACHE_TTL)
    
    Returns:
        True if cached successfully, False otherwise
    """
    client = get_redis_client()
    
    if client is None:
        return False
    
    try:
        cache_key = generate_cache_key(market, team, player, sport, league)
        cache_ttl = ttl if ttl is not None else CACHE_TTL
        
        client.setex(
            cache_key,
            cache_ttl,
            json.dumps(data)
        )
        
        print(f"✓ Cache SET: {cache_key} (TTL: {cache_ttl}s)")
        return True
        
    except Exception as e:
        print(f"Redis set error: {e}")
        return False


def invalidate_cache(market: Optional[str] = None,
                     team: Optional[str] = None,
                     player: Optional[str] = None,
                     sport: Optional[str] = None,
                     league: Optional[str] = None) -> bool:
    """
    Invalidate (delete) specific cache entry.
    
    Args:
        market: Market type
        team: Team name
        player: Player name
        sport: Sport name
        league: League name
    
    Returns:
        True if invalidated, False otherwise
    """
    client = get_redis_client()
    
    if client is None:
        return False
    
    try:
        cache_key = generate_cache_key(market, team, player, sport, league)
        result = client.delete(cache_key)
        
        if result:
            print(f"✓ Cache INVALIDATED: {cache_key}")
            return True
        else:
            print(f"✗ Cache key not found: {cache_key}")
            return False
            
    except Exception as e:
        print(f"Redis delete error: {e}")
        return False


def clear_all_cache() -> bool:
    """
    Clear all cache entries (use with caution).
    
    Returns:
        True if successful, False otherwise
    """
    client = get_redis_client()
    
    if client is None:
        return False
    
    try:
        # Delete all keys matching our cache pattern
        keys = client.keys('cache:*')
        if keys:
            deleted = client.delete(*keys)
            print(f"✓ Cleared {deleted} cache entries")
            return True
        else:
            print("No cache entries to clear")
            return True
            
    except Exception as e:
        print(f"Redis clear error: {e}")
        return False


def get_cache_stats() -> Dict[str, Any]:
    """
    Get cache statistics.
    
    Returns:
        Dictionary with cache statistics
    """
    client = get_redis_client()
    
    if client is None:
        return {
            "status": "unavailable",
            "connected": False
        }
    
    try:
        info = client.info()
        cache_keys = len(client.keys('cache:*'))
        
        return {
            "status": "online",
            "connected": True,
            "total_cache_keys": cache_keys,
            "redis_version": info.get('redis_version', 'unknown'),
            "used_memory_human": info.get('used_memory_human', 'unknown'),
            "connected_clients": info.get('connected_clients', 0),
            "total_commands_processed": info.get('total_commands_processed', 0),
            "uptime_in_seconds": info.get('uptime_in_seconds', 0)
        }
        
    except Exception as e:
        return {
            "status": "error",
            "connected": False,
            "error": str(e)
        }
