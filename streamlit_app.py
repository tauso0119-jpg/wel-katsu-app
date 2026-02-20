import streamlit as st
import pandas as pd
import json
import requests
import base64
import numpy as np
from datetime import datetime

# 1. ページ設定
st.set_page_config(page_title="ウェル活マスター", page_icon="🛒", layout="centered")

# 2. CSS（＋ーボタンを消し、スマホ入力を快適にする）
st.markdown("""
    <style>
    .block-container { padding: 1rem 1rem !important; }
    .money-summary {
        background-color: #fff1f1; padding: 15px; border-radius: 15px; 
        border: 2px solid #ff4b4b; margin-bottom: 15px; text-align: center;
    }
    .money-val { color: #ff4b4b; font-size: 26px; font-weight: bold; }
    
    /* 入力欄：スピンボタン（＋ー）を完全に消す */
    input[type=number]::-webkit-inner-spin-button, 
    input[type=number]::-webkit-outer-spin-button { 
        -webkit-appearance: none; margin: 0; 
    }
    input[type=number] { -moz-appearance: textfield; }
    
    /* テキスト入力欄の文字を大きく、右寄せにする */
    .stTextInput input { font-size: 18px !important; text-align: right !important; }
    
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
# データの不整合を自動修復
for item in data["inventory"]:
    if "quantity" not in item: item["quantity"] = 1
    if "real_name" not in item: item["real_name"] = ""
    if "current_price" not in item: item["current_price"] = None
    if "last_price" not in item: item["last_price"] = 0

now = datetime.now()
st.title(f"🛍️ {now.month}月 ウェル活")
t1, t2, t3, t4 = st.tabs(["🛒 買い物", "🏠 在庫", "➕ 追加", "📁 設定"])

with t1:
    with st.expander("💰 ポイント・予算設定"):
        input_pts = st.text_input("保有ポイント", value=str(data.get("points", 0)))
        if st.button("予算を更新"):
            data["points"] = int(input_pts) if input_pts.isdigit() else 0
            save_all_data(data); st.rerun()
    
    limit = int(data.get("points", 0) * 1.5)
    spent = 0
    buying_indices = [i for i, item in enumerate(data["inventory"]) if item.get("to_buy")]
    
    # 予算・合計の事前計算
    for i in buying_indices:
        item = data["inventory"][i]
        p = item.get("current_price") if item.get("current_price") is not None else item.get("last_price", 0)
        spent += (int(p) * int(item.get("quantity", 1)))

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
            
            # 個数入力
            old_q = item.get('quantity', 1)
            q_in = c2.text_input("個", value=str(old_q), key=f"q_{i}", label_visibility="collapsed")
            
            # 金額入力（現在値または前回値）
            current_p = item.get("current_price") if item.get("current_price") is not None else item.get("last_price", 0)
            p_in = c3.text_input("円", value=str(int(current_p)), key=f"p_{i}", label_visibility="collapsed")
            
            # 【重要】個数が変わった時の連動計算
            if q_in.isdigit() and int(q_in) != old_q:
                new_q = int(q_in)
                # 単価（1個あたり）を割り出し、新しい個数を掛ける
                unit_price = int(current_p / old_q) if old_q > 0 else current_p
                item['current_price'] = unit_price * new_q
                item['quantity'] = new_q
                st.rerun()
            
            # 金額が直接書き換えられた時
            if p_in.isdigit() and int(p_in) != int(current_p):
                item['current_price'] = int(p_in)
                st.rerun()

        st.divider()
        if st.button("🎉 買い物完了（保存）", type="primary"):
            for item in data["inventory"]:
                if item.get("to_buy"):
                    final_total = item.get("current_price") if item.get("current_price") is not None else item.get("last_price")
                    q = item.get("quantity", 1)
                    # 次回のために「単価」として保存
                    item["last_price"] = int(final_total / q) if q > 0 else final_total
                    item["current_price"] = None
                    item["quantity"] = 1
                    item["to_buy"] = False
            save_all_data(data); st.balloons(); st.rerun()

# 以下のタブはこれまでの設定を維持
with t2:
    sel_cat = st.selectbox("カテゴリ絞込", ["すべて"] + data["categories"], key="category_filter")
    for category in (data["categories"] if sel_cat == "すべて" else [sel_cat]):
        items_in_cat = [i for i, x in enumerate(data["inventory"]) if x["cat"] == category]
        if items_in_cat:
            st.markdown(f'<div style="background-color:#005bac;color:white;padding:4px 12px;border-radius:6px;font-size:13px;font-weight:bold;margin:15px 0 10px 0;">{category}</div>', unsafe_allow_html=True)
            for i in items_in_cat:
                item = data["inventory"][i]
                col1, col2 = st.columns([1, 9])
                is_on = col1.checkbox("", value=bool(item.get("to_buy")), key=f"inv_{i}", label_visibility="collapsed")
                if is_on != item.get("to_buy"):
                    item["to_buy"] = is_on
                    item["current_price"] = None
                    item["quantity"] = 1
                    save_all_data(data); st.rerun()
                name_html = f"<div><b>{item['name']}</b> <span style='font-size:11px;color:#888;'>(前回:{int(item.get('last_price',0))}円)</span></div>"
                if item.get('real_name'): name_html += f"<div class='real-name'>{item['real_name']}</div>"
                col2.markdown(name_html, unsafe_allow_html=True)

with t3:
    with st.form("add_form", clear_on_submit=True):
        n = st.text_input("分類名"); rn = st.text_input("実際の商品名"); c = st.selectbox("カテゴリ", data["categories"])
        if st.form_submit_button("登録") and n:
            data["inventory"].append({"name": n, "real_name": rn, "cat": c, "to_buy": False, "last_price": 0, "current_price": None, "quantity": 1})
            save_all_data(data); st.rerun()
