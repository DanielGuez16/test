from typing import Dict, List, Optional
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path

# Base de données utilisateurs simple (en production: vraie BDD)
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

def log_activity(username: str, action: str, details: str = ""):
    """Enregistre une activité utilisateur dans un fichier JSON persistant"""
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "username": username,
        "action": action,
        "details": details
    }
    
    # Charger les logs existants
    logs = []
    if os.path.exists(LOGS_FILE):
        try:
            with open(LOGS_FILE, "r", encoding="utf-8") as f:
                logs = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            # Si le fichier est corrompu ou vide, on repart à zéro
            logs = []
    
    # Ajouter le nouveau log
    logs.append(log_entry)
    
    # Limiter à 1000 logs maximum (pour éviter un fichier trop gros)
    if len(logs) > 1000:
        logs = logs[-1000:]  # Garder les 1000 plus récents
    
    # Sauvegarder dans le fichier
    try:
        # Créer le dossier si nécessaire
        Path(LOGS_FILE).parent.mkdir(exist_ok=True)
        
        with open(LOGS_FILE, "w", encoding="utf-8") as f:
            json.dump(logs, f, indent=2, ensure_ascii=False)
        
        print(f"LOG: {username} - {action} - {details}")
    except Exception as e:
        print(f"ERREUR sauvegarde log: {e}")

def get_logs(limit: int = 100) -> List[Dict]:
    """Récupère les logs d'activité depuis le fichier JSON"""
    if not os.path.exists(LOGS_FILE):
        return []
    
    try:
        with open(LOGS_FILE, "r", encoding="utf-8") as f:
            logs = json.load(f)
        
        # Retourner les derniers logs (limité)
        return logs[-limit:] if logs else []
    
    except (json.JSONDecodeError, FileNotFoundError, Exception) as e:
        print(f"ERREUR lecture logs: {e}")
        return []

def get_logs_stats() -> Dict:
    """Statistiques sur les logs"""
    logs = get_logs(10000)  # Charger beaucoup pour les stats
    
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