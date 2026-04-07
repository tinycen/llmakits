"""共享的重试状态容器。"""

from typing import Any, Dict

_GLOBAL_RETRY_STATE: Dict[str, Any] = {
    "force_base64_domains": set(),
    "domain_failure_stats": {},
    "last_failed_domain": "",
}


def get_retry_state() -> Dict[str, Any]:
    """返回重试策略共享状态（可变引用）。"""
    return _GLOBAL_RETRY_STATE


def get_retry_state_snapshot() -> Dict[str, Any]:
    """返回重试状态快照，避免外部直接修改。"""
    retry_state = _GLOBAL_RETRY_STATE
    domain_stats = retry_state["domain_failure_stats"]
    return {
        "force_base64_domains": sorted(list(retry_state["force_base64_domains"])),
        "domain_failure_stats": {domain: stats.copy() for domain, stats in domain_stats.items()},
        "last_failed_domain": retry_state["last_failed_domain"],
    }
