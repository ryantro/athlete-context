# athlete-context

Pulls training and recovery data from Garmin Connect and generates a structured markdown file for use as context in AI-assisted workout planning.

## What it does

Fetches 28 days of activity and sleep data from your Garmin account and produces a daily markdown report (`data/workout_context_<date>.md`) containing:

- 28-day baselines (sleep, HRV, resting HR, training volume)
- Acute:Chronic Training Load ratio (ATL/CTL)
- Sleep quality for the last 7 days
- Aerobic efficiency trend for recent runs
- Strength volume (sets/reps) for the last 7 days
- Full training log for the last 7 days
- Today's readiness summary

Paste the output into any AI assistant to get a workout recommendation grounded in your actual data.

## Setup

1. Clone the repo and create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the project root:
   ```
   GARMIN_EMAIL=your@email.com
   GARMIN_PASSWORD=yourpassword
   ```

## Usage

Generate today's workout context:
```bash
python scripts/generate_workout_context.py
```

Fetch raw strength activity details (for debugging):
```bash
python scripts/fetch_activity_details.py
```

Test Garmin connectivity and dump today's raw data:
```bash
python scripts/test_garmin.py
```

Output files are written to the `data/` directory (gitignored).

## Project structure

```
scripts/
  generate_workout_context.py  # main script — generates the context file
  fetch_activity_details.py    # fetches raw strength activity JSON
  test_garmin.py               # connectivity test, dumps today's data
data/                          # output files (gitignored)
```
