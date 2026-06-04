import os
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st
import requests


APP_TITLE = "Shirabeo Labs | Patient Insight"

CSV_PATH_ADCT = Path("data/rd_adct_responses.csv")
CSV_PATH_DLQI = Path("data/rd_dlqi_responses.csv")

ADMIN_EMAIL = "komura@shirabeo.com"
CONTACT_EMAIL = "contact@shirabeo.com"

APP_VERSION = "Patient Insight Demo v0.9"

JST = timezone(timedelta(hours=9))


def send_to_google_form(row):
    url = "https://docs.google.com/forms/d/e/1FAIpQLScC3M0830zqkGnnNsD8D_lOFoRwzyqFrd0ljMP6tAB530Jp1w/formResponse"

    data = {
        "entry.1599902592": row.get("visit_code", ""),
        "entry.1495391757": row.get("total_score", ""),
        "entry.1432435158": row.get("decision", ""),
        "entry.1577092948": row.get("timestamp", ""),
    }

    try:
        res = requests.post(url, data=data, timeout=10)
        print("FORM STATUS:", res.status_code)
        return res.status_code in [200, 302]
    except Exception as e:
        print("FORM ERROR:", e)
        return False


DLQI_QUESTIONS_JA = [
    "この1週間で、皮膚のかゆみ・痛み・ヒリヒリ感・しみる感じはどの程度ありましたか？",
    "この1週間で、皮膚のために恥ずかしい、または人目が気になると感じたことはどの程度ありましたか？",
    "この1週間で、皮膚のために買い物、家事、庭仕事などにどの程度支障がありましたか？",
    "この1週間で、皮膚のために着る服にどの程度影響がありましたか？",
    "この1週間で、皮膚のために社交・余暇活動にどの程度影響がありましたか？",
    "この1週間で、皮膚のためにスポーツがどの程度困難でしたか？",
    "この1週間で、皮膚のために仕事や勉強ができませんでしたか？",
    "この1週間で、皮膚のために配偶者、友人、家族との関係にどの程度問題がありましたか？",
    "この1週間で、皮膚のために性的な困難がどの程度ありましたか？",
    "この1週間で、皮膚の治療がどの程度問題になりましたか？ 例：家が汚れる、時間がかかるなど。",
]

DLQI_QUESTIONS_EN = [
    "Over the last week, how itchy, sore, painful or stinging has your skin been?",
    "Over the last week, how embarrassed or self-conscious have you been because of your skin?",
    "Over the last week, how much has your skin interfered with you going shopping or looking after your home or garden?",
    "Over the last week, how much has your skin influenced the clothes you wear?",
    "Over the last week, how much has your skin affected any social or leisure activities?",
    "Over the last week, how much has your skin made it difficult for you to do any sport?",
    "Over the last week, has your skin prevented you from working or studying?",
    "Over the last week, how much has your skin created problems with your partner or any of your close friends or relatives?",
    "Over the last week, how much has your skin caused any sexual difficulties?",
    "Over the last week, how much of a problem has the treatment for your skin been, for example by making your home messy, or by taking up time?",
]

DLQI_OPTIONS_JA = {
    "全くない / 該当しない": 0,
    "少し": 1,
    "かなり": 2,
    "非常に": 3,
}

DLQI_OPTIONS_EN = {
    "Not at all / Not relevant": 0,
    "A little": 1,
    "A lot": 2,
    "Very much": 3,
}

DLQI_Q7_OPTIONS_JA = {
    "はい、仕事または勉強ができなかった": 3,
    "いいえ、ただし仕事または勉強に支障があった": 2,
    "いいえ": 0,
    "該当しない": 0,
}

DLQI_Q7_OPTIONS_EN = {
    "Yes — prevented work or studying": 3,
    "No, but skin was a problem at work or studying": 2,
    "No": 0,
    "Not relevant": 0,
}


ADCT_QUESTIONS_JA = [
    "この1週間、アトピー性皮膚炎の症状はどの程度でしたか。",
    "この1週間、アトピー性皮膚炎のために激しいかゆみが起こったことは何日ありましたか。",
    "この1週間、アトピー性皮膚炎にどの程度悩まされましたか。",
    "この1週間、アトピー性皮膚炎のためになかなか寝付けなかったり、途中で目が覚めたりすることが何晩ありましたか。",
    "この1週間、アトピー性皮膚炎がどの程度日常の活動に影響しましたか。",
    "この1週間、アトピー性皮膚炎がどの程度気分や感情に影響しましたか。",
]

ADCT_QUESTIONS_EN = [
    "Over the last week, how would you rate your eczema symptoms?",
    "Over the last week, on how many days did you have intense episodes of itching because of your eczema?",
    "Over the last week, how bothered have you been by your eczema?",
    "Over the last week, on how many nights did you have difficulty falling asleep or wake up during the night because of your eczema?",
    "Over the last week, how much did your eczema affect your daily activities?",
    "Over the last week, how much did your eczema affect your mood or emotions?",
]

ADCT_OPTIONS_JA = [
    {"なし": 0, "軽い": 1, "中くらい": 2, "ひどい": 3, "かなりひどい": 4},
    {"全くなかった": 0, "1〜2日": 1, "3〜4日": 2, "5〜6日": 3, "毎日": 4},
    {"全くなかった": 0, "少し": 1, "ある程度": 2, "とても": 3, "極めて": 4},
    {"全くなかった": 0, "1〜2晩": 1, "3〜4晩": 2, "5〜6晩": 3, "毎晩": 4},
    {"全くなかった": 0, "少し": 1, "ある程度": 2, "とても": 3, "極めて": 4},
    {"全くなかった": 0, "少し": 1, "ある程度": 2, "とても": 3, "極めて": 4},
]

ADCT_OPTIONS_EN = [
    {"None": 0, "Mild": 1, "Moderate": 2, "Severe": 3, "Very severe": 4},
    {"Not at all": 0, "1–2 days": 1, "3–4 days": 2, "5–6 days": 3, "Every day": 4},
    {"Not at all": 0, "A little": 1, "Moderately": 2, "Very much": 3, "Extremely": 4},
    {"Not at all": 0, "1–2 nights": 1, "3–4 nights": 2, "5–6 nights": 3, "Every night": 4},
    {"Not at all": 0, "A little": 1, "Moderately": 2, "Very much": 3, "Extremely": 4},
    {"Not at all": 0, "A little": 1, "Moderately": 2, "Very much": 3, "Extremely": 4},
]


def get_secret(name: str, default: str | None = None) -> str | None:
    try:
        if name in st.secrets:
            return str(st.secrets[name])
    except Exception:
        pass
    return os.getenv(name, default)


def t(language: str, ja: str, en: str) -> str:
    return ja if language == "日本語" else en


