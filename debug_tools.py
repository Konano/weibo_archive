import base64
import json
import traceback
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any, Callable, TypeVar

import requests

F = TypeVar("F", bound=Callable[..., Any])

DEBUG_DIR = Path("debug")

_LAST_REQUEST: dict[str, Any] | None = None
_DID_DUMP = False


def _sanitize_request_kwargs(request_kwargs: dict[str, Any]) -> dict[str, Any]:
    sanitized = dict(request_kwargs)
    if "headers" in sanitized:
        if "cookie" in sanitized["headers"]:
            sanitized["headers"]["cookie"] = "<omitted>"
    return sanitized


def _safe_value(value: Any, limit: int = 4096) -> Any:
    if isinstance(value, bytes):
        return {
            "type": "bytes",
            "size": len(value),
            "preview_b64": base64.b64encode(value[:limit]).decode("ascii"),
            "truncated": len(value) > limit,
        }
    if isinstance(value, dict):
        return {str(key): _safe_value(item, limit) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_safe_value(item, limit) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return repr(value)


def _response_body_payload(response: requests.Response) -> dict[str, Any]:
    content_type = response.headers.get("content-type", "")
    if "json" in content_type or content_type.startswith("text/"):
        return {
            "kind": "text",
            "size": len(response.text),
            "content": response.text,
        }

    content = response.content
    limit = 256 * 1024
    return {
        "kind": "binary",
        "size": len(content),
        "preview_b64": base64.b64encode(content[:limit]).decode("ascii"),
        "truncated": len(content) > limit,
    }


def record_request(
    method: str,
    url: str,
    *,
    request_kwargs: dict[str, Any] | None = None,
    response: requests.Response | None = None,
    error: Exception | None = None,
) -> None:
    global _LAST_REQUEST

    payload: dict[str, Any] = {
        "method": method,
        "url": url,
        "request_kwargs": _safe_value(_sanitize_request_kwargs(request_kwargs or {})),
        "error": repr(error) if error is not None else None,
    }
    if response is not None:
        payload["response"] = {
            "status_code": response.status_code,
            "url": response.url,
            "reason": response.reason,
            "body": _response_body_payload(response),
        }
    _LAST_REQUEST = payload


def http_get(url: str, **kwargs: Any) -> requests.Response:
    try:
        response = requests.get(url, **kwargs)
    except Exception as exc:
        record_request("GET", url, request_kwargs=kwargs, error=exc)
        raise

    record_request("GET", url, request_kwargs=kwargs, response=response)
    return response


def dump_debug_info(func_name: str, exc: Exception, args: tuple[Any, ...], kwargs: dict[str, Any]) -> Path | None:
    global _DID_DUMP

    if _DID_DUMP:
        return None

    _DID_DUMP = True
    DEBUG_DIR.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dump_path = DEBUG_DIR / f"{timestamp}_{func_name}.json"
    payload = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "function": func_name,
        "exception": {
            "type": type(exc).__name__,
            "message": str(exc),
        },
        "args": _safe_value(args),
        "kwargs": _safe_value(kwargs),
        "traceback": traceback.format_exc(),
        "last_request": _LAST_REQUEST,
    }
    dump_path.write_text(json.dumps(
        payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[!] Debug info written to {dump_path}")
    print("[!] 请把 debug 文件和 traceback 一起反馈给维护者。")
    return dump_path


def debug_on_exception(func: F) -> F:
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any):
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            dump_debug_info(func.__name__, exc, args, kwargs)
            raise

    return wrapper  # type: ignore[return-value]
