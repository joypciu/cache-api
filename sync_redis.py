"""
Redis Sync Script
Automatically syncs database aliases to Redis every 2 minutes.
Ensures Redis cache stays in sync with SQLite database.
Production-ready for VPS deployment with systemd service.
"""

import sqlite3
import redis
import json
import time
import os
import sys
import logging
from datetime import datetime
from typing import Dict, Set, List
from pathlib import Path

# Setup logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
LOG_FILE = os.getenv('LOG_FILE', None)  # None = console only, or path to log file

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        *([] if not LOG_FILE else [logging.FileHandler(LOG_FILE)])
    ]
)
logger = logging.getLogger('redis_sync')

# Redis connection settings
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_DB = int(os.getenv('REDIS_DB', 0))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', None)

# Database path - configurable via environment variable
DB_PATH = os.getenv('DB_PATH', os.path.join(os.path.dirname(__file__), "sports_data.db"))

# Sync interval in seconds (default: 2 minutes)
SYNC_INTERVAL = int(os.getenv('SYNC_INTERVAL', 120))

# Redis key prefixes
ALIAS_PREFIX = "alias:"
ENTITY_PREFIX = "entity:"


def get_redis_client():
    """Get Redis client connection"""
    try:
        client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            password=REDIS_PASSWORD,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5
        )
        client.ping()
        logger.info(f"✓ Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
        return client
    except redis.ConnectionError as e:
        logger.error(f"Failed to connect to Redis at {REDIS_HOST}:{REDIS_PORT}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error connecting to Redis: {e}")
        return None


def get_db_connection():
    """Get database connection"""
    try:
        if not os.path.exists(DB_PATH):
            logger.error(f"Database file not found: {DB_PATH}")
            raise FileNotFoundError(f"Database file not found: {DB_PATH}")
        
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        logger.error(f"Database connection error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error connecting to database: {e}")
        raise


def get_all_entities_from_db() -> Dict[str, Dict]:
    """
    Get all entities (teams, players, leagues, markets) from database.
    Returns a dict with entity_key -> entity_data
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    entities = {}
    
    try:
        # Teams
        cursor.execute("SELECT id, name, normalized_name, sport, league FROM teams")
        for row in cursor.fetchall():
            key = f"{ENTITY_PREFIX}team:{row['id']}"
            entities[key] = {
                'id': row['id'],
                'name': row['name'],
                'normalized_name': row['normalized_name'],
                'sport': row['sport'],
                'league': row['league']
            }
        
        # Players
        cursor.execute("SELECT id, name, normalized_name, sport, team FROM players")
        for row in cursor.fetchall():
            key = f"{ENTITY_PREFIX}player:{row['id']}"
            entities[key] = {
                'id': row['id'],
                'name': row['name'],
                'normalized_name': row['normalized_name'],
                'sport': row['sport'],
                'team': row['team']
            }
        
        # Leagues
        cursor.execute("SELECT id, name, normalized_name, sport, country FROM leagues")
        for row in cursor.fetchall():
            key = f"{ENTITY_PREFIX}league:{row['id']}"
            entities[key] = {
                'id': row['id'],
                'name': row['name'],
                'normalized_name': row['normalized_name'],
                'sport': row['sport'],
                'country': row['country']
            }
        
        # Markets
        cursor.execute("SELECT id, name, normalized_name, sport FROM markets")
        for row in cursor.fetchall():
            key = f"{ENTITY_PREFIX}market:{row['id']}"
            entities[key] = {
                'id': row['id'],
                'name': row['name'],
                'normalized_name': row['normalized_name'],
                'sport': row['sport']
            }
        
    finally:
        conn.close()
    
    return entities


def get_all_entities_from_redis(redis_client) -> Dict[str, Dict]:
    """
    Get all entities from Redis.
    Returns a dict with entity_key -> entity_data
    """
    entities = {}
    
    try:
        pattern = f"{ENTITY_PREFIX}*"
        keys = redis_client.keys(pattern)
        
        for key in keys:
            value = redis_client.get(key)
            if value:
                try:
                    entities[key] = json.loads(value)
                except json.JSONDecodeError:
                    pass
    
    except Exception as e:
        logger.error(f"Error reading entities from Redis: {e}")
    
    return entities


def get_all_aliases_from_db() -> Dict[str, Set[str]]:
    """
    Get all aliases from database.
    Returns a dict with alias_key -> set of related IDs
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    aliases = {}
    
    try:
        # Team aliases
        cursor.execute("SELECT LOWER(alias) as alias, team_id FROM team_aliases")
        for row in cursor.fetchall():
            key = f"{ALIAS_PREFIX}team:{row['alias']}"
            if key not in aliases:
                aliases[key] = set()
            aliases[key].add(row['team_id'])
        
        # Player aliases
        cursor.execute("SELECT LOWER(alias) as alias, player_id FROM player_aliases")
        for row in cursor.fetchall():
            key = f"{ALIAS_PREFIX}player:{row['alias']}"
            if key not in aliases:
                aliases[key] = set()
            aliases[key].add(row['player_id'])
        
        # League aliases
        cursor.execute("SELECT LOWER(alias) as alias, league_id FROM league_aliases")
        for row in cursor.fetchall():
            key = f"{ALIAS_PREFIX}league:{row['alias']}"
            if key not in aliases:
                aliases[key] = set()
            aliases[key].add(row['league_id'])
        
        # Market aliases
        cursor.execute("SELECT LOWER(alias) as alias, market_id FROM market_aliases")
        for row in cursor.fetchall():
            key = f"{ALIAS_PREFIX}market:{row['alias']}"
            if key not in aliases:
                aliases[key] = set()
            aliases[key].add(row['market_id'])
        
    finally:
        conn.close()
    
    return aliases


def get_all_aliases_from_redis(redis_client) -> Dict[str, Set[str]]:
    """
    Get all aliases from Redis.
    Returns a dict with alias_key -> set of related IDs
    """
    aliases = {}
    
    try:
        # Get all alias keys
        pattern = f"{ALIAS_PREFIX}*"
        keys = redis_client.keys(pattern)
        
        for key in keys:
            value = redis_client.get(key)
            if value:
                try:
                    ids = json.loads(value)
                    if isinstance(ids, list):
                        aliases[key] = set(ids)
                    else:
                        aliases[key] = {ids}
                except json.JSONDecodeError:
                    # Single value, not JSON
                    aliases[key] = {value}
    
    except Exception as e:
        logger.error(f"Error reading from Redis: {e}")
    
    return aliases


def sync_entities():
    """Sync main table entities to Redis"""
    redis_client = get_redis_client()
    
    if not redis_client:
        logger.warning("Cannot connect to Redis. Skipping entity sync.")
        return
    
    try:
        logger.info("Starting entity sync...")
        
        # Get entities from both sources
        db_entities = get_all_entities_from_db()
        redis_entities = get_all_entities_from_redis(redis_client)
        
        # Track changes
        added = 0
        updated = 0
        deleted = 0
        
        # Find entities to add or update
        for key, db_data in db_entities.items():
            redis_data = redis_entities.get(key)
            
            if key not in redis_entities:
                # New entity - add to Redis
                redis_client.set(key, json.dumps(db_data))
                added += 1
            elif db_data != redis_data:
                # Existing entity with different data - update
                redis_client.set(key, json.dumps(db_data))
                updated += 1
        
        # Find entities to delete (in Redis but not in DB)
        for key in redis_entities:
            if key not in db_entities:
                redis_client.delete(key)
                deleted += 1
        
        # Log summary
        total_entities = len(db_entities)
        logger.info(f"Entity sync complete: {total_entities} total, {added} added, {updated} updated, {deleted} deleted")
        
        if added == 0 and updated == 0 and deleted == 0:
            logger.debug("No entity changes detected")
    
    except Exception as e:
        logger.error(f"Entity sync error: {e}", exc_info=True)


def sync_aliases():
    """Sync database aliases to Redis"""
    redis_client = get_redis_client()
    
    if not redis_client:
        logger.warning("Cannot connect to Redis. Skipping alias sync.")
        return
    
    try:
        logger.info("Starting alias sync...")
        
        # Get aliases from both sources
        db_aliases = get_all_aliases_from_db()
        redis_aliases = get_all_aliases_from_redis(redis_client)
        
        # Track changes
        added = 0
        updated = 0
        deleted = 0
        
        # Find aliases to add or update
        for key, db_ids in db_aliases.items():
            redis_ids = redis_aliases.get(key, set())
            
            if key not in redis_aliases:
                # New alias - add to Redis
                redis_client.set(key, json.dumps(list(db_ids)))
                added += 1
            elif db_ids != redis_ids:
                # Existing alias with different IDs - update
                redis_client.set(key, json.dumps(list(db_ids)))
                updated += 1
        
        # Find aliases to delete (in Redis but not in DB)
        for key in redis_aliases:
            if key not in db_aliases:
                redis_client.delete(key)
                deleted += 1
        
        # Log summary
        total_aliases = len(db_aliases)
        logger.info(f"Alias sync complete: {total_aliases} total, {added} added, {updated} updated, {deleted} deleted")
        
        if added == 0 and updated == 0 and deleted == 0:
            logger.debug("No alias changes detected")
    
    except Exception as e:
        logger.error(f"Alias sync error: {e}", exc_info=True)


def sync_all():
    """Main sync function - syncs both entities and aliases"""
    logger.info("=" * 60)
    logger.info("Starting full sync cycle")
    logger.info("=" * 60)
    
    try:
        # Sync entities (teams, players, leagues, markets)
        sync_entities()
        
        # Sync aliases
        sync_aliases()
        
        logger.info("=" * 60)
        logger.info("Full sync cycle complete")
        logger.info("=" * 60)
    except Exception as e:
        logger.error(f"Full sync failed: {e}", exc_info=True)


def clear_all_alias_cache(redis_client):
    """Clear all alias-related cache entries"""
    try:
        pattern = f"{ALIAS_PREFIX}*"
        keys = redis_client.keys(pattern)
        if keys:
            redis_client.delete(*keys)
            logger.info(f"Cleared {len(keys)} alias cache entries")
    except Exception as e:
        logger.error(f"Error clearing alias cache: {e}")


def clear_all_entity_cache(redis_client):
    """Clear all entity-related cache entries"""
    try:
        pattern = f"{ENTITY_PREFIX}*"
        keys = redis_client.keys(pattern)
        if keys:
            redis_client.delete(*keys)
            logger.info(f"Cleared {len(keys)} entity cache entries")
    except Exception as e:
        logger.error(f"Error clearing entity cache: {e}")


def run_continuous_sync():
    """Run sync continuously with interval"""
    logger.info("=" * 60)
    logger.info("Redis Database Sync Service")
    logger.info("=" * 60)
    logger.info(f"Database: {DB_PATH}")
    logger.info(f"Redis: {REDIS_HOST}:{REDIS_PORT}")
    logger.info(f"Sync interval: {SYNC_INTERVAL} seconds")
    logger.info(f"Log level: {LOG_LEVEL}")
    logger.info(f"Log file: {LOG_FILE or 'Console only'}")
    logger.info(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)
    
    # Initial sync
    sync_all()
    
    # Continuous sync loop
    try:
        while True:
            time.sleep(SYNC_INTERVAL)
            sync_all()
    
    except KeyboardInterrupt:
        logger.info("Sync service stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Sync service error: {e}", exc_info=True)
        sys.exit(1)


def run_single_sync():
    """Run a single sync operation"""
    logger.info("Running one-time sync...")
    sync_all()
    logger.info("Sync complete.")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        # Single sync mode
        run_single_sync()
    else:
        # Continuous sync mode
        run_continuous_sync()