def interpret_dlqi(score: int, language: str) -> tuple[str, str]:
    if score <= 1:
        return (
            t(language, "影響なし", "No effect"),
            t(language, "生活への明らかな影響はほとんどありません。", "No measurable effect on the patient's life."),
        )
    if score <= 5:
        return (
            t(language, "軽度の影響", "Small effect"),
            t(language, "生活への影響は軽度です。", "Small effect on the patient's life."),
        )
    if score <= 10:
        return (
            t(language, "中等度の影響", "Moderate effect"),
            t(language, "生活への影響は中等度です。", "Moderate effect on the patient's life."),
        )
    if score <= 20:
        return (
            t(language, "非常に大きな影響", "Very large effect"),
            t(language, "生活への影響は非常に大きい状態です。", "Very large effect on the patient's life."),
        )
    return (
        t(language, "極めて大きな影響", "Extremely large effect"),
        t(language, "生活への影響は極めて大きい状態です。", "Extremely large effect on the patient's life."),
    )


def interpret_adct(score: int, language: str) -> tuple[str, str]:
    if score >= 7:
        return (
            t(language, "コントロール不十分の可能性", "Possible uncontrolled atopic dermatitis"),
            t(
                language,
                "ADCTが7点以上です。症状、睡眠、日常生活への影響を医療者が確認してください。",
                "ADCT is 7 or higher. A qualified clinician should review symptoms, sleep, and daily-life impact.",
            ),
        )
    return (
        t(language, "比較的コントロール良好", "Relatively controlled"),
        t(
            language,
            "ADCTは7点未満です。通常診療の中で医療者が確認を継続してください。",
            "ADCT is below 7. Continue routine assessment by a qualified clinician.",
        ),
    )


def get_csv_path(instrument: str) -> Path:
    return CSV_PATH_ADCT if instrument == "ADCT" else CSV_PATH_DLQI


def save_result(row: dict):
    csv_path = get_csv_path(row.get("instrument", ""))
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame([row])

    if csv_path.exists():
        df.to_csv(csv_path, mode="a", header=False, index=False, encoding="utf-8-sig")
    else:
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")


def get_previous_adct(patient_code: str):
    if not patient_code or not CSV_PATH_ADCT.exists():
        return None

    try:
        df = pd.read_csv(CSV_PATH_ADCT, on_bad_lines="skip")
    except Exception:
        return None

    if "visit_code" not in df.columns or "total_score" not in df.columns:
        return None

    df_ad = df[df["visit_code"].astype(str) == str(patient_code)]

    if df_ad.empty:
        return None

    last_row = df_ad.sort_values("timestamp").iloc[-1]
    return int(last_row["total_score"])


def judge_adct_control(current: int, previous: int | None, scores: list[int], language: str) -> dict:
    """
    ADCTスライドに基づくコントロール判定。

    非コントロール／非維持の条件：
    1. ADCT総スコアが7点以上
    2. Q1, Q2, Q3, Q5, Q6 のいずれかが2点以上
    3. Q4が1点以上
    4. 前回から5点以上増加

    注意：
    - この判定は診療補助・確認促進のための表示です。
    - 診断、治療方針、薬剤選択、治療継続・中止を自動決定するものではありません。
    """

    reasons_ja = []
    reasons_en = []

    if current >= 7:
        reasons_ja.append("ADCT総スコアが7点以上")
        reasons_en.append("ADCT total score is 7 or higher")

    # スライド上の青色領域：
    # Q1, Q2, Q3, Q5, Q6 は2点以上
    blue_threshold_items = [0, 1, 2, 4, 5]
    for i in blue_threshold_items:
        if len(scores) > i and scores[i] >= 2:
            reasons_ja.append(f"Q{i + 1}が2点以上")
            reasons_en.append(f"Q{i + 1} score is 2 or higher")

    # Q4だけは1点以上
    if len(scores) > 3 and scores[3] >= 1:
        reasons_ja.append("Q4が1点以上")
        reasons_en.append("Q4 score is 1 or higher")

    # 前回から5点以上増加
    if previous is not None and (current - previous) >= 5:
        reasons_ja.append("前回から5点以上増加")
        reasons_en.append("Increase of 5 points or more from previous ADCT")

    uncontrolled = len(reasons_ja) > 0

    if uncontrolled:
        return {
            "decision": "非維持",
            "display_title": t(
                language,
                "コントロール不十分の可能性",
                "Possible uncontrolled atopic dermatitis",
            ),
            "message": t(
                language,
                "ADCTの結果から、アトピー性皮膚炎のコントロールが不十分な可能性があります。医療者による確認を推奨します。",
                "Based on the ADCT result, atopic dermatitis may be insufficiently controlled. Review by a qualified clinician is recommended.",
            ),
            "reasons": reasons_ja if language == "日本語" else reasons_en,
        }

    return {
        "decision": "維持",
        "display_title": t(
            language,
            "比較的コントロール良好",
            "Relatively controlled",
        ),
        "message": t(
            language,
            "ADCTの結果から、現時点では比較的コントロール良好と考えられます。通常診療の中で確認を継続してください。",
            "Based on the ADCT result, the condition appears relatively controlled at this time. Continue routine clinical review.",
        ),
        "reasons": [],
    }


def build_email_body(row: dict, result: dict) -> str:
    lines = [
        "New questionnaire submission",
        "",
        f"App: {APP_TITLE}",
        f"Version: {APP_VERSION}",
        f"Timestamp: {row.get('timestamp', '')}",
        f"Language: {row.get('language', '')}",
        f"Disease: {row.get('disease', '')}",
        f"Instrument: {row.get('instrument', '')}",
        f"Anonymous visit code: {row.get('visit_code', '') or '(blank)'}",
        f"Total score: {row.get('total_score', '')} / {row.get('max_score', '')}",
        f"Severity / interpretation: {row.get('severity', '')}",
        f"Decision support display: {row.get('decision', '')}",
        f"Decision reasons: {row.get('decision_reasons', '')}",
        f"Previous ADCT: {row.get('previous_adct', '')}",
        f"Delta ADCT: {row.get('delta_adct', '')}",
        "",
        "Item scores:",
    ]

    for i, score in enumerate(result["scores"], start=1):
        answer = result["answers"][i - 1]
        lines.append(f"Q{i}: {score} | {answer}")

    lines.extend([
        "",
        "Important notes:",
        "- This message is intended for clinical support only.",
        "- This app does not provide diagnosis or treatment instructions.",
        "- Final clinical decisions must be made by a qualified healthcare professional.",
        "- No direct personal identifiers should be entered into this app.",
    ])
    return "\n".join(lines)


