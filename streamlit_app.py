import streamlit as st
import pandas as pd
import json
import requests
import base64
import numpy as np
from datetime import datetime

# 1. ページ設定
st.set_page_config(page_title="ウェル活マスター Pro", page_icon="🛒", layout="centered")

# 2. デザインCSS（プロ仕様）
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .block-container { padding: 1rem 1rem !important; }
    
    /* 予算サマリー */
    .money-summary {
        background: linear-gradient(135deg, #ff4b4b 0%, #ff7676 100%);
        padding: 20px; border-radius: 18px; color: white;
        box-shadow: 0 4px 12px rgba(255, 75, 75, 0.2);
        margin-bottom: 20px; text-align: center;
    }
    .money-val { font-size: 30px; font-weight: 800; }

    /* 商品カード */
    .product-card {
        background: white; padding: 12px; border-radius: 12px;
        border: 1px solid #eee; margin-bottom: 10px;
    }
    .item-name { font-size: 16px; font-weight: 700; color: #333; }
    .unit-price-label { font-size: 11px; color: #ff4b4b; background: #fff1f1; padding: 2px 6px; border-radius: 4px; }
    .real-name { font-size: 12px; color: #999; }
    
    /* 入力欄スリム化 */
    .stTextInput input {
        font-size: 18px !important; font-weight: 600 !important;
        text-align: center !important; border-radius: 8px !important;
    }
    .stTextInput label { font-size: 11px !important; margin-bottom: 0 !important; color: #666 !important; }
    
    /* 区切り */
    hr { margin: 15px 0 !important; border: 0; border-top: 1px solid #eee; }
    </style>
    """, unsafe_allow_html=True)

# --- データ連携 ---
TOKEN = st.secrets["GITHUB_TOKEN"]
REPO = st.secrets["GITHUB_REPO"]
FILE_PATH = "data.json"
URL = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"

def load_data():
    res = requests.get(URL, headers={"Authorization": f"token {TOKEN}"})
    if res.status_code == 200:
        return json.loads(base64.b64decode(res.json()["content"]).decode("utf-8"))
    return {"inventory": [], "categories": ["洗面所", "キッチン", "お風呂"], "points": 0, "last_month": 1}

def save_data(full_data):
    current = requests.get(URL, headers={"Authorization": f"token {TOKEN}"}).json()
    payload = {
        "message": "Update Data",
        "content": base64.b64encode(json.dumps(full_data, ensure_ascii=False).encode("utf-8")).decode("utf-8"),
        "sha": current["sha"]
    }
    requests.put(URL, headers={"Authorization": f"token {TOKEN}"}, json=payload)

if "full_data" not in st.session_state:
    st.session_state.full_data = load_data()

data = st.session_state.full_data
for item in data["inventory"]:
    item.setdefault("quantity", 1); item.setdefault("real_name", ""); item.setdefault("current_price", None); item.setdefault("last_price", 0)

# --- メイン ---
now = datetime.now()
st.title(f"🛒 {now.month}月のウェル活")

t1, t2, t3, t4 = st.tabs(["🛍️ 買い物", "🏠 在庫", "➕ 追加", "📁 設定"])

with t1:
    limit = int(data.get("points", 0) * 1.5)
    spent = sum(int(i.get("current_price") or (i.get("last_price", 0) * i.get("quantity", 1))) for i in data["inventory"] if i.get("to_buy"))

    st.markdown(f"""
        <div class="money-summary">
            <div style="font-size:12px;opacity:0.9;">予算 {limit}円 ／ 合計 {int(spent)}円</div>
            <div class="money-val">残り {int(limit - spent)} 円</div>
        </div>
    """, unsafe_allow_html=True)

    buying_indices = [i for i, item in enumerate(data["inventory"]) if item.get("to_buy")]
    
    if not buying_indices:
        st.info("「在庫」タブでチェックを入れてください")
    else:
        for i in buying_indices:
            item = data["inventory"][i]
            
            # 商品ヘッダー
            u_price = item.get("last_price", 0)
            st.markdown(f"""
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div class="item-name">{item['name']}</div>
                    <div class="unit-price-label">単価 {u_price}円</div>
                </div>
                <div class="real-name">{item.get('real_name', '')}</div>
            """, unsafe_allow_html=True)
            
            c1, c2 = st.columns([1, 1.5])
            
            # 個数入力
            q_val = item.get('quantity', 1)
            q_in = c1.text_input("個数", value=str(q_val), key=f"q_{i}")
            
            # 金額入力 (連動計算の核)
            # current_priceが空なら「単価×個数」を表示
            display_p = item.get("current_price")
            if display_p is None:
                display_p = u_price * (int(q_in) if q_in.isdigit() else 1)
            
            p_in = c2.text_input("今回の合計(円)", value=str(int(display_p)), key=f"p_{i}")

            # 変化の検知
            if q_in.isdigit() and int(q_in) != q_val:
                item['quantity'] = int(q_in)
                item['current_price'] = u_price * int(q_in)
                st.rerun()

            if p_in.isdigit() and int(p_in) != int(display_p):
                item['current_price'] = int(p_in)
                st.rerun()
            
            st.markdown("<hr>", unsafe_allow_html=True)

        if st.button("🎉 お買い物完了", type="primary", use_container_width=True):
            for item in data["inventory"]:
                if item.get("to_buy"):
                    total = item.get("current_price") or (item.get("last_price") * item.get("quantity", 1))
                    q = item.get("quantity", 1)
                    item["last_price"] = int(total / q) if q > 0 else total
                    item["current_price"] = None; item["quantity"] = 1; item["to_buy"] = False
            save_data(data); st.balloons(); st.rerun()

with t2:
    # --- 在庫タブ (変更なし) ---
    sel_cat = st.selectbox("カテゴリ絞り込み", ["すべて"] + data["categories"], key="filter")
    for category in (data["categories"] if sel_cat == "すべて" else [sel_cat]):
        items = [i for i, x in enumerate(data["inventory"]) if x["cat"] == category]
        if items:
            st.markdown(f'<div style="background:#005bac;color:white;padding:4px 10px;border-radius:5px;font-size:12px;margin:10px 0;">{category}</div>', unsafe_allow_html=True)
            for i in items:
                item = data["inventory"][i]
                col1, col2 = st.columns([1, 9])
                if col1.checkbox("", value=bool(item.get("to_buy")), key=f"inv_{i}", label_visibility="collapsed"):
                    if not item.get("to_buy"): item["to_buy"] = True; save_data(data); st.rerun()
                else:
                    if item.get("to_buy"): item["to_buy"] = False; save_data(data); st.rerun()
                col2.markdown(f"**{item['name']}** <span style='color:#999;font-size:11px;'>({int(item.get('last_price',0))}円)</span>", unsafe_allow_html=True)

with t3:
    # --- 追加タブ ---
    with st.form("add"):
        n = st.text_input("分類名")
        rn = st.text_input("実際の商品名")
        c = st.selectbox("カテゴリ", data["categories"])
        if st.form_submit_button("登録") and n:
            data["inventory"].append({"name": n, "real_name": rn, "cat": c, "to_buy": False})
            save_data(data); st.rerun()

with t4:
    # --- 設定タブ ---
    new_c = st.text_input("新カテゴリ")
    if st.button("追加") and new_c:
        data["categories"].append(new_c); save_data(data); st.rerun()
    pts = st.text_input("保有ポイント", value=str(data.get("points", 0)))
    if st.button("ポイント保存"):
        data["points"] = int(pts) if pts.isdigit() else 0; save_data(data); st.rerun()
