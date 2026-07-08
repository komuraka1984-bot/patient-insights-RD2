import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

APP_TITLE = "Shirabeo Ops"
APP_VERSION = "Ops Dashboard v0.1"
JST = timezone(timedelta(hours=9))

# This app is for operational monitoring only.
# Do not show individual patient answers or direct personal identifiers here.
DEFAULT_CSV_TARGETS = [
    {"name": "RD ADCT", "path": "data/rd_adct_responses.csv", "instrument": "ADCT"},
    {"name": "RD DLQI", "path": "data/rd_dlqi_responses.csv", "instrument": "DLQI"},
]

DEFAULT_APP_URLS = [
    {"name": "RD2 / Ops", "url": os.getenv("RENDER_EXTERNAL_URL", "")},
    {"name": "RD4", "url": "https://patient-insights-rd4.onrender.com"},
    {"name": "RD5", "url": ""},
    {"name": "AD", "url": ""},
    {"name": "UCT", "url": ""},
    {"name": "DLQI", "url": ""},
]


def get_secret(name: str, default: str | None = None) -> str | None:
    try:
        if name in st.secrets:
            return str(st.secrets[name])
    except Exception:
        pass
    return os.getenv(name, default)


def now_jst() -> datetime:
    return datetime.now(JST)


def parse_timestamp_column(df: pd.DataFrame) -> pd.Series:
    if "timestamp" not in df.columns:
        return pd.Series(pd.NaT, index=df.index)
    return pd.to_datetime(df["timestamp"], errors="coerce")


def summarize_csv(target: dict) -> dict:
    path = Path(target["path"])
    summary = {
        "name": target["name"],
        "instrument": target.get("instrument", ""),
        "path": str(path),
        "exists": path.exists(),
        "status": "missing",
        "total_count": 0,
        "today_count": 0,
        "latest_time": "—",
        "priority_count": 0,
        "error": "",
    }

    if not path.exists():
        return summary

    try:
        df = pd.read_csv(path, on_bad_lines="skip")
    except Exception as exc:
        summary["status"] = "read_error"
        summary["error"] = str(exc)
        return summary

    if df.empty:
        summary["status"] = "empty"
        return summary

    ts = parse_timestamp_column(df)
    today = now_jst().date()

    summary["status"] = "ok"
    summary["total_count"] = int(len(df))
    summary["today_count"] = int((ts.dt.date == today).sum()) if ts.notna().any() else 0
    summary["latest_time"] = ts.dropna().max().strftime("%Y-%m-%d %H:%M") if ts.notna().any() else "不明"

    instrument = str(target.get("instrument", "")).upper()
    if instrument == "ADCT":
        if "decision" in df.columns:
            summary["priority_count"] = int((df["decision"].astype(str) == "非維持").sum())
        elif "total_score" in df.columns:
            scores = pd.to_numeric(df["total_score"], errors="coerce")
            summary["priority_count"] = int((scores >= 7).sum())
    elif instrument == "DLQI" and "total_score" in df.columns:
        scores = pd.to_numeric(df["total_score"], errors="coerce")
        summary["priority_count"] = int((scores >= 11).sum())

    return summary


def parse_app_urls() -> list[dict]:
    """
    Optional environment variable:
    OPS_APP_URLS="RD4|https://...,RD5|https://...,UCT|https://..."
    """
    raw = get_secret("OPS_APP_URLS", "") or ""
    custom = []
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        if "|" in item:
            name, url = item.split("|", 1)
        else:
            name, url = item, item
        custom.append({"name": name.strip(), "url": url.strip()})

    if custom:
        return custom
    return [app for app in DEFAULT_APP_URLS if app.get("url")]