def send_admin_email(row: dict, result: dict) -> tuple[bool, str]:
    smtp_host = get_secret("SMTP_HOST")
    smtp_port = int(get_secret("SMTP_PORT", "587"))
    smtp_user = get_secret("SMTP_USER")
    smtp_password = get_secret("SMTP_PASSWORD")
    smtp_from = get_secret("SMTP_FROM", smtp_user or ADMIN_EMAIL)

    missing = [
        name for name, value in {
            "SMTP_HOST": smtp_host,
            "SMTP_USER": smtp_user,
            "SMTP_PASSWORD": smtp_password,
            "SMTP_FROM": smtp_from,
        }.items() if not value
    ]

    if missing:
        return False, "Missing email settings: " + ", ".join(missing)

    subject = f"[Shirabeo Patient Insight] New {row['instrument']} Submission: {row['total_score']}/{row['max_score']}"
    body = build_email_body(row, result)

    msg = MIMEMultipart()
    msg["From"] = smtp_from
    msg["To"] = ADMIN_EMAIL
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_from, [ADMIN_EMAIL], msg.as_string())
        return True, "Email sent successfully."
    except Exception as e:
        print("EMAIL ERROR:", e)
        return False, f"Email sending failed: {e}"


def render_legal_notice(language: str):
    st.warning(
        t(
            language,
            "本アプリは、皮膚科診療における問診・患者報告アウトカムの整理を補助するためのデモ／試験運用版です。診断、治療方針、薬剤選択、治療継続・中止を自動的に決定するものではありません。最終的な診療判断は、必ず医師その他の資格を有する医療者が行ってください。",
            "This application is a demonstration / pilot tool intended to support questionnaire collection and organization of patient-reported outcomes in dermatology practice. It does not provide diagnosis, determine treatment plans, select medications, or automatically decide whether treatment should be continued or stopped. Final clinical decisions must always be made by a qualified healthcare professional.",
        )
    )

    with st.expander(t(language, "利用上の注意・法務表示（詳細）", "Important notices and legal information")):
        st.markdown(
            t(
                language,
                f"""
### 1. 本アプリの位置づけ
- 本アプリは、皮膚科診療における患者報告アウトカム（PRO）の入力、スコア整理、経時的な情報把握を補助するための試験運用版です。
- 本アプリは、医療者による問診・診察・検査・診療記録の確認を置き換えるものではありません。
- 本アプリの表示結果は、医療者による確認を促すための参考情報であり、単独で診断、重症度判定、治療方針、薬剤選択、治療継続・変更・中止を決定するものではありません。
- 本アプリは、現時点では研究・試験運用・診療補助目的のワークフロー支援ツールであり、医療機器としての承認・認証・届出を受けたものではありません。

### 2. 利用対象
- 本アプリは、医療機関または医療者の管理下で、皮膚科診療の補助として使用されることを想定しています。
- 患者さんが単独で診断や治療判断を行う目的で使用するものではありません。
- 強い症状、急な悪化、感染が疑われる症状、発熱、全身症状、その他緊急性が疑われる場合は、本アプリの結果にかかわらず、速やかに医療者へ相談してください。

### 3. 入力してはいけない情報
- 氏名、生年月日、住所、電話番号、メールアドレス、患者ID、診察券番号、保険証番号、マイナンバーなど、個人を直接特定できる情報は入力しないでください。
- 匿名コードを使用する場合は、医療機関内で適切に管理された非識別コードを使用してください。
- 自由記載欄や匿名コード欄に、個人を特定できる内容を入力しないでください。
- 入力内容に直接個人情報が含まれた場合、Shirabeo Labsはその内容を意図して取得するものではありません。

### 4. データの取扱い
- 入力された回答、スコア、匿名コード、送信日時、選択された疾患・質問票の種類などは、診療補助、試験運用、動作確認、品質改善、集計確認の目的で保存・確認される場合があります。
- 本アプリでは、氏名等の直接個人情報を入力しない運用を前提としています。
- 医療機関が匿名コードと患者情報を対応させる場合、その対応表は医療機関側で適切に管理してください。
- 本アプリで取得されたデータを研究、発表、外部報告等に使用する場合は、必要に応じて倫理審査、施設承認、匿名化処理、同意取得等の手続きを別途行います。
- 通信環境、外部サービス、サーバー、ブラウザ、端末の状態により、送信遅延、保存失敗、表示不具合が生じる可能性があります。

### 5. 表示結果について
- ADCT、DLQIなどのスコア表示は、患者報告アウトカムを整理するための補助情報です。
- 「維持」「非維持」等の表示は、入力された回答に基づく簡易的な診療補助表示であり、医学的判断そのものではありません。
- 表示結果が「維持」であっても、症状悪化や医療者が必要と判断する場合には、追加評価や治療方針の見直しが必要になることがあります。
- 表示結果が「非維持」であっても、直ちに治療変更や中止を意味するものではありません。医療者が診察所見、既往歴、併存症、治療歴、検査結果、患者希望等を総合して判断してください。

### 6. 質問票・スコア体系・第三者権利
- ADCT、DLQI等の質問票、名称、設問文、翻訳、スコア体系、解釈基準には、第三者の著作権、商標権、ライセンス条件、使用条件が存在する場合があります。
- 実運用、商用利用、外部提供、研究利用、出版物・講演資料での表示、企業・医療機関への提供にあたっては、必要な使用許諾、表示条件、ライセンス、引用条件を確認してください。
- 本アプリ内での質問票表示は、試験運用・デモ・診療補助フロー検討のための実装であり、権利関係の最終確認を不要にするものではありません。
- DLQIは皮膚疾患における生活の質への影響を把握するための指標として広く利用されていますが、外部提供・商用利用・出版・講演資料での利用条件は、必要に応じて確認してください。

### 7. 医療機器・薬機法上の位置づけ
- 本アプリは、現時点では診断、治療、予防を単独で目的とするものではなく、医療者の確認を補助する情報整理ツールとして設計されています。
- 本アプリは、医療機器としての承認、認証、届出を受けたプログラムではありません。
- 将来的に、診断、治療方針決定、薬剤選択、治療継続・中止判断等に直接関与する機能を追加する場合には、医療機器プログラム該当性、薬機法、関連ガイドライン、広告規制等について専門家確認を行う必要があります。

### 8. 免責
- 本アプリの利用により得られる情報の正確性、完全性、最新性、有用性について、Shirabeo Labsは可能な範囲で注意を払いますが、すべてを保証するものではありません。
- 本アプリの表示結果のみに基づく診断、治療変更、治療中止、受診延期、自己判断について、Shirabeo Labsは責任を負いません。
- 本アプリは、医療者と患者さんのコミュニケーションを補助するものであり、医療者による診療行為を代替するものではありません。

### 9. お問い合わせ
- 本アプリに関するお問い合わせ：{CONTACT_EMAIL}
                """,
                f"""
### 1. Positioning of this application
- This application is a pilot / demonstration tool intended to support the input, scoring, and longitudinal review of patient-reported outcomes (PROs) in dermatology practice.
- It does not replace medical interviews, physical examination, tests, or review of medical records by healthcare professionals.
- The displayed results are reference information to support review by healthcare professionals and must not be used alone to diagnose disease, determine severity, select medications, or decide whether treatment should be continued, changed, or stopped.
- This application is currently a workflow-support tool for research, pilot use, and clinical support. It has not been approved, certified, or registered as a medical device.

### 2. Intended users and use setting
- This application is intended to be used as a dermatology workflow-support tool under the management of a medical institution or healthcare professional.
- It is not intended for patients to independently diagnose disease or make treatment decisions.
- In case of severe symptoms, sudden worsening, suspected infection, fever, systemic symptoms, or any condition that may require urgent care, please consult a healthcare professional promptly regardless of the app result.

### 3. Information not to enter
- Do not enter directly identifiable information such as name, date of birth, address, phone number, email address, patient ID, medical record number, insurance number, or government identification number.
- If an anonymous code is used, it should be a non-identifying code appropriately managed within the medical institution.
- Do not enter any personally identifiable content in the anonymous code field or any free-text field.
- If directly identifiable information is entered, Shirabeo Labs does not intend to collect such information.

### 4. Handling of data
- Responses, scores, anonymous codes, submission time, selected disease, and questionnaire type may be stored and reviewed for clinical support, pilot operation, technical verification, quality improvement, and aggregate review.
- This application is operated on the assumption that directly identifiable information is not entered.
- If a medical institution links anonymous codes with patient identities, the correspondence table should be managed appropriately by the medical institution.
- If data obtained through this application are used for research, presentation, publication, or external reporting, necessary procedures such as ethics review, institutional approval, anonymization, and consent will be handled separately as appropriate.
- Transmission delays, storage failures, or display errors may occur depending on network conditions, external services, servers, browsers, or devices.

### 5. Displayed results
- ADCT, DLQI, and related scores are supportive information for organizing patient-reported outcomes.
- Displays such as “maintenance” or “non-maintenance” are simplified clinical-support indicators based on the entered responses and are not medical judgments themselves.
- Even if the display indicates “maintenance,” additional assessment or treatment review may be required if symptoms worsen or if the healthcare professional considers it necessary.
- Even if the display indicates “non-maintenance,” it does not immediately mean that treatment should be changed or stopped. Healthcare professionals should make comprehensive decisions based on examination findings, medical history, comorbidities, treatment history, test results, and patient preferences.

### 6. Questionnaires, scoring systems, and third-party rights
- ADCT, DLQI, questionnaire names, question wording, translations, scoring systems, and interpretation criteria may be subject to third-party copyrights, trademarks, licenses, or usage conditions.
- Before operational, commercial, external, research, publication, presentation, or institutional use, necessary permissions, display requirements, licenses, and citation conditions should be confirmed.
- Display of questionnaires within this application is for pilot use, demonstration, and workflow evaluation, and does not eliminate the need for rights clearance.
- DLQI is widely used as an index for assessing the quality-of-life impact of skin diseases, but conditions for external, commercial, publication, or presentation use should be confirmed as necessary.

### 7. Medical device and regulatory positioning
- This application is currently designed as an information-organization tool to support healthcare professional review and is not intended to independently diagnose, treat, or prevent disease.
- This application has not been approved, certified, or registered as a medical device.
- If future functions directly affect diagnosis, treatment planning, medication selection, or treatment continuation/discontinuation decisions, medical-device software applicability, pharmaceutical and medical device regulations, related guidelines, and advertising regulations should be reviewed with appropriate experts.

### 8. Disclaimer
- Shirabeo Labs takes reasonable care regarding the information provided by this application, but does not guarantee its accuracy, completeness, timeliness, or usefulness in every case.
- Shirabeo Labs is not responsible for diagnosis, treatment changes, treatment discontinuation, delayed consultation, or self-directed decisions made solely based on the displayed results.
- This application is intended to support communication between patients and healthcare professionals and does not replace medical care provided by healthcare professionals.

### 9. Contact
- Contact regarding this application: {CONTACT_EMAIL}
                """,
            )
        )



