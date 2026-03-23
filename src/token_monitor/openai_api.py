from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
import socket
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from .config import AppConfig


class OpenAIMonitorError(RuntimeError):
    """Raised when the upstream usage endpoint fails."""


@dataclass
class UsageSnapshot:
    source_label: str
    plan_name: str
    period_name: str
    unit: str
    is_valid: bool
    budget_usd: float
    remaining_budget_usd: float
    period_cost_usd: float
    overall_cost_usd: float
    usage_ratio: float
    request_count: int
    overall_request_count: int
    input_tokens: int
    output_tokens: int
    cached_tokens: int
    total_tokens: int
    overall_total_tokens: int
    rpm: int
    tpm: int
    average_duration_ms: float
    period_start: datetime
    period_end: datetime
    expires_at: datetime | None


def _month_range_utc() -> tuple[int, int, datetime, datetime]:
    now = datetime.now(UTC)
    start = datetime(now.year, now.month, 1, tzinfo=UTC)
    return int(start.timestamp()), int(now.timestamp()), start, now


def _request_json(
    base_url: str,
    path: str,
    api_key: str,
    organization_id: str = "",
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    endpoint = f"{base_url}/v1{path}"
    if params:
        endpoint = f"{endpoint}?{urlencode(params, doseq=True)}"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "token-monitor/1.0 (+https://github.com/ArrynBi/Token-monitor)",
        "Accept": "application/json",
    }
    if organization_id:
        headers["OpenAI-Organization"] = organization_id

    request = Request(endpoint, headers=headers, method="GET")
    last_error: Exception | None = None
    for attempt in range(2):
        try:
            with urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            if exc.code == 404:
                raise OpenAIMonitorError(f"{endpoint} 不存在或当前服务不支持该接口。") from exc
            raise OpenAIMonitorError(f"请求 {endpoint} 失败，HTTP {exc.code}: {body}") from exc
        except (TimeoutError, socket.timeout, URLError) as exc:
            last_error = exc
            if attempt == 0:
                time.sleep(0.6)
                continue
            if isinstance(exc, URLError):
                raise OpenAIMonitorError(f"无法连接 {endpoint}: {exc.reason}") from exc
            raise OpenAIMonitorError(f"请求 {endpoint} 超时。") from exc

    raise OpenAIMonitorError(f"请求 {endpoint} 失败: {last_error}")


