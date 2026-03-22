import logging
import json
import os
from datetime import datetime, timezone

class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "module": record.name,
            "message": record.getMessage(),
        }
        
        if hasattr(record, "extra"):
            log_data["extra"] = record.extra
            
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)

def get_logger(module_name: str) -> logging.Logger:
    """
    Retorna un logger JSON estructurado estandarizado.
    Lee el nivel desde la variable de entorno LOG_LEVEL (por defecto INFO).
    """
    logger = logging.getLogger(module_name)
    
    # Evita duplicar handlers si get_logger se llama varias veces para el mismo módulo
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
        
        # Obtener nivel de log de las variables de entorno, por defecto INFO
        log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
        log_level = getattr(logging, log_level_str, logging.INFO)
        logger.setLevel(log_level)
        
        # Evita propagar al logger root para no tener logs duplicados
        logger.propagate = False
        
    return logger
