"""Slack notification MCP server for Claude Code."""

import asyncio
import os
import sys
import time

import httpx
from mcp.server.fastmcp import FastMCP

SLACK_API = "https://slack.com/api"
DEFAULT_POLL_INTERVAL = 10  # seconds
DEFAULT_TIMEOUT = 1800  # 30 minutes


def _get_config() -> tuple[str, str]:
    token = os.environ.get("SLACK_BOT_TOKEN", "").strip()
    channel = os.environ.get("SLACK_CHANNEL", "").strip()
    errors = []
    if not token:
        errors.append("SLACK_BOT_TOKEN is not set")
    if not channel:
        errors.append("SLACK_CHANNEL is not set")
    if errors:
        for e in errors:
            print(f"slack-notify: {e}", file=sys.stderr)
        sys.exit(1)
    return token, channel


BOT_TOKEN, CHANNEL = _get_config()

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
        "Authorization": f"Bearer {BOT_TOKEN}",
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


async def _post_message(text: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{SLACK_API}/chat.postMessage",
            headers=_headers(),
            json={"channel": CHANNEL, "text": text},
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
                params={"channel": CHANNEL, "ts": thread_ts},
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
) -> str:
    """Post a message to Slack. Fire-and-forget.

    Args:
        message: The message body.
        subject: Optional subject line (rendered bold).
        sender: Optional sender name (e.g. "claude-1", "codex-review").
                Displayed as a prefix so the user can identify which agent sent it.
    """
    data = await _post_message(_format(message, subject, sender))
    return f"Posted (ts: {data['ts']})"


@mcp.tool()
async def slack_ask(
    message: str,
    subject: str | None = None,
    sender: str | None = None,
    poll_interval: float = DEFAULT_POLL_INTERVAL,
    timeout: float = DEFAULT_TIMEOUT,
) -> str:
    """Post a message to Slack, then wait for a human reply in the thread.

    Args:
        message: The message body.
        subject: Optional subject line (rendered bold).
        sender: Optional sender name (e.g. "claude-1", "codex-review").
                Displayed as a prefix so the user can identify which agent sent it.
        poll_interval: Seconds between polls (default 10).
        timeout: Max seconds to wait (default 1800 = 30min).
    """
    data = await _post_message(_format(message, subject, sender))
    bot_id = await _get_bot_user_id()
    return await _poll_for_reply(data["ts"], bot_id, poll_interval, timeout)


def main():
    mcp.run(transport="stdio")