def _as_float(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    return float(value)


def _as_int(value: Any) -> int:
    if value in (None, ""):
        return 0
    return int(value)


def _parse_iso_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def _host_label(base_url: str) -> str:
    parsed = urlparse(base_url)
    return parsed.netloc or base_url


def _sum_usage(page: dict[str, Any]) -> tuple[int, int, int, int, int]:
    request_count = 0
    input_tokens = 0
    output_tokens = 0
    cached_tokens = 0
    total_tokens = 0

    for bucket in page.get("data", []):
        for result in bucket.get("results", []):
            request_count += _as_int(result.get("num_model_requests") or result.get("num_requests"))
            input_tokens += _as_int(result.get("input_tokens"))
            output_tokens += _as_int(result.get("output_tokens"))
            cached_tokens += _as_int(result.get("input_cached_tokens"))
            total_tokens += _as_int(result.get("input_tokens")) + _as_int(result.get("output_tokens"))

    return request_count, input_tokens, output_tokens, cached_tokens, total_tokens


def _sum_costs(page: dict[str, Any]) -> float:
    total_cost = 0.0
    for bucket in page.get("data", []):
        for result in bucket.get("results", []):
            amount = result.get("amount") or {}
            total_cost += _as_float(amount.get("value"))
    return total_cost


def _fetch_gateway_usage(config: AppConfig) -> UsageSnapshot:
    page = _request_json(config.base_url, "/usage", config.api_key)

    is_valid = bool(page.get("isValid", True))
    if not is_valid:
        raise OpenAIMonitorError("上游返回 isValid=false，这个 API Key 当前不可用。")

    usage = page.get("usage") or {}
    today = usage.get("today") or {}
    total = usage.get("total") or {}
    subscription = page.get("subscription") or {}

    daily_limit = _as_float(subscription.get("daily_limit_usd"))
    weekly_limit = _as_float(subscription.get("weekly_limit_usd"))
    monthly_limit = _as_float(subscription.get("monthly_limit_usd"))

    daily_usage = _as_float(subscription.get("daily_usage_usd")) or _as_float(today.get("actual_cost") or today.get("cost"))
    weekly_usage = _as_float(subscription.get("weekly_usage_usd"))
    monthly_usage = _as_float(subscription.get("monthly_usage_usd"))

    remaining = _as_float(page.get("remaining", page.get("balance")))

    period_name = "今天"
    budget_usd = daily_limit
    period_cost_usd = daily_usage

    if monthly_limit > 0:
        period_name = "本月"
        budget_usd = monthly_limit
        period_cost_usd = monthly_usage or _as_float(total.get("actual_cost") or total.get("cost"))
    elif weekly_limit > 0:
        period_name = "本周"
        budget_usd = weekly_limit
        period_cost_usd = weekly_usage
    elif daily_limit > 0:
        period_name = "今天"
        budget_usd = daily_limit
        period_cost_usd = daily_usage
    elif remaining > 0:
        budget_usd = remaining + _as_float(today.get("actual_cost") or today.get("cost"))
        period_cost_usd = _as_float(today.get("actual_cost") or today.get("cost"))
    else:
        budget_usd = config.fallback_budget_usd
        period_cost_usd = _as_float(today.get("actual_cost") or today.get("cost"))

    usage_ratio = 0.0
    if budget_usd > 0:
        usage_ratio = min(1.0, max(0.0, period_cost_usd / budget_usd))

    overall_cost_usd = _as_float(total.get("actual_cost") or total.get("cost") or period_cost_usd)
    now = datetime.now(UTC)

    return UsageSnapshot(
        source_label=_host_label(config.base_url),
        plan_name=str(page.get("planName") or "网关用量").strip(),
        period_name=period_name,
        unit=str(page.get("unit") or "USD"),
        is_valid=is_valid,
        budget_usd=budget_usd,
        remaining_budget_usd=remaining,
        period_cost_usd=period_cost_usd,
        overall_cost_usd=overall_cost_usd,
        usage_ratio=usage_ratio,
        request_count=_as_int(today.get("requests")),
        overall_request_count=_as_int(total.get("requests", today.get("requests"))),
        input_tokens=_as_int(today.get("input_tokens")),
        output_tokens=_as_int(today.get("output_tokens")),
        cached_tokens=_as_int(today.get("cache_read_tokens")),
        total_tokens=_as_int(today.get("total_tokens")),
        overall_total_tokens=_as_int(total.get("total_tokens", today.get("total_tokens"))),
        rpm=_as_int(usage.get("rpm")),
        tpm=_as_int(usage.get("tpm")),
        average_duration_ms=_as_float(usage.get("average_duration_ms")),
        period_start=now,
        period_end=now,
        expires_at=_parse_iso_datetime(subscription.get("expires_at")),
    )


def _fetch_openai_org_usage(config: AppConfig) -> UsageSnapshot:
    if not config.organization_id:
        raise OpenAIMonitorError("使用 OpenAI 官方地址时，请填写 Organization ID。")

    start_ts, end_ts, period_start, period_end = _month_range_utc()
    usage_page = _request_json(
        config.base_url,
        "/organization/usage/completions",
        config.api_key,
        config.organization_id,
        {
            "start_time": start_ts,
            "end_time": end_ts,
            "bucket_width": "1d",
            "limit": 31,
        },
    )
    costs_page = _request_json(
        config.base_url,
        "/organization/costs",
        config.api_key,
        config.organization_id,
        {
            "start_time": start_ts,
            "end_time": end_ts,
            "bucket_width": "1d",
            "limit": 31,
        },
    )

    request_count, input_tokens, output_tokens, cached_tokens, total_tokens = _sum_usage(usage_page)
    total_cost_usd = _sum_costs(costs_page)
    budget_usd = config.fallback_budget_usd
    remaining_budget_usd = budget_usd - total_cost_usd
    usage_ratio = min(1.0, max(0.0, total_cost_usd / budget_usd)) if budget_usd > 0 else 0.0

    return UsageSnapshot(
        source_label=_host_label(config.base_url),
        plan_name="OpenAI 组织用量",
        period_name="本月",
        unit="USD",
        is_valid=True,
        budget_usd=budget_usd,
        remaining_budget_usd=remaining_budget_usd,
        period_cost_usd=total_cost_usd,
        overall_cost_usd=total_cost_usd,
        usage_ratio=usage_ratio,
        request_count=request_count,
        overall_request_count=request_count,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cached_tokens=cached_tokens,
        total_tokens=total_tokens,
        overall_total_tokens=total_tokens,
        rpm=0,
        tpm=0,
        average_duration_ms=0.0,
        period_start=period_start,
        period_end=period_end,
        expires_at=None,
    )


def fetch_snapshot(config: AppConfig) -> UsageSnapshot:
    if not config.api_key:
        raise OpenAIMonitorError("请先在设置中填写 API 密钥。")

    if "api.openai.com" in config.base_url:
        return _fetch_openai_org_usage(config)

    return _fetch_gateway_usage(config)