def render_research_consent_notice(language: str):
    """
    IRB研究用のアプリ内説明・同意確認ブロック。
    送信ボタン直前に表示し、チェックがない場合は送信しない。
    """
    st.markdown("---")
    st.markdown(
        t(
            language,
            "**研究参加について**",
            "**Research participation**",
        )
    )
    st.info(
        t(
            language,
            "本入力内容は、アトピー性皮膚炎におけるADCTのデジタル入力支援ツールの実装可能性を評価する研究に使用される場合があります。研究では、ADCT回答、入力時間、入力のしやすさ、入力者情報、医療者による確認状況などを、個人が特定されない形で解析します。",
            "The information entered here may be used for a research study evaluating the feasibility of a digital ADCT input-support tool for atopic dermatitis. The study may analyze ADCT responses, input duration, ease of input, who entered the responses, and clinician review status in a form that does not directly identify individuals.",
        )
    )
    st.caption(
        t(
            language,
            "診療内容は担当医が通常診療として判断し、本アプリが診断・治療方針を自動決定するものではありません。研究参加は任意であり、同意しない場合でも診療上の不利益はありません。同意されない場合は、通常診療の範囲で紙または口頭による確認を行います。",
            "Clinical care will be determined by the treating clinician as part of routine practice. This application does not automatically determine diagnosis or treatment policy. Research participation is voluntary, and refusal to participate will not result in any disadvantage in clinical care. If you do not agree, confirmation will be performed by paper form or verbally as part of routine care.",
        )
    )

def render_credit_footer(language: str):
    st.markdown("---")
    st.caption(
        t(
            language,
            f"{APP_VERSION} | Developed and operated by Shirabeo Labs. Contact: {CONTACT_EMAIL}",
            f"{APP_VERSION} | Developed and operated by Shirabeo Labs. Contact: {CONTACT_EMAIL}",
        )
    )
    st.caption(
        t(
            language,
            "本アプリは診療補助・問診支援を目的とした試験運用版であり、診断・治療方針・薬剤選択・治療継続または中止を自動決定するものではありません。最終的な診療判断は医療者が行ってください。",
            "This application is a pilot clinical-support and questionnaire-support tool. It does not automatically determine diagnosis, treatment plans, medication selection, or treatment continuation/discontinuation. Final clinical decisions should be made by a qualified healthcare professional.",
        )
    )


def render_adct_partner_notice(language: str):
    st.caption(
        t(
            language,
            "SanofiおよびRegeneronは、アトピー性皮膚炎領域における疾患啓発・患者報告アウトカム活用に関連する重要なステークホルダーとして表示しています。本アプリはShirabeo Labsが独自に作成・運用するものであり、SanofiまたはRegeneronによる製造・販売・配布・承認・保証・監修・共同開発を意味するものではありません。",
            "Sanofi and Regeneron are acknowledged as important stakeholders in atopic dermatitis disease awareness and patient-reported outcome utilization. This application is independently developed and operated by Shirabeo Labs and does not imply manufacture, sale, distribution, approval, guarantee, supervision, or co-development by Sanofi or Regeneron.",
        )
    )


