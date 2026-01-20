import streamlit as st
import pandas as pd
import json
import requests
import base64
from datetime import datetime

# 1. ページ設定
st.set_page_config(page_title="ウェル活マスター", page_icon="🛒")

# スマホ向けデザイン調整
st.markdown("""
    <style>
    .stButton > button { width: 100%; border-radius: 12px; font-weight: bold; height: 3.5em; }
    .money-font { color: #ff4b4b; font-size: 28px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# GitHub接続情報
TOKEN = st.secrets["GITHUB_TOKEN"]
REPO = st.secrets["GITHUB_REPO"]
FILE_PATH = "data.json"
URL = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"

def load_all_data():
    headers = {"Authorization": f"token {TOKEN}"}
    res = requests.get(URL, headers=headers)
    if res.status_code == 200:
        content = base64.b64decode(res.json()["content"]).decode("utf-8")
        return json.loads(content)
    return {"inventory": [], "categories": ["未分類"], "points": 0, "last_month": 1}

def save_all_data(full_data):
    headers = {"Authorization": f"token {TOKEN}"}
    current_file = requests.get(URL, headers=headers).json()
    json_data = json.dumps(full_data, ensure_ascii=False)
    new_content = base64.b64encode(json_data.encode("utf-8")).decode("utf-8")
    payload = {"message": "Update Data", "content": new_content, "sha": current_file["sha"]}
    requests.put(URL, headers=headers, json=payload)

# データ読み込み
if "full_data" not in st.session_state:
    st.session_state.full_data = load_all_data()

data = st.session_state.full_data
df = pd.DataFrame(data["inventory"])
if df.empty:
    df = pd.DataFrame(columns=["name", "cat", "to_buy", "last_price"])

# --- メイン画面トップ ---
now = datetime.now()
st.title(f"🛍️ {now.month}月分 ウェル活")

# ポイント・予算
with st.expander("💰 ポイント・予算設定"):
    col_pts, col_btn = st.columns([2, 1])
    points = col_pts.number_input("保有ポイント", value=data.get("points", 0), step=100)
    if col_btn.button("保存"):
        data["points"] = points
        save_all_data(data)
        st.rerun()
    limit_amount = int(points * 1.5)
    st.markdown(f"予算: <span class='money-font'>{limit_amount}</span> 円", unsafe_allow_html=True)

# タブ
tab1, tab2, tab3, tab4 = st.tabs(["🛒 買い物", "🏠 在庫", "➕ 商品追加", "📁 カテゴリ"])

# --- タブ1: 買い物 ---
with tab1:
    buying_df = df[df['to_buy'] == True]
    total_spent = 0
    if buying_df.empty:
        st.info("買い物リストは空です")
    else:
        for idx, row in buying_df.iterrows():
            with st.container():
                c1, c2, c3 = st.columns([2, 1, 1])
                c1.markdown(f"**{row['name']}**")
                p = c2.number_input("円", key=f"bp_{idx}", value=int(row['last_price']), step=10)
                total_spent += p
                if c3.button("完", key=f"cp_{idx}"):
                    df.at[idx, 'to_buy'] = False
                    df.at[idx, 'last_price'] = p
                    data["inventory"] = df.to_dict(orient="records")
                    save_all_data(data)
                    st.rerun()
    st.divider()
    remaining = limit_amount - total_spent
    st.markdown(f"現在: {total_spent}円 / 残り: <span class='money-font'>{remaining}</span>円", unsafe_allow_html=True)

# --- タブ2: 在庫 ---
with tab2:
    if not df.empty:
        sel_cat = st.selectbox("カテゴリ絞込", ["すべて"] + data["categories"])
        disp_df = df if sel_cat == "すべて" else df[df['cat'] == sel_cat]
        for idx, row in disp_df.iterrows():
            c1, c2 = st.columns([3, 1])
            is_buying = row['to_buy']
            icon = "🚨" if is_buying else "✅"
            c1.write(f"{icon} **{row['name']}** \n<small>{row['cat']} / 前:{row['last_price']}円</small>", unsafe_allow_html=True)
            if c2.button("取消" if is_buying else "買う", key=f"add_{idx}"):
                df.at[idx, 'to_buy'] = not is_buying
                data["inventory"] = df.to_dict(orient="records")
                save_all_data(data)
                st.rerun()

# --- タブ3: 商品追加 ---
with tab3:
    st.subheader("新しい商品を追加")
    with st.form("new_item"):
        n = st.text_input("商品名")
        # プルダウンでカテゴリを選択
        c = st.selectbox("カテゴリを選択", data["categories"])
        if st.form_submit_button("商品を登録"):
            if n:
                new_item = {"name": n, "cat": c, "to_buy": False, "last_price": 0}
                data["inventory"].append(new_item)
                save_all_data(data)
                st.success(f"{n} を登録しました！")
                st.rerun()

# --- タブ4: カテゴリ管理 ---
with tab4:
    st.subheader("カテゴリの登録・削除")
    new_c = st.text_input("新しいカテゴリ名（例：キッチン）")
    if st.button("カテゴリを追加"):
        if new_c and new_c not in data["categories"]:
            data["categories"].append(new_c)
            save_all_data(data)
            st.success(f"カテゴリ「{new_c}」を追加しました")
            st.rerun()
    
    st.divider()
    st.write("現在のカテゴリ（削除は慎重に！）")
    for cat in data["categories"]:
        col_name, col_del = st.columns([3, 1])
        col_name.write(cat)
        if col_del.button("削除", key=f"del_{cat}"):
            data["categories"].remove(cat)
            save_all_data(data)
            st.rerun()

# 月跨ぎリセット
if data.get("last_month") != now.month:
    for item in data["inventory"]:
        item["to_buy"] = False
    data["last_month"] = now.month
    save_all_data(data)
    st.rerun()
