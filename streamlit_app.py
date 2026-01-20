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
    .cat-header { 
        background-color: #f0f2f6; 
        padding: 5px 15px; 
        border-radius: 10px; 
        border-left: 5px solid #005bac; /* ウェルシアブルーっぽく */
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
    .total-font { font-size: 18px; font-weight: bold; }
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

# タブ
tab1, tab2, tab3, tab4 = st.tabs(["🛒 買い物", "🏠 在庫", "➕ 商品", "📁 カテゴリ"])

# --- タブ1: 買い物（ここに予算設定を集約！） ---
with tab1:
    # 1. ポイント・予算設定エリア
    with st.expander("💰 ポイント・予算設定", expanded=(data.get("points") == 0)):
        col_pts, col_btn = st.columns([2, 1])
        points = col_pts.number_input("保有ポイント", value=data.get("points", 0), step=100)
        if col_btn.button("保存", key="save_pts"):
            data["points"] = points
            save_all_data(data)
            st.rerun()
    
    limit_amount = int(points * 1.5)
    
    # 2. 現在の計算状況を表示
    buying_df = df[df['to_buy'] == True]
    total_spent = sum(buying_df['last_price'].astype(int))
    remaining = limit_amount - total_spent
    
    st.markdown(f"""
        <div class="money-box">
            <div class="total-font">予算(1.5倍): {limit_amount} 円</div>
            <div class="total-font">現在の合計: {total_spent} 円</div>
            <div style="margin-top:5px;">あと <span class="money-font">{remaining}</span> 円買えます</div>
        </div>
    """, unsafe_allow_html=True)
    
    if remaining < 0:
        st.error("予算オーバーです！")

    # 3. 買い物リスト本体
    if buying_df.empty:
        st.info("買い物リストは空です。「在庫」タブから選んでね！")
    else:
        st.subheader("🛒 カゴの中身をチェック")
        for idx, row in buying_df.iterrows():
            with st.container():
                c1, c2, c3 = st.columns([2, 1, 1])
                c1.markdown(f"**{row['name']}**")
                # 金額入力（入力すると即座に上の残金に反映されるようにrerunを入れるのが理想ですが、まずは入力保存を優先）
                p = c2.number_input("円", key=f"bp_{idx}", value=int(row['last_price']), step=10)
                
                # 金額が変わったらデータ更新して保存
                if p != row['last_price']:
                    df.at[idx, 'last_price'] = p
                    data["inventory"] = df.to_dict(orient="records")
                    save_all_data(data)
                    st.rerun()

                if c3.button("完", key=f"cp_{idx}"):
                    df.at[idx, 'to_buy'] = False
                    data["inventory"] = df.to_dict(orient="records")
                    save_all_data(data)
                    st.rerun()

# --- タブ2: 在庫（カテゴリ別） ---
with tab2:
    if not df.empty:
        sel_cat = st.selectbox("カテゴリ絞込", ["すべて"] + data["categories"])
        target_cats = data["categories"] if sel_cat == "すべて" else [sel_cat]
        
        for category in target_cats:
            cat_df = df[df['cat'] == category]
            if not cat_df.empty:
                st.markdown(f'<div class="cat-header">{category}</div>', unsafe_allow_html=True)
                for idx, row in cat_df.iterrows():
                    with st.container():
                        c1, c2 = st.columns([3, 1])
                        is_buying = row['to_buy']
                        icon = "🚨" if is_buying else "✅"
                        c1.write(f"{icon} **{row['name']}** \n<small>前回:{row['last_price']}円</small>", unsafe_allow_html=True)
                        if c2.button("取消" if is_buying else "買う", key=f"add_{idx}"):
                            df.at[idx, 'to_buy'] = not is_buying
                            data["inventory"] = df.to_dict(orient="records")
                            save_all_data(data)
                            st.rerun()
    else:
        st.write("「商品」から登録してね")

# --- タブ3・4（追加・カテゴリ） ---
with tab3:
    st.subheader("新しい商品")
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
    st.subheader("カテゴリ管理")
    new_c = st.text_input("新カテゴリ名")
    if st.button("追加"):
        if new_c and new_c not in data["categories"]:
            data["categories"].append(new_c)
            save_all_data(data)
            st.rerun()
    st.divider()
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
