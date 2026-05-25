"""Markdown and HTML report generation."""

from __future__ import annotations

import html
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
        f"- 基线模型数: **{len(report.baselines)}**",
        "",
    ]

    if report.baselines:
        lines.append("## 基线概况")
        lines.append("")
        for key, b in sorted(report.baselines.items()):
            lines.append(
                f"- `{key}`: {b.sample_count} 样本, 动态阈值 **{b.dynamic_threshold:.3f}**"
            )
        lines.append("")

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
        lines.extend(_render_alert_md(alert))
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def render_html_report(report: AnalysisReport) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    alert_rows = "".join(_render_alert_html(a) for a in report.alerts)
    baseline_rows = "".join(
        f"<li><code>{html.escape(k)}</code>: {b.sample_count} 样本, "
        f"阈值 {b.dynamic_threshold:.3f}</li>"
        for k, b in sorted(report.baselines.items())
    )
    if not alert_rows:
        alert_rows = "<p>未检测到高风险或中风险漂移。</p>"

    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"/>
<title>API Monitor 分析报告</title>
<style>
body {{ font-family: system-ui,sans-serif; max-width: 900px; margin: 2rem auto; padding: 0 1rem; }}
h1 {{ font-size: 1.4rem; }}
.alert {{ border-left: 4px solid #f59e0b; padding: 0.75rem; margin: 0.75rem 0; background: #f8fafc; }}
.alert.high {{ border-left-color: #ef4444; }}
ul {{ color: #475569; }}
</style></head><body>
<h1>API Monitor 离线分析报告</h1>
<p>生成时间: {html.escape(now)}</p>
<ul>
<li>总记录: {report.total_records}</li>
<li>已分析: {report.analyzed_records}</li>
<li>告警: {len(report.alerts)}</li>
</ul>
<h2>基线</h2><ul>{baseline_rows or '<li>暂无</li>'}</ul>
<h2>告警</h2>
{alert_rows}
</body></html>"""


def _render_alert_md(alert: AnalysisRow) -> list[str]:
    icon = "⚠️" if alert.risk_level == "high" else "ℹ️"
    expected = alert.expected_family or "未知"
    lines = [
        f"### {icon} 记录 #{alert.record_id} ({alert.risk_level.upper()})",
        "",
        f"- **检测时间**: {alert.timestamp}",
        f"- **请求模型**: `{alert.model_requested or 'n/a'}`",
        f"- **声称家族**: `{expected}` → **预测家族**: `{alert.predicted_family}`",
        f"- **置信度**: {alert.confidence:.2%}",
        f"- **文体指纹偏移**: {alert.drift_score:.4f} (动态阈值: {alert.dynamic_threshold or 'n/a'})",
    ]
    if alert.timing_pvalue is not None:
        lines.append(f"- **时序 KS p-value**: {alert.timing_pvalue:.4f}")
    if alert.fusion_score is not None:
        lines.append(f"- **融合分数**: {alert.fusion_score:.4f}")
    lines.append("")
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


def _render_alert_html(alert: AnalysisRow) -> str:
    ev = "".join(f"<li>{html.escape(e)}</li>" for e in alert.evidence)
    return (
        f'<div class="alert {html.escape(alert.risk_level)}">'
        f"<h3>#{alert.record_id} {html.escape(alert.risk_level.upper())}</h3>"
        f"<p>模型: <code>{html.escape(alert.model_requested or 'n/a')}</code>"
        f" · {html.escape(alert.expected_family or '?')} → "
        f"<strong>{html.escape(alert.predicted_family)}</strong>"
        f" · 融合分 {alert.fusion_score}</p>"
        f"<ul>{ev}</ul></div>"
    )
