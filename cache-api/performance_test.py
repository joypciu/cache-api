"""
Performance Test: Single vs Batch Queries
Tests VPS endpoint performance and identifies optimization opportunities
"""
import requests
import time
import json
from statistics import mean, median

VPS_URL = "http://142.44.160.36:8001"

def time_request(func):
    """Decorator to time requests"""
    start = time.time()
    result = func()
    elapsed = time.time() - start
    return result, elapsed

def test_single_queries():
    """Test individual single queries"""
    print("=" * 70)
    print("TEST 1: Individual Single Queries")
    print("=" * 70)
    
    queries = [
        {"team": "Lakers", "sport": "Basketball"},
        {"team": "Warriors", "sport": "Basketball"},
        {"team": "Bulls", "sport": "Basketball"},
        {"player": "LeBron James"},
        {"player": "Stephen Curry"},
        {"market": "moneyline"},
        {"market": "spread"}
    ]
    
    times = []
    total_start = time.time()
    
    for i, params in enumerate(queries, 1):
        def make_request():
            return requests.get(f"{VPS_URL}/cache", params=params)
        
        response, elapsed = time_request(make_request)
        times.append(elapsed)
        status = "✓" if response.status_code == 200 else "✗"
        print(f"  Query {i}: {status} {elapsed*1000:.2f}ms - {params}")
    
    total_elapsed = time.time() - total_start
    
    print(f"\n  Total Queries: {len(queries)}")
    print(f"  Total Time: {total_elapsed*1000:.2f}ms")
    print(f"  Average: {mean(times)*1000:.2f}ms")
    print(f"  Median: {median(times)*1000:.2f}ms")
    print(f"  Min: {min(times)*1000:.2f}ms")
    print(f"  Max: {max(times)*1000:.2f}ms")
    
    return total_elapsed, times

def test_batch_query():
    """Test batch query"""
    print("\n" + "=" * 70)
    print("TEST 2: Single Batch Query")
    print("=" * 70)
    
    batch_request = {
        "team": ["Lakers", "Warriors", "Bulls"],
        "player": ["LeBron James", "Stephen Curry"],
        "market": ["moneyline", "spread"],
        "sport": "Basketball"
    }
    
    def make_request():
        return requests.post(
            f"{VPS_URL}/cache/batch",
            json=batch_request,
            headers={"Content-Type": "application/json"}
        )
    
    response, elapsed = time_request(make_request)
    status = "✓" if response.status_code == 200 else "✗"
    
    print(f"  Status: {status}")
    print(f"  Time: {elapsed*1000:.2f}ms")
    print(f"  Items Requested: 7 (3 teams + 2 players + 2 markets)")
    
    if response.status_code == 200:
        data = response.json()
        found_count = 0
        if "team" in data:
            found_count += sum(1 for v in data["team"].values() if v is not None)
        if "player" in data:
            found_count += sum(1 for v in data["player"].values() if v is not None)
        if "market" in data:
            found_count += sum(1 for v in data["market"].values() if v is not None)
        print(f"  Items Found: {found_count}")
    
    return elapsed

def test_precision_batch():
    """Test precision batch query"""
    print("\n" + "=" * 70)
    print("TEST 3: Precision Batch Query")
    print("=" * 70)
    
    precision_request = {
        "queries": [
            {"team": "Lakers", "sport": "Basketball"},
            {"team": "Warriors", "sport": "Basketball"},
            {"team": "Bulls", "sport": "Basketball"},
            {"player": "LeBron James"},
            {"player": "Stephen Curry"},
            {"market": "moneyline"},
            {"market": "spread"}
        ]
    }
    
    def make_request():
        return requests.post(
            f"{VPS_URL}/cache/batch/precision",
            json=precision_request,
            headers={"Content-Type": "application/json"}
        )
    
    response, elapsed = time_request(make_request)
    status = "✓" if response.status_code == 200 else "✗"
    
    print(f"  Status: {status}")
    print(f"  Time: {elapsed*1000:.2f}ms")
    
    if response.status_code == 200:
        data = response.json()
        print(f"  Total Queries: {data.get('total_queries', 0)}")
        print(f"  Successful: {data.get('successful', 0)}")
        print(f"  Failed: {data.get('failed', 0)}")
    
    return elapsed

