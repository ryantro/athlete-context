from garminconnect import Garmin
import datetime
import json
import os
from dotenv import load_dotenv

load_dotenv()

email = os.getenv("GARMIN_EMAIL")
password = os.getenv("GARMIN_PASSWORD")

if not email or not password:
    raise ValueError("Missing GARMIN_EMAIL or GARMIN_PASSWORD in .env")

client = Garmin(email, password)
client.login()

today = datetime.date.today()
today_str = today.isoformat()
seven_days_ago = today - datetime.timedelta(days=7)
twenty_eight_days_ago = today - datetime.timedelta(days=28)

os.makedirs("data", exist_ok=True)

# ---------------------------------------------------------------------------
# Activity type normalization
# ---------------------------------------------------------------------------

CATEGORY_MAP = {
    "running": "Running",
    "trail_running": "Running",
    "treadmill_running": "Running",
    "cycling": "Cycling / MTB",
    "mountain_biking": "Cycling / MTB",
    "gravel_cycling": "Cycling / MTB",
    "road_biking": "Cycling / MTB",
    "indoor_cycling": "Cycling / MTB",
    "strength_training": "Strength / Bodybuilding",
    "fitness_equipment": "Strength / Bodybuilding",
    "indoor_rowing": "Strength / Bodybuilding",
    "hiit": "Strength / Bodybuilding",
}


def categorize(activity_type: str) -> str:
    normalized = (activity_type or "").lower().replace(" ", "_")
    return CATEGORY_MAP.get(normalized, "Other")


# ---------------------------------------------------------------------------
# Fetch data
# ---------------------------------------------------------------------------

print("Fetching 28 days of activity data...")
all_activities = client.get_activities_by_date(
    twenty_eight_days_ago.isoformat(), today_str
)

print("Fetching 28 days of sleep data...")
sleep_records = []
for i in range(28):
    date = today - datetime.timedelta(days=i + 1)  # sleep for *previous* night
    date_str = date.isoformat()
    try:
        raw = client.get_sleep_data(date_str)
        daily = raw.get("dailySleepDTO", {}) if raw else {}
        sleep_records.append({
            "date": date_str,
            "duration_seconds": daily.get("sleepTimeSeconds"),
            "score": daily.get("sleepScores", {}).get("overall", {}).get("value") if isinstance(daily.get("sleepScores"), dict) else None,
            "hrv_avg": daily.get("averageSpO2Value"),  # fallback; real HRV below
            "hrv_nightly_avg": (raw or {}).get("hrvSummary", {}).get("weeklyAvg") if raw else None,
            "resting_hr": daily.get("restingHeartRate"),
            "deep_seconds": daily.get("deepSleepSeconds"),
            "rem_seconds": daily.get("remSleepSeconds"),
            "light_seconds": daily.get("lightSleepSeconds"),
            "awake_seconds": daily.get("awakeSleepSeconds"),
        })
    except Exception as e:
        sleep_records.append({"date": date_str, "error": str(e)})

# ---------------------------------------------------------------------------
# Parse activities into structured dicts
# ---------------------------------------------------------------------------

def parse_activity(a: dict) -> dict:
    duration_s = a.get("duration") or 0
    distance_m = a.get("distance") or 0
    return {
        "date": (a.get("startTimeLocal") or "")[:10],
        "name": a.get("activityName", "Unknown"),
        "type_raw": a.get("activityType", {}).get("typeKey", "unknown"),
        "category": categorize(a.get("activityType", {}).get("typeKey", "")),
        "duration_min": round(duration_s / 60),
        "distance_km": round(distance_m / 1000, 2) if distance_m else None,
        "avg_hr": a.get("averageHR"),
        "max_hr": a.get("maxHR"),
        "calories": a.get("calories"),
        "training_load": a.get("activityTrainingLoad"),
        "aerobic_effect": a.get("aerobicTrainingEffect"),
        "anaerobic_effect": a.get("anaerobicTrainingEffect"),
    }


parsed_activities = [parse_activity(a) for a in all_activities]

# ---------------------------------------------------------------------------
# Rolling averages (28-day)
# ---------------------------------------------------------------------------

