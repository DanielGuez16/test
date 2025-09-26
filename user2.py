from typing import Dict, List, Optional
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path

from sharepoint_connector import SharePointClient
import pandas as pd
from io import BytesIO


# Configuration SharePoint pour les logs
SHAREPOINT_LOGS_PATH = "ALM_Metrics/logs/activity_logs.xlsx"  # Ajustez selon votre structure



# Base de donnÃ©es utilisateurs simple (en production: vraie BDD)
USERS_DB = {
    "daniel.guez@natixis.com": {
        "username": "daniel.guez@natixis.com",
        "password_hash": hashlib.sha256("admin123".encode()).hexdigest(),
        "full_name": "Daniel GUEZ",
        "role": "admin",
        "created_at": "2024-01-01T00:00:00"
    },
    "franck.pokou-ext@natixis.com": {
        "username": "franck.pokou-ext@natixis.com",
        "password_hash": hashlib.sha256("admin123".encode()).hexdigest(),
        "full_name": "Franck POKOU",
        "role": "admin", 
        "created_at": "2024-01-01T00:00:00"
    },
    "juvenalamos.ido@natixis.com": {
        "username": "juvenalamos.ido@natixis.com",
        "password_hash": hashlib.sha256("admin123".encode()).hexdigest(),
        "full_name": "Juvenal Amos IDO",
        "role": "admin", 
        "created_at": "2024-01-01T00:00:00"
    },
    "user.alm@natixis.com": {
        "username": "user.alm@natixis.com",
        "password_hash": hashlib.sha256("user123".encode()).hexdigest(),
        "full_name": "User ALM",
        "role": "user",
        "created_at": "2024-01-01T00:00:00"
    }
}

# Fichier de logs persistant
LOGS_FILE = "activity_logs.json"

def authenticate_user(username: str, password: str) -> Optional[Dict]:
    """Authentifie un utilisateur"""
    user = USERS_DB.get(username)
    if user:
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        if user["password_hash"] == password_hash:
            return user
    return None

def get_sharepoint_client():
    """Initialise le client SharePoint"""
    return SharePointClient()

def log_activity(username: str, action: str, details: str = ""):
    """Enregistre une activité utilisateur dans SharePoint Excel"""
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "username": username,
        "action": action,
        "details": details
    }
    
    try:
        client = get_sharepoint_client()
        
        # Tenter de lire le fichier existant
        try:
            binary_content = client.read_binary_file(SHAREPOINT_LOGS_PATH)
            existing_data = client.read_excel_file_as_dict(binary_content)
            logs_df = pd.DataFrame(existing_data)
        except:
            # Si le fichier n'existe pas, créer un DataFrame vide
            logs_df = pd.DataFrame(columns=["timestamp", "username", "action", "details"])
        
        # Ajouter le nouveau log
        new_log_df = pd.DataFrame([log_entry])
        logs_df = pd.concat([logs_df, new_log_df], ignore_index=True)
        
        # Limiter à 1000 logs maximum
        if len(logs_df) > 1000:
            logs_df = logs_df.tail(1000)
        
        # Sauvegarder dans SharePoint
        client.save_dataframe_in_sharepoint(logs_df, SHAREPOINT_LOGS_PATH, False)
        
        print(f"LOG: {username} - {action} - {details}")
        
    except Exception as e:
        print(f"ERREUR sauvegarde log SharePoint: {e}")
        # Fallback vers le fichier local en cas d'erreur SharePoint
        _log_activity_fallback(username, action, details)

def _log_activity_fallback(username: str, action: str, details: str = ""):
    """Sauvegarde locale de secours en cas d'erreur SharePoint"""
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "username": username,
        "action": action,
        "details": details
    }
    
    logs = []
    if os.path.exists(LOGS_FILE):
        try:
            with open(LOGS_FILE, "r", encoding="utf-8") as f:
                logs = json.load(f)
        except:
            logs = []
    
    logs.append(log_entry)
    if len(logs) > 1000:
        logs = logs[-1000:]
    
    try:
        with open(LOGS_FILE, "w", encoding="utf-8") as f:
            json.dump(logs, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"ERREUR sauvegarde fallback: {e}")

def get_logs(limit: int = 100) -> List[Dict]:
    """Récupère les logs depuis SharePoint"""
    try:
        client = get_sharepoint_client()
        binary_content = client.read_binary_file(SHAREPOINT_LOGS_PATH)
        logs_data = client.read_excel_file_as_dict(binary_content)
        
        # Convertir en DataFrame pour manipulation
        logs_df = pd.DataFrame(logs_data)
        
        # Trier par timestamp et limiter
        if not logs_df.empty and 'timestamp' in logs_df.columns:
            logs_df = logs_df.sort_values('timestamp', ascending=False)
            limited_logs = logs_df.head(limit)
            return limited_logs.to_dict('records')
        
        return []
        
    except Exception as e:
        print(f"ERREUR lecture logs SharePoint: {e}")
        # Fallback vers fichier local
        return _get_logs_fallback(limit)

def _get_logs_fallback(limit: int = 100) -> List[Dict]:
    """Lecture locale de secours"""
    if not os.path.exists(LOGS_FILE):
        return []
    
    try:
        with open(LOGS_FILE, "r", encoding="utf-8") as f:
            logs = json.load(f)
        return logs[-limit:] if logs else []
    except Exception as e:
        print(f"ERREUR lecture logs fallback: {e}")
        return []

def get_logs_stats() -> Dict:
    """Statistiques sur les logs depuis SharePoint"""
    try:
        client = get_sharepoint_client()
        binary_content = client.read_binary_file(SHAREPOINT_LOGS_PATH)
        logs_data = client.read_excel_file_as_dict(binary_content)
        
        if not logs_data:
            return {"total": 0, "users": 0, "actions": 0}
        
        logs_df = pd.DataFrame(logs_data)
        
        users_count = logs_df['username'].nunique() if 'username' in logs_df.columns else 0
        actions_count = logs_df['action'].nunique() if 'action' in logs_df.columns else 0
        
        first_log = None
        last_log = None
        
        if 'timestamp' in logs_df.columns and not logs_df.empty:
            sorted_logs = logs_df.sort_values('timestamp')
            first_log = sorted_logs.iloc[0]['timestamp']
            last_log = sorted_logs.iloc[-1]['timestamp']
        
        return {
            "total": len(logs_df),
            "users": users_count,
            "actions": actions_count,
            "first_log": first_log,
            "last_log": last_log
        }
        
    except Exception as e:
        print(f"ERREUR stats SharePoint: {e}")
        # Fallback vers fichier local
        return _get_logs_stats_fallback()

def _get_logs_stats_fallback() -> Dict:
    """Stats locales de secours"""
    logs = _get_logs_fallback(10000)
    
    if not logs:
        return {"total": 0, "users": 0, "actions": 0}
    
    users = set(log.get("username", "") for log in logs)
    actions = set(log.get("action", "") for log in logs)
    
    return {
        "total": len(logs),
        "users": len(users),
        "actions": len(actions),
        "first_log": logs[0].get("timestamp") if logs else None,
        "last_log": logs[-1].get("timestamp") if logs else None
    }