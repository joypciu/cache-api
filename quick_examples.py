"""
Quick Examples - How to Use the Cache API
Run this script to see practical examples of using the API
"""

import requests
import json
from typing import Optional, Dict, Any

# API Configuration
API_BASE = "http://localhost:8001"

def print_section(title):
    """Print formatted section header"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def search_cache(team: Optional[str] = None,
                 player: Optional[str] = None, 
                 league: Optional[str] = None,
                 market: Optional[str] = None,
                 sport: Optional[str] = None) -> Dict[str, Any]:
    """
    Search the cache API
    
    Args:
        team: Team name
        player: Player name
        league: League name
        market: Market type
        sport: Sport name
    
    Returns:
        API response as dictionary
    """
    params = {}
    if team: params["team"] = team
    if player: params["player"] = player
    if league: params["league"] = league
    if market: params["market"] = market
    if sport: params["sport"] = sport
    
    try:
        response = requests.get(f"{API_BASE}/cache", params=params, timeout=5)
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e), "found": False}

def get_cache_stats():
    """Get cache statistics"""
    try:
        response = requests.get(f"{API_BASE}/cache/stats", timeout=5)
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

def example_team_search():
    """Example: Search for a team"""
    print_section("Example 1: Search by Team")
    
    print("\n🔍 Searching for: Barcelona (Soccer)")
    result = search_cache(team="Barcelona", sport="Soccer")
    
    if result.get("found"):
        team = result["data"]["teams"][0]
        print(f"✓ Found: {team['normalized_name']}")
        print(f"  League: {team['league']}")
        print(f"  Abbreviation: {team['abbreviation']}")
        print(f"  Players: {team['player_count']}")
        
        if team['players']:
            print(f"\n  Sample players:")
            for player in team['players'][:5]:
                print(f"    - {player['name']} ({player.get('position', 'N/A')})")
    else:
        print("✗ Not found")

def example_player_search():
    """Example: Search for a player"""
    print_section("Example 2: Search by Player")
    
    print("\n🔍 Searching for: Lionel Messi")
    result = search_cache(player="Lionel Messi")
    
    if result.get("found"):
        player = result["data"]["players"][0]
        print(f"✓ Found: {player['normalized_name']}")
        print(f"  Team: {player['team']}")
        print(f"  League: {player['league']}")
        print(f"  Sport: {player['sport']}")
        print(f"  Position: {player.get('position', 'N/A')}")
    else:
        print("✗ Not found")

def example_league_search():
    """Example: Search for a league"""
    print_section("Example 3: Search by League")
    
    print("\n🔍 Searching for: UEFA - Europa League (Soccer)")
    result = search_cache(league="UEFA - Europa League", sport="Soccer")
    
    if result.get("found"):
        league = result["data"]["leagues"][0]
        print(f"✓ Found: {league['normalized_name']}")
        print(f"  Sport: {league['sport']}")
        print(f"  Teams: {league['team_count']}")
        
        if league['teams']:
            print(f"\n  Sample teams:")
            for team in league['teams'][:10]:
                print(f"    - {team['name']}")
    else:
        print("✗ Not found")

def example_market_search():
    """Example: Search for a market"""
    print_section("Example 4: Search by Market")
    
    print("\n🔍 Searching for: Moneyline market")
    result = search_cache(market="moneyline")
    
    if result.get("found"):
        market = result["data"]
        print(f"✓ Found: {market['normalized_name']}")
        print(f"  Type: {market['type']}")
        if market.get('sports'):
            print(f"  Available sports: {', '.join(market['sports'])}")
    else:
        print("✗ Not found")

def example_specific_player_on_team():
    """Example: Search for specific player on specific team"""
    print_section("Example 5: Search by Team + Player")
    
    print("\n🔍 Searching for: Kylian Mbappé on Real Madrid")
    result = search_cache(team="Real Madrid", player="Mbappe", sport="Soccer")
    
    if result.get("found"):
        player = result["data"]["players"][0]
        print(f"✓ Found: {player['normalized_name']}")
        print(f"  Team: {player['team']}")
        print(f"  Position: {player.get('position', 'N/A')}")
        print(f"  League: {player['league']}")
    else:
        print("✗ Not found")

def example_alias_normalization():
    """Example: Demonstrate alias normalization"""
    print_section("Example 6: Alias Normalization")
    
    aliases = [
        ("Man Utd", "Soccer"),
        ("Barca", "Soccer"),
        ("Real", "Soccer"),
    ]
    
    for alias, sport in aliases:
        print(f"\n🔍 Input: '{alias}'")
        result = search_cache(team=alias, sport=sport)
        
        if result.get("found"):
            team = result["data"]["teams"][0]
            print(f"  ✓ Normalized to: '{team['normalized_name']}'")
        else:
            print(f"  ✗ Not found")

def example_cache_stats():
    """Example: Get cache statistics"""
    print_section("Example 7: Cache Statistics")
    
    print("\n📊 Getting cache statistics...")
    stats = get_cache_stats()
    
    if "error" not in stats:
        print(f"\n  Status: {stats.get('status', 'unknown')}")
        print(f"  Redis Connected: {stats.get('connected', False)}")
        print(f"  Cached Entries: {stats.get('total_cache_keys', 0)}")
        print(f"  Redis Version: {stats.get('redis_version', 'unknown')}")
        print(f"  Memory Used: {stats.get('used_memory_human', 'unknown')}")
    else:
        print(f"  ✗ Error: {stats['error']}")

def example_batch_queries():
    """Example: Batch queries for multiple teams"""
    print_section("Example 8: Batch Queries")
    
    teams = ["Barcelona", "Real Madrid", "Manchester United", "Liverpool"]
    
    print(f"\n🔍 Searching for {len(teams)} teams...\n")
    
    results = []
    for team_name in teams:
        result = search_cache(team=team_name, sport="Soccer")
        if result.get("found"):
            team = result["data"]["teams"][0]
            results.append({
                "input": team_name,
                "normalized": team["normalized_name"],
                "league": team["league"],
                "players": team["player_count"]
            })
    
    # Print results
    for r in results:
        print(f"  {r['input']:20} → {r['normalized']:30} ({r['players']:2} players)")

def example_error_handling():
    """Example: Error handling"""
    print_section("Example 9: Error Handling")
    
    print("\n🔍 Searching for non-existent team...")
    result = search_cache(team="NonexistentTeam12345", sport="Soccer")
    
    if result.get("found"):
        print("  ✓ Found (unexpected!)")
    else:
        print("  ✗ Not found (expected)")
        print(f"  Message: {result.get('message', 'No message')}")
    
    print("\n🔍 Missing required parameter (team without sport)...")
    result = search_cache(team="Barcelona")  # Missing sport parameter
    
    if "error" in result:
        print(f"  ✗ Error: {result['error']}")
    elif "detail" in result:
        print(f"  ✗ Error: {result['detail']}")

def run_all_examples():
    """Run all usage examples"""
    print("="*60)
    print("  CACHE API - USAGE EXAMPLES")
    print("="*60)
    print("\nMake sure the API is running at http://localhost:8001")
    print("Start it with: cd cache-api && python main.py\n")
    
    try:
        # Test connection
        response = requests.get(f"{API_BASE}/health", timeout=2)
        if response.status_code == 200:
            print("✓ API is running!\n")
        else:
            print("✗ API returned unexpected status")
            return
    except requests.exceptions.RequestException:
        print("✗ Cannot connect to API. Please start it first:")
        print("   cd cache-api")
        print("   python main.py")
        return
    
    # Run all examples
    example_team_search()
    example_player_search()
    example_league_search()
    example_market_search()
    example_specific_player_on_team()
    example_alias_normalization()
    example_cache_stats()
    example_batch_queries()
    example_error_handling()
    
    print("\n" + "="*60)
    print("  ALL EXAMPLES COMPLETE")
    print("="*60)
    print("\nFor more information:")
    print("  - API Documentation: cache-api/README.md")
    print("  - Usage Guide: USAGE_GUIDE.md")
    print("  - Redis Documentation: cache-api/REDIS_README.md")
    print()

if __name__ == "__main__":
    run_all_examples()
