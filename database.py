"""Database service for managing lost and found items"""
import sqlite3
from typing import List, Dict, Optional

DB_FILE = "lostandfound.db"

def init_database():
    """Initialize the database and create tables if they don't exist"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Create found_items table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS found_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_type TEXT NOT NULL,
            color TEXT,
            brand TEXT,
            features TEXT,
            description TEXT,
            image_path TEXT,
            timestamp TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create lost_items table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lost_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_type TEXT NOT NULL,
            color TEXT,
            brand TEXT,
            features TEXT,
            description TEXT,
            image_path TEXT,
            timestamp TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def add_found_item(item_info: Dict) -> int:
    """Add a found item to the database"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO found_items (item_type, color, brand, features, description, image_path, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        item_info.get('item_type'),
        item_info.get('color'),
        item_info.get('brand'),
        item_info.get('features'),
        item_info.get('description'),
        item_info.get('image_path'),
        item_info.get('timestamp')
    ))
    
    item_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return item_id

def add_lost_item(item_info: Dict) -> int:
    """Add a lost item to the database"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO lost_items (item_type, color, brand, features, description, image_path, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        item_info.get('item_type'),
        item_info.get('color'),
        item_info.get('brand'),
        item_info.get('features'),
        item_info.get('description'),
        item_info.get('image_path'),
        item_info.get('timestamp')
    ))
    
    item_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return item_id

def get_all_found_items() -> List[Dict]:
    """Get all found items from the database"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM found_items ORDER BY created_at DESC')
    rows = cursor.fetchall()
    
    items = [dict(row) for row in rows]
    conn.close()
    return items

def get_all_lost_items() -> List[Dict]:
    """Get all lost items from the database"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM lost_items ORDER BY created_at DESC')
    rows = cursor.fetchall()
    
    items = [dict(row) for row in rows]
    conn.close()
    return items

def search_found_items(item_type: str = None, color: str = None) -> List[Dict]:
    """Search found items by type and/or color"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    query = 'SELECT * FROM found_items WHERE 1=1'
    params = []
    
    if item_type:
        query += ' AND item_type LIKE ?'
        params.append(f'%{item_type}%')
    
    if color:
        query += ' AND color LIKE ?'
        params.append(f'%{color}%')
    
    query += ' ORDER BY created_at DESC'
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    items = [dict(row) for row in rows]
    conn.close()
    return items

def get_database_stats() -> Dict:
    """Get statistics about the database"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM found_items')
    found_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM lost_items')
    lost_count = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        'found_items': found_count,
        'lost_items': lost_count,
        'total_items': found_count + lost_count
    }
