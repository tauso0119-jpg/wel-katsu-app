import streamlit as st
import pandas as pd
import json
import requests
import base64
import numpy as np
from datetime import datetime

# 1. ページ設定
st.set_page_config(page_title="ウェル活マスター", page_icon="🛒", layout="centered")

# 2. CSS：＋ーボタンを消し、数字入力を快適にする
st.markdown("""
    <style>
    .block-container { padding: 1rem 1rem !important; }
    .money-summary {
        background-color: #fff1f1; padding: 15px; border-radius: 15px; 
        border: 2px solid #ff4b4b; margin-bottom: 15px; text-align: center;
    }
    .money-val { color: #ff4b4b; font-size: 26px; font-weight: bold; }
    
    /* ＋ーボタンを非表示にし、右寄せにする */
    input[type=number]::-webkit-inner-spin-button, 
    input[type=number]::-webkit-outer-spin-button { 
        -webkit-appearance: none; margin: 0; 
    }
    input[type=number] {
        -moz-appearance: textfield;
        font-size: 18px !important;
        text-align: right !important;
    }
    .item-name { font-weight: bold; font-size: 16px; }
    .real-name { color: #888; font-size: 12px; margin-top: -5px; }
    </style>
    """, unsafe_allow_html=True)

# GitHub接続設定
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

# 月末リセット
now = datetime.now()
if data.get("last_month") != now.month:
    for item in data["inventory"]:
        item["to_buy"] = False; item["current_price"] = None; item["quantity"] = 1
    data["last_month"] = now.month; save_all_data(data)

st.title(f"🛍️ {now.month}月 ウェル活")
t1, t2, t3, t4 = st.tabs(["🛒 買い物", "🏠 在庫", "➕ 追加", "📁 設定"])

with t1:
    limit = int(data.get("points", 0) * 1.5)
    buying_indices = [i for i, item in enumerate(data["inventory"]) if item.get("to_buy")]
    
    # 合計のリアルタイム計算
    spent = 0
    for i in buying_indices:
        item = data["inventory"][i]
        # current_priceがあれば優先、なければ前回単価×個数
        p = item.get("current_price") if item.get("current_price") is not None else (item.get("last_price", 0) * item.get("quantity", 1))
        spent += int(p)

    st.markdown(f'<div class="money-summary"><div style="font-size:14px;color:#555;">予算 {limit}円 / 合計 {int(spent)}円</div><div class="money-val">残り {int(limit - spent)} 円</div></div>', unsafe_allow_html=True)
    
    if not buying_indices:
        st.info("在庫タブでチェックを入れてください")
    else:
        for i in buying_indices:
            item = data["inventory"][i]
            c1, c2, c3 = st.columns([2, 1, 1.2])
            
            # 商品名
            n_html = f"<div class='item-name'>{item['name']}</div>"
            if item.get('real_name'): n_html += f"<div class='real-name'>{item['real_name']}</div>"
            c1.markdown(n_html, unsafe_allow_html=True)
            
            # 個数入力（テキスト入力のnumericモードでテンキーを出す）
            old_q = item.get('quantity', 1)
            q_in = c2.text_input("個", value=str(old_q), key=f"q_{i}", label_visibility="collapsed")
            
            # 金額表示：個数が変わっていたら自動計算、そうでなければ入力値を反映
            if q_in.isdigit() and int(q_in) != old_q:
                new_q = int(q_in)
                item['quantity'] = new_q
                # 単価から再計算して金額欄を強制更新
                item['current_price'] = item.get('last_price', 0) * new_q
                st.rerun()

            current_p_val = item.get("current_price") if item.get("current_price") is not None else (item.get("last_price", 0) * int(q_in))
            p_in = c3.text_input("円", value=str(int(current_p_val)), key=f"p_{i}", label_visibility="collapsed")
            
            # 金額が手動で書き換えられた場合
            if p_in.isdigit() and int(p_in) != int(current_p_val):
                item['current_price'] = int(p_in)
                st.rerun()

        if st.button("🎉 買い物完了（保存）", type="primary", use_container_width=True):
            for i in buying_indices:
                item = data["inventory"][i]
                final_total = item.get("current_price") if item.get("current_price") is not None else (item.get("last_price", 0) * item.get("quantity", 1))
                # 単価を計算して保存
                item["last_price"] = int(final_total / item["quantity"]) if item["quantity"] > 0 else final_total
                item["current_price"] = None; item["quantity"] = 1; item["to_buy"] = False
            save_all_data(data); st.balloons(); st.rerun()

# 以下のタブは変更なし
with t2:
    sel_cat = st.selectbox("カテゴリ絞込", ["すべて"] + data["categories"], key="filter")
    for cat in (data["categories"] if sel_cat == "すべて" else [sel_cat]):
        items = [i for i, x in enumerate(data["inventory"]) if x["cat"] == cat]
        if items:
            st.markdown(f'<div style="background-color:#005bac;color:white;padding:4px 12px;border-radius:6px;font-size:13px;font-weight:bold;margin:15px 0 10px 0;">{cat}</div>', unsafe_allow_html=True)
            for i in items:
                it = data["inventory"][i]
                col1, col2 = st.columns([1, 9])
                if col1.checkbox("", value=it["to_buy"], key=f"chk_{i}", label_visibility="collapsed"):
                    if not it["to_buy"]: it["to_buy"] = True; save_all_data(data); st.rerun()
                else:
                    if it["to_buy"]: it["to_buy"] = False; save_all_data(data); st.rerun()
                col2.write(f"**{it['name']}** (前回:{it['last_price']}円)")
