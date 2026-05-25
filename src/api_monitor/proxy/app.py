"""FastAPI transparent reverse proxy — Plan A SentinelProxy."""

from __future__ import annotations

import time
from typing import Any
from urllib.parse import urljoin

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse

from api_monitor.config import Settings
from api_monitor.proxy.extract import (
    extract_metadata,
    extract_response_text,
    merge_streaming_chunks,
    parse_request_model,
)
from api_monitor.storage.logger import ResponseLogger


def _resolve_upstream(settings: Settings, request: Request) -> str | None:
    header = request.headers.get("x-sentinel-upstream")
    if header:
        return header.rstrip("/")
    if settings.upstream_base_url:
        return settings.upstream_base_url
    return None


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    logger = ResponseLogger(settings.db_path)
    app = FastAPI(
        title="API Monitor SentinelProxy",
        description="Plan A transparent proxy — record only, analyze offline",
        version="0.1.0",
    )

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "records": logger.count(),
            "upstream_configured": bool(settings.upstream_base_url),
        }

    @app.api_route(
        "/{full_path:path}",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
    )
    async def proxy(full_path: str, request: Request) -> Response:
        upstream_base = _resolve_upstream(settings, request)
        if not upstream_base:
            return JSONResponse(
                status_code=502,
                content={
                    "error": "upstream_not_configured",
                    "message": (
                        "Set SENTINEL_UPSTREAM_URL to your relay API base "
                        "(e.g. https://api.example.com), or send header "
                        "X-Sentinel-Upstream."
                    ),
                },
            )

        path = f"/{full_path}" if full_path else "/"
        if request.url.query:
            path = f"{path}?{request.url.query}"
        target_url = urljoin(upstream_base.rstrip("/") + "/", path.lstrip("/"))

        body = await request.body()
        model_requested = parse_request_model(body)
        headers = {
            k: v
            for k, v in request.headers.items()
            if k.lower() not in {"host", "content-length", "x-sentinel-upstream"}
        }

        start = time.perf_counter()
        ttft_ms: float | None = None

        async with httpx.AsyncClient(timeout=httpx.Timeout(600.0)) as client:
            upstream_request = client.build_request(
                request.method,
                target_url,
                headers=headers,
                content=body if body else None,
            )
            upstream_response = await client.send(upstream_request, stream=True)

        content_type = upstream_response.headers.get("content-type", "")
        is_stream = "text/event-stream" in content_type or body and b'"stream":true' in body

        if is_stream:
            chunks: list[bytes] = []

            async def stream_body() -> Any:
                nonlocal ttft_ms
                async for chunk in upstream_response.aiter_raw():
                    if ttft_ms is None and chunk:
                        ttft_ms = (time.perf_counter() - start) * 1000
                    chunks.append(chunk)
                    yield chunk
                await upstream_response.aclose()
                total_ms = (time.perf_counter() - start) * 1000
                merged = merge_streaming_chunks(chunks)
                if merged:
                    _record_response(
                        logger,
                        request=request,
                        upstream_url=target_url,
                        model_requested=model_requested,
                        body=merged,
                        ttft_ms=ttft_ms,
                        total_ms=total_ms,
                    )

            return StreamingResponse(
                stream_body(),
                status_code=upstream_response.status_code,
                headers=dict(upstream_response.headers),
                media_type=content_type or None,
            )

        raw = await upstream_response.aread()
        await upstream_response.aclose()
        total_ms = (time.perf_counter() - start) * 1000
        if raw:
            _record_response(
                logger,
                request=request,
                upstream_url=target_url,
                model_requested=model_requested,
                body=raw,
                ttft_ms=ttft_ms,
                total_ms=total_ms,
            )

        return Response(
            content=raw,
            status_code=upstream_response.status_code,
            headers=dict(upstream_response.headers),
            media_type=content_type or None,
        )

    return app


def _record_response(
    logger: ResponseLogger,
    *,
    request: Request,
    upstream_url: str,
    model_requested: str | None,
    body: bytes,
    ttft_ms: float | None,
    total_ms: float,
) -> None:
    text = extract_response_text(body)
    if not text.strip():
        return
    logger.log(
        method=request.method,
        path=str(request.url.path),
        upstream_url=upstream_url,
        model_requested=model_requested,
        response_text=text,
        metadata=extract_metadata(body),
        timing={"ttft_ms": ttft_ms, "total_ms": total_ms},
    )
