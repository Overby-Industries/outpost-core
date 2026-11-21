"""RFC 3339 helpers matching OTF-1's timestamp pattern (uppercase T and Z)."""
from datetime import datetime, timezone


def fmt(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))