def check_url(name: str, url: str) -> dict:
    result = {
        "name": name,
        "url": url,
        "status": "not_configured" if not url else "unknown",
        "status_code": "—",
        "latency_ms": "—",
        "checked_at": now_jst().strftime("%Y-%m-%d %H:%M:%S"),
        "error": "",
    }
    if not url:
        return result

    started = datetime.now()
    try:
        response = requests.get(url, timeout=8)
        elapsed = datetime.now() - started
        result["status_code"] = response.status_code
        result["latency_ms"] = int(elapsed.total_seconds() * 1000)
        result["status"] = "ok" if response.status_code < 500 else "server_error"
    except Exception as exc:
        result["status"] = "request_error"
        result["error"] = str(exc)
    return result


def status_icon(status: str) -> str:
    if status == "ok":
        return "🟢"
    if status in {"empty", "missing", "not_configured"}:
        return "⚪"
    return "🔴"


def require_admin() -> bool:
    configured_password = get_secret("ADMIN_PASSWORD")
    if not configured_password:
        st.warning("ADMIN_PASSWORD が未設定です。Render の Environment に設定してください。")
        return False

    password = st.text_input("管理者パスワード", type="password")
    if password == configured_password:
        return True
    if password:
        st.error("パスワードが違います。")
    return False


def render_header():
    st.set_page_config(page_title=APP_TITLE, page_icon="🛰️", layout="wide")
    st.title("🛰️ Shirabeo Ops")
    st.caption(f"{APP_VERSION} | 運用監視用ダッシュボード")
    st.info(
        "この画面はShirabeo Labs運営者用です。患者個別の回答内容は表示せず、件数・時刻・稼働状態のみを確認します。"
    )


def render_system_health():
    st.subheader("システム稼働確認")
    apps = parse_app_urls()

    if not apps:
        st.info("監視対象URLが未設定です。OPS_APP_URLS に name|url をカンマ区切りで設定できます。")
        return

    if st.button("URLヘルスチェックを実行", use_container_width=True):
        st.session_state["health_results"] = [check_url(app["name"], app["url"]) for app in apps]

    results = st.session_state.get("health_results")
    if not results:
        st.caption("ボタンを押すと、登録URLの応答を確認します。")
        return

    rows = []
    for r in results:
        rows.append({
            "状態": f"{status_icon(r['status'])} {r['status']}",
            "アプリ": r["name"],
            "HTTP": r["status_code"],
            "応答ms": r["latency_ms"],
            "確認時刻": r["checked_at"],
            "エラー": r["error"],
        })
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)


def render_csv_overview():
    st.subheader("入力件数・最終入力")
    summaries = [summarize_csv(target) for target in DEFAULT_CSV_TARGETS]

    total_today = sum(s["today_count"] for s in summaries)
    total_all = sum(s["total_count"] for s in summaries)
    total_priority = sum(s["priority_count"] for s in summaries)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("本日の入力", total_today)
    c2.metric("総入力", total_all)
    c3.metric("確認優先", total_priority)
    c4.metric("最終更新", now_jst().strftime("%H:%M"))

    rows = []
    for s in summaries:
        rows.append({
            "状態": f"{status_icon(s['status'])} {s['status']}",
            "データ": s["name"],
            "総件数": s["total_count"],
            "本日": s["today_count"],
            "確認優先": s["priority_count"],
            "最新入力": s["latest_time"],
            "CSV": s["path"],
            "エラー": s["error"],
        })
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)


def render_notes():
    st.subheader("運用メモ")
    st.markdown(
        """
- ここでは患者個別回答・設問別回答は表示しません。
- 監視対象URLは Render の Environment で `OPS_APP_URLS` に設定できます。
- 例：`RD4|https://patient-insights-rd4.onrender.com,RD5|https://...`
- CSVがRenderの一時ストレージ上にある場合、再デプロイ・再起動で消える可能性があります。将来は永続ストレージまたは外部DB化が必要です。
        """
    )


def main():
    render_header()

    if not require_admin():
        st.stop()

    tab1, tab2, tab3 = st.tabs(["Overview", "Health Check", "Notes"])
    with tab1:
        render_csv_overview()
    with tab2:
        render_system_health()
    with tab3:
        render_notes()

    st.caption("Developed and operated by Shirabeo Labs.")


if __name__ == "__main__":
    main()
