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

today = datetime.date.today().isoformat()

os.makedirs("data", exist_ok=True)

# Sleep data
sleep = client.get_sleep_data(today)
sleep_filename = f"data/sleep_{today}.json"

with open(sleep_filename, "w", encoding="utf-8") as f:
    json.dump(sleep, f, indent=2)

print(f"Saved sleep data to {sleep_filename}")

# Activity / workout data
start_date = today
end_date = today

activities = client.get_activities_by_date(start_date, end_date)
activities_filename = f"data/activities_{today}.json"

with open(activities_filename, "w", encoding="utf-8") as f:
    json.dump(activities, f, indent=2)

print(f"Saved {len(activities)} activities to {activities_filename}")