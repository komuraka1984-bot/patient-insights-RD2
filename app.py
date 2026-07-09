import os
from datetime import datetime, timezone, timedelta
from io import StringIO
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

APP_TITLE = "Shirabeo Ops"
APP_VERSION = "Ops Dashboard v0.2"
JST = timezone(timedelta(hours=9))

# This app is for operational monitoring only.
# Do not show individual patient answers or direct personal identifiers here.
DEFAULT_CSV_TARGETS = [
    {"name": "RD ADCT", "path": "data/rd_adct_responses.csv", "instrument": "ADCT"},
    {"name": "RD UCT", "path": "data/rd_uct_responses.csv", "instrument": "UCT"},
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


def status_icon(status: str) -> str:
    if status == "ok":
        return "🟢"
    if status in {"empty", "missing", "not_configured"}:
        return "⚪"
    return "🔴"


def read_score(row: pd.Series, instrument: str):
    instrument = str(instrument).upper()
    candidates = [
        "total_score",
        "total",
        f"{instrument.lower()}_total",
    ]
    for col in candidates:
        if col in row.index:
            value = row.get(col)
            if pd.notna(value) and str(value) != "":
                return value
    return ""


def normalize_submission_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize RD local CSV and MASTER Google Sheet columns into one Ops schema."""
    if df.empty:
        return pd.DataFrame(columns=[
            "timestamp", "visit_date", "facility_id", "disease", "instrument",
            "anonymous_id", "total_score", "max_score", "decision", "input_ease",
            "input_support", "source",
        ])

    normalized_rows = []
    for _, row in df.iterrows():
        instrument = str(row.get("instrument", row.get("scale", "")) or "").upper()
        if not instrument:
            # Try to infer from populated total columns in the MASTER sheet.
            if pd.notna(row.get("adct_total", None)) and str(row.get("adct_total", "")) != "":
                instrument = "ADCT"
            elif pd.notna(row.get("uct_total", None)) and str(row.get("uct_total", "")) != "":
                instrument = "UCT"
            elif pd.notna(row.get("dlqi_total", None)) and str(row.get("dlqi_total", "")) != "":
                instrument = "DLQI"
            else:
                instrument = "UNKNOWN"

        timestamp = row.get("timestamp", row.get("input_submitted_at", ""))
        timestamp_text = "" if pd.isna(timestamp) else str(timestamp)
        visit_date = row.get("visit_date", "")
        if (pd.isna(visit_date) or str(visit_date) == "") and timestamp_text:
            visit_date = timestamp_text[:10]

        normalized_rows.append({
            "timestamp": timestamp,
            "visit_date": visit_date,
            "facility_id": row.get("facility_id", row.get("site_id", "")),
            "disease": row.get("disease", ""),
            "instrument": instrument,
            "anonymous_id": row.get("anonymous_id", row.get("visit_code", "")),
            "total_score": read_score(row, instrument),
            "max_score": row.get("max_score", ""),
            "decision": row.get("doctor_check", row.get("decision", "")),
            "input_ease": row.get("input_ease", ""),
            "input_support": row.get("input_support", ""),
            "source": row.get("source", "MASTER"),
        })

    out = pd.DataFrame(normalized_rows)
    out["timestamp"] = pd.to_datetime(out["timestamp"], errors="coerce")
    out["total_score_numeric"] = pd.to_numeric(out["total_score"], errors="coerce")
    return out


@st.cache_data(ttl=60)
def load_master_csv(master_csv_url: str) -> tuple[pd.DataFrame, str]:
    if not master_csv_url:
        return pd.DataFrame(), "MASTER_CSV_URL is not set."

    try:
        response = requests.get(master_csv_url, timeout=20)
        response.raise_for_status()
        df = pd.read_csv(StringIO(response.text), on_bad_lines="skip")
        return normalize_submission_dataframe(df), ""
    except Exception as exc:
        return pd.DataFrame(), str(exc)


def load_local_csvs() -> tuple[pd.DataFrame, list[str]]:
    frames = []
    errors = []

    for target in DEFAULT_CSV_TARGETS:
        path = Path(target["path"])
        if not path.exists():
            continue
        try:
            df = pd.read_csv(path, on_bad_lines="skip")
            df["source"] = target["name"]
            frames.append(df)
        except Exception as exc:
            errors.append(f"{target['name']}: {exc}")

    if not frames:
        return pd.DataFrame(), errors

    raw = pd.concat(frames, ignore_index=True)
    return normalize_submission_dataframe(raw), errors


def count_priority(df: pd.DataFrame) -> int:
    if df.empty:
        return 0

    priority = pd.Series(False, index=df.index)
    instrument = df["instrument"].astype(str).str.upper()
    scores = pd.to_numeric(df["total_score"], errors="coerce")
    decisions = df["decision"].astype(str)

    priority |= (instrument == "ADCT") & ((decisions == "非維持") | (scores >= 7))
    priority |= (instrument == "UCT") & (scores < 12)
    priority |= (instrument == "DLQI") & (scores >= 11)
    return int(priority.sum())


def summarize_dataframe(df: pd.DataFrame) -> dict:
    summary = {
        "status": "missing",
        "total_count": 0,
        "today_count": 0,
        "latest_time": "—",
        "priority_count": 0,
        "instrument_counts": {},
    }

    if df.empty:
        summary["status"] = "empty"
        return summary

    ts = pd.to_datetime(df["timestamp"], errors="coerce") if "timestamp" in df.columns else pd.Series(pd.NaT, index=df.index)
    today = now_jst().date()

    summary["status"] = "ok"
    summary["total_count"] = int(len(df))
    summary["today_count"] = int((ts.dt.date == today).sum()) if ts.notna().any() else 0
    summary["latest_time"] = ts.dropna().max().strftime("%Y-%m-%d %H:%M") if ts.notna().any() else "不明"
    summary["priority_count"] = count_priority(df)
    summary["instrument_counts"] = df["instrument"].fillna("UNKNOWN").astype(str).value_counts().to_dict()
    return summary


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
        df = normalize_submission_dataframe(df)
    except Exception as exc:
        summary["status"] = "read_error"
        summary["error"] = str(exc)
        return summary

    if df.empty:
        summary["status"] = "empty"
        return summary

    instrument_df = df[df["instrument"].astype(str).str.upper() == str(target.get("instrument", "")).upper()]
    if instrument_df.empty:
        instrument_df = df

    s = summarize_dataframe(instrument_df)
    summary.update({
        "status": s["status"],
        "total_count": s["total_count"],
        "today_count": s["today_count"],
        "latest_time": s["latest_time"],
        "priority_count": s["priority_count"],
    })
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


def render_master_overview():
    st.subheader("MASTER入力件数・最終入力")

    master_csv_url = get_secret("MASTER_CSV_URL", "") or ""
    use_local_fallback = False

    if st.button("MASTERを再読み込み", use_container_width=True):
        load_master_csv.clear()

    if master_csv_url:
        df, error = load_master_csv(master_csv_url)
        source_label = "Google Sheet MASTER"
        if error:
            st.error(f"MASTER_CSV_URL の読み込みに失敗しました: {error}")
    else:
        df, local_errors = load_local_csvs()
        error = ""
        use_local_fallback = True
        source_label = "Ops local CSV fallback"
        st.warning("MASTER_CSV_URL が未設定です。現在はOps内ローカルCSVを確認しています。")
        for local_error in local_errors:
            st.error(local_error)

    summary = summarize_dataframe(df)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("本日の入力", summary["today_count"])
    c2.metric("総入力", summary["total_count"])
    c3.metric("確認優先", summary["priority_count"])
    c4.metric("最新入力", summary["latest_time"])

    st.caption(f"データソース：{source_label}")

    counts = summary.get("instrument_counts", {})
    if counts:
        count_rows = [{"質問票": key, "件数": value} for key, value in counts.items()]
        st.dataframe(pd.DataFrame(count_rows), hide_index=True, use_container_width=True)

    if df.empty:
        st.info("表示できる入力データがありません。")
        return

    st.markdown("### 最近の入力")
    recent_cols = [
        "timestamp", "facility_id", "instrument", "disease", "anonymous_id",
        "total_score", "max_score", "decision", "input_ease", "input_support",
    ]
    display_cols = [col for col in recent_cols if col in df.columns]
    recent = df.sort_values("timestamp", ascending=False, na_position="last").head(30)
    st.dataframe(recent[display_cols], hide_index=True, use_container_width=True)

    if use_local_fallback:
        st.markdown("### ローカルCSV別")
        render_local_csv_overview()


def render_local_csv_overview():
    summaries = [summarize_csv(target) for target in DEFAULT_CSV_TARGETS]
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
- Ops v0.2 は `MASTER_CSV_URL` が設定されている場合、Google Sheet MASTERのCSVを優先して読みます。
- `MASTER_CSV_URL` が未設定の場合は、従来どおりOps自身のローカルCSVを確認します。
- RD4の入力はRD4自身のCSVに保存され、Google Sheet MASTERへ送信されます。Opsで一元監視するにはMASTER CSV URLの設定が必要です。
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
        render_master_overview()
    with tab2:
        render_system_health()
    with tab3:
        render_notes()

    st.caption("Developed and operated by Shirabeo Labs.")


if __name__ == "__main__":
    main()
