import streamlit as st
import pandas as pd
import json
import requests
import base64
import numpy as np
from datetime import datetime

# 1. ページ設定
st.set_page_config(page_title="ウェル活マスター", page_icon="🛒", layout="centered")

# 2. CSS
st.markdown("""
    <style>
    .block-container { padding: 1rem 1rem !important; }
    .money-summary {
        background-color: #fff1f1; padding: 15px; border-radius: 15px; 
        border: 2px solid #ff4b4b; margin-bottom: 15px; text-align: center;
    }
    .money-val { color: #ff4b4b; font-size: 26px; font-weight: bold; }
    input[type=number]::-webkit-inner-spin-button, input[type=number]::-webkit-outer-spin-button { -webkit-appearance: none; margin: 0; }
    input[type=number] { -moz-appearance: textfield; }
    .stTextInput input { font-size: 16px !important; text-align: right !important; }
    div[data-baseweb="select"] input { readonly: readonly; inputmode: none; }
    .item-name { font-weight: bold; font-size: 16px; }
    .real-name { color: #888; font-size: 12px; margin-top: -5px; }
    </style>
    """, unsafe_allow_html=True)

# GitHub接続
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

# セッション状態からDFを作成（直接dataをいじるため）
data = st.session_state.full_data
df = pd.DataFrame(data["inventory"])

# 列のクリーニング
if df.empty:
    df = pd.DataFrame(columns=["name", "cat", "to_buy", "last_price", "current_price", "quantity", "real_name"])
else:
    if 'current_price' not in df.columns: df['current_price'] = None
    if 'quantity' not in df.columns: df['quantity'] = 1
    if 'real_name' not in df.columns: df['real_name'] = ""
    df['last_price'] = pd.to_numeric(df['last_price'], errors='coerce').fillna(0).astype(int)
    df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce').fillna(1).astype(int)

@st.dialog("商品の編集")
def edit_dialog(idx, row):
    n = st.text_input("分類名", value=row['name'])
    rn = st.text_input("実際の商品名", value=row.get('real_name', ""))
    c = st.selectbox("カテゴリ", data["categories"], index=data["categories"].index(row['cat']) if row['cat'] in data["categories"] else 0)
    c1, c2 = st.columns(2)
    if c1.button("✅ 保存", type="primary"):
        data["inventory"][idx].update({"name": n, "real_name": rn, "cat": c})
        save_all_data(data); st.rerun()
    if c2.button("🗑️ 削除"):
        data["inventory"].pop(idx)
        save_all_data(data); st.rerun()

now = datetime.now()
st.title(f"🛍️ {now.month}月 ウェル活")
t1, t2, t3, t4 = st.tabs(["🛒 買い物", "🏠 在庫", "➕ 追加", "📁 設定"])

# --- タブ1: 買い物 ---
with t1:
    with st.expander("💰 ポイント・予算設定"):
        input_pts = st.text_input("保有ポイント", value=str(data.get("points", 0)))
        if st.button("予算を更新"):
            data["points"] = int(input_pts) if input_pts.isdigit() else 0
            save_all_data(data); st.rerun()
    
    limit = int(data.get("points", 0) * 1.5)
    
    # 買い物リストの描画と計算
    spent = 0
    buying_items = [i for i in data["inventory"] if i.get("to_buy")]
    
    # 事前計算
    for item in buying_items:
        p = item.get("current_price") if item.get("current_price") is not None else item.get("last_price", 0)
        q = item.get("quantity", 1)
        spent += (int(p) * int(q))

    st.markdown(f"""
        <div class="money-summary">
            <div style="font-size:14px; color:#555;">予算 {limit}円 / 合計 {int(spent)}円</div>
            <div class="money-val">残り {int(limit - spent)} 円</div>
        </div>
    """, unsafe_allow_html=True)
    
    if not buying_items:
        st.info("在庫タブでチェックを入れてください")
    else:
        st.columns([2, 1, 1.2]) # ヘッダー代わり
        for i, item in enumerate(data["inventory"]):
            if item.get("to_buy"):
                c1, c2, c3 = st.columns([2, 1, 1.2])
                # 商品名表示
                name_html = f"<div class='item-name'>{item['name']}</div>"
                if item.get('real_name'): name_html += f"<div class='real-name'>{item['real_name']}</div>"
                c1.markdown(name_html, unsafe_allow_html=True)
                
                # 個数入力（変更されたら即座にdataを更新）
                q_val = str(item.get('quantity', 1))
                q_in = c2.text_input("個", value=q_val, key=f"q_{i}", label_visibility="collapsed")
                if q_in != q_val and q_in.isdigit():
                    item['quantity'] = int(q_in)
                    st.rerun() # 再計算のためにリロード
                
                # 単価入力
                p_val = str(int(item.get('current_price') if item.get('current_price') is not None else item.get('last_price', 0)))
                p_in = c3.text_input("円", value=p_val, key=f"p_{i}", label_visibility="collapsed")
                if p_in != p_val and p_in.isdigit():
                    item['current_price'] = int(p_in)
                    st.rerun() # 再計算のためにリロード

        st.divider()
        if st.button("🎉 買い物完了（保存）", type="primary"):
            for item in data["inventory"]:
                if item.get("to_buy"):
                    item["last_price"] = item.get("current_price") if item.get("current_price") is not None else item.get("last_price")
                    item["current_price"] = None
                    item["quantity"] = 1
                    item["to_buy"] = False
            save_all_data(data); st.balloons(); st.rerun()

