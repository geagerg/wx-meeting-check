import json
import sys
import time
from datetime import datetime, timedelta, time as dt_time
from pathlib import Path
from urllib.request import Request, urlopen

from get_access_token import get_access_token, load_config


def post_json(url: str, payload: dict) -> dict:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = Request(url, data=data, headers={"Content-Type": "application/json"})
    with urlopen(req, timeout=15) as resp:
        body = resp.read().decode("utf-8")
    return json.loads(body)


def get_user_meeting_ids(
    access_token: str,
    base_url: str,
    userid: str,
    begin_time: int,
    end_time: int,
    limit: int,
) -> list[str]:
    url = f"{base_url.rstrip('/')}/cgi-bin/meeting/get_user_meetingid?access_token={access_token}"
    cursor = ""
    meeting_ids: list[str] = []

    while True:
        payload = {
            "userid": userid,
            "cursor": cursor,
            "begin_time": begin_time,
            "end_time": end_time,
            "limit": limit,
        }
        data = post_json(url, payload)
        if data.get("errcode") != 0:
            raise RuntimeError(f"get_user_meetingid failed: {data}")
        meeting_ids.extend(data.get("meetingid_list", []))
        cursor = data.get("next_cursor")
        if not cursor:
            break

    return meeting_ids


def get_meeting_info(access_token: str, base_url: str, meetingid: str) -> dict:
    url = f"{base_url.rstrip('/')}/cgi-bin/meeting/get_info?access_token={access_token}"
    data = post_json(url, {"meetingid": meetingid})
    if data.get("errcode") != 0:
        raise RuntimeError(f"get_info failed for {meetingid}: {data}")
    return data


def format_meeting_title(info: dict) -> str:
    title = info.get("title") or info.get("meeting_title") or ""
    meeting_start = info.get("meeting_start")
    if isinstance(meeting_start, (int, float)):
        start_text = time.strftime("%H:%M", time.localtime(meeting_start))
        return f"{start_text} {title}".strip()
    return title.strip() or "<no title>"


def build_message(today_titles: list[str], tomorrow_titles: list[str]) -> str:
    today_date = datetime.now().strftime("%Y-%m-%d")
    tomorrow_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    lines = [f"今日会议（{today_date}）共 {len(today_titles)} 个："]
    if today_titles:
        lines.extend([f"- {item}" for item in today_titles])
    else:
        lines.append("- 无")

    lines.append("")
    lines.append(f"明日会议（{tomorrow_date}）共 {len(tomorrow_titles)} 个：")
    if tomorrow_titles:
        lines.extend([f"- {item}" for item in tomorrow_titles])
    else:
        lines.append("- 无")

    return "\n".join(lines)


def send_webhook(webhook_url: str, content: str) -> dict:
    payload = {"msgtype": "text", "text": {"content": content}}
    return post_json(webhook_url, payload)


def main() -> int:
    config_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("config.json")
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        print("Tip: copy config_example.json to config.json and fill in values.")
        return 1

    cfg = load_config(config_path)
    base_url = cfg.get("base_url", "https://qyapi.weixin.qq.com")
    userid = cfg.get("userid")
    limit = int(cfg.get("meeting_list_limit", 100))
    webhook_url = cfg.get("webhook_url")

    if not userid:
        print("Missing required config fields: userid")
        return 1
    if not webhook_url:
        print("Missing required config fields: webhook_url")
        return 1

    access_token, token_data = get_access_token(cfg)
    if not access_token:
        print(json.dumps(token_data, ensure_ascii=False, indent=2))
        return 2

    today = datetime.now().date()
    today_start = int(datetime.combine(today, dt_time(0, 0, 0)).timestamp())
    today_end = int(datetime.combine(today, dt_time(23, 59, 59)).timestamp())
    tomorrow = today + timedelta(days=1)
    tomorrow_start = int(datetime.combine(tomorrow, dt_time(0, 0, 0)).timestamp())
    tomorrow_end = int(datetime.combine(tomorrow, dt_time(23, 59, 59)).timestamp())

    try:
        today_ids = get_user_meeting_ids(access_token, base_url, userid, today_start, today_end, limit)
        tomorrow_ids = get_user_meeting_ids(access_token, base_url, userid, tomorrow_start, tomorrow_end, limit)
    except RuntimeError as exc:
        print(str(exc))
        return 2

    today_titles: list[str] = []
    for meetingid in today_ids:
        try:
            info = get_meeting_info(access_token, base_url, meetingid)
        except RuntimeError as exc:
            print(str(exc))
            continue
        today_titles.append(format_meeting_title(info))

    tomorrow_titles: list[str] = []
    for meetingid in tomorrow_ids:
        try:
            info = get_meeting_info(access_token, base_url, meetingid)
        except RuntimeError as exc:
            print(str(exc))
            continue
        tomorrow_titles.append(format_meeting_title(info))

    content = build_message(today_titles, tomorrow_titles)
    resp = send_webhook(webhook_url, content)
    print(json.dumps(resp, ensure_ascii=False, indent=2))
    return 0 if resp.get("errcode") == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
