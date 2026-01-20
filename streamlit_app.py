import streamlit as st
import pandas as pd
import json
import requests
import base64
from datetime import datetime

# 1. ページ設定
st.set_page_config(page_title="ウェル活マスター", page_icon="🛒")

# スマホ向けデザイン：入力BOXをスリムに、数字キーボードを出しやすく
st.markdown("""
    <style>
    .stButton > button { width: 100%; border-radius: 12px; font-weight: bold; height: 3.5em; }
    .cat-header { 
        background-color: #f0f2f6; 
        padding: 5px 15px; 
        border-radius: 10px; 
        border-left: 5px solid #005bac;
        margin: 20px 0 10px 0;
        font-weight: bold;
    }
    .money-box {
        background-color: #fff1f1;
        padding: 15px;
        border-radius: 15px;
        border: 2px solid #ff4b4b;
        margin-bottom: 20px;
    }
    .money-font { color: #ff4b4b; font-size: 24px; font-weight: bold; }
    /* 入力ボックスを短く、スッキリさせる設定 */
    div[data-testid="stTextInput"] { width: 80px !important; }
    input { text-align: right; padding: 5px !important; }
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

# --- メインタイトル ---
now = datetime.now()
st.title(f"🛍️ {now.month}月分 ウェル活")

tab1, tab2, tab3, tab4 = st.tabs(["🛒 買い物", "🏠 在庫", "➕ 商品", "📁 カテゴリ"])

# --- タブ1: 買い物 ---
with tab1:
    with st.expander("💰 ポイント・予算設定"):
        points_str = st.text_input("保有ポイント", value=str(data.get("points", 0)))
        if st.button("ポイント保存"):
            data["points"] = int(points_str) if points_str.isdigit() else 0
            save_all_data(data)
            st.rerun()
    
    limit_amount = int(data.get("points", 0) * 1.5)
    buying_df = df[df['to_buy'] == True]
    
    # 金額の計算（文字列を数値に変換）
    total_spent = sum(pd.to_numeric(buying_df['last_price'], errors='coerce').fillna(0))
    remaining = limit_amount - total_spent
    
    st.markdown(f"""
        <div class="money-box">
            <div style="font-size:16px;">予算: {limit_amount}円 / 合計: {int(total_spent)}円</div>
            <div style="margin-top:5px;">残り <span class="money-font">{int(remaining)}</span> 円</div>
        </div>
    """, unsafe_allow_html=True)

    if buying_df.empty:
        st.info("買い物リストは空です")
    else:
        for idx, row in buying_df.iterrows():
            with st.container():
                c1, c2, c3 = st.columns([2, 1, 1])
                c1.markdown(f"**{row['name']}**")
                
                # テキスト入力ボックス（＋ーなし）
                # label_visibility="collapsed" でラベルを消してスッキリ
                p_input = c2.text_input("金額", value=str(row['last_price']), key=f"txt_{idx}", label_visibility="collapsed")
                
                # 値が変わったら自動保存
                if p_input != str(row['last_price']):
                    df.at[idx, 'last_price'] = int(p_input) if p_input.isdigit() else 0
                    data["inventory"] = df.to_dict(orient="records")
                    save_all_data(data)
                    st.rerun()

                if c3.button("完", key=f"cp_{idx}"):
                    df.at[idx, 'to_buy'] = False
                    data["inventory"] = df.to_dict(orient="records")
                    save_all_data(data)
                    st.rerun()

# --- タブ2: 在庫 ---
with tab2:
    if not df.empty:
        sel_cat = st.selectbox("カテゴリ絞込", ["すべて"] + data["categories"])
        target_cats = data["categories"] if sel_cat == "すべて" else [sel_cat]
        for category in target_cats:
            cat_df = df[df['cat'] == category]
            if not cat_df.empty:
                st.markdown(f'<div class="cat-header">{category}</div>', unsafe_allow_html=True)
                for idx, row in cat_df.iterrows():
                    c1, c2 = st.columns([3, 1])
                    is_buying = row['to_buy']
                    c1.write(f"{'🚨' if is_buying else '✅'} **{row['name']}** \n<small>前回:{row['last_price']}円</small>", unsafe_allow_html=True)
                    if c2.button("取消" if is_buying else "買う", key=f"add_{idx}"):
                        df.at[idx, 'to_buy'] = not is_buying
                        data["inventory"] = df.to_dict(orient="records")
                        save_all_data(data)
                        st.rerun()

# --- タブ3・4（追加・カテゴリ） ---
with tab3:
    with st.form("new_item"):
        n = st.text_input("商品名")
        c = st.selectbox("カテゴリ", data["categories"])
        if st.form_submit_button("登録"):
            if n:
                new_item = {"name": n, "cat": c, "to_buy": False, "last_price": 0}
                data["inventory"].append(new_item)
                save_all_data(data)
                st.rerun()

with tab4:
    new_c = st.text_input("新カテゴリ名")
    if st.button("カテゴリ追加"):
        if new_c and new_c not in data["categories"]:
            data["categories"].append(new_c)
            save_all_data(data)
            st.rerun()
    st.divider()
    for cat in data["categories"]:
        c_name, c_del = st.columns([3, 1])
        c_name.write(cat)
        if c_del.button("削除", key=f"del_{cat}"):
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