def avg(values):
    vals = [v for v in values if v is not None]
    return round(sum(vals) / len(vals), 1) if vals else None


def fmt_duration(seconds):
    if seconds is None:
        return "—"
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    return f"{h}h {m:02d}m"


sleep_28 = [r for r in sleep_records if "error" not in r]

avg_sleep_dur_s = avg([r["duration_seconds"] for r in sleep_28])
avg_sleep_score = avg([r["score"] for r in sleep_28])
avg_hrv = avg([r["hrv_nightly_avg"] for r in sleep_28])
avg_rhr = avg([r["resting_hr"] for r in sleep_28])

# 28-day training volume by category
acts_28 = parsed_activities  # already filtered to 28 days

running_km_28 = sum(a["distance_km"] or 0 for a in acts_28 if a["category"] == "Running")
cycling_km_28 = sum(a["distance_km"] or 0 for a in acts_28 if a["category"] == "Cycling / MTB")
strength_sessions_28 = sum(1 for a in acts_28 if a["category"] == "Strength / Bodybuilding")
other_sessions_28 = sum(1 for a in acts_28 if a["category"] == "Other")

# ---------------------------------------------------------------------------
# Last 7 days slices
# ---------------------------------------------------------------------------

seven_day_dates = [(today - datetime.timedelta(days=i)).isoformat() for i in range(1, 8)]

sleep_7 = [r for r in sleep_records if r.get("date") in seven_day_dates]
sleep_7.sort(key=lambda r: r["date"])

acts_7 = [a for a in parsed_activities if a["date"] in seven_day_dates or a["date"] == today_str]
acts_7.sort(key=lambda a: a["date"])

rest_days_7 = len([d for d in seven_day_dates if not any(a["date"] == d for a in acts_7)])

# ---------------------------------------------------------------------------
# Today's status summary
# ---------------------------------------------------------------------------

yesterday = (today - datetime.timedelta(days=1)).isoformat()
yesterday_sleep = next((r for r in sleep_records if r.get("date") == yesterday), {})

yest_score = yesterday_sleep.get("score")
yest_hrv = yesterday_sleep.get("hrv_nightly_avg")

readiness_flags = []

if yest_score is not None and avg_sleep_score is not None:
    diff = yest_score - avg_sleep_score
    if diff >= 5:
        readiness_flags.append(f"Sleep quality above baseline (+{diff:.0f} pts vs 28-day avg)")
    elif diff <= -5:
        readiness_flags.append(f"Sleep quality below baseline ({diff:.0f} pts vs 28-day avg)")
    else:
        readiness_flags.append(f"Sleep quality near baseline ({yest_score} vs avg {avg_sleep_score})")

if yest_hrv is not None and avg_hrv is not None:
    diff = yest_hrv - avg_hrv
    if diff >= 3:
        readiness_flags.append(f"HRV elevated vs baseline (+{diff:.1f} ms) — good recovery signal")
    elif diff <= -3:
        readiness_flags.append(f"HRV suppressed vs baseline ({diff:.1f} ms) — consider lower intensity")
    else:
        readiness_flags.append(f"HRV near baseline ({yest_hrv} ms vs avg {avg_hrv} ms)")

running_km_7 = sum(a["distance_km"] or 0 for a in acts_7 if a["category"] == "Running")
strength_7 = sum(1 for a in acts_7 if a["category"] == "Strength / Bodybuilding")
cycling_km_7 = sum(a["distance_km"] or 0 for a in acts_7 if a["category"] == "Cycling / MTB")

readiness_flags.append(f"Rest days in last 7: {rest_days_7}")
readiness_flags.append(
    f"This week: {running_km_7:.1f} km running, {cycling_km_7:.1f} km cycling, {strength_7} strength sessions"
)

# ---------------------------------------------------------------------------
# Render markdown
# ---------------------------------------------------------------------------

lines = []

lines.append(f"# Workout Context — {today_str}")
lines.append("")
lines.append("## Athlete Profile")
lines.append(
    "Hybrid athlete balancing **strength training**, **bodybuilding**, **running**, and **mountain biking**. "
    "Use the data below to suggest today's workout, taking into account recovery, training load balance, and recent volume."
)
lines.append("")

