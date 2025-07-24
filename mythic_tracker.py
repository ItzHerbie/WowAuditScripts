import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests
import os
import json

# --- CONFIG ---
GOOGLE_SHEET_KEY = os.environ["GOOGLE_SHEET_KEY"]
SHEET_GID = "0"  # GID for "Overview" tab
DISCORD_WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]
DISCORD_ROLE_ID = os.environ["DISCORD_ROLE_ID"]
CREDS_FILE = "creds.json"

# --- AUTHENTICATE ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(CREDS_FILE, scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(GOOGLE_SHEET_KEY).worksheet("Overview")

# --- READ PLAYER DATA ---
data = sheet.get_all_values()
data = data[1:]  # Skip header row

# --- GROUP BUCKETS ---
group_0 = []
group_1_5 = []
group_6_10 = []
group_11_15 = []
group_16_plus = []

# --- BUILD ENTRIES ---
for idx, row in enumerate(data, start=2):  # Row 2 = first data row
    try:
        name = row[0].strip()  # Column A = index 0
        this_week_raw = row[70] if len(row) > 70 else ""
        this_week = int(this_week_raw) if this_week_raw.strip().isdigit() else 0
    except Exception as e:
        print(f"Skipping row {idx} due to error: {e}")
        continue

    if not name:
        continue

    entry = f"{name} ({this_week} dungeons)"

    if this_week == 0:
        group_0.append(f"⚠️ {entry}")
    elif this_week <= 5:
        group_1_5.append(f"🟡 {entry}")
    elif this_week <= 10:
        group_6_10.append(f"🟢 {entry}")
    elif this_week <= 15:
        group_11_15.append(f"🔵 {entry}")
    else:
        group_16_plus.append(f"🏆 {entry}")

# --- BUILD MESSAGE CONTENT ---
sections = []

if group_0:
    sections.append("**⚠️ Players with 0 runs:**\n" + "\n".join(group_0))
if group_1_5:
    sections.append("**🟡 Players with 1–5 runs:**\n" + "\n".join(group_1_5))
if group_6_10:
    sections.append("**🟢 Players with 6–10 runs:**\n" + "\n".join(group_6_10))
if group_11_15:
    sections.append("**🔵 Players with 11–15 runs:**\n" + "\n".join(group_11_15))
if group_16_plus:
    sections.append("**🏆 Players with 16+ runs:**\n" + "\n".join(group_16_plus))

full_message = "\n\n".join(sections) if sections else "No valid player data found."

# --- SEND TO DISCORD ---
def send_to_discord(content, mention_role=False):
    if not content.strip():
        return

    payload = {
        "content": f"<@&{DISCORD_ROLE_ID}>\n{content}" if mention_role else content,
        "allowed_mentions": {
            "parse": [],
            "roles": [DISCORD_ROLE_ID] if mention_role else []
        }
    }

    response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
    if response.status_code == 204:
        print("✅ Posted chunk to Discord.")
    else:
        print(f"❌ Discord post failed: {response.status_code} - {response.text}")

# --- SPLIT AND POST ---
chunks = [full_message[i:i+1900] for i in range(0, len(full_message), 1900)]
for i, chunk in enumerate(chunks):
    send_to_discord(chunk, mention_role=(i == 0))  # Only @ on first message
