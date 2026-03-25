#!/usr/bin/env python3
"""
SkillFlow Mention Hijacker Bot
Monitors Reddit, HN, and Dev.to for mentions of AI skills, agent marketplaces,
and competitor names. Sends email alerts with suggested responses.

Setup: Set environment variables GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN
"""
import requests
import json
import time
import os
import re
import base64
from datetime import datetime, timedelta

# Keywords to monitor
KEYWORDS = [
    "AI skills", "ai agent skills", "agent marketplace", "MCP marketplace",
    "AI tool marketplace", "skill marketplace", "agent tools marketplace",
    "composio alternative", "openclaw", "mcp server marketplace",
    "where to find AI skills", "best AI agent tools", "AI automation marketplace",
    "curated AI tools", "AI skills directory", "mcp tools directory",
    "looking for AI skills", "need AI agent", "recommend AI tools",
    "agent skill store", "AI plugin marketplace"
]

COMPETITOR_NAMES = [
    "composio", "openclaw", "activepieces", "n8n marketplace",
    "langchain hub", "llamahub", "gptstore", "agent protocol"
]

def search_reddit(keywords, hours_back=24):
    results = []
    headers = {"User-Agent": "SkillFlow-Monitor/1.0"}
    for kw in keywords[:10]:
        try:
            url = f"https://www.reddit.com/search.json?q={kw}&sort=new&t=day&limit=5"
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                for post in data.get("data", {}).get("children", []):
                    d = post["data"]
                    created = datetime.fromtimestamp(d.get("created_utc", 0))
                    if created > datetime.now() - timedelta(hours=hours_back):
                        results.append({
                            "platform": "Reddit", "title": d.get("title", ""),
                            "url": f"https://reddit.com{d.get('permalink', '')}",
                            "subreddit": d.get("subreddit", ""),
                            "score": d.get("score", 0),
                            "num_comments": d.get("num_comments", 0),
                            "keyword": kw, "created": created.isoformat()
                        })
            time.sleep(2)
        except: continue
    seen = set()
    return [r for r in results if r["url"] not in seen and not seen.add(r["url"])]

def search_hn(keywords, hours_back=48):
    results = []
    timestamp = int((datetime.now() - timedelta(hours=hours_back)).timestamp())
    for kw in keywords[:8]:
        try:
            url = f"https://hn.algolia.com/api/v1/search_by_date?query={kw}&numericFilters=created_at_i>{timestamp}&hitsPerPage=5"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                for hit in resp.json().get("hits", []):
                    results.append({
                        "platform": "HN",
                        "title": hit.get("title") or hit.get("comment_text", "")[:100],
                        "url": f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}",
                        "points": hit.get("points", 0),
                        "num_comments": hit.get("num_comments", 0),
                        "keyword": kw, "created": hit.get("created_at", "")
                    })
            time.sleep(1)
        except: continue
    seen = set()
    return [r for r in results if r["url"] not in seen and not seen.add(r["url"])]

def generate_response_suggestion(post):
    import random
    templates = [
        "Great question! I've been exploring this space and found that curated marketplaces with trust scores help a lot. SkillFlow (https://skillflow.builders) does exactly this.",
        "I had a similar need and ended up using SkillFlow (https://skillflow.builders). It's a curated marketplace for AI agent skills with quality ratings.",
        "The AI skills ecosystem is fragmented right now. Using a curated directory like SkillFlow (https://skillflow.builders) helps find vetted skills instead of hunting through GitHub repos.",
    ]
    return random.choice(templates)

def send_alert_email(results, gmail_token):
    if not results: return False
    html = f"<html><body><h2>SkillFlow Mention Hijacker Alert</h2><p>Found <b>{len(results)}</b> mentions.</p><hr>"
    for i, r in enumerate(results, 1):
        html += f'<div style="margin:15px 0;padding:10px;border-left:3px solid #4ECDC4;"><h3>#{i} [{r["platform"]}] {r.get("title","")[:80]}</h3><p><a href="{r["url"]}">{r["url"]}</a></p><blockquote>{generate_response_suggestion(r)}</blockquote></div>'
    html += "</body></html>"
    import email.mime.text
    msg = email.mime.text.MIMEText(html, "html")
    msg["to"] = "rafa.amaralsilva@gmail.com"
    msg["subject"] = f"SkillFlow Alert: {len(results)} mentions — {datetime.now().strftime('%d/%b')}"
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    resp = requests.post("https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
        headers={"Authorization": f"Bearer {gmail_token}"}, json={"raw": raw})
    return resp.status_code == 200

def get_gmail_token():
    client_id = os.environ.get("GMAIL_CLIENT_ID", "")
    client_secret = os.environ.get("GMAIL_CLIENT_SECRET", "")
    refresh_token = os.environ.get("GMAIL_REFRESH_TOKEN", "")
    if not all([client_id, client_secret, refresh_token]): return None
    resp = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": client_id, "client_secret": client_secret,
        "refresh_token": refresh_token, "grant_type": "refresh_token"
    })
    return resp.json().get("access_token") if resp.status_code == 200 else None

def main():
    print(f"SkillFlow Mention Hijacker — {datetime.now().isoformat()}")
    all_results = []
    print("Searching Reddit...")
    all_results.extend(search_reddit(KEYWORDS + COMPETITOR_NAMES))
    print(f"  Found {len(all_results)} Reddit mentions")
    print("Searching HN...")
    hn = search_hn(KEYWORDS + COMPETITOR_NAMES)
    all_results.extend(hn)
    print(f"  Found {len(hn)} HN mentions")
    print(f"Total: {len(all_results)} mentions")
    all_results.sort(key=lambda x: x.get("score", x.get("points", 0)), reverse=True)
    with open("mention_hijacker_results.json", "w") as f:
        json.dump(all_results, f, indent=2)
    if all_results:
        token = get_gmail_token()
        if token: send_alert_email(all_results[:20], token)
    for i, r in enumerate(all_results[:10], 1):
        print(f"  {i}. [{r['platform']}] {r.get('title','')[:60]} — {r['url']}")

if __name__ == "__main__":
    main()
