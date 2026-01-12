"""
Rate limiting utility with exponential backoff and retry logic.
Handles rate limit errors gracefully across multiple APIs.
"""
import time
import random
import logging
from typing import Callable, Any, Optional
from functools import wraps

logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter with exponential backoff for API calls."""
    
    def __init__(self, base_delay: float = 1.0, max_delay: float = 60.0, 
                 backoff_factor: float = 2.0, jitter: bool = True):
        """
        Initialize rate limiter.
        
        Args:
            base_delay: Base delay between requests in seconds
            max_delay: Maximum delay between requests in seconds
            backoff_factor: Multiplier for exponential backoff
            jitter: Add random jitter to avoid thundering herd
        """
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter
        self.last_request_time = 0
        self.consecutive_errors = 0
    
    def wait(self):
        """Wait for the appropriate delay before next request."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        # Calculate delay (increases with consecutive errors)
        delay = self.base_delay * (self.backoff_factor ** self.consecutive_errors)
        delay = min(delay, self.max_delay)
        
        # Add jitter to avoid synchronized requests
        if self.jitter:
            jitter_amount = delay * 0.1 * random.random()  # 0-10% jitter
            delay += jitter_amount
        
        # Wait if needed
        if time_since_last < delay:
            sleep_time = delay - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def record_success(self):
        """Record a successful request (reset error counter)."""
        self.consecutive_errors = 0
    
    def record_error(self):
        """Record an error (increase backoff)."""
        self.consecutive_errors += 1
        logger.warning(f"Rate limit error detected. Consecutive errors: {self.consecutive_errors}")
    
    def reset(self):
        """Reset error counter."""
        self.consecutive_errors = 0


def with_retry(max_retries: int = 3, base_delay: float = 1.0, 
                backoff_factor: float = 2.0, retry_on: tuple = (429, 500, 502, 503, 504)):
    """
    Decorator to retry function calls with exponential backoff on rate limit errors.
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay before retry in seconds
        backoff_factor: Multiplier for exponential backoff
        retry_on: HTTP status codes that should trigger retry
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    # Check if it's a rate limit error
                    should_retry = False
                    if hasattr(e, 'response') and hasattr(e.response, 'status_code'):
                        status_code = e.response.status_code
                        if status_code in retry_on:
                            should_retry = True
                            logger.warning(f"Rate limit error {status_code} on attempt {attempt + 1}/{max_retries + 1}")
                    elif "rate limit" in str(e).lower() or "429" in str(e):
                        should_retry = True
                        logger.warning(f"Rate limit error detected on attempt {attempt + 1}/{max_retries + 1}")
                    
                    if should_retry and attempt < max_retries:
                        # Exponential backoff with jitter
                        delay = base_delay * (backoff_factor ** attempt)
                        jitter = delay * 0.1 * random.random()
                        sleep_time = delay + jitter
                        logger.info(f"Waiting {sleep_time:.2f} seconds before retry...")
                        time.sleep(sleep_time)
                        continue
                    else:
                        # Don't retry or max retries reached
                        break
            
            # If we get here, all retries failed
            logger.error(f"Function {func.__name__} failed after {max_retries + 1} attempts")
            raise last_exception
        
        return wrapper
    return decorator



