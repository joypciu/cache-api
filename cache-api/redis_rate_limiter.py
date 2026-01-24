"""
Redis-based Rate Limiter Module
Provides rate limiting for API endpoints using Redis sliding window algorithm.
"""

import time
import uuid
from typing import Tuple, Dict, Any, List, Optional
from redis_cache import get_redis_client
from collections import defaultdict
import json

# Rate limit configurations (requests per window)
RATE_LIMITS = {
    "default": {"limit": 100, "window": 60},                    # 100 requests per minute
    "/cache": {"limit": 200, "window": 60},                     # 200 requests per minute
    "/cache/batch": {"limit": 20, "window": 60},                # 20 requests per minute (expensive)
    "/cache/batch/precision": {"limit": 10, "window": 60},      # 10 requests per minute (very expensive)
}


def check_rate_limit(
    identifier: str,
    endpoint: str = "default",
    custom_limit: Optional[int] = None,
    custom_window: Optional[int] = None
) -> Tuple[bool, int, int]:
    """
    Check if request is within rate limit using Redis sliding window.
    
    This uses Redis sorted sets with timestamps as scores to implement
    a sliding window rate limiter - the industry standard approach.
    
    Args:
        identifier: User identifier (token, UUID, or IP)
        endpoint: API endpoint path
        custom_limit: Override default request limit
        custom_window: Override default time window (seconds)
    
    Returns:
        Tuple of (allowed: bool, remaining: int, reset_time: int)
        - allowed: True if request should be allowed
        - remaining: Number of requests remaining in window
        - reset_time: Unix timestamp when limit resets
    
    Example:
        allowed, remaining, reset = check_rate_limit("user123", "/cache")
        if not allowed:
            raise HTTPException(429, "Rate limit exceeded")
    """
    redis_client = get_redis_client()
    
    # Graceful fallback: if Redis is unavailable, allow all requests
    if not redis_client:
        return True, 999, 0
    
    # Get rate limit config for this endpoint
    config = RATE_LIMITS.get(endpoint, RATE_LIMITS["default"])
    limit = custom_limit or config["limit"]
    window = custom_window or config["window"]
    
    current_time = time.time()
    window_start = current_time - window
    
    # Create unique key for this user+endpoint combination
    key = f"rate_limit:{identifier}:{endpoint}"
    
    try:
        # Remove requests outside the current window (older than window_start)
        redis_client.zremrangebyscore(key, 0, window_start)
        
        # Count requests in current window
        current_count = redis_client.zcard(key)
        
        # Check if limit exceeded
        if current_count >= limit:
            # Get oldest request timestamp to calculate reset time
            oldest = redis_client.zrange(key, 0, 0, withscores=True)
            reset_at = int(oldest[0][1] + window) if oldest else int(current_time + window)
            return False, 0, reset_at
        
        # Add this request to the window
        request_id = str(uuid.uuid4())
        redis_client.zadd(key, {request_id: current_time})
        
        # Set expiration to prevent memory leaks (window + 10 second buffer)
        redis_client.expire(key, window + 10)
        
        # Calculate remaining requests
        remaining = limit - current_count - 1
        reset_at = int(current_time + window)
        
        return True, remaining, reset_at
        
    except Exception as e:
        print(f"Rate limit check error: {e}")
        # On error, allow request (fail open)
        return True, limit, 0


def get_rate_limit_stats(identifier: Optional[str] = None) -> Dict[str, Any]:
    """
    Get rate limit statistics for admin monitoring.
    
    Args:
        identifier: Optional specific user to check (None = all users)
    
    Returns:
        Dictionary with rate limit statistics
    """
    redis_client = get_redis_client()
    
    if not redis_client:
        return {
            "error": "Redis unavailable",
            "stats": None
        }
    
    try:
        stats = {
            "timestamp": time.time(),
            "window_seconds": 60,
            "clients": [],
            "summary": {
                "total_clients": 0,
                "total_active_requests": 0,
                "limited_clients": 0
            }
        }
        
        # Get all rate limit keys
        pattern = f"rate_limit:{identifier}:*" if identifier else "rate_limit:*"
        keys = redis_client.keys(pattern)
        
        client_stats = defaultdict(lambda: {
            "identifier": None,
            "endpoints": {},
            "total_requests": 0,
            "status": "normal"
        })
        
        current_time = time.time()
        
        for key in keys:
            # Parse key: rate_limit:identifier:endpoint
            parts = key.split(":", 2)
            if len(parts) != 3:
                continue
            
            client_id = parts[1]
            endpoint = parts[2]
            
            # Count requests in this window
            count = redis_client.zcard(key)
            
            if count == 0:
                continue
            
            # Get endpoint config
            config = RATE_LIMITS.get(endpoint, RATE_LIMITS["default"])
            limit = config["limit"]
            
            # Calculate status
            usage_percent = (count / limit) * 100
            if count >= limit:
                status = "rate_limited"
            elif usage_percent >= 80:
                status = "near_limit"
            else:
                status = "normal"
            
            # Get oldest and newest request times
            oldest = redis_client.zrange(key, 0, 0, withscores=True)
            newest = redis_client.zrange(key, -1, -1, withscores=True)
            
            oldest_time = oldest[0][1] if oldest else current_time
            newest_time = newest[0][1] if newest else current_time
            
            client_stats[client_id]["identifier"] = client_id
            client_stats[client_id]["endpoints"][endpoint] = {
                "requests": count,
                "limit": limit,
                "remaining": max(0, limit - count),
                "usage_percent": round(usage_percent, 2),
                "status": status,
                "oldest_request": oldest_time,
                "newest_request": newest_time,
                "window_start": current_time - 60
            }
            client_stats[client_id]["total_requests"] += count
            
            if status == "rate_limited" or client_stats[client_id]["status"] == "normal":
                client_stats[client_id]["status"] = status
        
        # Convert to list
        stats["clients"] = list(client_stats.values())
        stats["summary"]["total_clients"] = len(stats["clients"])
        stats["summary"]["total_active_requests"] = sum(c["total_requests"] for c in stats["clients"])
        stats["summary"]["limited_clients"] = sum(1 for c in stats["clients"] if c["status"] == "rate_limited")
        
        # Sort by total requests (most active first)
        stats["clients"].sort(key=lambda x: x["total_requests"], reverse=True)
        
        return stats
        
    except Exception as e:
        print(f"Error getting rate limit stats: {e}")
        return {
            "error": str(e),
            "stats": None
        }


