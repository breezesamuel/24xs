# Rate Limiting - Token Bucket + Sliding Window Log
import time, threading, hashlib
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Dict, Tuple, Optional
from pathlib import Path

BASE = Path(r"F:/2026/24xs/11_数据资产")
OUT = BASE / "registry_real_verified"
OUT.mkdir(exist_ok=True)

@dataclass
class RateLimitConfig:
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    requests_per_day: int = 10000
    burst_allowance: int = 10  # token bucket burst

class TokenBucket:
    def __init__(self, capacity: int, refill_rate_per_sec: float):
        self.capacity = capacity
        self.tokens = float(capacity)
        self.refill_rate = refill_rate_per_sec
        self.last_refill = time.time()
        self._lock = threading.Lock()
    
    def consume(self, tokens: int = 1) -> bool:
        with self._lock:
            now = time.time()
            elapsed = now - self.last_refill
            self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
            self.last_refill = now
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
    
    def available(self) -> float:
        with self._lock:
            now = time.time()
            elapsed = now - self.last_refill
            return min(self.capacity, self.tokens + elapsed * self.refill_rate)

class SlidingWindowLog:
    def __init__(self, window_seconds: int, max_requests: int):
        self.window = window_seconds
        self.max_requests = max_requests
        self.requests = deque()
        self._lock = threading.Lock()
    
    def record(self) -> bool:
        with self._lock:
            now = time.time()
            cutoff = now - self.window
            while self.requests and self.requests[0] < cutoff:
                self.requests.popleft()
            if len(self.requests) < self.max_requests:
                self.requests.append(now)
                return True
            return False
    
    def current_count(self) -> int:
        with self._lock:
            now = time.time()
            cutoff = now - self.window
            while self.requests and self.requests[0] < cutoff:
                self.requests.popleft()
            return len(self.requests)

class RateLimiter:
    def __init__(self, config: RateLimitConfig = None):
        self.config = config or RateLimitConfig()
        self.buckets: Dict[str, TokenBucket] = {}
        self.windows: Dict[str, Dict[str, SlidingWindowLog]] = defaultdict(dict)
        self._lock = threading.Lock()
        self._cleanup_interval = 300  # 5 minutes
        self._last_cleanup = time.time()
    
    def _get_bucket_key(self, identifier: str, scope: str) -> str:
        return f"{scope}:{identifier}"
    
    def _get_or_create_bucket(self, identifier: str, scope: str, capacity: int, refill_rate: float) -> TokenBucket:
        key = self._get_bucket_key(identifier, scope)
        with self._lock:
            if key not in self.buckets:
                self.buckets[key] = TokenBucket(capacity, refill_rate)
            return self.buckets[key]
    
    def _get_or_create_window(self, identifier: str, scope: str, window_seconds: int, max_requests: int) -> SlidingWindowLog:
        scope_key = self._get_bucket_key(identifier, scope)
        with self._lock:
            if scope_key not in self.windows[scope]:
                self.windows[scope][scope_key] = SlidingWindowLog(window_seconds, max_requests)
            return self.windows[scope][scope_key]
    
    def check_limit(self, identifier: str, cost: int = 1) -> Tuple[bool, Dict]:
        """
        Check if request is allowed.
        Returns (allowed, info_dict)
        """
        # Cleanup old entries periodically
        self._maybe_cleanup()
        
        # Per-minute window (sliding)
        minute_window = self._get_or_create_window(identifier, "minute", 60, self.config.requests_per_minute)
        minute_allowed = minute_window.record()
        minute_remaining = self.config.requests_per_minute - minute_window.current_count()
        
        # Per-hour window
        hour_window = self._get_or_create_window(identifier, "hour", 3600, self.config.requests_per_hour)
        hour_allowed = hour_window.record()
        hour_remaining = self.config.requests_per_hour - hour_window.current_count()
        
        # Per-day window
        day_window = self._get_or_create_window(identifier, "day", 86400, self.config.requests_per_day)
        day_allowed = day_window.record()
        day_remaining = self.config.requests_per_day - day_window.current_count()
        
        # Token bucket for burst
        bucket = self._get_or_create_bucket(identifier, "burst", self.config.burst_allowance, self.config.burst_allowance / 60.0)
        burst_allowed = bucket.consume(cost)
        burst_available = int(bucket.available())
        
        allowed = minute_allowed and hour_allowed and day_allowed and burst_allowed
        
        # If not allowed, rollback the window records (approximate)
        if not allowed:
            # Note: sliding window log doesn\'t support easy rollback
            # In production, use Redis Lua script for atomic check-and-record
            pass
        
        info = {
            "allowed": allowed,
            "minute": {"limit": self.config.requests_per_minute, "remaining": max(0, minute_remaining), "reset_in": 60},
            "hour": {"limit": self.config.requests_per_hour, "remaining": max(0, hour_remaining), "reset_in": 3600},
            "day": {"limit": self.config.requests_per_day, "remaining": max(0, day_remaining), "reset_in": 86400},
            "burst": {"limit": self.config.burst_allowance, "available": burst_available}
        }
        
        return allowed, info
    
    def _maybe_cleanup(self):
        now = time.time()
        if now - self._last_cleanup > self._cleanup_interval:
            with self._lock:
                cutoff = now - 86400  # keep 24h
                # Clean sliding windows
                for scope in list(self.windows.keys()):
                    for key in list(self.windows[scope].keys()):
                        window = self.windows[scope][key]
                        with window._lock:
                            while window.requests and window.requests[0] < cutoff:
                                window.requests.popleft()
                            if not window.requests:
                                del self.windows[scope][key]
                # Clean token buckets (keep all, they are small)
            self._last_cleanup = now
    
    def reset(self, identifier: str):
        with self._lock:
            for scope in ["minute", "hour", "day", "burst"]:
                key = self._get_bucket_key(identifier, scope)
                if scope in self.windows and key in self.windows[scope]:
                    del self.windows[scope][key]
                if key in self.buckets:
                    del self.buckets[key]

