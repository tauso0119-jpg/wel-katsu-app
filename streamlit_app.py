import streamlit as st
import pandas as pd
import json
import requests
import base64
from datetime import datetime

# ページ設定
st.set_page_config(page_title="ウェル活Vibes", page_icon="🛒")

# GitHub接続情報（Secretsから取得）
try:
    TOKEN = st.secrets["GITHUB_TOKEN"]
    REPO = st.secrets["GITHUB_REPO"]
except:
    st.error("StreamlitのSecrets設定が足りないよ！GITHUB_TOKEN と GITHUB_REPO を設定してね。")
    st.stop()

FILE_PATH = "data.json"
URL = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"

# データを読み込む
def load_data():
    headers = {"Authorization": f"token {TOKEN}"}
    res = requests.get(URL, headers=headers)
    if res.status_code == 200:
        content = base64.b64decode(res.json()["content"]).decode("utf-8")
        data = json.loads(content)
        # 読み込んだデータが空リストならサンプルを出す
        if not data:
            return pd.DataFrame([{"name": "サンプル", "cat": "テスト", "stock": True, "price": 0, "date": ""}])
        return pd.DataFrame(data)
    return pd.DataFrame([{"name": "読み込み失敗", "cat": "エラー", "stock": True, "price": 0, "date": ""}])

# データを保存する
def save_data(df):
    headers = {"Authorization": f"token {TOKEN}"}
    current_file = requests.get(URL, headers=headers).json()
    new_content = base64.b64encode(df.to_json(orient="records", force_ascii=False).encode("utf-8")).decode("utf-8")
    payload = {"message": "Update", "content": new_content, "sha": current_file["sha"]}
    requests.put(URL, headers=headers, json=payload)

# データの初期化
if "df" not in st.session_state:
    st.session_state.df = load_data()

st.title("🛒 ウェル活・在庫管理")

tab1, tab2, tab3 = st.tabs(["📋 買い物リスト", "🏠 在庫チェック", "➕ 品目追加"])

# タブ1: 買い物（stockがFalseのもの）
with tab1:
    # 確実に文字列として判定
    to_buy = st.session_state.df[st.session_state.df['stock'].astype(str).str.upper() == 'FALSE']
    if not to_buy.empty:
        for idx, row in to_buy.iterrows():
            col1, col2 = st.columns([3, 1])
            col1.warning(f"**{row['name']}**")
            if col2.button("補充", key=f"b_{idx}"):
                st.session_state.df.at[idx, 'stock'] = True
                save_data(st.session_state.df)
                st.rerun()
    else:
        st.success("買うものリストは空です✨")

# タブ2: 在庫一覧
with tab2:
    for idx, row in st.session_state.df.iterrows():
        col1, col2 = st.columns([3, 1])
        is_ok = str(row['stock']).upper() == 'TRUE'
        status = "✅" if is_ok else "🚨"
        col1.write(f"{status} **{row['name']}** ({row['cat']})")
        if col2.button("切替", key=f"s_{idx}"):
            st.session_state.df.at[idx, 'stock'] = not is_ok
            save_data(st.session_state.df)
            st.rerun()

# タブ3: 追加
with tab3:
    with st.form("add"):
        n = st.text_input("品名")
        c = st.text_input("場所")
        if st.form_submit_button("追加") and n and c:
            new_row = pd.DataFrame([{"name": n, "cat": c, "stock": True, "price": 0, "date": ""}])
            st.session_state.df = pd.concat([st.session_state.df, new_row], ignore_index=True)
            save_data(st.session_state.df)
            st.rerun()
