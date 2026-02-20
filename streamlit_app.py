import streamlit as st
import json
import requests
import base64
from datetime import datetime

# 1. ページ設定
st.set_page_config(page_title="ウェル活マスター Pro", page_icon="🛒", layout="centered")

# 2. 【最強】上下固定（Sticky Header & Footer）CSS
st.markdown("""
    <style>
    /* 全体の背景 */
    .main { background-color: #f8f9fa; }
    
    /* 上部予算カードの固定 */
    .sticky-header {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        z-index: 1000;
        background-color: #f8f9fa;
        padding: 10px 20px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    }

    /* 下部完了ボタンの固定 */
    .sticky-footer {
        position: fixed;
        bottom: 0;
        left: 0;
        width: 100%;
        z-index: 1000;
        background-color: white;
        padding: 15px 20px;
        box-shadow: 0 -2px 10px rgba(0,0,0,0.1);
    }

    /* 固定パーツに被らないための余白調整 */
    .content-wrapper {
        margin-top: 100px; /* 予算カードの高さ分 */
        margin-bottom: 100px; /* 完了ボタンの高さ分 */
    }

    /* 予算サマリーカード */
    .money-summary {
        background: linear-gradient(135deg, #ff4b4b 0%, #ff7676 100%);
        padding: 15px; border-radius: 15px; color: white;
        text-align: center;
    }
    .money-val { font-size: 26px; font-weight: 800; line-height: 1.2; }
    .money-sub { font-size: 11px; opacity: 0.9; }

    /* 商品表示 */
    .item-name { font-size: 17px; font-weight: 700; color: #333; margin-top: 15px; }
    .real-name { font-size: 12px; color: #999; margin-bottom: 5px; }
    
    /* 合計金額の表示エリア */
    .total-display {
        background-color: #f0f2f6; padding: 10px; border-radius: 10px;
        text-align: center; font-size: 18px; font-weight: 800; color: #333; border: 1px solid #ddd;
    }
    .total-label { font-size: 10px; color: #666; margin-bottom: 2px; text-align: center; }

    /* 入力欄 */
    .stTextInput input {
        font-size: 17px !important; font-weight: 600 !important;
        text-align: center !important; border-radius: 10px !important; height: 45px !important;
    }
    
    /* 完了ボタン自体のスタイル */
    .stButton > button {
        width: 100%;
        background-color: #ff4b4b !important;
        color: white !important;
        border-radius: 12px !important;
        height: 50px !important;
        font-weight: bold !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- GitHubデータ連携 ---
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

# --- メインロジック ---
now = datetime.now()
st.title(f"🛒 {now.month}月のウェル活")

t1, t2, t3, t4 = st.tabs(["🛍️ 買い物", "🏠 在庫", "➕ 追加", "📁 設定"])

with t1:
    limit = int(data.get("points", 0) * 1.5)
    buying_indices = [i for i, item in enumerate(data["inventory"]) if item.get("to_buy")]
    current_spent = sum(int(data["inventory"][i].get("last_price", 0) * data["inventory"][i].get("quantity", 1)) for i in buying_indices)

    # 1. 強制固定ヘッダー（HTMLで直接記述）
    st.markdown(f"""
        <div class="sticky-header">
            <div class="money-summary">
                <div class="money-val">あと {int(limit - current_spent)} 円</div>
                <div class="money-sub">合計: {int(current_spent)}円 / 予算: {limit}円</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # 2. コンテンツエリア（余白をもたせる）
    st.markdown('<div class="content-wrapper">', unsafe_allow_html=True)
    
    with st.expander("💰 ポイント・予算設定"):
        input_pts = st.text_input("保有ポイントを入力", value=str(data.get("points", 0)), key="pts_input")
        if st.button("予算を更新"):
            data["points"] = int(input_pts) if input_pts.isdigit() else 0
            save_data(data); st.rerun()

    if not buying_indices:
        st.info("「在庫」タブでチェックを入れてください")
    else:
        for i in buying_indices:
            item = data["inventory"][i]
            st.markdown(f'<div class="item-name">{item["name"]}</div>', unsafe_allow_html=True)
            if item.get("real_name"):
                st.markdown(f'<div class="real-name">{item["real_name"]}</div>', unsafe_allow_html=True)

            c1, c2, c3 = st.columns([1.2, 1, 1.5])
            new_u = c1.text_input("単価", value=str(int(item.get("last_price", 0))), key=f"u_{i}")
            new_q = c2.text_input("個数", value=str(int(item.get("quantity", 1))), key=f"q_{i}")
            
            if new_u.isdigit() and int(new_u) != item.get("last_price", 0):
                item["last_price"] = int(new_u); st.rerun()
            if new_q.isdigit() and int(new_q) != item.get("quantity", 1):
                item["quantity"] = int(new_q); st.rerun()

            total_val = int(item["last_price"] * item["quantity"])
            c3.markdown(f'<div class="total-label">合計金額</div><div class="total-display">{total_val}円</div>', unsafe_allow_html=True)
            st.markdown('<hr style="margin:10px 0; border:0; border-top:1px solid #eee;">', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True) # コンテンツ終了

    # 3. 強制固定フッター
    # ボタンをクリック可能にするため、ここだけはStreamlitのボタンを配置するコンテナにする
    st.markdown('<div class="sticky-footer">', unsafe_allow_html=True)
    if st.button("🎉 お買い物完了", type="primary", use_container_width=True, key="finish_btn"):
        for i in buying_indices:
            item = data["inventory"][i]
            item["quantity"] = 1; item["to_buy"] = False
        save_data(data); st.balloons(); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# 他のタブ（変更なし）
with t2:
    sel_cat = st.selectbox("絞り込み", ["すべて"] + data["categories"])
    for cat in (data["categories"] if sel_cat == "すべて" else [sel_cat]):
        items = [i for i, x in enumerate(data["inventory"]) if x["cat"] == cat]
        if items:
            st.markdown(f'<div style="background:#eee; padding:5px 10px; border-radius:8px; font-weight:bold; margin-bottom:10px;">{cat}</div>', unsafe_allow_html=True)
            for i in items:
                it = data["inventory"][i]
                col1, col2 = st.columns([1, 9])
                is_on = col1.checkbox("", value=bool(it.get("to_buy")), key=f"inv_{i}", label_visibility="collapsed")
                if is_on != it.get("to_buy"):
                    it["to_buy"] = is_on; it["quantity"] = 1; save_data(data); st.rerun()
                col2.markdown(f"**{it['name']}** <small style='color:#666;'>(前回:{int(it.get('last_price',0))}円)</small><br><span style='font-size:12px; color:#999;'>{it.get('real_name','')}</span>", unsafe_allow_html=True)

with t3:
    with st.form("add_new"):
        n = st.text_input("分類名"); rn = st.text_input("実際の商品名"); c = st.selectbox("カテゴリ", data["categories"])
        if st.form_submit_button("登録") and n:
            data["inventory"].append({"name": n, "real_name": rn, "cat": c, "to_buy": False, "last_price": 0})
            save_data(data); st.rerun()

with t4:
    pts = st.text_input("保有ポイント(T/V)", value=str(data.get("points", 0)), key="pts_tab")
    if st.button("更新", key="save_pts_tab"):
        data["points"] = int(pts) if pts.isdigit() else 0; save_data(data); st.rerun()
    new_c = st.text_input("カテゴリ追加")
    if st.button("追加") and new_c:
        data["categories"].append(new_c); save_data(data); st.rerun()
