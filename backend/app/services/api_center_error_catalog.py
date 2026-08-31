from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

FaultCategory = Literal[
    "configuration",
    "authentication",
    "connectivity",
    "capacity",
    "rate_limit",
    "upstream",
    "timeout",
    "compatibility",
    "response_contract",
    "cancellation",
    "scheduler",
    "unknown",
]

FaultSeverity = Literal["info", "warning", "error", "critical"]


@dataclass(frozen=True)
class ApiErrorClassification:
    code: str
    category: FaultCategory
    severity: FaultSeverity
    retryable: bool
    operator_action: str
    system_action: str


_DEFAULT_CLASSIFICATION = ApiErrorClassification(
    code="unknown_error",
    category="unknown",
    severity="warning",
    retryable=True,
    operator_action="查看调用链路和中转站状态；如果同站连续异常，可手动停用该站后观察。",
    system_action="运行时会在任务预算内尝试其他可用候选。",
)

ERROR_CLASSIFICATIONS: dict[str, ApiErrorClassification] = {
    "invalid_base_url": ApiErrorClassification(
        code="invalid_base_url",
        category="configuration",
        severity="error",
        retryable=False,
        operator_action="修正 API 地址，应填写 OpenAI-compatible 根地址或可规范化的 chat completions 地址。",
        system_action="保存前拒绝入库，不消耗后续调度。",
    ),
    "unsupported_provider_type": ApiErrorClassification(
        code="unsupported_provider_type",
        category="configuration",
        severity="error",
        retryable=False,
        operator_action="选择当前已支持的 Provider 类型，或先新增适配器再接入。",
        system_action="保存前拒绝入库。",
    ),
    "api_probe_failed": ApiErrorClassification(
        code="api_probe_failed",
        category="configuration",
        severity="error",
        retryable=False,
        operator_action="根据具体探测错误修正地址、模型或密钥后重新保存。",
        system_action="探测未通过时不会保存新库存。",
    ),
    "api_credential_duplicate": ApiErrorClassification(
        code="api_credential_duplicate",
        category="configuration",
        severity="warning",
        retryable=False,
        operator_action="复用已有 API，或改用不同 Key/不同模型保存为新的库存。",
        system_action="阻止同站同模型同 Key 重复入库。",
    ),
    "credential_not_active": ApiErrorClassification(
        code="credential_not_active",
        category="configuration",
        severity="warning",
        retryable=False,
        operator_action="启用该 API，或从任务主备配置中移除它。",
        system_action="不调用管理员已停用的 API。",
    ),
    "credential_not_found": ApiErrorClassification(
        code="credential_not_found",
        category="configuration",
        severity="warning",
        retryable=False,
        operator_action="重新选择仍存在的 API。",
        system_action="拒绝保存失效引用。",
    ),
    "authentication_failed": ApiErrorClassification(
        code="authentication_failed",
        category="authentication",
        severity="critical",
        retryable=False,
        operator_action="检查密钥是否正确、是否过期、是否有该模型权限。",
        system_action="确定性鉴权失败不会盲目重试；运行时会尝试其他候选。",
    ),
    "model_not_found": ApiErrorClassification(
        code="model_not_found",
        category="configuration",
        severity="error",
        retryable=False,
        operator_action="核对模型名、账号权限和中转站实际支持的模型列表。",
        system_action="不会把模型配置错误误报为网络异常。",
    ),
    "connection_failed": ApiErrorClassification(
        code="connection_failed",
        category="connectivity",
        severity="warning",
        retryable=True,
        operator_action="检查 API 地址、DNS、本机网络或中转站是否整体不可达。",
        system_action="健康探测有限重试；运行时切换候选并记录同站异常信号。",
    ),
    "connection_timeout": ApiErrorClassification(
        code="connection_timeout",
        category="connectivity",
        severity="warning",
        retryable=True,
        operator_action="观察该中转站是否持续建连慢，必要时手动停用整站。",
        system_action="有限重试并与响应等待超时分开记录。",
    ),
    "network_error": ApiErrorClassification(
        code="network_error",
        category="connectivity",
        severity="warning",
        retryable=True,
        operator_action="检查本机网络、代理、TLS 或中转站网络波动。",
        system_action="运行时会继续尝试其他候选。",
    ),
    "rate_limited": ApiErrorClassification(
        code="rate_limited",
        category="rate_limit",
        severity="warning",
        retryable=True,
        operator_action="增加同模型其他 Key、降低该站压力，或等待额度恢复。",
        system_action="当前请求切换候选；后续自动退避由下一波实现。",
    ),
    "upstream_unavailable": ApiErrorClassification(
        code="upstream_unavailable",
        category="upstream",
        severity="warning",
        retryable=True,
        operator_action="如果同一中转站多 Key 集中 5xx，可手动停用整站。",
        system_action="健康探测有限重试；运行时切换候选。",
    ),
    "provider_http_error": ApiErrorClassification(
        code="provider_http_error",
        category="upstream",
        severity="warning",
        retryable=True,
        operator_action="查看中转站响应状态，必要时联系服务商或切换站点。",
        system_action="记录 HTTP 异常并尝试其他候选。",
    ),
    "provider_timeout": ApiErrorClassification(
        code="provider_timeout",
        category="timeout",
        severity="warning",
        retryable=True,
        operator_action="观察该站是否普遍慢；健康检查会用独立窗口验证是否仍可用。",
        system_action="运行时按任务预算切换候选，不让单个慢 API 吃完全部时间。",
    ),
    "response_timeout": ApiErrorClassification(
        code="response_timeout",
        category="timeout",
        severity="warning",
        retryable=True,
        operator_action="如果该模型稳定较慢，可保留人工指定；自动任务会优先其他健康候选。",
        system_action="健康探测有限重试；运行时在预算内接力候选。",
    ),
    "scheduler_budget_exhausted": ApiErrorClassification(
        code="scheduler_budget_exhausted",
        category="scheduler",
        severity="warning",
        retryable=True,
        operator_action="查看本次任务是否候选普遍过慢，必要时增加可用健康 API。",
        system_action="本机停止等待剩余候选并记录预算耗尽。",
    ),
    "scheduler_capacity_timeout": ApiErrorClassification(
        code="scheduler_capacity_timeout",
        category="capacity",
        severity="warning",
        retryable=True,
        operator_action="增加可用 API 或提高已验证安全容量。",
        system_action="容量等待超过任务预算后失败，不强行压满载 API。",
    ),
    "capacity_saturated": ApiErrorClassification(
        code="capacity_saturated",
        category="capacity",
        severity="info",
        retryable=True,
        operator_action="通常无需处理；若频繁出现，说明当前 Key 池不够。",
        system_action="不发起调用，继续选择其他候选或在预算内等待。",
    ),
    "invalid_json_response": ApiErrorClassification(
        code="invalid_json_response",
        category="response_contract",
        severity="error",
        retryable=True,
        operator_action="该模型可能不稳定输出 JSON，可切换更适合结构化输出的模型。",
        system_action="视为候选契约失败并切换，不误报网络。",
    ),
    "invalid_response_shape": ApiErrorClassification(
        code="invalid_response_shape",
        category="response_contract",
        severity="error",
        retryable=True,
        operator_action="确认模型是否遵守当前任务输出结构；必要时换模型。",
        system_action="记录为任务契约失败并切换候选。",
    ),
    "validation_error": ApiErrorClassification(
        code="validation_error",
        category="response_contract",
        severity="error",
        retryable=True,
        operator_action="查看对应任务输出契约，必要时换用更稳定模型。",
        system_action="拒绝不符合项目 schema 的响应并尝试候选。",
    ),
    "empty_response": ApiErrorClassification(
        code="empty_response",
        category="response_contract",
        severity="warning",
        retryable=True,
        operator_action="观察该模型是否经常空返回；必要时切换模型。",
        system_action="记录空响应并尝试其他候选。",
    ),
    "temperature_not_supported": ApiErrorClassification(
        code="temperature_not_supported",
        category="compatibility",
        severity="warning",
        retryable=True,
        operator_action="无需手动调整；保存测试会自动改为不发送 temperature。",
        system_action="自动尝试兼容参数组合。",
    ),
    "temperature_value_unsupported": ApiErrorClassification(
        code="temperature_value_unsupported",
        category="compatibility",
        severity="warning",
        retryable=True,
        operator_action="无需手动猜值；系统会测试候选温度。",
        system_action="自动尝试其他 temperature 值或不发送参数。",
    ),
    "response_format_unsupported": ApiErrorClassification(
        code="response_format_unsupported",
        category="compatibility",
        severity="warning",
        retryable=True,
        operator_action="通常无需处理；系统会移除 response_format 后验证 JSON。",
        system_action="降级为不发送 response_format 后继续请求。",
    ),
    "request_rejected": ApiErrorClassification(
        code="request_rejected",
        category="compatibility",
        severity="error",
        retryable=False,
        operator_action="检查模型名、接口协议和请求参数是否兼容。",
        system_action="不盲目重试确定性请求参数错误。",
    ),
    "task_capability_unsupported": ApiErrorClassification(
        code="task_capability_unsupported",
        category="compatibility",
        severity="error",
        retryable=False,
        operator_action="不要把该 API 放入此任务自动候选；可用于已验证兼容的其他任务。",
        system_action="该 API 不进入不兼容任务的自动候选。",
    ),
    "provider_not_configured": ApiErrorClassification(
        code="provider_not_configured",
        category="configuration",
        severity="error",
        retryable=False,
        operator_action="在 API 中心新增并启用可用 API。",
        system_action="不发起外部模型调用。",
    ),
    "api_center_unconfigured": ApiErrorClassification(
        code="api_center_unconfigured",
        category="scheduler",
        severity="error",
        retryable=False,
        operator_action="为当前任务配置人工主备，或启用可自动候选的健康 API。",
        system_action="调度器没有可用候选时直接跳过并记录。",
    ),
    "request_cancelled": ApiErrorClassification(
        code="request_cancelled",
        category="cancellation",
        severity="info",
        retryable=False,
        operator_action="通常无需处理；这是调用方主动取消或页面离开导致。",
        system_action="停止等待和后续 fallback，不误报网络故障。",
    ),
    "scheduler_cancelled": ApiErrorClassification(
        code="scheduler_cancelled",
        category="cancellation",
        severity="info",
        retryable=False,
        operator_action="通常无需处理；如频繁出现，检查页面等待或用户取消行为。",
        system_action="调度收到取消信号后停止等待。",
    ),
    "client_wait_timeout": ApiErrorClassification(
        code="client_wait_timeout",
        category="timeout",
        severity="info",
        retryable=False,
        operator_action="刷新页面并查看后台调用链路，不要据此修改 API 健康结论。",
        system_action="页面等待结束不改变后端健康状态。",
    ),
}


def classify_api_error(code: str | None) -> ApiErrorClassification | None:
    if not code:
        return None
    normalized = code.strip()
    if not normalized:
        return None
    return ERROR_CLASSIFICATIONS.get(
        normalized,
        ApiErrorClassification(
            code=normalized,
            category=_DEFAULT_CLASSIFICATION.category,
            severity=_DEFAULT_CLASSIFICATION.severity,
            retryable=_DEFAULT_CLASSIFICATION.retryable,
            operator_action=_DEFAULT_CLASSIFICATION.operator_action,
            system_action=_DEFAULT_CLASSIFICATION.system_action,
        ),
    )