def get_url_stats() -> Dict[str, Any]:
    """
    Get URL access statistics from rate limit data.
    
    Returns:
        Dictionary with URL access statistics
    """
    redis_client = get_redis_client()
    
    if not redis_client:
        return {
            "error": "Redis unavailable",
            "stats": None
        }
    
    try:
        # Get all rate limit keys
        keys = redis_client.keys("rate_limit:*")
        
        endpoint_stats = defaultdict(lambda: {
            "endpoint": None,
            "total_requests": 0,
            "unique_clients": set(),
            "limit": 0
        })
        
        for key in keys:
            # Parse key: rate_limit:identifier:endpoint
            parts = key.split(":", 2)
            if len(parts) != 3:
                continue
            
            client_id = parts[1]
            endpoint = parts[2]
            
            count = redis_client.zcard(key)
            
            if count == 0:
                continue
            
            endpoint_stats[endpoint]["endpoint"] = endpoint
            endpoint_stats[endpoint]["total_requests"] += count
            endpoint_stats[endpoint]["unique_clients"].add(client_id)
            
            # Get limit
            config = RATE_LIMITS.get(endpoint, RATE_LIMITS["default"])
            endpoint_stats[endpoint]["limit"] = config["limit"]
        
        # Convert sets to counts
        stats = []
        for endpoint, data in endpoint_stats.items():
            stats.append({
                "endpoint": data["endpoint"],
                "total_requests": data["total_requests"],
                "unique_clients": len(data["unique_clients"]),
                "avg_requests_per_client": round(data["total_requests"] / len(data["unique_clients"]), 2) if data["unique_clients"] else 0,
                "rate_limit": data["limit"],
                "window_seconds": 60
            })
        
        # Sort by total requests
        stats.sort(key=lambda x: x["total_requests"], reverse=True)
        
        return {
            "timestamp": time.time(),
            "total_endpoints": len(stats),
            "total_requests": sum(s["total_requests"] for s in stats),
            "endpoints": stats
        }
        
    except Exception as e:
        print(f"Error getting URL stats: {e}")
        return {
            "error": str(e),
            "stats": None
        }


def get_request_stats() -> Dict[str, Any]:
    """
    Get aggregated request statistics.
    
    Returns:
        Dictionary with request statistics
    """
    redis_client = get_redis_client()
    
    if not redis_client:
        return {
            "error": "Redis unavailable",
            "stats": None
        }
    
    try:
        keys = redis_client.keys("rate_limit:*")
        
        stats = {
            "timestamp": time.time(),
            "window_seconds": 60,
            "total_requests": 0,
            "total_clients": set(),
            "total_endpoints": set(),
            "by_endpoint": defaultdict(int),
            "status": {
                "normal": 0,
                "near_limit": 0,
                "rate_limited": 0
            }
        }
        
        for key in keys:
            parts = key.split(":", 2)
            if len(parts) != 3:
                continue
            
            client_id = parts[1]
            endpoint = parts[2]
            
            count = redis_client.zcard(key)
            
            if count == 0:
                continue
            
            stats["total_requests"] += count
            stats["total_clients"].add(client_id)
            stats["total_endpoints"].add(endpoint)
            stats["by_endpoint"][endpoint] += count
            
            # Check status
            config = RATE_LIMITS.get(endpoint, RATE_LIMITS["default"])
            limit = config["limit"]
            usage_percent = (count / limit) * 100
            
            if count >= limit:
                stats["status"]["rate_limited"] += 1
            elif usage_percent >= 80:
                stats["status"]["near_limit"] += 1
            else:
                stats["status"]["normal"] += 1
        
        # Convert sets to counts
        stats["total_clients"] = len(stats["total_clients"])
        stats["total_endpoints"] = len(stats["total_endpoints"])
        stats["by_endpoint"] = dict(stats["by_endpoint"])
        
        return stats
        
    except Exception as e:
        print(f"Error getting request stats: {e}")
        return {
            "error": str(e),
            "stats": None
        }


def clear_rate_limits(identifier: Optional[str] = None, endpoint: Optional[str] = None) -> bool:
    """
    Clear rate limits for debugging/testing (admin only).
    
    Args:
        identifier: Optional specific user (None = all users)
        endpoint: Optional specific endpoint (None = all endpoints)
    
    Returns:
        True if successful
    """
    redis_client = get_redis_client()
    
    if not redis_client:
        return False
    
    try:
        if identifier and endpoint:
            pattern = f"rate_limit:{identifier}:{endpoint}"
        elif identifier:
            pattern = f"rate_limit:{identifier}:*"
        elif endpoint:
            pattern = f"rate_limit:*:{endpoint}"
        else:
            pattern = "rate_limit:*"
        
        keys = redis_client.keys(pattern)
        if keys:
            redis_client.delete(*keys)
        
        return True
        
    except Exception as e:
        print(f"Error clearing rate limits: {e}")
        return False
