import sqlite3
import json
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)
DB_PATH = Path("data/lcr_history.db")

def init_database():
    """Initialise la base de données"""
    DB_PATH.parent.mkdir(exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS analysis_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            analysis_date TEXT NOT NULL,
            table_name TEXT NOT NULL,
            data_json TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(analysis_date, table_name)
        )
    """)
    
    conn.commit()
    conn.close()
    logger.info("✅ Database initialized")

def save_table_result(analysis_date: str, table_name: str, data: dict):
    """Sauvegarde un résultat de tableau"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO analysis_history (analysis_date, table_name, data_json)
            VALUES (?, ?, ?)
        """, (analysis_date, table_name, json.dumps(data, ensure_ascii=False)))
        
        conn.commit()
        conn.close()
        logger.info(f"💾 Saved {table_name} for {analysis_date}")
    except Exception as e:
        logger.error(f"❌ Error saving {table_name}: {e}")

def get_historical_data(table_name: str, days_back: int = 10):
    """Récupère les N dernières DATES DISTINCTES pour un tableau"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # D'abord, récupérer les N dernières dates distinctes
        cursor.execute("""
            SELECT DISTINCT analysis_date
            FROM analysis_history
            WHERE table_name = ?
            ORDER BY analysis_date DESC
            LIMIT ?
        """, (table_name, days_back))
        
        dates = [row[0] for row in cursor.fetchall()]
        
        if not dates:
            conn.close()
            return []
        
        # Ensuite, récupérer la donnée la plus récente pour chaque date
        placeholders = ','.join('?' * len(dates))
        cursor.execute(f"""
            SELECT analysis_date, data_json
            FROM analysis_history
            WHERE table_name = ? AND analysis_date IN ({placeholders})
            GROUP BY analysis_date
            HAVING created_at = MAX(created_at)
            ORDER BY analysis_date DESC
        """, (table_name, *dates))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [(row[0], json.loads(row[1])) for row in rows]
    except Exception as e:
        logger.error(f"❌ Error retrieving {table_name}: {e}")
        return []