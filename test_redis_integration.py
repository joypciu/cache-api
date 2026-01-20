"""
Test Redis Integration
Quick test to verify Redis caching is working correctly.
"""

import sys
import os

# Add cache-api to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'cache-api'))

from redis_cache import (
    get_redis_client,
    get_cache_stats,
    generate_cache_key,
    set_cached_data,
    get_cached_data,
    clear_all_cache
)
from cache_db import get_cache_entry

def test_redis_connection():
    """Test basic Redis connection"""
    print("\n=== Testing Redis Connection ===")
    client = get_redis_client()
    
    if client:
        print("✓ Redis connected successfully")
        try:
            client.ping()
            print("✓ Redis PING successful")
            return True
        except Exception as e:
            print(f"✗ Redis PING failed: {e}")
            return False
    else:
        print("✗ Redis connection failed")
        return False


def test_cache_stats():
    """Test cache statistics"""
    print("\n=== Testing Cache Statistics ===")
    stats = get_cache_stats()
    print(f"Status: {stats.get('status')}")
    print(f"Connected: {stats.get('connected')}")
    
    if stats.get('connected'):
        print(f"Total cache keys: {stats.get('total_cache_keys')}")
        print(f"Redis version: {stats.get('redis_version')}")
        print(f"Memory used: {stats.get('used_memory_human')}")
        return True
    
    return False


def test_cache_operations():
    """Test cache set/get operations"""
    print("\n=== Testing Cache Operations ===")
    
    # Test data
    test_data = {
        "type": "test",
        "message": "This is a test cache entry",
        "timestamp": "2026-01-01"
    }
    
    # Test cache key generation
    cache_key = generate_cache_key(team="Lakers", sport="Basketball")
    print(f"Generated cache key: {cache_key}")
    
    # Test SET operation
    print("\nTesting SET operation...")
    success = set_cached_data(
        test_data,
        team="Lakers",
        sport="Basketball",
        ttl=60  # 60 seconds for testing
    )
    
    if success:
        print("✓ Cache SET successful")
    else:
        print("✗ Cache SET failed")
        return False
    
    # Test GET operation
    print("\nTesting GET operation...")
    retrieved = get_cached_data(team="Lakers", sport="Basketball")
    
    if retrieved:
        print("✓ Cache GET successful")
        print(f"Retrieved data: {retrieved}")
        
        if retrieved == test_data:
            print("✓ Data matches original")
            return True
        else:
            print("✗ Data mismatch")
            return False
    else:
        print("✗ Cache GET failed")
        return False


def test_database_with_cache():
    """Test database query with Redis caching"""
    print("\n=== Testing Database Query with Caching ===")
    
    # Clear cache first
    print("Clearing all cache...")
    clear_all_cache()
    
    # First query - should be a cache MISS
    print("\nFirst query (should be cache MISS)...")
    result1 = get_cache_entry(team="Manchester United", sport="Soccer")
    
    if result1:
        print(f"✓ Query returned data: {result1.get('type')}")
        if result1.get('type') == 'team':
            print(f"  Teams found: {result1.get('team_count')}")
    else:
        print("✗ No data returned")
        return False
    
    # Second query - should be a cache HIT
    print("\nSecond query (should be cache HIT)...")
    result2 = get_cache_entry(team="Manchester United", sport="Soccer")
    
    if result2:
        print(f"✓ Query returned data from cache")
        
        if result1 == result2:
            print("✓ Cached data matches original")
            return True
        else:
            print("✗ Cached data mismatch")
            return False
    else:
        print("✗ No data returned")
        return False


def run_all_tests():
    """Run all Redis integration tests"""
    print("="*60)
    print("REDIS INTEGRATION TESTS")
    print("="*60)
    
    tests = [
        ("Redis Connection", test_redis_connection),
        ("Cache Statistics", test_cache_stats),
        ("Cache Operations", test_cache_operations),
        ("Database with Cache", test_database_with_cache)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ Test '{test_name}' raised exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Redis integration is working correctly.")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please check Redis configuration.")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
