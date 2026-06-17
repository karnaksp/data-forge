"""Telegram diary command parsing and validation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


ACTIVITY_TYPES = {
    "skate",
    "snowboard",
    "volleyball",
    "moto_lesson",
    "gym",
    "walk",
    "rest",
}
RESULTS = {"good", "ok", "bad", "skipped"}
CAPTURE_COMMANDS = {
    "/sleep",
    "/mood",
    "/pain",
    "/plan",
    "/moto",
    "/trade",
    "/note",
}


@dataclass(frozen=True)
class ActivityLog:
    activity_type: str
    start_time: str | None
    end_time: str | None
    location_label: str | None
    intensity: int
    mood: int
    fatigue: int
    pain_flag: bool
    pain_text: str | None
    result: str
    notes: str
    logged_at: str


@dataclass(frozen=True)
class PersonalCapture:
    command: str
    domain: str
    capture_type: str
    value: int | None
    unit: str | None
    activity_type: str | None
    result: str | None
    pain_flag: bool
    note: str
    payload: dict[str, Any]
    logged_at: str


def parse_log_command(text: str) -> ActivityLog:
    """Parse compact and detailed Telegram diary entries.

    Compact form:
    /log skate 7 8 4 good dry session

    Detailed form:
    /log activity=skate intensity=7 mood=8 fatigue=4 result=good loc=spot pain=no notes=dry
    """

    parts = text.strip().split(maxsplit=6)
    if len(parts) < 6 or parts[0] != "/log":
        raise ValueError(
            "Use: /log activity intensity mood fatigue result notes; "
            "or /log activity=skate intensity=7 mood=8 fatigue=4 result=good loc=spot pain=no notes=text"
        )
    if "=" in parts[1]:
        return parse_key_value_log(text)

    activity, intensity, mood, fatigue, result = parts[1:6]
    notes = parts[6] if len(parts) > 6 else ""
    return build_log(
        activity=activity,
        intensity=intensity,
        mood=mood,
        fatigue=fatigue,
        result=result,
        notes=notes,
    )


def parse_capture_command(text: str) -> PersonalCapture:
    """Parse quick Telegram/CLI capture commands into a local-safe event.

    Supported examples:
    /sleep 7.5h quality=82 recovery=76
    /mood 8 calm focus
    /pain 4 wrist after moto
    /plan finish lakehouse evidence
    /moto 6 ok cones and slow turns
    /trade SPY watchlist no impulse
    /note remembered useful context
    """

    stripped = text.strip()
    name = command_name(stripped)
    if name not in CAPTURE_COMMANDS:
        raise ValueError(f"Unsupported capture command: {name or text}")
    payload = stripped[len(name) :].strip()
    tokens = payload.split()
    pairs, words = split_key_values(tokens)
    logged_at = datetime.now(timezone.utc).isoformat()

    if name == "/sleep":
        value = sleep_minutes(words[0]) if words else optional_int(pairs.get("minutes"))
        note = " ".join(words[1:] if words else words)
        return PersonalCapture(
            command=name,
            domain="recovery",
            capture_type="sleep",
            value=value,
            unit="minutes" if value is not None else None,
            activity_type=None,
            result=None,
            pain_flag=False,
            note=note,
            payload=pairs,
            logged_at=logged_at,
        )
    if name == "/mood":
        value = required_bounded_first("mood", words, pairs, 1, 10)
        return capture(name, "wellbeing", "mood", value, "score_1_10", words[1:], pairs, logged_at)
    if name == "/pain":
        value = required_bounded_first("pain", words, pairs, 0, 10)
        return PersonalCapture(
            command=name,
            domain="wellbeing",
            capture_type="pain",
            value=value,
            unit="score_0_10",
            activity_type=None,
            result=None,
            pain_flag=value > 0,
            note=" ".join(words[1:]),
            payload=pairs,
            logged_at=logged_at,
        )
    if name == "/plan":
        return capture(name, "planning", "plan", None, None, words, pairs, logged_at)
    if name == "/moto":
        value = optional_bounded_first("intensity", words, pairs, 1, 10)
        result = first_result(words) or pairs.get("result") or "ok"
        note_words = drop_leading_score_and_result(words, result)
        return PersonalCapture(
            command=name,
            domain="activity",
            capture_type="activity",
            value=value,
            unit="intensity_1_10" if value is not None else None,
            activity_type="moto_lesson",
            result=result if result in RESULTS else "ok",
            pain_flag=truthy(pairs.get("pain", "no")),
            note=" ".join(note_words),
            payload=pairs,
            logged_at=logged_at,
        )
    if name == "/trade":
        return capture(name, "market", "trade_note", None, None, words, pairs, logged_at)
    return capture(name, "personal", "note", None, None, words, pairs, logged_at)


def capture(
    command: str,
    domain: str,
    capture_type: str,
    value: int | None,
    unit: str | None,
    words: list[str],
    pairs: dict[str, str],
    logged_at: str,
) -> PersonalCapture:
    return PersonalCapture(
        command=command,
        domain=domain,
        capture_type=capture_type,
        value=value,
        unit=unit,
        activity_type=None,
        result=None,
        pain_flag=False,
        note=" ".join(words),
        payload=pairs,
        logged_at=logged_at,
    )


def capture_to_activity_log(event: PersonalCapture) -> ActivityLog | None:
    if event.activity_type != "moto_lesson":
        return None
    return build_log(
        activity="moto_lesson",
        intensity=str(event.value or 5),
        mood=str(event.payload.get("mood", 5)),
        fatigue=str(event.payload.get("fatigue", 5)),
        result=event.result or "ok",
        notes=event.note,
        location_label=event.payload.get("loc", event.payload.get("location")),
        pain_flag=event.pain_flag,
        pain_text=event.payload.get("pain_text"),
    )


def render_capture_ack(event: PersonalCapture) -> str:
    value = f" {event.value}{' ' + event.unit if event.unit else ''}" if event.value is not None else ""
    suffix = f": {event.note}" if event.note else ""
    return f"Captured {event.capture_type}{value}{suffix}."


def append_capture_jsonl(event: PersonalCapture, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(asdict(event), sort_keys=True) + "\n")


def split_key_values(tokens: list[str]) -> tuple[dict[str, str], list[str]]:
    pairs: dict[str, str] = {}
    words: list[str] = []
    for token in tokens:
        if "=" in token:
            key, value = token.split("=", 1)
            pairs[key.strip().lower()] = value.strip().replace("_", " ")
        else:
            words.append(token.replace("_", " "))
    return pairs, words


def required_bounded_first(label: str, words: list[str], pairs: dict[str, str], minimum: int, maximum: int) -> int:
    value = pairs.get(label) or (words[0] if words else "")
    return bounded_int_range(label, value, minimum, maximum)


def optional_bounded_first(label: str, words: list[str], pairs: dict[str, str], minimum: int, maximum: int) -> int | None:
    value = pairs.get(label) or (words[0] if words else "")
    if not value:
        return None
    try:
        return bounded_int_range(label, value, minimum, maximum)
    except ValueError:
        return None


def bounded_int_range(label: str, value: str, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError(f"{label} must be an integer from {minimum} to {maximum}") from exc
    if parsed < minimum or parsed > maximum:
        raise ValueError(f"{label} must be from {minimum} to {maximum}")
    return parsed


def sleep_minutes(value: str) -> int:
    normalized = value.strip().lower()
    if normalized.endswith("h"):
        minutes = int(float(normalized[:-1]) * 60)
        if minutes <= 0:
            raise ValueError("sleep duration must be positive")
        return minutes
    if ":" in normalized:
        hours, minutes = normalized.split(":", 1)
        total = int(hours) * 60 + int(minutes)
        if total <= 0:
            raise ValueError("sleep duration must be positive")
        return total
    minutes = int(float(normalized))
    if minutes <= 0:
        raise ValueError("sleep duration must be positive")
    return minutes


def optional_int(value: str | None) -> int | None:
    if not value:
        return None
    parsed = int(value)
    if parsed <= 0:
        raise ValueError("value must be positive")
    return parsed


def truthy(value: str) -> bool:
    return value.lower() in {"1", "yes", "true", "y", "pain"}


def first_result(words: list[str]) -> str | None:
    for word in words:
        if word in RESULTS:
            return word
    return None


def drop_leading_score_and_result(words: list[str], result: str | None) -> list[str]:
    remaining = list(words)
    if remaining:
        try:
            int(remaining[0])
            remaining = remaining[1:]
        except ValueError:
            pass
    if result in remaining:
        remaining.remove(result)
    return remaining


def parse_key_value_log(text: str) -> ActivityLog:
    payload = text.strip()[len("/log") :].strip()
    values: dict[str, str] = {}
    for token in payload.split():
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        values[key.strip().lower()] = value.strip()
    missing = [key for key in ["activity", "intensity", "mood", "fatigue", "result"] if key not in values]
    if missing:
        raise ValueError(f"Missing /log fields: {', '.join(missing)}")
    pain_value = values.get("pain", values.get("pain_flag", "no"))
    pain_flag = pain_value.lower() in {"1", "yes", "true", "y", "pain"}
    notes = values.get("notes", "")
    return build_log(
        activity=values["activity"],
        intensity=values["intensity"],
        mood=values["mood"],
        fatigue=values["fatigue"],
        result=values["result"],
        notes=notes.replace("_", " "),
        start_time=values.get("start"),
        end_time=values.get("end"),
        location_label=values.get("loc", values.get("location")),
        pain_flag=pain_flag,
        pain_text=values.get("pain_text"),
    )


def build_log(
    *,
    activity: str,
    intensity: str,
    mood: str,
    fatigue: str,
    result: str,
    notes: str,
    start_time: str | None = None,
    end_time: str | None = None,
    location_label: str | None = None,
    pain_flag: bool = False,
    pain_text: str | None = None,
) -> ActivityLog:
    if activity not in ACTIVITY_TYPES:
        raise ValueError(f"Unknown activity: {activity}")
    if result not in RESULTS:
        raise ValueError(f"Unknown result: {result}")
    return ActivityLog(
        activity_type=activity,
        start_time=start_time,
        end_time=end_time,
        location_label=location_label.replace("_", " ") if location_label else None,
        intensity=bounded_int("intensity", intensity),
        mood=bounded_int("mood", mood),
        fatigue=bounded_int("fatigue", fatigue),
        pain_flag=pain_flag,
        pain_text=pain_text.replace("_", " ") if pain_text else None,
        result=result,
        notes=notes,
        logged_at=datetime.now(timezone.utc).isoformat(),
    )


def bounded_int(label: str, value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError(f"{label} must be an integer from 1 to 10") from exc
    if parsed < 1 or parsed > 10:
        raise ValueError(f"{label} must be from 1 to 10")
    return parsed


def command_name(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("/"):
        return ""
    return stripped.split(maxsplit=1)[0]
