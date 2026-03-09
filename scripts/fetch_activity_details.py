"""
Fetches full activity detail JSON for all strength/bodybuilding activities
from the last N days and saves each one to data/activity_<id>_<date>.json.
"""
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

DAYS_BACK = 7

STRENGTH_TYPES = {
    "strength_training",
    "fitness_equipment",
    "indoor_rowing",
    "hiit",
}

client = Garmin(email, password)
client.login()

today = datetime.date.today()
start = (today - datetime.timedelta(days=DAYS_BACK)).isoformat()
end = today.isoformat()

os.makedirs("data", exist_ok=True)

print(f"Fetching activities from {start} to {end}...")
activities = client.get_activities_by_date(start, end)

strength_activities = [
    a for a in activities
    if (a.get("activityType", {}).get("typeKey") or "").lower() in STRENGTH_TYPES
]

print(f"Found {len(strength_activities)} strength activity/activities.")

for a in strength_activities:
    activity_id = a.get("activityId")
    date = (a.get("startTimeLocal") or "")[:10]
    name = a.get("activityName", "Unknown").replace(" ", "_")

    print(f"  Fetching details for: {a.get('activityName')} on {date} (ID: {activity_id})...")
    details = client.get_activity(activity_id)

    filename = f"data/activity_{activity_id}_{date}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(details, f, indent=2)

    print(f"  Saved to {filename}")

print("\nDone.")