def test_cache_performance():
    """Test cache hit vs cache miss performance"""
    print("\n" + "=" * 70)
    print("TEST 4: Cache Performance (Hit vs Miss)")
    print("=" * 70)
    
    # First request (likely cache miss or cold)
    def first_request():
        return requests.get(f"{VPS_URL}/cache", params={"team": "Lakers", "sport": "Basketball"})
    
    _, first_time = time_request(first_request)
    print(f"  First Request (cache miss): {first_time*1000:.2f}ms")
    
    # Second request (cache hit)
    def second_request():
        return requests.get(f"{VPS_URL}/cache", params={"team": "Lakers", "sport": "Basketball"})
    
    _, second_time = time_request(second_request)
    print(f"  Second Request (cache hit): {second_time*1000:.2f}ms")
    
    if first_time > 0:
        improvement = ((first_time - second_time) / first_time) * 100
        print(f"  Cache Improvement: {improvement:.1f}%")
        print(f"  Speedup: {first_time/second_time:.2f}x faster")
    
    return first_time, second_time

def test_repeated_batch():
    """Test batch query performance over multiple runs"""
    print("\n" + "=" * 70)
    print("TEST 5: Batch Query Consistency (5 runs)")
    print("=" * 70)
    
    batch_request = {
        "team": ["Lakers", "Warriors"],
        "player": ["LeBron James"],
        "market": ["moneyline"],
        "sport": "Basketball"
    }
    
    times = []
    for i in range(5):
        def make_request():
            return requests.post(
                f"{VPS_URL}/cache/batch",
                json=batch_request,
                headers={"Content-Type": "application/json"}
            )
        
        _, elapsed = time_request(make_request)
        times.append(elapsed)
        print(f"  Run {i+1}: {elapsed*1000:.2f}ms")
    
    print(f"\n  Average: {mean(times)*1000:.2f}ms")
    print(f"  Median: {median(times)*1000:.2f}ms")
    print(f"  Std Dev: {(max(times) - min(times))*1000:.2f}ms")
    
    return times

def main():
    print("\n" + "=" * 70)
    print("CACHE API PERFORMANCE TEST")
    print(f"VPS Endpoint: {VPS_URL}")
    print("=" * 70)
    
    try:
        # Test 1: Individual queries
        single_total, single_times = test_single_queries()
        
        # Test 2: Batch query
        batch_time = test_batch_query()
        
        # Test 3: Precision batch
        precision_time = test_precision_batch()
        
        # Test 4: Cache performance
        cache_miss, cache_hit = test_cache_performance()
        
        # Test 5: Consistency
        batch_times = test_repeated_batch()
        
        # Summary
        print("\n" + "=" * 70)
        print("PERFORMANCE SUMMARY")
        print("=" * 70)
        print(f"\n  Single Queries (7 requests): {single_total*1000:.2f}ms")
        print(f"  Batch Query (1 request): {batch_time*1000:.2f}ms")
        print(f"  Precision Batch (1 request): {precision_time*1000:.2f}ms")
        
        if single_total > 0:
            batch_improvement = ((single_total - batch_time) / single_total) * 100
            precision_improvement = ((single_total - precision_time) / single_total) * 100
            
            print(f"\n  Batch vs Single Improvement: {batch_improvement:.1f}%")
            print(f"  Batch Speedup: {single_total/batch_time:.2f}x faster")
            
            print(f"\n  Precision vs Single Improvement: {precision_improvement:.1f}%")
            print(f"  Precision Speedup: {single_total/precision_time:.2f}x faster")
        
        # Recommendations
        print("\n" + "=" * 70)
        print("OPTIMIZATION RECOMMENDATIONS")
        print("=" * 70)
        
        avg_single = mean(single_times) * 1000
        avg_batch = mean(batch_times) * 1000
        
        recommendations = []
        
        if avg_single > 100:
            recommendations.append("⚠ Single queries >100ms - Consider database query optimization")
        
        if avg_batch > 200:
            recommendations.append("⚠ Batch queries >200ms - Consider parallel processing within batch")
        
        if cache_hit > 50:
            recommendations.append("⚠ Cache hits >50ms - Redis connection may need optimization")
        
        if cache_miss / cache_hit > 10:
            recommendations.append("✓ Excellent cache performance - cache hits are much faster")
        elif cache_miss / cache_hit > 5:
            recommendations.append("✓ Good cache performance")
        else:
            recommendations.append("⚠ Cache performance could be improved")
        
        if batch_improvement > 50:
            recommendations.append("✓ Batch endpoint provides significant performance gain")
        
        if not recommendations:
            recommendations.append("✓ All metrics look good - no major optimizations needed")
        
        for rec in recommendations:
            print(f"  {rec}")
        
        print("\n" + "=" * 70)
        
    except requests.exceptions.ConnectionError:
        print("\n✗ ERROR: Could not connect to VPS endpoint")
        print(f"  Make sure {VPS_URL} is accessible")
    except Exception as e:
        print(f"\n✗ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