def render_dlqi(language: str):
    questions = DLQI_QUESTIONS_JA if language == "日本語" else DLQI_QUESTIONS_EN
    options_common = DLQI_OPTIONS_JA if language == "日本語" else DLQI_OPTIONS_EN
    q7_options = DLQI_Q7_OPTIONS_JA if language == "日本語" else DLQI_Q7_OPTIONS_EN

    scores = []
    answers = []

    for i, q in enumerate(questions, start=1):
        st.markdown(f"**Q{i}. {q}**")
        opts = q7_options if i == 7 else options_common
        answer = st.radio(
            t(language, f"Q{i}の回答", f"Answer Q{i}"),
            list(opts.keys()),
            key=f"dlqi_{language}_{i}",
            label_visibility="collapsed",
        )
        scores.append(opts[answer])
        answers.append(answer)
        st.write("")

    total = int(sum(scores))
    severity, interpretation = interpret_dlqi(total, language)

    return {
        "instrument": "DLQI",
        "disease": "Psoriasis",
        "total_score": total,
        "max_score": 30,
        "severity": severity,
        "interpretation": interpretation,
        "scores": scores,
        "answers": answers,
    }


def render_adct(language: str):
    questions = ADCT_QUESTIONS_JA if language == "日本語" else ADCT_QUESTIONS_EN
    options_list = ADCT_OPTIONS_JA if language == "日本語" else ADCT_OPTIONS_EN

    scores = []
    answers = []

    for i, q in enumerate(questions, start=1):
        st.markdown(f"**Q{i}. {q}**")
        opts = options_list[i - 1]
        answer = st.radio(
            t(language, f"Q{i}の回答", f"Answer Q{i}"),
            list(opts.keys()),
            key=f"adct_{language}_{i}",
            label_visibility="collapsed",
        )
        scores.append(opts[answer])
        answers.append(answer)
        st.write("")

    st.markdown("---")
    st.markdown(
        t(
            language,
            "**試験運用に関する確認項目**",
            "**Pilot-operation questions**",
        )
    )

    input_support_options = [
        t(language, "自分で最後まで入力した", "Completed all entries by myself"),
        t(language, "病院スタッフの説明・補助を受けながら、自分で入力した", "Completed by myself with explanation or support from hospital staff"),
        t(language, "病院スタッフが代わりに入力した", "Hospital staff entered the responses on my behalf"),
        t(language, "家族・付き添いの方が代わりに入力した", "A family member or accompanying person entered the responses on my behalf"),
    ]
    input_support = st.radio(
        t(
            language,
            "この質問票の入力はどのように行いましたか？",
            "How was this questionnaire entered?",
        ),
        input_support_options,
        key=f"adct_input_support_{language}",
    )

    input_ease_options = [
        t(language, "とても簡単だった", "Very easy"),
        t(language, "簡単だった", "Easy"),
        t(language, "やや難しかった", "Somewhat difficult"),
        t(language, "難しかった", "Difficult"),
    ]
    input_ease = st.radio(
        t(
            language,
            "今回の入力はどう感じましたか？",
            "How easy or difficult was this entry process?",
        ),
        input_ease_options,
        key=f"adct_input_ease_{language}",
    )

    total = int(sum(scores))
    severity, interpretation = interpret_adct(total, language)

    return {
        "instrument": "ADCT",
        "disease": "Atopic dermatitis",
        "total_score": total,
        "max_score": 24,
        "severity": severity,
        "interpretation": interpretation,
        "scores": scores,
        "answers": answers,
        "input_support": input_support,
        "input_ease": input_ease,
    }


def clinician_priority_label(row: pd.Series, instrument_label: str) -> tuple[str, str]:
    """
    医療者確認画面だけで使う表示用ラベル。
    CSVの保存形式や患者入力ロジックには影響しません。
    """
    decision = str(row.get("decision", "") or "")
    try:
        total_score = int(float(row.get("total_score", 0)))
    except Exception:
        total_score = 0

    if instrument_label == "ADCT":
        if decision == "非維持" or total_score >= 7:
            return "確認優先", "🔴"
        return "通常確認", "🟢"

    # DLQIは診断・治療判断ではなく、生活影響の大きさを見落とさないための表示用。
    if total_score >= 21:
        return "生活影響：極めて大", "🔴"
    if total_score >= 11:
        return "生活影響：大", "🟠"
    if total_score >= 6:
        return "生活影響：中等度", "🟡"
    return "通常確認", "🟢"


def format_clinician_value(value) -> str:
    if pd.isna(value):
        return ""
    return str(value)


