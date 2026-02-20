import streamlit as st
import pandas as pd
import json
import requests
import base64
import numpy as np
from datetime import datetime

# 1. ページ設定
st.set_page_config(
    page_title="ウェル活マスター Pro", 
    page_icon="🛒", 
    layout="centered",
    initial_sidebar_state="collapsed"
)

# iOS用のPWA設定
st.components.v1.html(
    """
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    """,
    height=0,
)

# 2. デザインCSS
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display:none;}
    [data-testid="stHeader"] {display: none;}
    
    .main { background-color: #f8f9fa; }
    .block-container { padding: 0.5rem 1rem !important; }

    .app-title {
        font-size: clamp(20px, 6vw, 28px);
        font-weight: 850;
        color: #333;
        letter-spacing: -0.5px;
        margin: 10px 0 15px 0;
        display: flex; align-items: center; gap: 8px;
    }

    .money-summary {
        background: linear-gradient(135deg, #ff4b4b 0%, #ff7676 100%);
        padding: 18px; border-radius: 20px; color: white;
        box-shadow: 0 4px 15px rgba(255, 75, 75, 0.2);
        margin-bottom: 20px; text-align: center;
    }
    .money-val { font-size: 30px; font-weight: 850; }
    .money-sub { font-size: 12px; opacity: 0.9; margin-bottom: 2px; }

    /* 商品名と斜線スタイル */
    .item-name { font-size: 16px; font-weight: 700; color: #333; margin-bottom: 1px; }
    .item-done { font-size: 16px; font-weight: 700; color: #bbb; text-decoration: line-through; }
    .real-name { font-size: 11px; color: #999; margin-bottom: 4px; display: block; }
    .real-done { font-size: 11px; color: #ccc; text-decoration: line-through; margin-bottom: 4px; }
    
    /* 商品ごとの合計表示 */
    .item-total {
        font-size: 14px; font-weight: 800; color: #ff4b4b;
        text-align: right; margin-top: 5px; padding-right: 5px;
    }

    .stTextInput input {
        border-radius: 12px !important; border: 1px solid #e0e0e0 !important;
        font-size: 16px !important; font-weight: 600 !important;
        text-align: center !important; height: 42px !important;
    }

    .cat-header {
        background-color: #333; color: white;
        padding: 8px 15px; border-radius: 10px;
        font-weight: 800; font-size: 13px;
        margin: 20px 0 10px 0; letter-spacing: 0.5px;
    }

    div[data-baseweb="select"] input { readonly: readonly; inputmode: none; }
    .stTabs [aria-selected="true"] { background-color: #ff4b4b !important; color: white !important; border-radius: 10px 10px 0 0; }
    </style>
    """, unsafe_allow_html=True)

# --- GitHub連携 ---
TOKEN = st.secrets["GITHUB_TOKEN"]
REPO = st.secrets["GITHUB_REPO"]
FILE_PATH = "data.json"
URL = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"

def load_data():
    headers = {"Authorization": f"token {TOKEN}"}
    try:
        res = requests.get(URL, headers=headers)
        if res.status_code == 200:
            return json.loads(base64.b64decode(res.json()["content"]).decode("utf-8"))
    except: pass
    return {"inventory": [], "categories": ["洗面所", "キッチン", "お風呂"], "points": 0, "last_month": 1}

def save_data(full_data):
    headers = {"Authorization": f"token {TOKEN}"}
    current = requests.get(URL, headers=headers).json()
    payload = {
        "message": "Update Data",
        "content": base64.b64encode(json.dumps(full_data, ensure_ascii=False).encode("utf-8")).decode("utf-8"),
        "sha": current["sha"]
    }
    requests.put(URL, headers=headers, json=payload)

if "full_data" not in st.session_state:
    st.session_state.full_data = load_data()

data = st.session_state.full_data
for item in data["inventory"]:
    item.setdefault("quantity", 1); item.setdefault("real_name", ""); item.setdefault("current_price", None); item.setdefault("last_price", 0); item.setdefault("is_packed", False)

# --- UI構築 ---
now = datetime.now()
st.markdown(f'<div class="app-title">🛍️ {now.month}月のウェル活</div>', unsafe_allow_html=True)

t1, t2, t3, t4 = st.tabs(["🛍️ 買い物", "🏠 在庫", "➕ 追加", "📁 設定"])

with t1:
    with st.expander("💰 予算・ポイントを設定する"):
        input_pts = st.text_input("保有ポイント", value=str(data.get("points", 0)))
        if st.button("予算を更新", use_container_width=True):
            data["points"] = int(input_pts) if input_pts.isdigit() else 0
            save_data(data); st.rerun()

    limit = int(data.get("points", 0) * 1.5)
    
    # 全体の合計金額計算
    total_spent = 0
    buying_indices = [i for i, item in enumerate(data["inventory"]) if item.get("to_buy")]
    
    for i in buying_indices:
        item = data["inventory"][i]
        q = item.get("quantity", 1)
        p = item.get("current_price") if item.get("current_price") is not None else item.get("last_price", 0)
        total_spent += (int(p) * int(q))

    st.markdown(f"""
        <div class="money-summary">
            <div class="money-sub">総予算 {limit}円 ／ 合計 {int(total_spent)}円</div>
            <div class="money-val">残り {int(limit - total_spent)} 円</div>
        </div>
    """, unsafe_allow_html=True)

    if not buying_indices:
        st.info("「在庫」タブから選んでください")
    else:
        for i in buying_indices:
            item = data["inventory"][i]
            
            # チェックボックスと商品名
            head_col1, head_col2 = st.columns([1, 9])
            packed = head_col1.checkbox("", value=item.get("is_packed", False), key=f"pack_{i}", label_visibility="collapsed")
            if packed != item.get("is_packed"):
                item["is_packed"] = packed; st.rerun()
            
            name_style = "item-done" if packed else "item-name"
            real_style = "real-done" if packed else "real-name"
            
            head_col2.markdown(f"<div class='{name_style}'>{item['name']}</div>", unsafe_allow_html=True)
            if item.get('real_name'):
                head_col2.markdown(f"<div class='{real_style}'>{item['real_name']}</div>", unsafe_allow_html=True)
            
            # 個数と単価の入力
            c1, c2 = st.columns([1, 1])
            q_val = item.get('quantity', 1)
            q_in = c1.text_input("個数", value=str(q_val), key=f"q_{i}")
            
            p_val = item.get("current_price") if item.get("current_price") is not None else item.get("last_price", 0)
            p_in = c2.text_input("単価(1個)", value=str(int(p_val)), key=f"p_{i}")

            # 変更検知
            if q_in.isdigit() and int(q_in) != q_val:
                item['quantity'] = int(q_in); st.rerun()
            if p_in.isdigit() and int(p_in) != int(p_val):
                item['current_price'] = int(p_in); st.rerun()
            
            # その商品の合計を表示（ここが復活！）
            item_sum = int(q_in if q_in.isdigit() else 0) * int(p_in if p_in.isdigit() else 0)
            st.markdown(f"<div class='item-total'>小計: {item_sum} 円</div>", unsafe_allow_html=True)
            st.divider()

        if st.button("🎉 お買い物完了", type="primary", use_container_width=True):
            for item in data["inventory"]:
                if item.get("to_buy"):
                    # 最終的な単価を保存
                    item["last_price"] = item.get("current_price") if item.get("current_price") is not None else item.get("last_price")
                    item["current_price"] = None; item["quantity"] = 1; item["to_buy"] = False; item["is_packed"] = False
            save_data(data); st.balloons(); st.rerun()

with t2:
    sel_cat = st.selectbox("フィルタ", ["すべて"] + data["categories"], key="filter")
    for category in (data["categories"] if sel_cat == "すべて" else [sel_cat]):
        items = [i for i, x in enumerate(data["inventory"]) if x["cat"] == category]
        if items:
            st.markdown(f'<div class="cat-header">◼️ {category.upper()}</div>', unsafe_allow_html=True)
            for i in items:
                item = data["inventory"][i]
                col1, col2 = st.columns([1, 8])
                is_on = col1.checkbox("", value=bool(item.get("to_buy")), key=f"inv_{i}", label_visibility="collapsed")
                if is_on != item.get("to_buy"):
                    item["to_buy"] = is_on; item["current_price"] = None; item["quantity"] = 1; item["is_packed"] = False
                    save_data(data); st.rerun()
                col2.markdown(f"**{item['name']}** <small>({int(item.get('last_price',0))}円)</small><br><span style='color:#999;font-size:12px;'>{item.get('real_name','')}</span>", unsafe_allow_html=True)

with t3:
    with st.form("add"):
        n = st.text_input("分類名"); rn = st.text_input("実際の商品名"); c = st.selectbox("カテゴリ", data["categories"])
        if st.form_submit_button("登録") and n:
            data["inventory"].append({"name": n, "real_name": rn, "cat": c, "to_buy": False, "last_price": 0, "quantity": 1, "is_packed": False})
            save_data(data); st.rerun()

with t4:
    st.write("カテゴリ管理")
    new_c = st.text_input("新カテゴリ名")
    if st.button("カテゴリ追加"): data["categories"].append(new_c); save_data(data); st.rerun()

if data.get("last_month") != now.month:
    for item in data["inventory"]: item["to_buy"] = False; item["current_price"] = None; item["quantity"] = 1; item["is_packed"] = False
    data.update({"last_month": now.month}); save_data(data); st.rerun()
