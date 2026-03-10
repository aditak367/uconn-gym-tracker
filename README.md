# UConn Rec Gym Occupancy Tracker

Automatically logs occupancy of the UConn Student Rec Center every 15 minutes and displays it on a public dashboard hosted entirely on GitHub — no server, no cost, no card required.

## How it works

1. **GitHub Actions** runs `logger.py` every 15 minutes
2. `logger.py` connects to SafeSpace via WebSocket, grabs the current occupancy, and appends a row to `data/occupancy.csv`
3. The updated CSV is committed back to the repo automatically
4. **GitHub Pages** serves `docs/index.html` — a dashboard that reads the CSV and renders live charts

## Logging schedule (Eastern Time)

| Day | Hours |
|-----|-------|
| Monday – Friday | 5:00 AM – 10:00 PM |
| Saturday – Sunday | 10:00 AM – 5:00 PM |

Outside these hours the workflow runs but exits immediately without logging.

## Setup (one-time, ~5 minutes)

### 1. Fork or clone this repo

Click **Fork** on GitHub, or:

```bash
git clone https://github.com/YOUR_USERNAME/uconn-gym-tracker.git
cd uconn-gym-tracker
```

### 2. Enable GitHub Actions

Go to your repo → **Actions** tab → click **"I understand my workflows, go ahead and enable them"** if prompted.

### 3. Enable GitHub Pages

Go to your repo → **Settings** → **Pages**:
- Source: **Deploy from a branch**
- Branch: `main` / `docs`
- Click **Save**

GitHub will give you a URL like:
```
https://YOUR_USERNAME.github.io/uconn-gym-tracker/
```

### 4. Give Actions permission to commit

Go to **Settings** → **Actions** → **General** → scroll to **Workflow permissions**:
- Select **Read and write permissions**
- Click **Save**

That's it — the workflow will start running automatically on its next scheduled trigger.

### 5. Test it manually

Go to **Actions** → **Log Gym Occupancy** → **Run workflow** → **Run workflow**

Check the run logs to confirm it fetched occupancy and committed a row to `data/occupancy.csv`.

## Files

```
.github/
  workflows/
    log.yml          # GitHub Actions schedule
logger.py            # Fetches occupancy via WebSocket, appends to CSV
data/
  occupancy.csv      # Auto-generated data file (committed by Actions)
docs/
  index.html         # GitHub Pages dashboard
requirements.txt     # Python deps for the Action
```

## Dashboard

The dashboard at your GitHub Pages URL shows:
- Latest occupancy reading and % capacity
- Today's peak
- Scatter plot of occupancy vs. time of day (filterable by day of week)
- Weekly heatmap (avg occupancy by day × hour)

Refreshes automatically every 5 minutes.
