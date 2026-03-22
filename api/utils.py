from typing import Any, Dict
from datetime import datetime, timezone

def success_response(data: Any, total: int = None) -> Dict[str, Any]:
    res = {
        "data": data,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    if total is not None:
        res["total"] = total
    return res

def error_response(msg: str, code: str) -> Dict[str, str]:
    return {
        "error": msg,
        "code": code,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
