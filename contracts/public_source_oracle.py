# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

"""Public Source Oracle — reusable Intelligent Contract.

Registers named public JSON sources and attests extracted values through
GenLayer leader/validator consensus. Each validator independently fetches
the same URL, walks the same JSON path, and compares the extracted decision
value. State is updated only after that comparison succeeds.

This is an on-chain primitive, not a product UI and not an LLM-judgement demo.
"""

import json
import typing
from dataclasses import dataclass

from genlayer import *

ERROR_EXPECTED = "[EXPECTED]"
ERROR_EXTERNAL = "[EXTERNAL]"
ERROR_TRANSIENT = "[TRANSIENT]"
ERROR_PARSE = "[PARSE]"

KIND_NUMBER = "number"
KIND_TEXT = "text"
KIND_BOOLEAN = "boolean"
ALLOWED_KINDS = (KIND_NUMBER, KIND_TEXT, KIND_BOOLEAN)

STATUS_ACTIVE = "active"
STATUS_PAUSED = "paused"

# Numeric values are stored as micro-units (value * 1_000_000).
MICRO_SCALE = 1_000_000
MAX_NAME_LEN = 64
MAX_URL_LEN = 512
MAX_PATH_LEN = 128
MAX_TOLERANCE_BPS = 10_000


@allow_storage
@dataclass
class Feed:
    creator: Address
    name: str
    source_url: str
    json_path: str
    value_kind: str
    tolerance_bps: u256
    status: str
    last_number: i256
    last_text: str
    last_bool: bool
    last_http_status: u32
    settlement_count: u256
    last_error: str


def _user_error(prefix: str, message: str):
    raise gl.vm.UserError(f"{prefix} {message}")


def _http_status(response) -> int:
    status = getattr(response, "status_code", None)
    if status is None:
        status = getattr(response, "status", None)
    return int(status or 0)


def _response_text(response) -> str:
    body = getattr(response, "body", b"")
    if isinstance(body, bytes):
        return body.decode("utf-8")
    return str(body)


def _walk_json_path(data, json_path: str):
    path = json_path.strip()
    if path in ("", ".", "$"):
        return data

    current = data
    for raw_part in path.split("."):
        part = raw_part.strip()
        if part in ("", "$"):
            continue
        if isinstance(current, list):
            try:
                index = int(part)
            except (TypeError, ValueError):
                _user_error(ERROR_EXPECTED, f"path segment '{part}' is not a list index")
            if index < 0 or index >= len(current):
                _user_error(ERROR_EXPECTED, f"path index {index} is out of range")
            current = current[index]
            continue
        if isinstance(current, dict):
            if part not in current:
                _user_error(ERROR_EXPECTED, f"path field '{part}' was not found")
            current = current[part]
            continue
        _user_error(ERROR_EXPECTED, f"cannot walk path segment '{part}' on {type(current).__name__}")
    return current


def _to_micro(value) -> int:
    if isinstance(value, bool) or value is None:
        _user_error(ERROR_EXPECTED, "numeric feed received a non-numeric value")
    if isinstance(value, int):
        return int(value) * MICRO_SCALE
    try:
        return int(round(float(str(value).strip()) * MICRO_SCALE))
    except (TypeError, ValueError):
        _user_error(ERROR_EXPECTED, f"cannot parse number from {value!r}")


def _to_text(value) -> str:
    if isinstance(value, (dict, list)):
        _user_error(ERROR_EXPECTED, "text feed requires a primitive JSON value")
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value).strip()


def _to_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in ("true", "yes", "1"):
            return True
        if lowered in ("false", "no", "0"):
            return False
    _user_error(ERROR_EXPECTED, f"cannot parse boolean from {value!r}")


def _normalize_text(value: str) -> str:
    return " ".join(str(value).strip().split())


def _empty_result(kind: str, http_status: int) -> dict:
    return {
        "kind": kind,
        "number": 0,
        "text": "",
        "boolean": False,
        "http_status": http_status,
    }


def _extract_from_url(url: str, json_path: str, kind: str) -> dict:
    response = gl.nondet.web.get(url)
    status = _http_status(response)
    if 400 <= status < 500:
        _user_error(ERROR_EXTERNAL, f"source returned {status}")
    if status >= 500 or status == 0:
        _user_error(ERROR_TRANSIENT, f"source unavailable ({status})")

    raw = _response_text(response)
    try:
        payload = json.loads(raw)
    except (TypeError, ValueError):
        _user_error(ERROR_PARSE, "source body is not valid JSON")

    extracted = _walk_json_path(payload, json_path)
    result = _empty_result(kind, status)
    if kind == KIND_NUMBER:
        result["number"] = _to_micro(extracted)
    elif kind == KIND_BOOLEAN:
        result["boolean"] = _to_bool(extracted)
    else:
        result["text"] = _to_text(extracted)
    return result


