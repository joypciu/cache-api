"""Quick performance test for the Cache API"""
import requests
import time

API_URL = "http://localhost:8001"

def test_single_queries(count=7):
    """Test single query performance"""
    print("\n=== SINGLE QUERY TEST ===")
    times = []
    
    for i in range(count):
        start = time.time()
        response = requests.get(f"{API_URL}/cache", params={"team": "Barcelona", "sport": "Soccer"})
        elapsed = (time.time() - start) * 1000
        times.append(elapsed)
        print(f"  Request {i+1}: {elapsed:.0f} ms")
    
    avg = sum(times) / len(times)
    total = sum(times)
    print(f"\n  Average: {avg:.0f} ms")
    print(f"  Total (7 requests): {total:.0f} ms")
    return avg, total

def test_batch_query():
    """Test batch query performance"""
    print("\n=== BATCH QUERY TEST ===")
    
    payload = {
        "team": ["Barcelona", "Real Madrid", "Manchester United"],
        "sport": "Soccer"
    }
    
    start = time.time()
    response = requests.post(f"{API_URL}/cache/batch", json=payload)
    elapsed = (time.time() - start) * 1000
    
    print(f"  Time: {elapsed:.0f} ms (1 request, 3 teams)")
    return elapsed

def test_precision_batch():
    """Test precision batch query performance"""
    print("\n=== PRECISION BATCH TEST ===")
    
    payload = {
        "queries": [
            {"team": "Barcelona", "sport": "Soccer"},
            {"team": "Real Madrid", "sport": "Soccer"},
            {"team": "Manchester United", "sport": "Soccer"}
        ]
    }
    
    start = time.time()
    response = requests.post(f"{API_URL}/cache/precision-batch", json=payload)
    elapsed = (time.time() - start) * 1000
    
    print(f"  Time: {elapsed:.0f} ms (1 request, 3 queries)")
    return elapsed

if __name__ == "__main__":
    print("="*50)
    print("PERFORMANCE TEST RESULTS")
    print("="*50)
    
    # Clear cache first for fair test
    try:
        requests.delete(f"{API_URL}/cache/clear")
        print("\n✓ Cache cleared")
    except:
        pass
    
    time.sleep(1)
    
    # Run tests
    single_avg, single_total = test_single_queries(7)
    batch_time = test_batch_query()
    precision_time = test_precision_batch()
    
    # Summary
    print("\n" + "="*50)
    print("SUMMARY")
    print("="*50)
    print(f"Single queries (7 requests): {single_total:.0f} ms")
    print(f"Batch query (1 request):     {batch_time:.0f} ms")
    print(f"Precision batch (1 request): {precision_time:.0f} ms")
    
    # Compare with before
    print("\n" + "="*50)
    print("IMPROVEMENT vs BEFORE")
    print("="*50)
    before_single = 4399
    before_batch = 859
    before_precision = 899
    
    single_improvement = ((before_single - single_total) / before_single) * 100
    batch_improvement = ((before_batch - batch_time) / before_batch) * 100
    precision_improvement = ((before_precision - precision_time) / before_precision) * 100
    
    print(f"Single queries:   {before_single}ms → {single_total:.0f}ms ({single_improvement:.1f}% faster)")
    print(f"Batch query:      {before_batch}ms → {batch_time:.0f}ms ({batch_improvement:.1f}% faster)")
    print(f"Precision batch:  {before_precision}ms → {precision_time:.0f}ms ({precision_improvement:.1f}% faster)")