# --- タブ2: 在庫 ---
with t2:
    sel_cat = st.selectbox("カテゴリ絞込", ["すべて"] + data["categories"], key="category_filter")
    for category in (data["categories"] if sel_cat == "すべて" else [sel_cat]):
        items_in_cat = [i for i in data["inventory"] if i["cat"] == category]
        if items_in_cat:
            st.markdown(f'<div style="background-color:#005bac;color:white;padding:4px 12px;border-radius:6px;font-size:13px;font-weight:bold;margin:15px 0 10px 0;">{category}</div>', unsafe_allow_html=True)
            for i, item in enumerate(data["inventory"]):
                if item["cat"] == category:
                    col1, col2 = st.columns([1, 9])
                    checked = col1.checkbox("", value=bool(item.get("to_buy")), key=f"inv_{i}", label_visibility="collapsed")
                    if checked != item.get("to_buy"):
                        item["to_buy"] = checked
                        item["current_price"] = None
                        item["quantity"] = 1
                        save_all_data(data); st.rerun()
                    name_html = f"<div><b>{item['name']}</b> <span style='font-size:11px;color:#888;'>(前回:{int(item.get('last_price',0))}円)</span></div>"
                    if item.get('real_name'): name_html += f"<div class='real-name'>{item['real_name']}</div>"
                    col2.markdown(name_html, unsafe_allow_html=True)

# --- タブ3: 追加 ---
with t3:
    with st.form("add_form", clear_on_submit=True):
        n = st.text_input("分類名"); rn = st.text_input("実際の商品名"); c = st.selectbox("カテゴリ", data["categories"])
        if st.form_submit_button("登録") and n:
            data["inventory"].append({"name": n, "real_name": rn, "cat": c, "to_buy": False, "last_price": 0, "current_price": None, "quantity": 1})
            save_all_data(data); st.rerun()
    st.divider()
    search = st.text_input("検索")
    for i, item in enumerate(data["inventory"]):
        if not search or search in item['name'] or search in item.get('real_name', ''):
            ec1, ec2 = st.columns([7, 3])
            ec1.write(f"**{item['name']}**")
            if ec2.button("編集", key=f"ed_{i}"): edit_dialog(i, item)

# --- タブ4: 設定 ---
with t4:
    new_c = st.text_input("新カテゴリ")
    if st.button("追加") and new_c:
        data["categories"].append(new_c); save_all_data(data); st.rerun()
    for cat in data["categories"]:
        cl1, cl2 = st.columns([7, 3])
        cl1.write(cat)
        if cl2.button("削除", key=f"del_{cat}"):
            if len(data["categories"]) > 1:
                data["categories"].remove(cat); save_all_data(data); st.rerun()

# 月跨ぎリセット
if data.get("last_month") != now.month:
    for item in data["inventory"]: item["to_buy"] = False; item["current_price"] = None; item["quantity"] = 1
    data["last_month"] = now.month; save_all_data(data); st.rerun()
