import streamlit as st
import json
import requests
import base64
from datetime import datetime

# 1. ページ設定
st.set_page_config(page_title="ウェル活マスター Pro", page_icon="🛒", layout="centered")

# 2. 【究極】画面全体を制御するCSS
st.markdown("""
    <style>
    /* Streamlit標準のヘッダーや余白を強制非表示 */
    header {visibility: hidden;}
    .main .block-container {padding: 0 !important; max-width: 100% !important;}
    
    /* 画面全体を固定してスクロールさせない（中身だけスクロールさせる準備） */
    html, body, [data-testid="stAppViewContainer"] {
        overflow: hidden;
        height: 100vh;
    }

    /* 予算ヘッダー：最上部に固定 */
    .ultra-header {
        position: fixed;
        top: 0; left: 0; right: 0;
        height: 90px;
        background: linear-gradient(135deg, #ff4b4b 0%, #ff7676 100%);
        color: white;
        z-index: 9999;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        box-shadow: 0 4px 10px rgba(0,0,0,0.1);
    }

    /* 完了フッター：最下部に固定 */
    .ultra-footer {
        position: fixed;
        bottom: 0; left: 0; right: 0;
        height: 80px;
        background: white;
        z-index: 9999;
        padding: 15px;
        box-shadow: 0 -4px 10px rgba(0,0,0,0.05);
    }

    /* 商品リスト：ヘッダーとフッターの間だけでスクロール */
    .scroll-content {
        position: absolute;
        top: 90px;
        bottom: 80px;
        left: 0; right: 0;
        overflow-y: auto;
        padding: 15px;
        -webkit-overflow-scrolling: touch; /* iPhoneでのスクロールを滑らかに */
    }

    .money-val { font-size: 28px; font-weight: 850; line-height: 1; margin-bottom: 5px;}
    .money-sub { font-size: 11px; opacity: 0.9; }
    
    .item-card { background: white; border-radius: 12px; padding: 10px; margin-bottom: 15px; border: 1px solid #eee; }
    .item-name { font-size: 17px; font-weight: 700; color: #333; }
    .real-name { font-size: 12px; color: #999; }
    
    .total-display {
        background-color: #f0f2f6; padding: 8px; border-radius: 10px;
        text-align: center; font-size: 18px; font-weight: 800; color: #333;
    }

    /* 完了ボタンの見た目 */
    div.stButton > button {
        width: 100% !important;
        background-color: #ff4b4b !important;
        color: white !important;
        border-radius: 12px !important;
        height: 50px !important;
        font-weight: bold !important;
        border: none !important;
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

# タブ切り替え（固定表示を活かすため買い物タブ以外は普通に表示）
tab_choice = st.sidebar.radio("メニュー", ["🛍️ 買い物", "🏠 在庫", "➕ 追加", "📁 設定"])

if tab_choice == "🛍️ 買い物":
    limit = int(data.get("points", 0) * 1.5)
    buying_indices = [i for i, item in enumerate(data["inventory"]) if item.get("to_buy")]
    current_spent = sum(int(data["inventory"][i].get("last_price", 0) * data["inventory"][i].get("quantity", 1)) for i in buying_indices)

    # 1. 究極固定ヘッダー
    st.markdown(f"""
        <div class="ultra-header">
            <div class="money-sub">予算: {limit}円 ／ 合計: {int(current_spent)}円</div>
            <div class="money-val">あと {int(limit - current_spent)} 円</div>
        </div>
    """, unsafe_allow_html=True)

    # 2. スクロールコンテンツ
    st.markdown('<div class="scroll-content">', unsafe_allow_html=True)
    
    if not buying_indices:
        st.info("「在庫」タブでチェックを入れてください")
    else:
        for i in buying_indices:
            item = data["inventory"][i]
            st.markdown(f"""
                <div class="item-name">{item["name"]}</div>
                <div class="real-name">{item.get("real_name", "")}</div>
            """, unsafe_allow_html=True)
            
            c1, c2, c3 = st.columns([1.2, 1, 1.5])
            new_u = c1.text_input("単価", value=str(int(item.get("last_price", 0))), key=f"u_{i}")
            new_q = c2.text_input("個数", value=str(int(item.get("quantity", 1))), key=f"q_{i}")
            
            if new_u.isdigit() and int(new_u) != item.get("last_price", 0):
                item["last_price"] = int(new_u); st.rerun()
            if new_q.isdigit() and int(new_q) != item.get("quantity", 1):
                item["quantity"] = int(new_q); st.rerun()

            total_val = int(item["last_price"] * item["quantity"])
            c3.markdown(f'<div style="font-size:10px;color:#666;text-align:center;">合計</div><div class="total-display">{total_val}円</div>', unsafe_allow_html=True)
            st.markdown('<hr style="margin:10px 0; border:0; border-top:1px solid #eee;">', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # 3. 究極固定フッター
    st.markdown('<div class="ultra-footer">', unsafe_allow_html=True)
    if st.button("🎉 お買い物完了", type="primary", use_container_width=True):
        for i in buying_indices:
            item = data["inventory"][i]
            item["quantity"] = 1; item["to_buy"] = False
        save_data(data); st.balloons(); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

else:
    # 買い物以外のタブは、固定を解除して普通に表示
    st.title(tab_choice)
    if tab_choice == "🏠 在庫":
        sel_cat = st.selectbox("絞り込み", ["すべて"] + data["categories"])
        for cat in (data["categories"] if sel_cat == "すべて" else [sel_cat]):
            items = [i for i, x in enumerate(data["inventory"]) if x["cat"] == cat]
            if items:
                st.markdown(f"#### {cat}")
                for i in items:
                    it = data["inventory"][i]
                    col1, col2 = st.columns([1, 8])
                    if col1.checkbox("", value=bool(it.get("to_buy")), key=f"inv_{i}"):
                        if not it.get("to_buy"): it["to_buy"] = True; save_data(data); st.rerun()
                    else:
                        if it.get("to_buy"): it["to_buy"] = False; save_data(data); st.rerun()
                    col2.markdown(f"**{it['name']}** ({int(it.get('last_price',0))}円)")
    
    elif tab_choice == "➕ 追加":
        with st.form("add"):
            n = st.text_input("分類名"); rn = st.text_input("実際の商品名"); c = st.selectbox("カテゴリ", data["categories"])
            if st.form_submit_button("登録"):
                data["inventory"].append({"name": n, "real_name": rn, "cat": c, "to_buy": False, "last_price": 0})
                save_data(data); st.rerun()

    elif tab_choice == "📁 設定":
        pts = st.text_input("保有ポイント", value=str(data.get("points", 0)))
        if st.button("更新"):
            data["points"] = int(pts) if pts.isdigit() else 0; save_data(data); st.rerun()
