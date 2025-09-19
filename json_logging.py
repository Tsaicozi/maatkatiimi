"""
JSON-structured logging for production use
"""
import json
import logging
import uuid
from datetime import datetime
from typing import Optional, Dict, Any


class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record):
        payload = {
            "level": record.levelname,
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
            "logger": record.name,
            "msg": record.getMessage(),
        }
        
        # Add correlation IDs if present
        if hasattr(record, 'run_id'):
            payload["run_id"] = record.run_id
        if hasattr(record, 'cycle_id'):
            payload["cycle_id"] = record.cycle_id
        if hasattr(record, 'token_symbol'):
            payload["token_symbol"] = record.token_symbol
        if hasattr(record, 'alert_name'):
            payload["alert_name"] = record.alert_name
            
        # Add exception info if present
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
            
        return json.dumps(payload, ensure_ascii=False)


class CorrelationLogger:
    """Logger with correlation ID support"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.run_id: Optional[str] = None
        self.cycle_id: Optional[str] = None
        
    def set_run_id(self, run_id: str):
        """Set run correlation ID"""
        self.run_id = run_id
        
    def set_cycle_id(self, cycle_id: str):
        """Set cycle correlation ID"""
        self.cycle_id = cycle_id
        
    def _log_with_correlation(self, level: int, msg: str, *args, **kwargs):
        """Log with correlation IDs"""
        extra = kwargs.get('extra', {})
        if self.run_id:
            extra['run_id'] = self.run_id
        if self.cycle_id:
            extra['cycle_id'] = self.cycle_id
        kwargs['extra'] = extra
        self.logger.log(level, msg, *args, **kwargs)
        
    def info(self, msg: str, *args, **kwargs):
        self._log_with_correlation(logging.INFO, msg, *args, **kwargs)
        
    def warning(self, msg: str, *args, **kwargs):
        self._log_with_correlation(logging.WARNING, msg, *args, **kwargs)
        
    def error(self, msg: str, *args, **kwargs):
        self._log_with_correlation(logging.ERROR, msg, *args, **kwargs)
        
    def debug(self, msg: str, *args, **kwargs):
        self._log_with_correlation(logging.DEBUG, msg, *args, **kwargs)


def setup_json_logging(level: str = "INFO") -> CorrelationLogger:
    """Setup JSON logging for production"""
    
    # Clear existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    
    # Setup JSON formatter
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, level.upper()))
    
    # Create correlation logger
    return CorrelationLogger("hybrid_bot")


def generate_run_id() -> str:
    """Generate unique run ID"""
    return f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"


def generate_cycle_id() -> str:
    """Generate unique cycle ID"""
    return f"cycle_{datetime.now().strftime('%H%M%S')}_{str(uuid.uuid4())[:8]}"


# Example usage
if __name__ == "__main__":
    # Setup JSON logging
    logger = setup_json_logging("INFO")
    
    # Set correlation IDs
    logger.set_run_id(generate_run_id())
    logger.set_cycle_id(generate_cycle_id())
    
    # Log with correlation
    logger.info("Bot started", extra={"component": "main"})
    logger.warning("API rate limit approaching", extra={"api": "dex_screener"})
    logger.error("RPC connection failed", extra={"endpoint": "solana_rpc"})

