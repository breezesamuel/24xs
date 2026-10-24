# Webhook delivery with exponential backoff, dead letter queue, idempotency
import json, hashlib, time, uuid, sqlite3, threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum

BASE = Path(r"F:/2026/24xs/11_数据资产")
OUT = BASE / "registry_real_verified"
OUT.mkdir(exist_ok=True)

class WebhookStatus(Enum):
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"

@dataclass
class WebhookEvent:
    event_id: str
    event_type: str
    payload: Dict
    target_url: str
    headers: Dict[str, str]
    created_at: str
    attempts: int = 0
    max_attempts: int = 5
    status: str = WebhookStatus.PENDING.value
    last_attempt_at: Optional[str] = None
    last_error: Optional[str] = None
    next_retry_at: Optional[str] = None
    delivered_at: Optional[str] = None

class WebhookQueue:
    def __init__(self, db_path: Path = None):
        self.db_path = db_path or (OUT / "webhook_queue.db")
        self._init_db()
        self._lock = threading.Lock()
        self._running = False
        self._worker_thread = None
    
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS webhook_events (
                    event_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    target_url TEXT NOT NULL,
                    headers TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    attempts INTEGER DEFAULT 0,
                    max_attempts INTEGER DEFAULT 5,
                    status TEXT DEFAULT 'pending',
                    last_attempt_at TEXT,
                    last_error TEXT,
                    next_retry_at TEXT,
                    delivered_at TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_status_next_retry ON webhook_events(status, next_retry_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_event_type ON webhook_events(event_type)")
            conn.commit()
    
    def enqueue(self, event_type: str, payload: Dict, target_url: str, headers: Dict = None, max_attempts: int = 5) -> str:
        event_id = f"evt_{uuid.uuid4().hex[:16]}"
        now = datetime.utcnow().isoformat() + "Z"
        event = WebhookEvent(
            event_id=event_id,
            event_type=event_type,
            payload=payload,
            target_url=target_url,
            headers=headers or {"Content-Type": "application/json"},
            created_at=now,
            max_attempts=max_attempts,
            next_retry_at=now
        )
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO webhook_events (event_id, event_type, payload, target_url, headers, created_at, attempts, max_attempts, status, next_retry_at)
                    VALUES (?, ?, ?, ?, ?, ?, 0, ?, 'pending', ?)
                """, (event_id, event_type, json.dumps(payload, ensure_ascii=False), target_url, json.dumps(headers or {}), now, max_attempts, now))
                conn.commit()
        return event_id
    
    def _calculate_backoff(self, attempt: int) -> int:
        """Exponential backoff: 1m, 5m, 15m, 1h, 6h"""
        delays = [60, 300, 900, 3600, 21600]
        return delays[min(attempt, len(delays) - 1)]
    
    def _deliver(self, event: WebhookEvent) -> tuple[bool, Optional[str]]:
        import urllib.request, urllib.error
        try:
            data = json.dumps(event.payload, ensure_ascii=False).encode("utf-8")
            req = urllib.request.Request(event.target_url, data=data, headers=event.headers, method="POST")
            with urllib.request.urlopen(req, timeout=30) as resp:
                if 200 <= resp.status < 300:
                    return True, None
                else:
                    return False, f"HTTP {resp.status}: {resp.read().decode()}"
        except urllib.error.HTTPError as e:
            return False, f"HTTP {e.code}: {e.read().decode()}"
        except Exception as e:
            return False, str(e)
    
    def process_pending(self, batch_size: int = 50) -> int:
        now = datetime.utcnow().isoformat() + "Z"
        processed = 0
        
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM webhook_events 
                    WHERE status IN ('pending', 'failed') 
                    AND (next_retry_at IS NULL OR next_retry_at <= ?)
                    ORDER BY created_at ASC
                    LIMIT ?
                """, (now, batch_size))
                events = cursor.fetchall()
                
                for row in events:
                    event = WebhookEvent(
                        event_id=row["event_id"],
                        event_type=row["event_type"],
                        payload=json.loads(row["payload"]),
                        target_url=row["target_url"],
                        headers=json.loads(row["headers"]),
                        created_at=row["created_at"],
                        attempts=row["attempts"],
                        max_attempts=row["max_attempts"],
                        status=row["status"],
                        last_attempt_at=row["last_attempt_at"],
                        last_error=row["last_error"],
                        next_retry_at=row["next_retry_at"],
                        delivered_at=row["delivered_at"]
                    )
                    
                    success, error = self._deliver(event)
                    event.attempts += 1
                    event.last_attempt_at = datetime.utcnow().isoformat() + "Z"
                    
                    if success:
                        event.status = WebhookStatus.DELIVERED.value
                        event.delivered_at = datetime.utcnow().isoformat() + "Z"
                        event.next_retry_at = None
                    elif event.attempts >= event.max_attempts:
                        event.status = WebhookStatus.DEAD_LETTER.value
                        event.next_retry_at = None
                    else:
                        event.status = WebhookStatus.FAILED.value
                        event.last_error = error
                        delay = self._calculate_backoff(event.attempts)
                        event.next_retry_at = (datetime.utcnow() + timedelta(seconds=delay)).isoformat() + "Z"
                    
                    conn.execute("""
                        UPDATE webhook_events SET
                            attempts = ?, status = ?, last_attempt_at = ?, last_error = ?,
                            next_retry_at = ?, delivered_at = ?
                        WHERE event_id = ?
                    """, (event.attempts, event.status, event.last_attempt_at, event.last_error,
                          event.next_retry_at, event.delivered_at, event.event_id))
                    conn.commit()
                    processed += 1
        
        return processed
    
    def get_dead_letters(self, limit: int = 100) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM webhook_events WHERE status = 'dead_letter' ORDER BY created_at DESC LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]
    
    def retry_dead_letter(self, event_id: str) -> bool:
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT status FROM webhook_events WHERE event_id = ?", (event_id,))
                row = cursor.fetchone()
                if not row or row[0] != WebhookStatus.DEAD_LETTER.value:
                    return False
                conn.execute("""
                    UPDATE webhook_events SET status = 'pending', attempts = 0, last_error = NULL,
                        next_retry_at = ?, last_attempt_at = NULL
                    WHERE event_id = ?
                """, (datetime.utcnow().isoformat() + "Z", event_id))
                conn.commit()
                return True
    
    def get_stats(self) -> Dict:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT status, COUNT(*) as count FROM webhook_events GROUP BY status
            """)
            stats = {row[0]: row[1] for row in cursor.fetchall()}
            return stats
    
    def start_worker(self, interval: int = 30):
        """Start background worker thread"""
        if self._running:
            return
        self._running = True
        def worker():
            while self._running:
                try:
                    self.process_pending()
                except Exception:
                    pass
                time.sleep(interval)
        self._worker_thread = threading.Thread(target=worker, daemon=True)
        self._worker_thread.start()
    
    def stop_worker(self):
        self._running = False
        if self._worker_thread:
            self._worker_thread.join(timeout=5)

# Global instance
webhook_queue = WebhookQueue()

# Convenience functions
def enqueue_webhook(event_type: str, payload: Dict, target_url: str, headers: Dict = None, max_attempts: int = 5) -> str:
    return webhook_queue.enqueue(event_type, payload, target_url, headers, max_attempts)

def start_webhook_worker(interval: int = 30):
    webhook_queue.start_worker(interval)

def stop_webhook_worker():
    webhook_queue.stop_worker()

def get_webhook_stats() -> Dict:
    return webhook_queue.get_stats()

# Example usage for MoltsPay webhook
def enqueue_moltspay_delivery(purchase_id: str, asset_id: str, download_url: str, expires_at: str, buyer_email: str):
    """Queue delivery notification email webhook"""
    payload = {
        "type": "delivery_ready",
        "purchase_id": purchase_id,
        "asset_id": asset_id,
        "download_url": download_url,
        "expires_at": expires_at,
        "buyer_email": buyer_email
    }
    # Target could be an email service webhook or internal handler
    return enqueue_webhook("delivery_ready", payload, "https://api.emailservice.com/webhook", max_attempts=3)

print("Webhook queue module ready")
