import streamlit as st
import pandas as pd
import json
import requests
import base64
import numpy as np
from datetime import datetime

# 1. ページ設定
st.set_page_config(page_title="ウェル活マスター Pro", page_icon="🛒", layout="centered")

# 2. プロ仕様のデザインCSS
st.markdown("""
    <style>
    /* 全体の背景と余白 */
    .main { background-color: #f8f9fa; }
    .block-container { padding: 1.5rem 1rem !important; }
    
    /* 予算サマリーカード */
    .money-summary {
        background: linear-gradient(135deg, #ff4b4b 0%, #ff7676 100%);
        padding: 20px; border-radius: 20px; color: white;
        box-shadow: 0 4px 15px rgba(255, 75, 75, 0.3);
        margin-bottom: 25px; text-align: center;
    }
    .money-val { font-size: 32px; font-weight: 850; letter-spacing: -1px; }
    .money-sub { font-size: 14px; opacity: 0.9; margin-bottom: 5px; }

    /* 商品カードのデザイン */
    .product-card {
        background: white; padding: 15px; border-radius: 15px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05); margin-bottom: 12px;
        border: 1px solid #eee;
    }
    .item-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px; }
    .item-name { font-size: 17px; font-weight: 700; color: #333; }
    .real-name { font-size: 12px; color: #999; margin-top: 2px; }
    
    /* 入力エリアの横並び調整 */
    div[data-testid="stHorizontalBlock"] {
        background: #fdfdfd; padding: 10px; border-radius: 10px; border: 1px dashed #ddd;
    }
    
    /* 入力欄：枠線を消してスッキリ */
    .stTextInput input {
        border-radius: 8px !important; border: 1px solid #e0e0e0 !important;
        font-size: 18px !important; font-weight: 600 !important;
        text-align: center !important; height: 45px !important;
    }
    .stTextInput label { font-size: 11px !important; color: #666 !important; font-weight: bold !important; margin-bottom: 2px !important; }

    /* プルダウンのキーボード抑止 */
    div[data-baseweb="select"] input { readonly: readonly; inputmode: none; }
    
    /* ボタンデザイン */
    .stButton>button {
        border-radius: 12px !important; font-weight: 700 !important;
        padding: 0.5rem 1rem !important; transition: 0.3s !important;
    }
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

# --- メインUI ---
now = datetime.now()
st.title(f"🛒 {now.month}月のウェル活")

t1, t2, t3, t4 = st.tabs(["🛍️ 買い物", "🏠 在庫", "➕ 追加", "📁 設定"])

with t1:
    limit = int(data.get("points", 0) * 1.5)
    spent = sum(int(i.get("current_price") or i.get("last_price", 0)) * int(i.get("quantity", 1)) for i in data["inventory"] if i.get("to_buy"))

    st.markdown(f"""
        <div class="money-summary">
            <div class="money-sub">総予算 {limit}円 ／ 現在の合計 {int(spent)}円</div>
            <div class="money-val">残り {int(limit - spent)} 円</div>
        </div>
    """, unsafe_allow_html=True)

    buying_indices = [i for i, item in enumerate(data["inventory"]) if item.get("to_buy")]
    
    if not buying_indices:
        st.info("「在庫」タブから買うものを選んでください")
    else:
        for i in buying_indices:
            item = data["inventory"][i]
            
            # 商品カード開始
            st.markdown(f"""
                <div class="item-header">
                    <div>
                        <div class="item-name">{item['name']}</div>
                        <div class="real-name">{item.get('real_name', '')}</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            c1, c2 = st.columns([1, 1])
            
            # 個数入力
            q_val = item.get('quantity', 1)
            q_in = c1.text_input("個数", value=str(q_val), key=f"q_{i}")
            
            # 金額入力 (連動計算)
            current_p = item.get("current_price") or item.get("last_price", 0)
            p_in = c2.text_input("金額(合計)", value=str(int(current_p * (int(q_in) if q_in.isdigit() else 1) if item.get("current_price") is None else current_p)), key=f"p_{i}")

            # UX向上のための即時反映ロジック
            if q_in.isdigit() and int(q_in) != q_val:
                # 個数が変わったら、単価を維持して合計金額を自動計算
                unit = int(current_p / q_val) if q_val > 0 else current_p
                item['quantity'] = int(q_in)
                item['current_price'] = unit * int(q_in)
                st.rerun()

            if p_in.isdigit() and int(p_in) != int(current_p):
                item['current_price'] = int(p_in)
                st.rerun()
            
            st.markdown("---")

        if st.button("🎉 お買い物完了", type="primary", use_container_width=True):
            for item in data["inventory"]:
                if item.get("to_buy"):
                    total = item.get("current_price") or item.get("last_price")
                    q = item.get("quantity", 1)
                    item["last_price"] = int(total / q) if q > 0 else total
                    item["current_price"] = None; item["quantity"] = 1; item["to_buy"] = False
            save_data(data); st.balloons(); st.rerun()

with t2:
    sel_cat = st.selectbox("カテゴリ絞り込み", ["すべて"] + data["categories"], key="filter")
    for category in (data["categories"] if sel_cat == "すべて" else [sel_cat]):
        items = [i for i, x in enumerate(data["inventory"]) if x["cat"] == category]
        if items:
            st.markdown(f"### {category}")
            for i in items:
                item = data["inventory"][i]
                col1, col2 = st.columns([1, 8])
                if col1.checkbox("", value=bool(item.get("to_buy")), key=f"inv_{i}"):
                    if not item.get("to_buy"): item["to_buy"] = True; save_data(data); st.rerun()
                else:
                    if item.get("to_buy"): item["to_buy"] = False; save_data(data); st.rerun()
                col2.markdown(f"**{item['name']}** <small>({int(item.get('last_price',0))}円)</small><br><span style='color:#999;font-size:12px;'>{item.get('real_name','')}</span>", unsafe_allow_html=True)

with t3:
    with st.form("add"):
        n = st.text_input("分類名（例：洗剤）")
        rn = st.text_input("実際の商品名")
        c = st.selectbox("カテゴリ", data["categories"])
        if st.form_submit_button("登録") and n:
            data["inventory"].append({"name": n, "real_name": rn, "cat": c, "to_buy": False})
            save_data(data); st.rerun()

with t4:
    new_c = st.text_input("新カテゴリ")
    if st.button("追加") and new_c:
        data["categories"].append(new_c); save_data(data); st.rerun()
    pts = st.number_input("保有ポイント", value=data.get("points", 0))
    if st.button("ポイント保存"):
        data["points"] = pts; save_data(data); st.rerun()

if data.get("last_month") != now.month:
    for item in data["inventory"]: item["to_buy"] = False; item["current_price"] = None; item["quantity"] = 1
    data.update({"last_month": now.month}); save_data(data); st.rerun()
