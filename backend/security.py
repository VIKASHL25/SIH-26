import os
import time
import logging
from typing import Dict, Tuple, Optional, Any
from fastapi import Header, HTTPException, Request
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SecurityModule")

# Shared Internal API Key for Microservices (Loaded from .env)
INTERNAL_SERVICE_KEY = os.getenv("INTERNAL_SERVICE_KEY", "d8f4e2a1b9c8d7e6f5a4b3c2d1e0f9a8")

def verify_internal_key(x_internal_key: Optional[str] = Header(None, alias="X-Internal-Key")):
    """
    Validates internal service-to-service authentication header (X-Internal-Key).
    
    Security Note: Shared secret header validation for microservices inter-communication.
    Mutual TLS (mTLS) with client certificates is the planned production upgrade path.
    """
    if not x_internal_key or x_internal_key != INTERNAL_SERVICE_KEY:
        logger.warning(f"[SECURITY AUDIT] Unauthorized inter-service request attempt. Key provided: '{x_internal_key}'")
        raise HTTPException(
            status_code=401,
            detail="Unauthorized: Invalid or missing internal service API key (X-Internal-Key)."
        )
    return True

# ---------------------------------------------------------------------------
# Rate Limiting (In-Memory Sliding Window per IP)
# ---------------------------------------------------------------------------

class SlidingWindowRateLimiter:
    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        # Storage: client_ip -> list of timestamps
        self.requests: Dict[str, list] = {}

    def is_rate_limited(self, client_ip: str, endpoint_path: str = "") -> bool:
        now = time.time()
        cutoff = now - self.window_seconds

        if client_ip not in self.requests:
            self.requests[client_ip] = []

        # Filter out timestamps older than the window
        timestamps = [ts for ts in self.requests[client_ip] if ts > cutoff]
        self.requests[client_ip] = timestamps

        if len(timestamps) >= self.max_requests:
            logger.warning(
                f"[SECURITY AUDIT] Rate limit exceeded: Source IP={client_ip}, Endpoint={endpoint_path}, "
                f"Count={len(timestamps)}/{self.max_requests} in {self.window_seconds}s."
            )
            return True

        self.requests[client_ip].append(now)
        return False

# Global instance for Gateway endpoints
ip_rate_limiter = SlidingWindowRateLimiter(max_requests=60, window_seconds=60)

