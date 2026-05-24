"""Markdown report generation."""

from __future__ import annotations

from datetime import datetime, timezone

from api_monitor.models import AnalysisReport, AnalysisRow


def render_markdown_report(report: AnalysisReport) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = [
        "# API Monitor 离线分析报告",
        "",
        f"**生成时间**: {now}",
        "",
        "## 概览",
        "",
        f"- 总记录数: **{report.total_records}**",
        f"- 已分析（满足最小文本长度）: **{report.analyzed_records}**",
        f"- 告警条数: **{len(report.alerts)}**",
        "",
    ]

    if report.summary_by_family:
        lines.append("## 预测模型家族分布")
        lines.append("")
        for family, count in sorted(
            report.summary_by_family.items(), key=lambda x: -x[1]
        ):
            lines.append(f"- `{family}`: {count}")
        lines.append("")

    if not report.alerts:
        lines.append("> 未检测到高风险或中风险漂移。")
        lines.append("")
        return "\n".join(lines)

    lines.append("## 告警详情")
    lines.append("")
    for alert in report.alerts:
        lines.extend(_render_alert(alert))
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def _render_alert(alert: AnalysisRow) -> list[str]:
    icon = "⚠️" if alert.risk_level == "high" else "ℹ️"
    expected = alert.expected_family or "未知"
    lines = [
        f"### {icon} 记录 #{alert.record_id} ({alert.risk_level.upper()})",
        "",
        f"- **检测时间**: {alert.timestamp}",
        f"- **请求模型**: `{alert.model_requested or 'n/a'}`",
        f"- **声称家族**: `{expected}` → **预测家族**: `{alert.predicted_family}`",
        f"- **置信度**: {alert.confidence:.2%}",
        f"- **文体指纹偏移**: {alert.drift_score:.4f}",
        "",
    ]
    if alert.evidence:
        lines.append("**证据**:")
        for i, item in enumerate(alert.evidence, 1):
            lines.append(f"{i}. {item}")
        lines.append("")
    lines.append(
        f"**建议**: 当前后端输出风格更接近 **{alert.predicted_family.upper()}** 系列，"
        f"与请求的 **{expected.upper()}** 不一致时请人工复核。"
    )
    return lines