def _numbers_equivalent(leader: int, validator: int, tolerance_bps: int) -> bool:
    if tolerance_bps <= 0:
        return leader == validator
    delta = abs(leader - validator)
    base = abs(leader) if leader != 0 else abs(validator)
    if base == 0:
        return delta == 0
    return delta * MAX_TOLERANCE_BPS <= base * tolerance_bps


def _results_equivalent(leader_data, validator_data, kind: str, tolerance_bps: int) -> bool:
    if not isinstance(leader_data, dict) or not isinstance(validator_data, dict):
        return False
    if leader_data.get("kind") != kind or validator_data.get("kind") != kind:
        return False
    leader_status = int(leader_data.get("http_status", 0))
    validator_status = int(validator_data.get("http_status", 0))
    if not (200 <= leader_status < 300 and 200 <= validator_status < 300):
        return False
    if kind == KIND_NUMBER:
        return _numbers_equivalent(
            int(leader_data.get("number", 0)),
            int(validator_data.get("number", 0)),
            tolerance_bps,
        )
    if kind == KIND_BOOLEAN:
        return bool(leader_data.get("boolean")) is bool(validator_data.get("boolean"))
    return _normalize_text(leader_data.get("text", "")) == _normalize_text(
        validator_data.get("text", "")
    )


def _error_message(result) -> str:
    if hasattr(result, "message") and result.message:
        return str(result.message)
    return str(result)


def _handle_leader_error(leader_result, leader_fn) -> bool:
    leader_msg = _error_message(leader_result)
    try:
        leader_fn()
        return False
    except gl.vm.UserError as error:
        validator_msg = _error_message(error)
        if validator_msg.startswith(ERROR_EXPECTED) or validator_msg.startswith(ERROR_EXTERNAL):
            return validator_msg == leader_msg
        if validator_msg.startswith(ERROR_PARSE) and leader_msg.startswith(ERROR_PARSE):
            return True
        if validator_msg.startswith(ERROR_TRANSIENT) and leader_msg.startswith(ERROR_TRANSIENT):
            return True
        return False
    except Exception:
        return False