def inject_clinician_ui_css():
    """
    医療者確認画面の見た目だけを整えるCSS。
    患者入力、CSV保存形式、判定ロジックには影響しません。
    """
    st.markdown(
        """
        <style>
        .clinician-card {
            border: 1px solid rgba(120, 120, 120, 0.25);
            border-radius: 16px;
            padding: 18px 18px 14px 18px;
            margin: 14px 0 18px 0;
            background: rgba(250, 250, 250, 0.78);
            box-shadow: 0 2px 10px rgba(0,0,0,0.04);
        }
        .clinician-card-priority {
            border-left: 8px solid #d93025;
            background: rgba(255, 245, 245, 0.88);
        }
        .clinician-card-normal {
            border-left: 8px solid #188038;
            background: rgba(246, 252, 248, 0.88);
        }
        .clinician-card-impact-high {
            border-left: 8px solid #f29900;
            background: rgba(255, 250, 240, 0.88);
        }
        .clinician-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 12px;
            margin-bottom: 8px;
        }
        .clinician-title {
            font-size: 1.15rem;
            font-weight: 800;
            line-height: 1.3;
        }
        .clinician-badge {
            display: inline-block;
            border-radius: 999px;
            padding: 5px 12px;
            font-size: 0.86rem;
            font-weight: 700;
            background: rgba(0,0,0,0.07);
            white-space: nowrap;
        }
        .clinician-meta {
            color: rgba(49, 51, 63, 0.72);
            font-size: 0.92rem;
            margin: 0 0 10px 0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_clinician_submission_card(row: pd.Series, instrument_label: str, index: int):
    priority_text, priority_icon = clinician_priority_label(row, instrument_label)

    timestamp = format_clinician_value(row.get("timestamp", ""))
    visit_code = format_clinician_value(row.get("visit_code", ""))
    total_score = format_clinician_value(row.get("total_score", ""))
    max_score = format_clinician_value(row.get("max_score", ""))
    severity = format_clinician_value(row.get("severity", ""))
    decision = format_clinician_value(row.get("decision", ""))
    previous_adct = format_clinician_value(row.get("previous_adct", ""))
    delta_adct = format_clinician_value(row.get("delta_adct", ""))
    decision_reasons = format_clinician_value(row.get("decision_reasons", ""))

    is_priority = priority_text != "通常確認"
    if instrument_label == "ADCT":
        card_class = "clinician-card-priority" if is_priority else "clinician-card-normal"
    else:
        card_class = "clinician-card-impact-high" if is_priority else "clinician-card-normal"

    st.markdown(
        f"""
        <div class="clinician-card {card_class}">
            <div class="clinician-header">
                <div class="clinician-title">{priority_icon} {priority_text}</div>
                <div class="clinician-badge">{instrument_label} #{index + 1}</div>
            </div>
            <div class="clinician-meta">送信日時：{timestamp or "—"}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns([1.1, 1.1, 1.8])
    c1.metric("匿名コード", visit_code or "未入力")
    c2.metric("スコア", f"{total_score} / {max_score}")
    c3.metric("結果", decision or severity or "—")

    if instrument_label == "ADCT":
        h1, h2 = st.columns(2)
        h1.metric("前回ADCT", previous_adct or "初回/不明")
        h2.metric("変化量 Δ", delta_adct or "—")

        if decision_reasons:
            st.error(f"確認理由：{decision_reasons}")
        elif decision == "維持":
            st.success("非維持条件には該当していません。通常診療の中で確認してください。")
        else:
            st.info("ADCTの結果を通常診療の中で確認してください。")
    else:
        if severity:
            st.info(f"DLQI解釈：{severity}")

    score_cols = [col for col in row.index if re.fullmatch(r"q\d+_score", str(col))]
    score_cols = sorted(score_cols, key=lambda x: int(re.findall(r"\d+", x)[0]))

    if score_cols:
        score_text = "　".join([
            f"{col.replace('_score', '').upper()}={format_clinician_value(row.get(col, ''))}"
            for col in score_cols
        ])
        st.caption("項目別スコア：" + score_text)

    with st.expander("回答詳細を表示"):
        detail_rows = []
        for col in score_cols:
            q_num = re.findall(r"\d+", col)[0]
            answer_col = f"q{q_num}_answer"
            detail_rows.append({
                "項目": f"Q{q_num}",
                "スコア": format_clinician_value(row.get(col, "")),
                "回答": format_clinician_value(row.get(answer_col, "")),
            })

        if detail_rows:
            st.dataframe(pd.DataFrame(detail_rows), hide_index=True, use_container_width=True)
        else:
            st.caption("項目別データがありません。")

    st.divider()


def show_csv_tab(label: str, csv_path: Path, file_name: str):
    inject_clinician_ui_css()

    st.subheader(f"{label} 送信結果")
    st.caption("確認が必要な送信を上に出し、匿名コード・日付・優先表示で絞り込めます。")

    if not csv_path.exists():
        st.info(f"{label}データはまだありません。")
        return

    csv_bytes = csv_path.read_bytes()

    try:
        df = pd.read_csv(csv_path, on_bad_lines="skip")
    except Exception as e:
        st.warning(f"{label} CSVの読み込みに失敗しました。")
        st.caption(str(e))
        st.download_button(
            f"{label} CSVをそのままダウンロード",
            data=csv_bytes,
            file_name=file_name,
            mime="text/csv",
            use_container_width=True,
        )
        return

    if df.empty:
        st.info(f"{label}データはまだありません。")
        return

    df = df.copy()

    if "timestamp" in df.columns:
        df["_timestamp_dt"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df = df.sort_values("_timestamp_dt", ascending=False, na_position="last")
    else:
        df["_timestamp_dt"] = pd.NaT
        df = df.iloc[::-1]

    today = datetime.now(JST).date()
    valid_dates = df["_timestamp_dt"].dropna()

    total_count = len(df)
    today_count = int((df["_timestamp_dt"].dt.date == today).sum()) if not valid_dates.empty else 0
    latest_time = (
        df["_timestamp_dt"].dropna().max().strftime("%Y-%m-%d %H:%M")
        if not valid_dates.empty
        else "不明"
    )

    df["_priority_label"] = df.apply(lambda r: clinician_priority_label(r, label)[0], axis=1)
    df["_priority_icon"] = df.apply(lambda r: clinician_priority_label(r, label)[1], axis=1)
    df["_is_priority"] = df["_priority_label"] != "通常確認"
    priority_count = int(df["_is_priority"].sum())

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("全送信数", total_count)
    m2.metric("本日の送信", today_count)
    m3.metric("確認優先", priority_count)
    m4.metric("最新送信", latest_time)

    latest_row = df.iloc[0]
    latest_label = format_clinician_value(latest_row.get("_priority_label", ""))
    latest_code = format_clinician_value(latest_row.get("visit_code", ""))
    latest_score = format_clinician_value(latest_row.get("total_score", ""))
    latest_max = format_clinician_value(latest_row.get("max_score", ""))
    latest_timestamp = format_clinician_value(latest_row.get("timestamp", ""))

    st.markdown("#### 最新1件")
    st.info(
        f"{label} / {latest_label} / 匿名コード：{latest_code or '未入力'} / "
        f"スコア：{latest_score}/{latest_max} / {latest_timestamp or '日時不明'}"
    )

    with st.expander("CSVダウンロード"):
        st.download_button(
            f"{label} CSVダウンロード",
            data=csv_bytes,
            file_name=file_name,
            mime="text/csv",
            use_container_width=True,
        )

    st.markdown("#### 絞り込み")
    f1, f2 = st.columns([1.2, 1])

    visit_query = f1.text_input(
        "匿名コードで検索",
        placeholder="例：AD001",
        key=f"{label}_visit_query",
    )

    priority_only = f2.checkbox(
        "確認優先のみ表示",
        key=f"{label}_priority_only",
    )

    filtered = df.copy()

    if visit_query and "visit_code" in filtered.columns:
        filtered = filtered[
            filtered["visit_code"].astype(str).str.contains(visit_query, case=False, na=False)
        ]

    if not valid_dates.empty:
        min_date = valid_dates.min().date()
        max_date = valid_dates.max().date()
        date_range = st.date_input(
            "日付範囲",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
            key=f"{label}_date_range",
        )

        if isinstance(date_range, tuple) and len(date_range) == 2:
            start_date, end_date = date_range
            filtered = filtered[
                (filtered["_timestamp_dt"].dt.date >= start_date)
                & (filtered["_timestamp_dt"].dt.date <= end_date)
            ]

    if priority_only:
        filtered = filtered[filtered["_is_priority"]]

    filtered = filtered.sort_values(
        by=["_is_priority", "_timestamp_dt"],
        ascending=[False, False],
        na_position="last",
    )

    st.caption(f"表示件数：{len(filtered)} / {len(df)}")

    st.markdown("#### 一覧サマリー")

    summary_cols = [
        "_priority_icon",
        "_priority_label",
        "timestamp",
        "visit_code",
        "total_score",
        "max_score",
        "decision",
        "severity",
        "previous_adct",
        "delta_adct",
    ]
    existing_cols = [c for c in summary_cols if c in filtered.columns]

    summary_df = filtered[existing_cols].copy()
    rename_map = {
        "_priority_icon": "",
        "_priority_label": "確認区分",
        "timestamp": "送信日時",
        "visit_code": "匿名コード",
        "total_score": "スコア",
        "max_score": "満点",
        "decision": "判定",
        "severity": "解釈",
        "previous_adct": "前回ADCT",
        "delta_adct": "Δ",
    }
    summary_df = summary_df.rename(columns=rename_map)

    st.dataframe(summary_df, hide_index=True, use_container_width=True)

    st.markdown("#### カード表示")

    max_cards = min(20, len(filtered))
    if max_cards == 0:
        st.info("条件に一致する送信結果はありません。")
    else:
        if max_cards == 1:
            display_count = 1
            st.caption("カード表示件数：1件")
        else:
            display_count = st.slider(
                "カード表示件数",
                min_value=1,
                max_value=max_cards,
                value=min(5, max_cards),
                key=f"{label}_display_count",
            )

        for i, (_, row) in enumerate(filtered.head(display_count).iterrows()):
            render_clinician_submission_card(row, label, i)

    with st.expander("全CSV列を確認する"):
        display_df = filtered.drop(
            columns=["_timestamp_dt", "_priority_label", "_priority_icon", "_is_priority"],
            errors="ignore",
        )
        st.dataframe(display_df, use_container_width=True)

    st.caption(
        "この画面は送信結果を見やすく整理するための医療者向け確認画面です。"
        "患者入力・保存データ・判定ロジックは変更していません。"
    )


def main():
    st.set_page_config(page_title=APP_TITLE, page_icon="📝", layout="centered")

    st.title(APP_TITLE)
    st.caption("DLQI for psoriasis / ADCT for atopic dermatitis")
    st.caption(APP_VERSION)

    language = st.sidebar.radio("Language / 言語", ["日本語", "English"], index=0)

    render_legal_notice(language)

    disease_param = st.query_params.get("disease", "ad")
    disease_param = str(disease_param).lower()

    if disease_param in ["psoriasis", "ps", "dlqi"]:
        default_index = 0
    else:
        default_index = 1

    disease_mode = st.sidebar.radio(
        t(language, "疾患・質問票", "Disease / questionnaire"),
        [
            t(language, "乾癬：DLQI", "Psoriasis: DLQI"),
            t(language, "アトピー性皮膚炎：ADCT", "Atopic dermatitis: ADCT"),
        ],
        index=default_index,
    )

    st.info(
        t(
            language,
            "過去1週間を振り返って回答してください。氏名・生年月日・住所・患者ID・診察券番号などの直接個人情報は入力しないでください。",
            "Please answer based on the last 7 days. Do not enter direct personal identifiers such as name, date of birth, address, patient ID, or medical record number.",
        )
    )

    if (
        "questionnaire_started_at" not in st.session_state
        or st.session_state.get("questionnaire_timer_disease_mode") != disease_mode
    ):
        st.session_state["questionnaire_started_at"] = datetime.now(JST).isoformat()
        st.session_state["questionnaire_timer_disease_mode"] = disease_mode

    is_adct_selected = "ADCT" in disease_mode
    visit_code_digits = ""

    with st.form("questionnaire_form", clear_on_submit=False):
        if is_adct_selected:
            visit_code_digits = st.text_input(
                t(language, "匿名コード（AD + 半角数字3桁）", "Anonymous code (AD + 3 digits)"),
                max_chars=3,
                placeholder=t(language, "例：001", "Example: 001"),
                help=t(
                    language,
                    "アトピー性皮膚炎では、患者さんは半角数字3桁のみを入力してください。アプリ側で自動的に AD001 のような匿名コードとして保存します。氏名、患者ID、診察券番号は入力しないでください。",
                    "For atopic dermatitis, enter 3 half-width digits only. The app will automatically save it as an anonymous code such as AD001. Do not enter name, patient ID, or medical record number.",
                ),
            )

            if visit_code_digits and re.fullmatch(r"[0-9]{3}", visit_code_digits):
                visit_code = f"AD{visit_code_digits}"
                st.caption(t(language, f"保存される匿名コード：{visit_code}", f"Anonymous code to be saved: {visit_code}"))
            elif visit_code_digits:
                visit_code = ""
                st.error(t(language, "匿名コードは半角数字3桁で入力してください。例：001", "Please enter exactly 3 half-width digits. Example: 001"))
            else:
                visit_code = ""
                st.caption(t(language, "受付で案内された半角数字3桁を入力してください。", "Please enter the 3-digit number provided by the clinic."))
        else:
            visit_code = st.text_input(
                t(language, "匿名コード", "Anonymous visit code"),
                placeholder=t(language, "例：PS001。空欄でも可。", "Example: PS001. Optional."),
                help=t(
                    language,
                    "匿名コードのみ使用してください。氏名、患者ID、診察券番号は入力しないでください。",
                    "Use an anonymous code only. Do not enter name, patient ID, or medical record number.",
                ),
            )

        st.divider()

        if "DLQI" in disease_mode:
            result = render_dlqi(language)
        else:
            result = render_adct(language)

        if result["instrument"] == "ADCT":
            render_research_consent_notice(language)
            consent = st.checkbox(
                t(
                    language,
                    "上記の説明を確認し、本研究への参加に同意します。",
                    "I have reviewed the explanation above and agree to participate in this research study.",
                ),
                key=f"research_consent_{language}_{result['instrument']}",
            )
        else:
            consent = st.checkbox(
                t(
                    language,
                    "上記の注意事項を確認しました。直接個人情報を入力せず、本アプリの結果が診断・治療方針を自動決定するものではないことを理解しました。",
                    "I have reviewed the notices above. I understand that I should not enter direct personal identifiers and that this app does not automatically determine diagnosis or treatment.",
                ),
                key=f"general_consent_{language}_{result['instrument']}",
            )

        submitted = st.form_submit_button(
            t(language, "送信", "Submit"),
            use_container_width=True,
        )

    if submitted:
        if not consent:
            st.error(
                t(
                    language,
                    "送信するには、研究参加に関する説明または利用上の注意を確認し、チェックボックスにチェックしてください。",
                    "To submit, please review the research participation explanation or notices and check the confirmation box.",
                )
            )
            st.stop()

        if result["instrument"] == "ADCT":
            if not re.fullmatch(r"[0-9]{3}", visit_code_digits or ""):
                st.error(
                    t(
                        language,
                        "アトピー性皮膚炎の匿名コードは、半角数字3桁のみで入力してください。例：001",
                        "For atopic dermatitis, please enter exactly 3 half-width digits. Example: 001",
                    )
                )
                st.stop()
            visit_code = f"AD{visit_code_digits}"

        now_dt = datetime.now(JST)
        now = now_dt.strftime("%Y-%m-%d %H:%M:%S")

        input_started_at = st.session_state.get("questionnaire_started_at", "")
        input_duration_seconds = None
        input_duration_minutes = None

        if input_started_at:
            try:
                started_dt = datetime.fromisoformat(str(input_started_at))
                input_duration_seconds = round((now_dt - started_dt).total_seconds(), 1)
                input_duration_minutes = round(input_duration_seconds / 60, 2)
            except Exception:
                input_duration_seconds = None
                input_duration_minutes = None

        previous_adct = None
        delta_adct = None
        decision = ""
        decision_reasons = ""
        adct_judgement = None

        if result["instrument"] == "ADCT":
            previous_adct = get_previous_adct(visit_code)
            adct_judgement = judge_adct_control(
                result["total_score"],
                previous_adct,
                result["scores"],
                language,
            )
            decision = adct_judgement["decision"]
            decision_reasons = " / ".join(adct_judgement["reasons"])

            if previous_adct is not None:
                delta_adct = result["total_score"] - previous_adct

        row = {
            "timestamp": now,
            "app_version": APP_VERSION,
            "language": language,
            "disease": result["disease"],
            "instrument": result["instrument"],
            "visit_code": visit_code,
            "total_score": result["total_score"],
            "max_score": result["max_score"],
            "severity": result["severity"],
            "previous_adct": previous_adct,
            "delta_adct": delta_adct,
            "decision": decision,
            "decision_reasons": decision_reasons,
            "input_started_at": input_started_at,
            "input_submitted_at": now,
            "input_duration_seconds": input_duration_seconds,
            "input_duration_minutes": input_duration_minutes,
            "input_support": result.get("input_support", ""),
            "input_ease": result.get("input_ease", ""),
            "consent_checked": True,
            "consent_method": "in_app_checkbox_before_submission",
            "research_consent_checked": True if result["instrument"] == "ADCT" else "",
            "research_consent_text_version": "ADCT digital PRO feasibility consent v1.0" if result["instrument"] == "ADCT" else "",
            "research_consent_timestamp": now if result["instrument"] == "ADCT" else "",
        }

        for i, score in enumerate(result["scores"], start=1):
            row[f"q{i}_score"] = score
            row[f"q{i}_answer"] = result["answers"][i - 1]

        save_result(row)
        send_to_google_form(row)

        st.session_state["questionnaire_started_at"] = datetime.now(JST).isoformat()
        st.session_state["questionnaire_timer_disease_mode"] = disease_mode

        st.success(t(language, "送信されました。", "Submitted successfully."))

        st.metric(
            result["instrument"] + " " + t(language, "合計点", "total score"),
            f"{result['total_score']} / {result['max_score']}",
        )

        st.caption(
            t(
                language,
                "以下の表示は診療補助のための参考情報です。最終的な判断は医療者が行ってください。",
                "The following display is reference information for clinical support. Final decisions should be made by a qualified healthcare professional.",
            )
        )

        if result["instrument"] == "ADCT":
            st.markdown("---")

            if decision == "維持":
                st.markdown(
                    "<h1 style='text-align:center; color:green;'>🟢 維持</h1>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    "<p style='text-align:center; font-size:20px;'>現在の治療維持が妥当と考えられる可能性があります</p>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    "<h1 style='text-align:center; color:red;'>🔴 非維持</h1>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    "<p style='text-align:center; font-size:20px;'>状態の再評価を推奨します</p>",
                    unsafe_allow_html=True,
                )

            if previous_adct is not None:
                st.markdown(
                    f"<p style='text-align:center;'>ADCT: {result['total_score']}（前回 {previous_adct}） / Δ {delta_adct}</p>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"<p style='text-align:center;'>ADCT: {result['total_score']}（初回）</p>",
                    unsafe_allow_html=True,
                )

            if adct_judgement is not None:
                st.subheader(adct_judgement["display_title"])
                st.write(adct_judgement["message"])

                if adct_judgement["reasons"]:
                    st.markdown("**判定理由**" if language == "日本語" else "**Reasons for flagging**")
                    for reason in adct_judgement["reasons"]:
                        st.markdown(f"- {reason}")
                else:
                    st.caption(
                        t(
                            language,
                            "ADCT総スコア、各項目スコア、前回比のいずれも非維持条件には該当しませんでした。",
                            "The total ADCT score, item scores, and change from previous ADCT did not meet the non-maintenance criteria.",
                        )
                    )

            st.caption(
                t(
                    language,
                    "「維持／非維持」はADCT回答に基づく簡易的な診療補助表示であり、治療継続・変更・中止を自動決定するものではありません。",
                    "The maintenance / non-maintenance display is a simplified clinical-support indicator based on ADCT responses and does not automatically determine whether treatment should be continued, changed, or stopped.",
                )
            )
        else:
            st.subheader(result["severity"])
            st.write(result["interpretation"])
            st.caption(
                t(
                    language,
                    "DLQIの結果は生活の質への影響を把握するための参考情報です。診療判断は医療者が総合的に行ってください。",
                    "The DLQI result is reference information for understanding quality-of-life impact. Clinical decisions should be made comprehensively by a qualified healthcare professional.",
                )
            )

    st.divider()

    show_admin = st.checkbox(
        t(language, "医療者モードを表示", "Show clinician mode")
    )

    if show_admin:
        with st.expander(
            t(language, "医療者用：送信結果確認・CSVダウンロード", "Clinician view: submission review and CSV download")
        ):
            admin_password = st.text_input(
                t(language, "管理者パスワード", "Admin password"),
                type="password",
                help=t(
                    language,
                    "RenderのEnvironmentに ADMIN_PASSWORD を設定してください。",
                    "Set ADMIN_PASSWORD in Render Environment.",
                ),
            )

            configured_password = get_secret("ADMIN_PASSWORD")

            if not configured_password:
                st.caption(
                    t(
                        language,
                        "ADMIN_PASSWORD が未設定のため、CSV閲覧は無効です。",
                        "CSV view is disabled because ADMIN_PASSWORD is not configured.",
                    )
                )
            elif admin_password == configured_password:
                tab_adct, tab_dlqi = st.tabs(["ADCT", "DLQI"])

                with tab_adct:
                    show_csv_tab("ADCT", CSV_PATH_ADCT, "adct_results.csv")

                with tab_dlqi:
                    show_csv_tab("DLQI", CSV_PATH_DLQI, "dlqi_results.csv")

            elif admin_password:
                st.error(t(language, "パスワードが違います。", "Incorrect password."))

    st.caption(
        t(
            language,
            "このアプリは診療補助目的です。診断、治療方針、薬剤選択、治療継続・中止を自動的に決定するものではありません。最終的な診療判断は医療者が行ってください。",
            "For clinical support only. This app does not provide diagnosis, treatment plans, medication selection, or automatic treatment continuation/discontinuation decisions. Final clinical decisions should be made by a qualified clinician.",
        )
    )

    render_credit_footer(language)

    if "ADCT" in disease_mode:
        render_adct_partner_notice(language)


if __name__ == "__main__":
    main()