# Tier-based configs
TIER_CONFIGS = {
    "starter": RateLimitConfig(requests_per_minute=30, requests_per_hour=500, requests_per_day=5000, burst_allowance=5),
    "professional": RateLimitConfig(requests_per_minute=60, requests_per_hour=2000, requests_per_day=20000, burst_allowance=10),
    "enterprise": RateLimitConfig(requests_per_minute=200, requests_per_hour=10000, requests_per_day=100000, burst_allowance=50),
    "admin": RateLimitConfig(requests_per_minute=1000, requests_per_hour=50000, requests_per_day=500000, burst_allowance=200)
}

# Global limiter instance
_global_limiter = RateLimiter()

def get_limiter(tier: str = "professional") -> RateLimiter:
    return RateLimiter(TIER_CONFIGS.get(tier, TIER_CONFIGS["professional"]))

def check_rate_limit(identifier: str, tier: str = "professional", cost: int = 1) -> Tuple[bool, Dict]:
    limiter = get_limiter(tier)
    return limiter.check_limit(identifier, cost)

# Middleware helper for CF Pages Functions
def rate_limit_middleware(tier_header: str = "x-customer-tier", id_header: str = "x-customer-id"):
    def middleware(request):
        customer_id = request.headers.get(id_header)
        tier = request.headers.get(tier_header, "professional")
        if not customer_id:
            return {"ok": False, "error": "missing_customer_id"}, 400
        
        allowed, info = check_rate_limit(customer_id, tier)
        
        # Add rate limit headers
        headers = {
            "X-RateLimit-Limit-Minute": str(info["minute"]["limit"]),
            "X-RateLimit-Remaining-Minute": str(info["minute"]["remaining"]),
            "X-RateLimit-Limit-Hour": str(info["hour"]["limit"]),
            "X-RateLimit-Remaining-Hour": str(info["hour"]["remaining"]),
            "X-RateLimit-Limit-Day": str(info["day"]["limit"]),
            "X-RateLimit-Remaining-Day": str(info["day"]["remaining"]),
            "X-RateLimit-Burst-Available": str(info["burst"]["available"])
        }
        
        if not allowed:
            return {"ok": False, "error": "rate_limit_exceeded", "retry_after": info["minute"]["reset_in"]}, 429, headers
        
        return None, 200, headers  # None means continue
    
    return middleware

print("Rate limiter module ready")
