"""Reference upstream comparison (official API vs relay)."""

from __future__ import annotations

from urllib.parse import urlparse

from api_monitor.models import ResponseRecord


def upstream_host(url: str) -> str:
    if not url:
        return ""
    try:
        return urlparse(url).netloc.lower()
    except Exception:
        return ""


def resolve_upstream_kind(
    upstream_url: str,
    *,
    relay_url: str,
    reference_url: str,
) -> str:
    host = upstream_host(upstream_url)
    if reference_url and host and host == upstream_host(reference_url):
        return "reference"
    if relay_url and host and host == upstream_host(relay_url):
        return "relay"
    return "unknown"


def reference_comparison_evidence(
    record: ResponseRecord,
    *,
    reference_records: list[ResponseRecord],
    relay_url: str,
) -> list[str]:
    """Compare relay record fingerprints against reference-channel samples."""
    if not reference_records:
        return []

    kind = record.metadata.get("upstream_kind")
    if kind != "relay":
        return []

    ref_fps: set[str] = set()
    ref_models: set[str] = set()
    for r in reference_records:
        fp = r.metadata.get("system_fingerprint")
        if fp is not None:
            ref_fps.add(str(fp))
        m = r.metadata.get("model")
        if m is not None:
            ref_models.add(str(m))

    evidence: list[str] = []
    fp = record.metadata.get("system_fingerprint")
    if ref_fps and fp is not None and str(fp) not in ref_fps:
        evidence.append(
            f"对照验证: 中转站 system_fingerprint `{fp}` 与官方直连样本不一致"
        )
    elif ref_fps and fp is None:
        evidence.append("对照验证: 中转站缺失 system_fingerprint，官方直连样本存在")

    resp_model = record.metadata.get("model")
    if ref_models and resp_model and str(resp_model) not in ref_models:
        evidence.append(
            f"对照验证: 响应 model `{resp_model}` 与官方直连记录 {sorted(ref_models)[:2]} 不一致"
        )

    if relay_url and record.upstream_url:
        if upstream_host(record.upstream_url) != upstream_host(relay_url):
            evidence.append("对照验证: 请求未经过配置的中转站上游地址")

    return evidence
