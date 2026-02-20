import streamlit as st
import pandas as pd
import json
import requests
import base64
import numpy as np
from datetime import datetime

# 1. ページ設定
st.set_page_config(page_title="ウェル活マスター", page_icon="🛒", layout="centered")

# 2. CSS：スマホ最適化（＋ーを消し、文字サイズを調整）
st.markdown("""
    <style>
    .block-container { padding: 1rem 1rem !important; }
    .money-summary {
        background-color: #fff1f1; padding: 15px; border-radius: 15px; 
        border: 2px solid #ff4b4b; margin-bottom: 15px; text-align: center;
    }
    .money-val { color: #ff4b4b; font-size: 26px; font-weight: bold; }
    
    /* ＋ーボタンを非表示、右寄せ */
    input[type=number]::-webkit-inner-spin-button, 
    input[type=number]::-webkit-outer-spin-button { 
        -webkit-appearance: none; margin: 0; 
    }
    input[type=number] {
        -moz-appearance: textfield;
        font-size: 16px !important;
        text-align: right !important;
    }
    .stTextInput input { font-size: 16px !important; text-align: right !important; }

    .item-name { font-weight: bold; font-size: 15px; margin-bottom: 5px; }
    .total-label { color: #ff4b4b; font-weight: bold; font-size: 16px; text-align: right; line-height: 40px; }
    </style>
    """, unsafe_allow_html=True)

# GitHub接続
TOKEN = st.secrets["GITHUB_TOKEN"]
REPO = st.secrets["GITHUB_REPO"]
FILE_PATH = "data.json"
URL = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"

def load_all_data():
    headers = {"Authorization": f"token {TOKEN}"}
    try:
        res = requests.get(URL, headers=headers)
        if res.status_code == 200:
            content = base64.b64decode(res.json()["content"]).decode("utf-8")
            return json.loads(content)
    except: pass
    return {"inventory": [], "categories": ["洗面所", "キッチン", "お風呂"], "points": 0, "last_month": 1}

def save_all_data(full_data):
    headers = {"Authorization": f"token {TOKEN}"}
    current_file = requests.get(URL, headers=headers).json()
    json_data = json.dumps(full_data, ensure_ascii=False)
    new_content = base64.b64encode(json_data.encode("utf-8")).decode("utf-8")
    payload = {"message": "Update Data", "content": new_content, "sha": current_file["sha"]}
    requests.put(URL, headers=headers, json=payload)

if "full_data" not in st.session_state:
    st.session_state.full_data = load_all_data()

data = st.session_state.full_data

now = datetime.now()
st.title(f"🛍️ {now.month}月 ウェル活")
t1, t2, t3, t4 = st.tabs(["🛒 買い物", "🏠 在庫", "➕ 追加", "📁 設定"])

with t1:
    limit = int(data.get("points", 0) * 1.5)
    buying_indices = [i for i, item in enumerate(data["inventory"]) if item.get("to_buy")]
    
    # 全体の合計金額を事前計算
    spent = 0
    for i in buying_indices:
        item = data["inventory"][i]
        price = item.get("current_price") if item.get("current_price") is not None else item.get("last_price", 0)
        spent += (int(price) * int(item.get("quantity", 1)))

    st.markdown(f'<div class="money-summary"><div style="font-size:14px;color:#555;">予算 {limit}円 / 合計 {int(spent)}円</div><div class="money-val">残り {int(limit - spent)} 円</div></div>', unsafe_allow_html=True)
    
    if not buying_indices:
        st.info("在庫タブでチェックを入れてください")
    else:
        # 見出し
        h1, h2, h3, h4 = st.columns([1.5, 0.8, 1, 1])
        h2.caption("個数")
        h3.caption("単価")
        h4.caption("合計")

        for i in buying_indices:
            item = data["inventory"][i]
            c1, c2, c3, c4 = st.columns([1.5, 0.8, 1, 1])
            
            # 1. 商品名
            c1.markdown(f"<div class='item-name'>{item['name']}</div>", unsafe_allow_html=True)
            
            # 2. 個数入力 (テンキー対応)
            old_q = item.get('quantity', 1)
            q_in = c2.text_input("個", value=str(old_q), key=f"q_{i}", label_visibility="collapsed")
            if q_in.isdigit() and int(q_in) != old_q:
                item['quantity'] = int(q_in); st.rerun()
            
            # 3. 単価入力 (前回価格を初期値に)
            current_u_price = item.get("current_price") if item.get("current_price") is not None else item.get("last_price", 0)
            p_in = c3.text_input("単", value=str(int(current_u_price)), key=f"p_{i}", label_visibility="collapsed")
            if p_in.isdigit() and int(p_in) != int(current_u_price):
                item['current_price'] = int(p_in); st.rerun()
            
            # 4. 合計表示 (自動計算)
            subtotal = int(current_u_price) * int(q_in if q_in.isdigit() else 0)
            c4.markdown(f"<div class='total-label'>{subtotal}円</div>", unsafe_allow_html=True)

        st.divider()
        if st.button("🎉 買い物完了（保存）", type="primary", use_container_width=True):
            for i in buying_indices:
                item = data["inventory"][i]
                if item.get("current_price") is not None:
                    item["last_price"] = item["current_price"]
                item["current_price"] = None
                item["quantity"] = 1
                item["to_buy"] = False
            save_all_data(data); st.balloons(); st.rerun()

# 以下のタブはこれまでの設定を維持（変更なし）
with t2:
    sel_cat = st.selectbox("カテゴリ絞込", ["すべて"] + data["categories"], key="filter")
    for cat in (data["categories"] if sel_cat == "すべて" else [sel_cat]):
        items = [i for i, x in enumerate(data["inventory"]) if x["cat"] == cat]
        if items:
            st.markdown(f'<div style="background-color:#005bac;color:white;padding:4px 12px;border-radius:6px;font-size:13px;font-weight:bold;margin:15px 0 10px 0;">{cat}</div>', unsafe_allow_html=True)
            for i in items:
                it = data["inventory"][i]
                col1, col2 = st.columns([1, 9])
                is_on = col1.checkbox("", value=it["to_buy"], key=f"chk_{i}", label_visibility="collapsed")
                if is_on != it["to_buy"]:
                    it["to_buy"] = is_on; it["current_price"] = None; it["quantity"] = 1
                    save_all_data(data); st.rerun()
                col2.write(f"**{it['name']}** (前回:{it['last_price']}円)")
