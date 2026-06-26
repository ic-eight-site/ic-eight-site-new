import urllib.request
import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
from datetime import datetime, timezone

KEYWORDS = [
    "localization",
    "translation",
    "i18n",
    "l10n",
    "LLM",
    "UX copy",
    "localization pipeline",
]

GMAIL_USER = os.environ["GMAIL_USER"]
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]
TO_EMAIL = os.environ.get("TO_EMAIL", "hello@ic-eight.com")

def fetch_hn(keyword, tag):
    url = f"https://hn.algolia.com/api/v1/search?query={urllib.parse.quote(keyword)}&tags={tag}&hitsPerPage=20"
    with urllib.request.urlopen(url) as r:
        return json.loads(r.read())["hits"]

def scan():
    import urllib.parse
    now = datetime.now(timezone.utc).timestamp()
    seen = set()
    fresh = []

    for keyword in KEYWORDS:
        for tag in ["story", "ask_hn", "show_hn"]:
            try:
                hits = fetch_hn(keyword, tag)
                for h in hits:
                    if h["objectID"] in seen:
                        continue
                    seen.add(h["objectID"])
                    age_days = (now - h["created_at_i"]) / 86400
                    if age_days <= 14:
                        fresh.append({
                            "title": h.get("title", ""),
                            "url": f"https://news.ycombinator.com/item?id={h['objectID']}",
                            "points": h.get("points", 0),
                            "comments": h.get("num_comments", 0),
                            "age_days": round(age_days, 1),
                            "keyword": keyword,
                            "tag": tag,
                        })
            except Exception as e:
                print(f"Error fetching {keyword}/{tag}: {e}")

    fresh.sort(key=lambda x: x["age_days"])
    return fresh

def build_email(threads):
    today = datetime.now().strftime("%Y-%m-%d")

    if not threads:
        body_html = "<p>今日は新しいスレなしにゃ。明日また確認するにゃ！</p>"
        body_text = "今日は新しいスレなしにゃ。明日また確認するにゃ！"
    else:
        rows_html = ""
        rows_text = ""
        for t in threads:
            tag_label = {"ask_hn": "Ask HN", "show_hn": "Show HN", "story": "Story"}.get(t["tag"], t["tag"])
            rows_html += f"""
            <tr>
              <td style="padding:10px; border-bottom:1px solid #d8d4cc;">
                <a href="{t['url']}" style="color:#c84b2f; font-weight:500; text-decoration:none;">{t['title']}</a><br>
                <span style="font-size:12px; color:#7a7670;">
                  [{tag_label}] キーワード: {t['keyword']} &nbsp;|&nbsp;
                  ▲ {t['points']} pts &nbsp;|&nbsp;
                  💬 {t['comments']} コメント &nbsp;|&nbsp;
                  🕐 {t['age_days']}日前
                </span>
              </td>
            </tr>"""
            rows_text += f"- {t['title']}\n  {t['url']}\n  [{tag_label}] {t['keyword']} | {t['points']}pts | {t['comments']}コメント | {t['age_days']}日前\n\n"

        body_html = f"""
        <table style="width:100%; border-collapse:collapse; font-family:sans-serif;">
          {rows_html}
        </table>"""
        body_text = rows_text

    html = f"""
    <html><body style="background:#f5f2ec; padding:20px; font-family:sans-serif;">
      <h2 style="font-family:Georgia,serif; font-weight:400; color:#1a1a18;">HN Scanner — {today}</h2>
      <p style="color:#7a7670; font-size:14px;">14日以内の新着スレ: <strong>{len(threads)}件</strong></p>
      <div style="background:#fff; border-radius:8px; border:1px solid #d8d4cc; overflow:hidden; margin-top:16px;">
        {body_html}
      </div>
      <p style="color:#7a7670; font-size:12px; margin-top:16px;">IC Eight HN Scanner 自動配信にゃ 😼</p>
    </body></html>"""

    return html, body_text

def send_email(threads):
    html, text = build_email(threads)
    today = datetime.now().strftime("%Y-%m-%d")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"HN Scanner {today} — {len(threads)}件の新着スレにゃ 😼"
    msg["From"] = GMAIL_USER
    msg["To"] = TO_EMAIL
    msg.attach(MIMEText(text, "plain"))
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_USER, TO_EMAIL, msg.as_string())
    print(f"メール送信完了にゃ: {len(threads)}件")

if __name__ == "__main__":
    print("スキャン開始にゃ…")
    threads = scan()
    print(f"{len(threads)}件見つかったにゃ")
    send_email(threads)
