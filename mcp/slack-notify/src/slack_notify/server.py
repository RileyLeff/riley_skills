"""Slack notification MCP server for Claude Code."""

import asyncio
import os
import time

import httpx
from mcp.server.fastmcp import FastMCP

SLACK_API = "https://slack.com/api"
DEFAULT_POLL_INTERVAL = 10  # seconds
DEFAULT_TIMEOUT = 1800  # 30 minutes

_bot_token: str | None = None
_default_channel: str | None = None


def _get_token() -> str:
    global _bot_token
    if _bot_token:
        return _bot_token
    token = os.environ.get("SLACK_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("slack-notify: missing env var SLACK_BOT_TOKEN")
    _bot_token = token
    return _bot_token


def _resolve_channel(channel: str | None) -> str:
    global _default_channel
    if channel:
        return channel
    if _default_channel:
        return _default_channel
    default = os.environ.get("SLACK_CHANNEL", "").strip()
    if not default:
        raise RuntimeError(
            "slack-notify: no channel provided and SLACK_CHANNEL env var is not set"
        )
    _default_channel = default
    return _default_channel


mcp = FastMCP(
    "slack-notify",
    instructions=(
        "Slack notification tools. Use slack_notify for fire-and-forget messages. "
        "Use slack_ask when you need a human response — it posts a message and "
        "waits for a threaded reply."
    ),
)


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_get_token()}",
        "Content-Type": "application/json; charset=utf-8",
    }


def _format(message: str, subject: str | None, sender: str | None) -> str:
    parts = []
    if sender:
        parts.append(f"[{sender}]")
    if subject:
        parts.append(f"*{subject}*")
    parts.append(message)
    return "\n".join(parts) if len(parts) > 1 else parts[0]


async def _post_message(text: str, channel: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{SLACK_API}/chat.postMessage",
            headers=_headers(),
            json={"channel": channel, "text": text},
        )
        resp.raise_for_status()
        data = resp.json()
        if not data.get("ok"):
            raise RuntimeError(f"Slack API error: {data.get('error', 'unknown')}")
        return data


async def _get_bot_user_id() -> str:
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{SLACK_API}/auth.test", headers=_headers())
        resp.raise_for_status()
        data = resp.json()
        if not data.get("ok"):
            raise RuntimeError(f"auth.test failed: {data.get('error')}")
        return data["user_id"]


async def _poll_for_reply(
    thread_ts: str,
    bot_user_id: str,
    channel: str,
    poll_interval: float,
    timeout: float,
) -> str:
    deadline = time.monotonic() + timeout
    async with httpx.AsyncClient() as client:
        while time.monotonic() < deadline:
            await asyncio.sleep(poll_interval)
            resp = await client.get(
                f"{SLACK_API}/conversations.replies",
                headers=_headers(),
                params={"channel": channel, "ts": thread_ts},
            )
            resp.raise_for_status()
            data = resp.json()
            if not data.get("ok"):
                raise RuntimeError(f"Slack API error: {data.get('error', 'unknown')}")
            # messages[0] is the parent; look for human replies after it
            for msg in data.get("messages", [])[1:]:
                if msg.get("user") != bot_user_id:
                    return msg.get("text", "")
    raise TimeoutError(f"No reply received within {int(timeout)}s")


@mcp.tool()
async def slack_notify(
    message: str,
    subject: str | None = None,
    sender: str | None = None,
    channel: str | None = None,
) -> str:
    """Post a message to Slack. Fire-and-forget.

    Args:
        message: The message body.
        subject: Optional subject line (rendered bold).
        sender: Optional sender name (e.g. "claude-1", "codex-review").
                Displayed as a prefix so the user can identify which agent sent it.
        channel: Optional Slack channel ID (e.g. "C0123456789").
                 Falls back to SLACK_CHANNEL env var if not provided.
    """
    resolved = _resolve_channel(channel)
    data = await _post_message(_format(message, subject, sender), resolved)
    return f"Posted (ts: {data['ts']})"


@mcp.tool()
async def slack_ask(
    message: str,
    subject: str | None = None,
    sender: str | None = None,
    channel: str | None = None,
    poll_interval: float = DEFAULT_POLL_INTERVAL,
    timeout: float = DEFAULT_TIMEOUT,
) -> str:
    """Post a message to Slack, then wait for a human reply in the thread.

    Args:
        message: The message body.
        subject: Optional subject line (rendered bold).
        sender: Optional sender name (e.g. "claude-1", "codex-review").
                Displayed as a prefix so the user can identify which agent sent it.
        channel: Optional Slack channel ID (e.g. "C0123456789").
                 Falls back to SLACK_CHANNEL env var if not provided.
        poll_interval: Seconds between polls (default 10).
        timeout: Max seconds to wait (default 1800 = 30min).
    """
    resolved = _resolve_channel(channel)
    data = await _post_message(_format(message, subject, sender), resolved)
    bot_id = await _get_bot_user_id()
    return await _poll_for_reply(data["ts"], bot_id, resolved, poll_interval, timeout)


def main():
    mcp.run(transport="stdio")
