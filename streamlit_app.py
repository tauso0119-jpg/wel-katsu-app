import streamlit as st
import pandas as pd
import json
import requests
import base64
from datetime import datetime

# 1. ページ設定
st.set_page_config(page_title="ウェル活マスター", page_icon="🛒")

# GitHub接続情報
TOKEN = st.secrets["GITHUB_TOKEN"]
REPO = st.secrets["GITHUB_REPO"]
FILE_PATH = "data.json"
URL = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"

# スタイル（スマホで見やすく）
st.markdown("""
    <style>
    .stButton > button { width: 100%; border-radius: 10px; height: 3em; }
    .main-font { font-size:20px !important; font-weight: bold; }
    .money-font { color: #d33682; font-size: 24px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# データを読み書きする関数
def load_all_data():
    headers = {"Authorization": f"token {TOKEN}"}
    res = requests.get(URL, headers=headers)
    if res.status_code == 200:
        content = base64.b64decode(res.json()["content"]).decode("utf-8")
        return json.loads(content)
    return {"inventory": [], "points": 0}

def save_all_data(full_data):
    headers = {"Authorization": f"token {TOKEN}"}
    current_file = requests.get(URL, headers=headers).json()
    json_data = json.dumps(full_data, ensure_ascii=False)
    new_content = base64.b64encode(json_data.encode("utf-8")).decode("utf-8")
    payload = {"message": "Update Data", "content": new_content, "sha": current_file["sha"]}
    requests.put(URL, headers=headers, json=payload)

# 初期化
if "full_data" not in st.session_state:
    st.session_state.full_data = load_all_data()

data = st.session_state.full_data
df = pd.DataFrame(data["inventory"])
if df.empty:
    df = pd.DataFrame(columns=["name", "cat", "to_buy", "last_price"])

# --- メイン画面 ---
now = datetime.now()
st.title(f"🛍️ {now.month}月分 ウェル活")

# ポイント計算セクション
with st.sidebar:
    st.header("💰 ポイント設定")
    points = st.number_input("保有Vポイント/イオンポイント", value=data.get("points", 0), step=100)
    if st.button("ポイント保存"):
        data["points"] = points
        save_all_data(data)
        st.success("保存完了")
    
    limit_amount = int(points * 1.5)
    st.metric("お買い物上限 (1.5倍)", f"{limit_amount} 円")

# タブ分け
tab1, tab2, tab3 = st.tabs(["🛒 買い物リスト", "🏠 在庫リスト", "➕ 品目追加"])

# --- タブ1: 買い物リスト ---
with tab1:
    buying_df = df[df['to_buy'] == True]
    
    # 合計計算
    total_spent = 0
    st.subheader("今月の買うもの")
    
    for idx, row in buying_df.iterrows():
        with st.container():
            c1, c2, c3 = st.columns([2, 1, 1])
            c1.markdown(f"**{row['name']}**")
            # 金額入力
            input_price = c2.number_input("金額", key=f"buy_p_{idx}", value=int(row['last_price']), step=10)
            total_spent += input_price
            
            if c3.button("完了", key=f"comp_{idx}"):
                # 完了したら在庫リストに戻し、金額を保存、買うものフラグを下ろす
                df.at[idx, 'to_buy'] = False
                df.at[idx, 'last_price'] = input_price
                data["inventory"] = df.to_dict(orient="records")
                save_all_data(data)
                st.rerun()

    st.divider()
    remaining = limit_amount - total_spent
    st.markdown(f"現在の合計: **{total_spent} 円**")
    st.markdown(f"あと <span class='money-font'>{remaining}</span> 円分買えます", unsafe_allow_html=True)
    if remaining < 0:
        st.error("予算オーバーです！")

# --- タブ2: 在庫リスト ---
with tab2:
    st.subheader("お家在庫リスト")
    if not df.empty:
        selected_cat = st.selectbox("カテゴリ絞り込み", ["すべて"] + list(df['cat'].unique()))
        display_df = df if selected_cat == "すべて" else df[df['cat'] == selected_cat]
        
        for idx, row in display_df.iterrows():
            c1, c2 = st.columns([3, 1])
            status = "🚨 買う！" if row['to_buy'] else "✅ 在庫あり"
            c1.write(f"**{row['name']}** ({row['cat']})  \n<small>前回: {row['last_price']}円</small>", unsafe_allow_html=True)
            
            label = "リストから外す" if row['to_buy'] else "これ買う！"
            if c2.button(label, key=f"add_list_{idx}"):
                df.at[idx, 'to_buy'] = not row['to_buy']
                data["inventory"] = df.to_dict(orient="records")
                save_all_data(data)
                st.rerun()
    else:
        st.info("品目を追加してください")

# --- タブ3: 品目追加 ---
with tab3:
    st.subheader("新しい商品を追加")
    with st.form("new_item"):
        new_n = st.text_input("商品名")
        new_c = st.text_input("カテゴリ（洗面所、お風呂など）")
        if st.form_submit_button("追加"):
            if new_n and new_c:
                new_data = {"name": new_n, "cat": new_c, "to_buy": False, "last_price": 0}
                data["inventory"].append(new_data)
                save_all_data(data)
                st.success(f"{new_n}を追加しました")
                st.rerun()

# 月跨ぎリセット機能（月初に自動でto_buyをFalseにする）
# ※簡易的に、最後に保存した月と現在の月が違えばリセットするロジック
if "last_month" not in data:
    data["last_month"] = now.month
    save_all_data(data)

if data["last_month"] != now.month:
    for item in data["inventory"]:
        item["to_buy"] = False
    data["last_month"] = now.month
    save_all_data(data)
    st.rerun()
