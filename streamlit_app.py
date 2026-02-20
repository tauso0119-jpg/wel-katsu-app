import streamlit as st
import pd
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

# 2. 強制固定（Fixed）＆ デザインCSS
st.markdown("""
    <style>
    /* ノイズ消去 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display:none;}
    [data-testid="stHeader"] {display: none;}
    
    .main { background-color: #f8f9fa; }
    
    /* 予算サマリーを「Fixed（絶対固定）」にして、常に最前面に配置 */
    .fixed-header {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        z-index: 999999;
        background-color: #f8f9fa;
        padding: 10px 15px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.05);
    }

    .money-summary {
        background: linear-gradient(135deg, #ff4b4b 0%, #ff7676 100%);
        padding: 12px; border-radius: 15px; color: white;
        text-align: center;
    }
    .money-val { font-size: 26px; font-weight: 850; line-height: 1.2; }
    .money-sub { font-size: 11px; opacity: 0.9; }

    /* 固定した分、中身が隠れないように上の余白を空ける */
    .block-container { padding: 90px 1rem 1rem 1rem !important; }

    .app-title {
        font-size: clamp(18px, 5vw, 22px);
        font-weight: 850;
        color: #333;
        margin-bottom: 10px;
    }

    /* 斜線スタイル */
    .item-name { font-size: 16px; font-weight: 700; color: #333; }
    .item-done { font-size: 16px; font-weight: 700; color: #bbb !important; text-decoration: line-through; }
    .real-name { font-size: 11px; color: #999; margin-bottom: 4px; display: block; }
    .real-done { font-size: 11px; color: #ccc !important; text-decoration: line-through; margin-bottom: 4px; }
    
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
        margin: 20px 0 10px 0;
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

# --- 予算計算 ---
limit = int(data.get("points", 0) * 1.5)
total_spent = sum(int(i.get("current_price") or (i.get("last_price", 0) * i.get("quantity", 1))) for i in data["inventory"] if i.get("to_buy"))

# --- 強制固定ヘッダー（HTMLで直書き） ---
st.markdown(f"""
    <div class="fixed-header">
        <div class="money-summary">
            <div class="money-sub">予算 {limit}円 ／ 合計 {int(total_spent)}円</div>
            <div class="money-val">残り {int(limit - total_spent)} 円</div>
        </div>
    </div>
""", unsafe_allow_html=True)

# --- メイン構成 ---
now = datetime.now()
st.markdown(f'<div class="app-title">🛍️ {now.month}月のウェル活</div>', unsafe_allow_html=True)

t1, t2, t3, t4 = st.tabs(["🛍️ 買い物", "🏠 在庫", "➕ 追加", "📁 設定"])

# --- タブ1：買い物 ---
with t1:
    with st.expander("💰 予算・ポイント設定"):
        input_pts = st.text_input("保有ポイント", value=str(data.get("points", 0)))
        if st.button("更新", use_container_width=True):
            data["points"] = int(input_pts) if input_pts.isdigit() else 0
            save_data(data); st.rerun()

    buying_indices = [i for i, item in enumerate(data["inventory"]) if item.get("to_buy")]
    if not buying_indices:
        st.info("「在庫」タブから選んでください")
    else:
        for i in buying_indices:
            item = data["inventory"][i]
            head_col1, head_col2 = st.columns([1, 9])
            packed = head_col1.checkbox("", value=item.get("is_packed", False), key=f"pack_{i}", label_visibility="collapsed")
            if packed != item.get("is_packed"):
                item["is_packed"] = packed; st.rerun()
            
            name_style = "item-done" if packed else "item-name"
            real_style = "real-done" if packed else "real-name"
            head_col2.markdown(f"<div class='{name_style}'>{item['name']}</div>", unsafe_allow_html=True)
            if item.get('real_name'):
                head_col2.markdown(f"<div class='{real_style}'>{item['real_name']}</div>", unsafe_allow_html=True)
            
            c1, c2 = st.columns([1, 1])
            q_val = item.get('quantity', 1)
            q_in = c1.text_input("個数", value=str(q_val), key=f"q_{i}")
            p_val = item.get("current_price") if item.get("current_price") is not None else item.get("last_price", 0)
            p_in = c2.text_input("単価", value=str(int(p_val)), key=f"p_{i}")

            if q_in.isdigit() and int(q_in) != q_val: item['quantity'] = int(q_in); st.rerun()
            if p_in.isdigit() and int(p_in) != int(p_val): item['current_price'] = int(p_in); st.rerun()
            
            item_sum = int(q_in if q_in.isdigit() else 0) * int(p_in if p_in.isdigit() else 0)
            st.markdown(f"<div class='item-total'>小計: {item_sum} 円</div>", unsafe_allow_html=True)
            st.divider()

        if st.button("🎉 お買い物完了", type="primary", use_container_width=True):
            for item in data["inventory"]:
                if item.get("to_buy"):
                    item["last_price"] = item.get("current_price") if item.get("current_price") is not None else item.get("last_price")
                    item["current_price"] = None; item["quantity"] = 1; item["to_buy"] = False; item["is_packed"] = False
            save_data(data); st.balloons(); st.rerun()

# --- タブ2：在庫 ---
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

# --- タブ3：追加 ---
with t3:
    st.subheader("🆕 新しく追加")
    with st.form("add_form", clear_on_submit=True):
        n = st.text_input("分類名"); rn = st.text_input("実際の商品名"); c = st.selectbox("カテゴリ", data["categories"])
        if st.form_submit_button("登録", use_container_width=True) and n:
            data["inventory"].append({"name": n, "real_name": rn, "cat": c, "to_buy": False, "last_price": 0, "quantity": 1, "is_packed": False})
            save_data(data); st.rerun()
    st.divider()
    for i, item in enumerate(data["inventory"]):
        with st.expander(f"{item['cat']} | {item['name']}"):
            new_n = st.text_input("分類名", value=item['name'], key=f"edit_n_{i}")
            new_rn = st.text_input("商品名", value=item['real_name'], key=f"edit_rn_{i}")
            new_c = st.selectbox("カテゴリ", data["categories"], index=data["categories"].index(item['cat']), key=f"edit_c_{i}")
            new_p = st.number_input("前回価格", value=int(item['last_price']), key=f"edit_p_{i}")
            c1, c2 = st.columns(2)
            if c1.button("更新", key=f"upd_{i}", use_container_width=True):
                item.update({"name": new_n, "real_name": new_rn, "cat": new_c, "last_price": new_p})
                save_data(data); st.rerun()
            if c2.button("削除", key=f"del_{i}", use_container_width=True, type="secondary"):
                data["inventory"].pop(i); save_data(data); st.rerun()

# --- タブ4：設定 ---
with t4:
    new_cat_name = st.text_input("新カテゴリ名")
    if st.button("カテゴリ追加", use_container_width=True) and new_cat_name:
        if new_cat_name not in data["categories"]:
            data["categories"].append(new_cat_name); save_data(data); st.rerun()
    st.divider()
    for cat in data["categories"]:
        col1, col2 = st.columns([4, 1])
        col1.write(cat)
        if col2.button("🗑️", key=f"del_cat_{cat}"):
            if any(item['cat'] == cat for item in data["inventory"]): st.error("使用中のため削除不可")
            else: data["categories"].remove(cat); save_data(data); st.rerun()

if data.get("last_month") != now.month:
    for item in data["inventory"]: item["to_buy"] = False; item["current_price"] = None; item["quantity"] = 1; item["is_packed"] = False
    data.update({"last_month": now.month}); save_data(data); st.rerun()
