import streamlit as st
import pandas as pd
import json
import requests
import base64
from datetime import datetime

# 1. ページの設定
st.set_page_config(page_title="ウェル活Vibes", page_icon="🛒")

# スマホ向けのデザイン調整
st.markdown("""
    <style>
    .stButton > button { width: 100%; border-radius: 12px; font-weight: bold; height: 3.5em; }
    </style>
    """, unsafe_allow_html=True)

# 2. GitHub接続設定（Secretsから読み込み）
TOKEN = st.secrets["GITHUB_TOKEN"]
REPO = st.secrets["GITHUB_REPO"]
FILE_PATH = "data.json"
URL = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"

# データをGitHubから読み込む関数
def load_data():
    headers = {"Authorization": f"token {TOKEN}"}
    res = requests.get(URL, headers=headers)
    if res.status_code == 200:
        content = base64.b64decode(res.json()["content"]).decode("utf-8")
        data = json.loads(content)
        return pd.DataFrame(data)
    # ファイルがない場合は空の表を返す
    return pd.DataFrame(columns=["name", "cat", "stock", "price", "date"])

# データをGitHubに保存する関数
def save_data(df):
    headers = {"Authorization": f"token {TOKEN}"}
    # 現在のファイルのSHA（バージョン情報）を取得
    current_file = requests.get(URL, headers=headers).json()
    sha = current_file["sha"]
    
    # 日本語が化けないようにjson化してBase64エンコード
    json_data = df.to_json(orient="records", force_ascii=False)
    new_content = base64.b64encode(json_data.encode("utf-8")).decode("utf-8")
    
    payload = {
        "message": "Update inventory from App",
        "content": new_content,
        "sha": sha
    }
    requests.put(URL, headers=headers, json=payload)

# データの初期化
if "df" not in st.session_state:
    st.session_state.df = load_data()

df = st.session_state.df

st.title("🛒 ウェル活・在庫管理")

# 3. タブ機能
tab1, tab2, tab3 = st.tabs(["📋 買い物リスト", "🏠 在庫チェック", "➕ 品目追加"])

# --- タブ1: 買い物リスト ---
with tab1:
    to_buy = df[df['stock'].astype(str).upper() == 'FALSE']
    if not to_buy.empty:
        st.subheader("🚨 今日買うもの")
        for idx, row in to_buy.iterrows():
            col1, col2, col3 = st.columns([2, 1, 1])
            col1.warning(f"**{row['name']}**")
            price = col2.number_input("円", key=f"p_{idx}", value=int(row.get('price', 0)))
            if col3.button("補充", key=f"b_{idx}"):
                df.at[idx, 'stock'] = True
                df.at[idx, 'price'] = price
                df.at[idx, 'date'] = datetime.now().strftime('%m/%d')
                save_data(df)
                st.success("補充完了！")
                st.rerun()
    else:
        st.success("買うものリストは空です✨")

# --- タブ2: 在庫チェック ---
with tab2:
    st.subheader("🏠 お家在庫")
    cats = ["すべて"] + sorted(df['cat'].unique().tolist())
    sel_cat = st.selectbox("場所を選択", cats)
    
    view_df = df if sel_cat == "すべて" else df[df['cat'] == sel_cat]
    
    for idx, row in view_df.iterrows():
        col1, col2 = st.columns([3, 1])
        is_stock = str(row['stock']).upper() == 'TRUE'
        status = "✅" if is_stock else "🚨"
        col1.write(f"{status} **{row['name']}** ({row['cat']})")
        if col2.button("切替", key=f"sw_{idx}"):
            df.at[idx, 'stock'] = not is_stock
            save_data(df)
            st.rerun()

# --- タブ3: 品目追加 ---
with tab3:
    st.subheader("新しい品物を追加")
    with st.form("add_form"):
        new_n = st.text_input("品名 (例: 洗剤)")
        new_c = st.text_input("場所 (例: 洗面所)")
        if st.form_submit_button("リストに追加"):
            if new_n and new_c:
                new_row = pd.DataFrame([{"name": new_n, "cat": new_c, "stock": True, "price": 0, "date": ""}])
                st.session_state.df = pd.concat([df, new_row], ignore_index=True)
                save_data(st.session_state.df)
                st.success(f"{new_n} を追加しました！")
                st.rerun()

# サイドバー
st.sidebar.metric("ウェル活まで", "当日！" if datetime.now().day == 20 else f"あと {20-datetime.now().day} 日")
