import streamlit as st
import json
import requests
import base64
from datetime import datetime

# 1. ページ設定
st.set_page_config(page_title="ウェル活マスター Pro", page_icon="🛒", layout="centered")

# 2. スマホ実機検証に基づいたCSS（タブ・予算・ボタンをすべて両立）
st.markdown("""
    <style>
    /* 1. 全体レイアウト：タブを隠さないように調整 */
    .main .block-container { padding: 0 !important; }
    
    /* 2. 予算ヘッダーの固定（スクロールしても上についてくる） */
    .sticky-header {
        position: -webkit-sticky; /* Safari対応 */
        position: sticky;
        top: 0;
        z-index: 999;
        background-color: white;
        padding: 10px 15px;
        border-bottom: 1px solid #eee;
    }

    /* 3. 完了ボタンの固定（画面下部に常に表示） */
    .fixed-footer {
        position: fixed;
        bottom: 0;
        left: 0;
        width: 100%;
        z-index: 9999;
        background-color: rgba(255, 255, 255, 0.95);
        padding: 10px 20px 25px 20px; /* iPhoneのバーを考慮した余白 */
        border-top: 1px solid #ddd;
        box-shadow: 0 -2px 10px rgba(0,0,0,0.05);
    }

    /* 予算カードのデザイン */
    .money-summary {
        background: linear-gradient(135deg, #ff4b4b 0%, #ff7676 100%);
        padding: 12px; border-radius: 12px; color: white; text-align: center;
    }
    .money-val { font-size: 24px; font-weight: 850; line-height: 1.2; }
    .money-sub { font-size: 10px; opacity: 0.9; }

    /* コンテンツエリアの余白（フッターに被らないように） */
    .content-padding { padding-bottom: 100px; padding-left: 15px; padding-right: 15px; }

    /* 商品表示 */
    .item-name { font-size: 17px; font-weight: 700; color: #333; margin-top: 15px; }
    .real-name { font-size: 11px; color: #999; margin-bottom: 5px; }
    
    .total-display {
        background-color: #f0f2f6; padding: 10px; border-radius: 10px;
        text-align: center; font-size: 18px; font-weight: 800; color: #333; border: 1px solid #ddd;
    }

    /* 入力欄のサイズ調整（スマホで押しやすく） */
    .stTextInput input {
        font-size: 16px !important; height: 45px !important;
    }

    /* 完了ボタン */
    div.stButton > button {
        width: 100% !important; background-color: #ff4b4b !important;
        color: white !important; border-radius: 10px !important;
        height: 50px !important; font-weight: bold !important; border: none !important;
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
st.title(f"🛍️ {now.month}月のウェル活")

# タブを復活（スマホの画面上部で切り替え可能）
t1, t2, t3, t4 = st.tabs(["🛍️ 買い物", "🏠 在庫", "➕ 追加", "📁 設定"])

with t1:
    limit = int(data.get("points", 0) * 1.5)
    buying_indices = [i for i, item in enumerate(data["inventory"]) if item.get("to_buy")]
    current_spent = sum(int(data["inventory"][i].get("last_price", 0) * data["inventory"][i].get("quantity", 1)) for i in buying_indices)

    # 1. 予算ヘッダー（スクロール固定）
    st.markdown(f"""
        <div class="sticky-header">
            <div class="money-summary">
                <div class="money-val">あと {int(limit - current_spent)} 円</div>
                <div class="money-sub">合計: {int(current_spent)}円 / 予算: {limit}円</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # 2. コンテンツ（上下に余白を設ける）
    st.markdown('<div class="content-padding">', unsafe_allow_html=True)
    
    # 予算設定を復活（アコーディオン形式で場所を取らないように）
    with st.expander("💰 ポイント・予算設定"):
        pts_in = st.text_input("保有ポイントを入力", value=str(data.get("points", 0)), key="pts_t1")
        if st.button("予算を更新", key="btn_pts_t1"):
            data["points"] = int(pts_in) if pts_in.isdigit() else 0
            save_data(data); st.rerun()

    if not buying_indices:
        st.info("「在庫」タブでチェックを入れてください")
    else:
        for i in buying_indices:
            item = data["inventory"][i]
            st.markdown(f'<div class="item-name">{item["name"]}</div><div class="real-name">{item.get("real_name", "")}</div>', unsafe_allow_html=True)
            
            c1, c2, c3 = st.columns([1.2, 1, 1.5])
            new_u = c1.text_input("単価", value=str(int(item.get("last_price", 0))), key=f"u_{i}")
            new_q = c2.text_input("個数", value=str(int(item.get("quantity", 1))), key=f"q_{i}")
            
            if new_u.isdigit() and int(new_u) != item.get("last_price", 0):
                item["last_price"] = int(new_u); st.rerun()
            if new_q.isdigit() and int(new_q) != item.get("quantity", 1):
                item["quantity"] = int(new_q); st.rerun()

            total_val = int(item["last_price"] * item["quantity"])
            c3.markdown(f'<div style="font-size:10px;color:#666;text-align:center;">合計</div><div class="total-display">{total_val}円</div>', unsafe_allow_html=True)
            st.divider()

    st.markdown('</div>', unsafe_allow_html=True)

    # 3. 完了ボタン（最下部固定）
    st.markdown('<div class="fixed-footer">', unsafe_allow_html=True)
    if st.button("🎉 お買い物完了", type="primary", use_container_width=True, key="finish_t1"):
        for i in buying_indices:
            item = data["inventory"][i]
            item["quantity"] = 1; item["to_buy"] = False
        save_data(data); st.balloons(); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# 他のタブもすべて復活
with t2:
    sel_cat = st.selectbox("カテゴリ絞り込み", ["すべて"] + data["categories"])
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
                col2.markdown(f"**{it['name']}** ({int(it.get('last_price',0))}円)<br><small>{it.get('real_name','')}</small>", unsafe_allow_html=True)

with t3:
    with st.form("add_item"):
        n = st.text_input("分類名"); rn = st.text_input("実際の商品名"); c = st.selectbox("カテゴリ", data["categories"])
        if st.form_submit_button("登録"):
            data["inventory"].append({"name": n, "real_name": rn, "cat": c, "to_buy": False, "last_price": 0})
            save_data(data); st.rerun()

with t4:
    st.subheader("設定")
    pts = st.text_input("保有ポイント(T/V)", value=str(data.get("points", 0)), key="pts_t4")
    if st.button("更新", key="btn_pts_t4"):
        data["points"] = int(pts) if pts.isdigit() else 0; save_data(data); st.rerun()
    new_cat = st.text_input("新しいカテゴリ")
    if st.button("追加"):
        data["categories"].append(new_cat); save_data(data); st.rerun()