# 28-day baselines
lines.append("## 28-Day Baselines")
lines.append("")
lines.append("| Metric | 28-Day Avg |")
lines.append("|--------|-----------|")
lines.append(f"| Sleep duration | {fmt_duration(avg_sleep_dur_s)} |")

lines.append(f"| Sleep score | {avg_sleep_score if avg_sleep_score is not None else '—'} |")
lines.append(f"| Nightly HRV avg | {avg_hrv if avg_hrv is not None else '—'} ms |")
lines.append(f"| Resting HR | {avg_rhr if avg_rhr is not None else '—'} bpm |")
lines.append(f"| Running volume | {running_km_28:.1f} km over 28 days ({running_km_28/4:.1f} km/week avg) |")
lines.append(f"| Cycling volume | {cycling_km_28:.1f} km over 28 days ({cycling_km_28/4:.1f} km/week avg) |")
lines.append(f"| Strength sessions | {strength_sessions_28} sessions over 28 days ({strength_sessions_28/4:.1f}/week avg) |")
lines.append("")

# Sleep — last 7 days
lines.append("## Sleep — Last 7 Days")
lines.append("")
lines.append("| Date | Duration | Score | HRV (nightly) | RHR | Deep | REM |")
lines.append("|------|----------|-------|---------------|-----|------|-----|")

for r in sleep_7:
    if "error" in r:
        lines.append(f"| {r['date']} | *fetch error* | — | — | — | — | — |")
        continue
    total_s = r.get("duration_seconds") or 0
    deep_pct = f"{r['deep_seconds']/total_s*100:.0f}%" if total_s and r.get("deep_seconds") else "—"
    rem_pct = f"{r['rem_seconds']/total_s*100:.0f}%" if total_s and r.get("rem_seconds") else "—"
    lines.append(
        f"| {r['date']} "
        f"| {fmt_duration(r.get('duration_seconds'))} "
        f"| {r.get('score') or '—'} "
        f"| {r.get('hrv_nightly_avg') or '—'} ms "
        f"| {r.get('resting_hr') or '—'} bpm "
        f"| {deep_pct} "
        f"| {rem_pct} |"
    )

lines.append("")

# Training — last 7 days
lines.append("## Training — Last 7 Days")
lines.append("")

all_dates = sorted(set(seven_day_dates + [today_str]))
for date in all_dates:
    day_acts = [a for a in acts_7 if a["date"] == date]
    label = "Today" if date == today_str else date
    if not day_acts:
        lines.append(f"### {label} — Rest Day")
        lines.append("")
        continue
    lines.append(f"### {label}")
    for a in day_acts:
        lines.append(f"- **{a['name']}** ({a['category']})")
        details = []
        details.append(f"{a['duration_min']} min")
        if a["distance_km"]:
            details.append(f"{a['distance_km']} km")
        if a["avg_hr"]:
            details.append(f"Avg HR: {a['avg_hr']} bpm")
        if a["max_hr"]:
            details.append(f"Max HR: {a['max_hr']} bpm")
        if a["calories"]:
            details.append(f"{a['calories']} kcal")
        if a["training_load"]:
            details.append(f"Training Load: {a['training_load']:.0f}")
        if a["aerobic_effect"]:
            details.append(f"Aerobic Effect: {a['aerobic_effect']:.1f}")
        lines.append(f"  - {' | '.join(details)}")
    lines.append("")

# Today's status summary
lines.append("## Today's Readiness Summary")
lines.append("")
for flag in readiness_flags:
    lines.append(f"- {flag}")
lines.append("")
lines.append(
    "> Use the above data to recommend a workout for today. "
    "Consider muscle group balance, cardiovascular load, recovery signals (HRV, sleep score), "
    "and the athlete's hybrid training goals."
)

# ---------------------------------------------------------------------------
# Write output
# ---------------------------------------------------------------------------

output_path = f"data/workout_context_{today_str}.md"
with open(output_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"\nWorkout context saved to: {output_path}")
