"""Daily personal context profiles for LifeHub."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from lifehub.recommendations import RecommendationEvent, goal_progress_rows
from lifehub.signals import ContextSignal


@dataclass(frozen=True)
class DailyContextProfile:
    profile_date: str
    timezone: str
    top_activity: str
    top_decision: str
    top_score: int
    readiness_state: str
    sessions_7d: int
    avg_mood_7d: float
    avg_fatigue_7d: float
    pain_sessions_7d: int
    useful_decision_days_7d: int
    follow_rate_7d: float
    open_goal_count: int
    signal_count_7d: int
    highest_signal_domain: str
    highest_signal_urgency: int
    context_summary: str
    generated_at: str


def build_daily_context_profile(
    recommendations: list[RecommendationEvent],
    week_summary: dict | None = None,
    decision_metrics: dict | None = None,
    signals: list[ContextSignal] | None = None,
    preferences: dict | None = None,
    timezone_name: str = "Europe/Moscow",
    recovery_summary: dict | None = None,
) -> DailyContextProfile:
    summary = week_summary or {}
    metrics = decision_metrics or {}
    context_signals = sorted(signals or [], key=lambda item: (item.urgency, item.confidence), reverse=True)
    best = recommendations[0] if recommendations else None
    goal_rows = goal_progress_rows(summary, preferences)
    open_goal_count = sum(1 for row in goal_rows if int(row["done"]) < int(row["target"]))
    generated_at = datetime.now(timezone.utc).isoformat()
    profile_date = generated_at[:10]
    recovery = recovery_summary or {}
    readiness_state = classify_readiness(best, summary, metrics, open_goal_count, recovery)
    top_signal = context_signals[0] if context_signals else None
    context_summary = summarize_daily_context(
        best,
        summary,
        metrics,
        open_goal_count,
        context_signals,
        readiness_state,
        recovery,
    )
    confidence, gaps = profile_confidence_and_gaps(summary, metrics, context_signals, recovery, generated_at)
    if gaps:
        context_summary = f"{context_summary}; confidence={confidence}/100; data_gaps={', '.join(gaps)}"
    else:
        context_summary = f"{context_summary}; confidence={confidence}/100; data_gaps=none"

    return DailyContextProfile(
        profile_date=profile_date,
        timezone=timezone_name,
        top_activity=best.activity if best else "none",
        top_decision=best.decision if best else "recover",
        top_score=best.score if best else 0,
        readiness_state=readiness_state,
        sessions_7d=int(summary.get("sessions") or 0),
        avg_mood_7d=round(float(summary.get("avg_mood") or 0), 2),
        avg_fatigue_7d=round(float(summary.get("avg_fatigue") or 0), 2),
        pain_sessions_7d=int(summary.get("pain_sessions") or 0),
        useful_decision_days_7d=int(metrics.get("useful_decision_days") or 0),
        follow_rate_7d=round(float(metrics.get("follow_rate") or 0), 3),
        open_goal_count=open_goal_count,
        signal_count_7d=len(context_signals),
        highest_signal_domain=top_signal.domain if top_signal else "none",
        highest_signal_urgency=top_signal.urgency if top_signal else 0,
        context_summary=context_summary,
        generated_at=generated_at,
    )


def classify_readiness(
    best: RecommendationEvent | None,
    week_summary: dict,
    decision_metrics: dict,
    open_goal_count: int,
    recovery_summary: dict | None = None,
) -> str:
    if not best:
        return "needs_data"
    fatigue = float(week_summary.get("avg_fatigue") or 0)
    pain_sessions = int(week_summary.get("pain_sessions") or 0)
    follow_rate = float(decision_metrics.get("follow_rate") or 0)
    recovery_score = float((recovery_summary or {}).get("latest_recovery_score") or 0)
    if pain_sessions > 0 or fatigue >= 8 or (recovery_score and recovery_score < 55) or best.decision == "recover":
        return "recovery_first"
    if best.decision == "go" and best.score >= 80 and open_goal_count > 0:
        return "act_on_open_goal"
    if best.decision == "go" and follow_rate >= 0.7:
        return "trusted_go"
    if best.decision == "go":
        return "good_window"
    return "caution_window"


def summarize_daily_context(
    best: RecommendationEvent | None,
    week_summary: dict,
    decision_metrics: dict,
    open_goal_count: int,
    signals: list[ContextSignal],
    readiness_state: str,
    recovery_summary: dict | None = None,
) -> str:
    if not best:
        return "No recommendation data yet; ingest weather and compute scores first."
    parts = [
        f"{best.activity} is top action at {best.score}/100 ({best.decision})",
        f"state={readiness_state}",
        f"sessions_7d={int(week_summary.get('sessions') or 0)}",
        f"fatigue={float(week_summary.get('avg_fatigue') or 0):.1f}",
        f"useful_days={int(decision_metrics.get('useful_decision_days') or 0)}",
        f"open_goals={open_goal_count}",
    ]
    if signals:
        parts.append(f"top_signal={signals[0].domain}:{signals[0].urgency}")
    recovery_score = float((recovery_summary or {}).get("latest_recovery_score") or 0)
    sleep_minutes = int(float((recovery_summary or {}).get("latest_duration_minutes") or 0))
    if recovery_score:
        parts.append(f"sleep_recovery={recovery_score:.0f}/100")
    if sleep_minutes:
        parts.append(f"sleep_minutes={sleep_minutes}")
    return "; ".join(parts)


def render_daily_context_profile(profile: DailyContextProfile) -> str:
    confidence, gaps = extract_confidence_and_gaps(profile.context_summary)
    return "\n".join(
        [
            "LifeHub daily context profile",
            f"Date: {profile.profile_date} ({profile.timezone})",
            f"Top action: {profile.top_activity} ({profile.top_score}/100, {profile.top_decision})",
            f"State: {profile.readiness_state}",
            (
                "7d loop: "
                f"{profile.sessions_7d} sessions, mood {profile.avg_mood_7d}/10, "
                f"fatigue {profile.avg_fatigue_7d}/10, pain sessions {profile.pain_sessions_7d}"
            ),
            (
                "Decision quality: "
                f"{profile.useful_decision_days_7d} useful days, "
                f"follow rate {profile.follow_rate_7d:.0%}, open goals {profile.open_goal_count}"
            ),
            (
                "Signals: "
                f"{profile.signal_count_7d} active, top {profile.highest_signal_domain} "
                f"urgency {profile.highest_signal_urgency}/10"
            ),
            f"Profile confidence: {confidence}/100",
            f"Data gaps: {', '.join(gaps) if gaps else 'none'}",
            f"Summary: {profile.context_summary}",
        ]
    )


def profile_confidence_and_gaps(
    week_summary: dict,
    decision_metrics: dict,
    signals: list[ContextSignal],
    recovery_summary: dict,
    generated_at: str,
) -> tuple[int, list[str]]:
    gaps: list[str] = []
    confidence = 100
    now = parse_dt(generated_at) or datetime.now(timezone.utc)

    if int(week_summary.get("sessions") or 0) <= 0:
        gaps.append("activity_diary_empty")
        confidence -= 25
    if not has_fresh_timestamp(week_summary, now, 10):
        gaps.append("activity_diary_freshness_unknown")
        confidence -= 10

    if not decision_metrics:
        gaps.append("decision_feedback_missing")
        confidence -= 15
    elif not has_fresh_timestamp(decision_metrics, now, 14):
        gaps.append("decision_feedback_freshness_unknown")
        confidence -= 8

    if not signals:
        gaps.append("context_signals_missing")
        confidence -= 10
    elif stale_signal_count(signals, now, 7) == len(signals):
        gaps.append("context_signals_stale")
        confidence -= 10

    if not recovery_summary:
        gaps.append("sleep_recovery_missing")
        confidence -= 10
    elif recovery_summary.get("latest_woke_at") and is_older_than(str(recovery_summary["latest_woke_at"]), now, 3):
        gaps.append("sleep_recovery_stale")
        confidence -= 10

    return max(0, min(100, confidence)), gaps


def has_fresh_timestamp(payload: dict, now: datetime, max_age_days: int) -> bool:
    for key in ["generated_at", "updated_at", "logged_at", "latest_logged_at", "as_of"]:
        value = payload.get(key)
        if value and not is_older_than(str(value), now, max_age_days):
            return True
    return False


def stale_signal_count(signals: list[ContextSignal], now: datetime, max_age_days: int) -> int:
    return sum(1 for signal in signals if is_older_than(signal.occurred_at, now, max_age_days))


def is_older_than(value: str, now: datetime, max_age_days: int) -> bool:
    parsed = parse_dt(value)
    if not parsed:
        return True
    return (now - parsed).total_seconds() > max_age_days * 86400


def parse_dt(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def extract_confidence_and_gaps(summary: str) -> tuple[int, list[str]]:
    confidence = 0
    gaps: list[str] = []
    for part in [item.strip() for item in summary.split(";")]:
        if part.startswith("confidence="):
            raw = part.split("=", 1)[1].split("/", 1)[0]
            try:
                confidence = int(raw)
            except ValueError:
                confidence = 0
        elif part.startswith("data_gaps="):
            raw_gaps = part.split("=", 1)[1]
            gaps = [] if raw_gaps == "none" else [item.strip() for item in raw_gaps.split(",") if item.strip()]
    return confidence, gaps
