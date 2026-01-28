import json
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen


def load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def fetch_access_token(corpid: str, corpsecret: str, base_url: str) -> dict:
    params = {"corpid": corpid, "corpsecret": corpsecret}
    url = f"{base_url.rstrip('/')}/cgi-bin/gettoken?{urlencode(params)}"
    with urlopen(url, timeout=10) as resp:
        body = resp.read().decode("utf-8")
    return json.loads(body)


def read_cached_token(path: Path, skew_seconds: int = 60) -> str | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    token = data.get("access_token")
    expires_at = data.get("expires_at")
    if not token or not isinstance(expires_at, (int, float)):
        return None
    if time.time() + skew_seconds >= float(expires_at):
        return None
    return token


def write_cached_token(path: Path, access_token: str, expires_in: int) -> None:
    expires_at = int(time.time() + int(expires_in))
    payload = {
        "access_token": access_token,
        "expires_at": expires_at,
        "expires_at_iso": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(expires_at)),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def get_access_token(cfg: dict) -> tuple[str | None, dict]:
    corpid = cfg.get("corpid")
    corpsecret = cfg.get("corpsecret")
    base_url = cfg.get("base_url", "https://qyapi.weixin.qq.com")
    cache_file = Path(cfg.get("token_cache_file", "token_cache.json"))

    if not corpid or not corpsecret:
        return None, {"errcode": 1, "errmsg": "Missing required config fields: corpid, corpsecret"}

    cached = read_cached_token(cache_file)
    if cached:
        return cached, {"errcode": 0, "access_token": cached, "from_cache": True}

    data = fetch_access_token(corpid, corpsecret, base_url)
    if data.get("errcode") == 0 and data.get("access_token") and data.get("expires_in"):
        write_cached_token(cache_file, data["access_token"], data["expires_in"])
        return data["access_token"], data
    return None, data
