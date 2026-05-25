"""Command-line interface."""

from __future__ import annotations

import sys
from pathlib import Path

import click
import uvicorn

from api_monitor.alerts import dispatch_report_alerts
from api_monitor.analyzer.report import (
    render_html_report,
    render_json_report,
    render_markdown_report,
)
from api_monitor.analyzer.service import analyzer_from_settings
from api_monitor.config import Settings
from api_monitor.proxy.app import create_app
from api_monitor.storage.baseline import BaselineStore
from api_monitor.storage.logger import ResponseLogger
from api_monitor.storage.user_settings import UserSettingsStore, settings_path_for_db


@click.group()
@click.version_option(package_name="api-monitor")
def main() -> None:
    """API Monitor — Plan A transparent proxy + offline MiniLM analysis."""


@main.command("serve")
@click.option("--host", default=None, help="监听地址 (默认 SENTINEL_HOST 或 127.0.0.1)")
@click.option("--port", default=None, type=int, help="监听端口 (默认 8080)")
@click.option(
    "--upstream",
    default=None,
    help="中转站 API 根地址，如 https://api.example.com",
)
@click.option("--db", "db_path", default=None, type=click.Path(), help="SQLite 数据库路径")
@click.option("--no-dashboard", is_flag=True, help="禁用 Web 仪表板")
def serve(
    host: str | None,
    port: int | None,
    upstream: str | None,
    db_path: str | None,
    no_dashboard: bool,
) -> None:
    """启动透明代理 (方案 A)。"""
    settings = Settings.from_env()
    if upstream:
        settings = settings.with_overrides(upstream_base_url=upstream.rstrip("/"))
    if db_path:
        settings = settings.with_overrides(db_path=Path(db_path))
    if no_dashboard:
        settings = settings.with_overrides(enable_dashboard=False)

    bind_host = host or settings.host
    bind_port = port or settings.port

    if not settings.upstream_base_url:
        click.echo(
            "警告: 未设置 SENTINEL_UPSTREAM_URL / --upstream，"
            "代理将返回 502 直至配置上游。",
            err=True,
        )

    dash = (
        f"http://{bind_host}:{bind_port}/dashboard"
        if settings.enable_dashboard
        else "(已禁用)"
    )
    click.echo(
        f"SentinelProxy 监听 http://{bind_host}:{bind_port}\n"
        f"上游: {settings.upstream_base_url or '(未配置)'}\n"
        f"数据库: {settings.db_path}\n"
        f"仪表板: {dash}\n"
        f"扩展上报: http://{bind_host}:{bind_port}/api/ingest\n"
        "请将客户端 OPENAI_BASE_URL 指向 "
        f"http://{bind_host}:{bind_port}/v1"
    )

    app = create_app(settings)
    uvicorn.run(app, host=bind_host, port=bind_port, log_level="info")


@main.command("status")
@click.option("--db", "db_path", default=None, type=click.Path(), help="SQLite 数据库路径")
def status(db_path: str | None) -> None:
    """查看已记录响应数量与基线概况。"""
    settings = Settings.from_env()
    path = Path(db_path) if db_path else settings.db_path
    count = ResponseLogger(path).count()
    baselines = BaselineStore(path).list_all()
    click.echo(f"数据库: {path}")
    click.echo(f"已记录响应: {count}")
    click.echo(f"基线模型数: {len(baselines)}")


@main.command("baseline-refresh")
@click.option("--db", "db_path", default=None, type=click.Path(), help="SQLite 数据库路径")
def baseline_refresh(db_path: str | None) -> None:
    """从全部历史记录重建基线（不生成告警报告）。"""
    settings = Settings.from_env()
    path = Path(db_path) if db_path else settings.db_path
    records = ResponseLogger(path).fetch_all()
    if not records:
        click.echo("没有记录可用于重建基线。")
        sys.exit(1)

    analyzer = analyzer_from_settings(settings, db_path=str(path))
    try:
        profiles = analyzer.refresh_baselines(records)
    except RuntimeError as exc:
        click.echo(str(exc), err=True)
        sys.exit(2)

    click.echo(f"已更新 {len(profiles)} 个模型基线。")
    for key, p in sorted(profiles.items()):
        click.echo(
            f"  {key}: {p.sample_count} 样本, 阈值 {p.dynamic_threshold:.3f}"
        )


@main.command("analyze")
@click.option("--db", "db_path", default=None, type=click.Path(), help="SQLite 数据库路径")
@click.option("--limit", default=None, type=int, help="最多分析条数")
@click.option(
    "-o",
    "--output",
    "output_path",
    default=None,
    type=click.Path(),
    help="报告输出路径",
)
@click.option(
    "--format",
    "report_format",
    type=click.Choice(["markdown", "html", "json", "md"], case_sensitive=False),
    default="markdown",
    help="报告格式",
)
@click.option(
    "--min-length",
    default=None,
    type=int,
    help="最小响应文本长度 (默认 SENTINEL_MIN_TEXT_LENGTH)",
)
@click.option("--no-notify", is_flag=True, help="不发送系统通知/Webhook")
def analyze(
    db_path: str | None,
    limit: int | None,
    output_path: str | None,
    report_format: str,
    min_length: int | None,
    no_notify: bool,
) -> None:
    """离线批量分析已记录响应并生成报告。"""
    settings = Settings.from_env()
    path = Path(db_path) if db_path else settings.db_path
    records = ResponseLogger(path).fetch_all(limit=limit)
    if not records:
        click.echo("没有可分析的记录。请先通过代理产生 API 流量。")
        sys.exit(1)

    analyzer = analyzer_from_settings(settings, db_path=str(path))
    if min_length:
        analyzer = OfflineAnalyzerOverride(analyzer, min_length)
    try:
        report = analyzer.analyze_records(records)
    except RuntimeError as exc:
        click.echo(str(exc), err=True)
        sys.exit(2)

    fmt = report_format.lower()
    if fmt == "md":
        fmt = "markdown"
    if fmt == "json":
        content = render_json_report(report)
    elif fmt == "html":
        content = render_html_report(report)
    else:
        content = render_markdown_report(report)

    if output_path:
        out = Path(output_path)
        out.write_text(content, encoding="utf-8")
        click.echo(f"报告已写入: {out}")
    else:
        click.echo(content)

    if not no_notify and report.alerts:
        prefs = UserSettingsStore(settings_path_for_db(path)).load()
        notify = dispatch_report_alerts(report, prefs)
        click.echo(
            f"告警通知: 系统 {notify.system_sent} 条, Webhook {notify.webhook_sent} 条",
            err=True,
        )

    if report.alerts:
        high = sum(1 for a in report.alerts if a.risk_level == "high")
        click.echo(
            f"\n共 {len(report.alerts)} 条告警 (高风险 {high} 条), "
            f"平滑抑制 {report.alerts_suppressed_by_smoothing} 条, "
            f"基线更新 {report.baselines_updated} 次",
            err=True,
        )
        sys.exit(0 if high == 0 else 1)


class OfflineAnalyzerOverride:
    """Thin wrapper to override min_text_length for one analyze run."""

    def __init__(self, inner, min_length: int):
        self._inner = inner
        self._inner.min_text_length = min_length

    def analyze_records(self, records):
        return self._inner.analyze_records(records)


if __name__ == "__main__":
    main()
