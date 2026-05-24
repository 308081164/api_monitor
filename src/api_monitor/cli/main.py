"""CLI entry: serve proxy, run offline analysis, show status."""

from __future__ import annotations

import sys
from pathlib import Path

import click
import uvicorn

from api_monitor.analyzer.offline import OfflineAnalyzer
from api_monitor.analyzer.report import render_markdown_report
from api_monitor.config import Settings
from api_monitor.proxy.app import create_app
from api_monitor.storage.logger import ResponseLogger


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
def serve(
    host: str | None,
    port: int | None,
    upstream: str | None,
    db_path: str | None,
) -> None:
    """启动透明代理 (方案 A)。"""
    settings = Settings.from_env()
    if upstream:
        settings = Settings(
            host=settings.host,
            port=settings.port,
            upstream_base_url=upstream.rstrip("/"),
            db_path=Path(db_path) if db_path else settings.db_path,
            min_text_length=settings.min_text_length,
            drift_threshold=settings.drift_threshold,
        )
    elif db_path:
        settings = Settings(
            host=settings.host,
            port=settings.port,
            upstream_base_url=settings.upstream_base_url,
            db_path=Path(db_path),
            min_text_length=settings.min_text_length,
            drift_threshold=settings.drift_threshold,
        )

    bind_host = host or settings.host
    bind_port = port or settings.port

    if not settings.upstream_base_url:
        click.echo(
            "警告: 未设置 SENTINEL_UPSTREAM_URL / --upstream，"
            "代理将返回 502 直至配置上游。",
            err=True,
        )

    click.echo(
        f"SentinelProxy 监听 http://{bind_host}:{bind_port}\n"
        f"上游: {settings.upstream_base_url or '(未配置)'}\n"
        f"数据库: {settings.db_path}\n"
        "请将客户端 OPENAI_BASE_URL 指向 "
        f"http://{bind_host}:{bind_port}/v1"
    )

    app = create_app(settings)
    uvicorn.run(app, host=bind_host, port=bind_port, log_level="info")


@main.command("status")
@click.option("--db", "db_path", default=None, type=click.Path(), help="SQLite 数据库路径")
def status(db_path: str | None) -> None:
    """查看已记录响应数量。"""
    settings = Settings.from_env()
    path = Path(db_path) if db_path else settings.db_path
    count = ResponseLogger(path).count()
    click.echo(f"数据库: {path}")
    click.echo(f"已记录响应: {count}")


@main.command("analyze")
@click.option("--db", "db_path", default=None, type=click.Path(), help="SQLite 数据库路径")
@click.option("--limit", default=None, type=int, help="最多分析条数")
@click.option(
    "-o",
    "--output",
    "output_path",
    default=None,
    type=click.Path(),
    help="Markdown 报告输出路径",
)
@click.option(
    "--min-length",
    default=None,
    type=int,
    help="最小响应文本长度 (默认 SENTINEL_MIN_TEXT_LENGTH)",
)
def analyze(
    db_path: str | None,
    limit: int | None,
    output_path: str | None,
    min_length: int | None,
) -> None:
    """离线批量分析已记录响应并生成报告。"""
    settings = Settings.from_env()
    path = Path(db_path) if db_path else settings.db_path
    records = ResponseLogger(path).fetch_all(limit=limit)
    if not records:
        click.echo("没有可分析的记录。请先通过代理产生 API 流量。")
        sys.exit(1)

    analyzer = OfflineAnalyzer(
        min_text_length=min_length or settings.min_text_length,
        drift_threshold=settings.drift_threshold,
    )
    try:
        report = analyzer.analyze_records(records)
    except RuntimeError as exc:
        click.echo(str(exc), err=True)
        sys.exit(2)

    md = render_markdown_report(report)
    if output_path:
        out = Path(output_path)
        out.write_text(md, encoding="utf-8")
        click.echo(f"报告已写入: {out}")
    else:
        click.echo(md)

    if report.alerts:
        high = sum(1 for a in report.alerts if a.risk_level == "high")
        click.echo(f"\n共 {len(report.alerts)} 条告警 (高风险 {high} 条)", err=True)
        sys.exit(0 if high == 0 else 1)


if __name__ == "__main__":
    main()