class PublicSourceOracle(gl.Contract):
    owner: Address
    next_feed_id: u256
    feeds: TreeMap[u256, Feed]
    feed_ids_by_name: TreeMap[str, u256]

    def __init__(self):
        self.owner = gl.message.sender_address

    def _require_feed(self, feed_id: int) -> Feed:
        key = u256(int(feed_id))
        if key not in self.feeds:
            _user_error(ERROR_EXPECTED, f"unknown feed {feed_id}")
        return self.feeds[key]

    def _require_manager(self, feed: Feed) -> None:
        sender = gl.message.sender_address
        if sender != feed.creator and sender != self.owner:
            _user_error(ERROR_EXPECTED, "not authorized")

    def _validate_registration(
        self,
        name: str,
        source_url: str,
        json_path: str,
        value_kind: str,
        tolerance_bps: int,
    ):
        clean_name = name.strip()
        if not clean_name or len(clean_name) > MAX_NAME_LEN:
            _user_error(ERROR_EXPECTED, "name must be 1-64 characters")
        if clean_name in self.feed_ids_by_name:
            _user_error(ERROR_EXPECTED, "name already registered")

        url = source_url.strip()
        if not url.startswith("https://") or len(url) > MAX_URL_LEN:
            _user_error(ERROR_EXPECTED, "source_url must be an https URL")

        path = json_path.strip()
        if len(path) > MAX_PATH_LEN:
            _user_error(ERROR_EXPECTED, "json_path is too long")

        kind = value_kind.strip().lower()
        if kind not in ALLOWED_KINDS:
            _user_error(ERROR_EXPECTED, "value_kind must be number, text, or boolean")

        tolerance = int(tolerance_bps)
        if tolerance < 0 or tolerance > MAX_TOLERANCE_BPS:
            _user_error(ERROR_EXPECTED, "tolerance_bps must be 0-10000")
        if kind != KIND_NUMBER:
            tolerance = 0
        return clean_name, url, path, kind, tolerance

    @gl.public.write
    def register_feed(
        self,
        name: str,
        source_url: str,
        json_path: str,
        value_kind: str,
        tolerance_bps: int,
    ) -> None:
        clean_name, url, path, kind, tolerance = self._validate_registration(
            name, source_url, json_path, value_kind, tolerance_bps
        )
        feed_id = self.next_feed_id
        self.feeds[feed_id] = Feed(
            creator=gl.message.sender_address,
            name=clean_name,
            source_url=url,
            json_path=path,
            value_kind=kind,
            tolerance_bps=u256(tolerance),
            status=STATUS_ACTIVE,
            last_number=i256(0),
            last_text="",
            last_bool=False,
            last_http_status=u32(0),
            settlement_count=u256(0),
            last_error="",
        )
        self.feed_ids_by_name[clean_name] = feed_id
        self.next_feed_id += 1

    @gl.public.write
    def pause_feed(self, feed_id: int) -> None:
        feed = self._require_feed(feed_id)
        self._require_manager(feed)
        feed.status = STATUS_PAUSED

    @gl.public.write
    def resume_feed(self, feed_id: int) -> None:
        feed = self._require_feed(feed_id)
        self._require_manager(feed)
        feed.status = STATUS_ACTIVE

    @gl.public.write
    def settle(self, feed_id: int) -> None:
        feed = self._require_feed(feed_id)
        if feed.status != STATUS_ACTIVE:
            _user_error(ERROR_EXPECTED, "feed is paused")

        url = str(feed.source_url)
        path = str(feed.json_path)
        kind = str(feed.value_kind)
        tolerance_bps = int(feed.tolerance_bps)

        def leader_fn():
            return _extract_from_url(url, path, kind)

        def validator_fn(leader_result) -> bool:
            if not isinstance(leader_result, gl.vm.Return):
                return _handle_leader_error(leader_result, leader_fn)
            try:
                validator_data = leader_fn()
            except gl.vm.UserError:
                return False
            except Exception:
                return False
            return _results_equivalent(leader_result.calldata, validator_data, kind, tolerance_bps)

        result = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)

        feed.last_http_status = u32(int(result["http_status"]))
        feed.last_error = ""
        feed.settlement_count += 1
        if kind == KIND_NUMBER:
            feed.last_number = i256(int(result["number"]))
            feed.last_text = ""
            feed.last_bool = False
        elif kind == KIND_BOOLEAN:
            feed.last_bool = bool(result["boolean"])
            feed.last_number = i256(0)
            feed.last_text = ""
        else:
            feed.last_text = str(result["text"])
            feed.last_number = i256(0)
            feed.last_bool = False

    def _feed_view(self, feed_id: int, feed: Feed):
        creator = feed.creator.as_hex if hasattr(feed.creator, "as_hex") else str(feed.creator)
        return {
            "id": int(feed_id),
            "creator": creator,
            "name": str(feed.name),
            "source_url": str(feed.source_url),
            "json_path": str(feed.json_path),
            "value_kind": str(feed.value_kind),
            "tolerance_bps": int(feed.tolerance_bps),
            "status": str(feed.status),
            "last_number": int(feed.last_number),
            "last_text": str(feed.last_text),
            "last_bool": bool(feed.last_bool),
            "last_http_status": int(feed.last_http_status),
            "settlement_count": int(feed.settlement_count),
            "last_error": str(feed.last_error),
        }

    @gl.public.view
    def get_owner(self) -> str:
        return self.owner.as_hex if hasattr(self.owner, "as_hex") else str(self.owner)

    @gl.public.view
    def get_feed_count(self) -> int:
        return int(self.next_feed_id)

    @gl.public.view
    def has_feed(self, name: str) -> bool:
        return name.strip() in self.feed_ids_by_name

    @gl.public.view
    def get_feed_id(self, name: str) -> int:
        key = name.strip()
        if key not in self.feed_ids_by_name:
            _user_error(ERROR_EXPECTED, f"unknown feed name '{name}'")
        return int(self.feed_ids_by_name[key])

    @gl.public.view
    def get_feed(self, feed_id: int) -> typing.Any:
        feed = self._require_feed(feed_id)
        return self._feed_view(feed_id, feed)

    @gl.public.view
    def get_last_value(self, feed_id: int) -> typing.Any:
        feed = self._require_feed(feed_id)
        kind = str(feed.value_kind)
        if kind == KIND_NUMBER:
            value = int(feed.last_number)
        elif kind == KIND_BOOLEAN:
            value = bool(feed.last_bool)
        else:
            value = str(feed.last_text)
        return {
            "id": int(feed_id),
            "name": str(feed.name),
            "kind": kind,
            "value": value,
            "http_status": int(feed.last_http_status),
            "settlement_count": int(feed.settlement_count),
            "status": str(feed.status),
        }
