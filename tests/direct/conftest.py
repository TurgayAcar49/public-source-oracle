"""Shared helpers for Public Source Oracle direct-mode tests."""

import json


BTC_FEED = {
    "name": "btc-usd",
    "source_url": "https://api.example.com/v1/prices/btc",
    "json_path": "data.price",
    "value_kind": "number",
    "tolerance_bps": 200,
}

STATUS_FEED = {
    "name": "repo-status",
    "source_url": "https://api.example.com/v1/status",
    "json_path": "state",
    "value_kind": "text",
    "tolerance_bps": 0,
}

FLAG_FEED = {
    "name": "maintenance",
    "source_url": "https://api.example.com/v1/flags",
    "json_path": "maintenance",
    "value_kind": "boolean",
    "tolerance_bps": 0,
}


def to_hex(addr):
    if hasattr(addr, "as_hex"):
        return addr.as_hex
    from genlayer.py.types import Address

    return Address(addr).as_hex


def mock_json(direct_vm, url_part: str, payload, status: int = 200):
    body = payload if isinstance(payload, str) else json.dumps(payload)
    direct_vm.mock_web(
        rf".*{url_part}.*",
        {"status": status, "body": body},
    )


def register(contract, feed: dict):
    contract.register_feed(
        feed["name"],
        feed["source_url"],
        feed["json_path"],
        feed["value_kind"],
        feed["tolerance_bps"],
    )
    return contract.get_feed_id(feed["name"])
