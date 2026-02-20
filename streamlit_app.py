import streamlit as st
import pandas as pd
import json
import requests
import base64
import numpy as np
from datetime import datetime

# 1. ページ設定
st.set_page_config(page_title="ウェル活マスター", page_icon="🛒", layout="centered")

# 2. 強力なスマホ最適化CSS
st.markdown("""
    <style>
    .block-container { padding: 1rem 1rem !important; }
    .money-summary {
        background-color: #fff1f1; padding: 15px; border-radius: 15px; 
        border: 2px solid #ff4b4b; margin-bottom: 15px; text-align: center;
    }
    .money-val { color: #ff4b4b; font-size: 26px; font-weight: bold; }
    
    /* ＋ーボタン（スピンボタン）を徹底的に排除 */
    input::-webkit-outer-spin-button,
    input::-webkit-inner-spin-button {
        -webkit-appearance: none;
        margin: 0;
    }
    input[type=number] {
        -moz-appearance: textfield;
        font-size: 18px !important;
        text-align: right !important;
    }
    
    /* 入力枠のスタイル固定 */
    .stNumberInput div div input {
        border-radius: 8px !important;
    }

    .item-name { font-weight: bold; font-size: 16px; }
    .real-name { color: #888; font-size: 11px; margin-top: -2px; }
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

# 月末リセット
now = datetime.now()
if data.get("last_month") != now.month:
    for item in data["inventory"]:
        item["to_buy"] = False
        item["current_price"] = None
        item["quantity"] = 1
    data["last_month"] = now.month
    save_all_data(data)

st.title(f"🛍️ {now.month}月 ウェル活")
t1, t2, t3, t4 = st.tabs(["🛒 買い物", "🏠 在庫", "➕ 追加", "📁 設定"])

with t1:
    limit = int(data.get("points", 0) * 1.5)
    
    # 買い物リストのインデックスを取得
    buying_indices = [i for i, item in enumerate(data["inventory"]) if item.get("to_buy")]
    
    # 合計金額の計算（ここでリアルタイム計算を行う）
    spent = 0
    for i in buying_indices:
        item = data["inventory"][i]
        # current_priceがNoneならlast_priceを使う
        price = item.get("current_price") if item.get("current_price") is not None else item.get("last_price", 0)
        spent += int(price) * int(item.get("quantity", 1))

    st.markdown(f'<div class="money-summary"><div style="font-size:14px;color:#555;">予算 {limit}円 / 合計 {int(spent)}円</div><div class="money-val">残り {int(limit - spent)} 円</div></div>', unsafe_allow_html=True)
    
    if not buying_indices:
        st.info("在庫タブでチェックを入れてください")
    else:
        for i in buying_indices:
            item = data["inventory"][i]
            c1, c2, c3 = st.columns([2, 1, 1.2])
            
            # 商品名
            name_label = f"<div class='item-name'>{item['name']}</div>"
            if item.get('real_name'): name_label += f"<div class='real-name'>{item['real_name']}</div>"
            c1.markdown(name_label, unsafe_allow_html=True)
            
            # 個数入力（＋ーを消すため label_visibility="collapsed"）
            q_val = item.get('quantity', 1)
            new_q = c2.number_input("個", value=int(q_val), min_value=1, key=f"q_in_{i}", label_visibility="collapsed")
            
            # 単価（1個あたりの値段）を保持しておく
            unit_p = item.get("last_price", 0)
            
            # 金額入力
            p_val = item.get("current_price") if item.get("current_price") is not None else (unit_p * new_q)
            new_p = c3.number_input("円", value=int(p_val), min_value=0, key=f"p_in_{i}", label_visibility="collapsed")
            
            # 【連動ロジック】個数が変わったら金額を自動更新
            if new_q != q_val:
                item['quantity'] = new_q
                item['current_price'] = unit_p * new_q
                st.rerun()
            
            # 金額が手動で変わった場合
            if item.get("current_price") is not None and new_p != item['current_price']:
                item['current_price'] = new_p
                st.rerun()
            elif item.get("current_price") is None and new_p != (unit_p * q_val):
                item['current_price'] = new_p
                st.rerun()

        if st.button("🎉 買い物完了（保存）", type="primary", use_container_width=True):
            for i in buying_indices:
                item = data["inventory"][i]
                # 最終的な単価（合計÷個数）を保存
                total = item.get("current_price") if item.get("current_price") is not None else (item.get("last_price", 0) * item.get("quantity", 1))
                item["last_price"] = int(total / item["quantity"])
                item["current_price"] = None
                item["quantity"] = 1
                item["to_buy"] = False
            save_all_data(data); st.balloons(); st.rerun()

# 在庫・追加・設定（変更なしのため中身を維持）
with t2:
    sel_cat = st.selectbox("カテゴリ絞込", ["すべて"] + data["categories"], key="filter")
    for cat in (data["categories"] if sel_cat == "すべて" else [sel_cat]):
        items = [i for i, x in enumerate(data["inventory"]) if x["cat"] == cat]
        if items:
            st.markdown(f'<div style="background-color:#005bac;color:white;padding:4px 12px;border-radius:6px;font-size:13px;font-weight:bold;margin:10px 0 10px 0;">{cat}</div>', unsafe_allow_html=True)
            for i in items:
                it = data["inventory"][i]
                col1, col2 = st.columns([1, 9])
                if col1.checkbox("", value=it["to_buy"], key=f"chk_{i}", label_visibility="collapsed"):
                    if not it["to_buy"]: it["to_buy"] = True; save_all_data(data); st.rerun()
                else:
                    if it["to_buy"]: it["to_buy"] = False; save_all_data(data); st.rerun()
                col2.write(f"**{it['name']}** (前回:{it['last_price']}円)")
