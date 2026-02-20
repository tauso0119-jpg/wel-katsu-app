import streamlit as st
import json
import requests
import base64
from datetime import datetime

# 1. ページ設定
st.set_page_config(page_title="ウェル活マスター Pro", page_icon="🛒", layout="centered")

# 2. 最高のUI/UXのためのデザインCSS
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .block-container { padding: 1rem 1rem !important; }
    
    /* 予算カード */
    .money-summary {
        background: linear-gradient(135deg, #ff4b4b 0%, #ff7676 100%);
        padding: 20px; border-radius: 18px; color: white;
        box-shadow: 0 4px 12px rgba(255, 75, 75, 0.2);
        margin-bottom: 20px; text-align: center;
    }
    .money-val { font-size: 32px; font-weight: 850; }

    /* 商品カードのデザイン */
    .product-card {
        background: white; padding: 15px; border-radius: 15px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05); margin-bottom: 15px;
        border: 1px solid #eee;
    }
    .item-name { font-size: 18px; font-weight: 700; color: #333; margin-bottom: 2px; }
    .real-name { font-size: 12px; color: #999; margin-bottom: 10px; }
    
    /* 入力欄のラベルと数値のスタイル */
    .stTextInput label { font-size: 11px !important; color: #666 !important; font-weight: bold !important; }
    .stTextInput input {
        font-size: 18px !important; font-weight: 600 !important;
        text-align: center !important; border-radius: 10px !important;
        height: 48px !important;
    }
    
    /* ボタンのブラッシュアップ */
    .stButton>button {
        border-radius: 12px !important; height: 50px !important; font-weight: bold !important;
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
    item.setdefault("quantity", 1); item.setdefault("last_price", 0); item.setdefault("current_price", None)

# --- メイン画面 ---
now = datetime.now()
st.title(f"🛍️ {now.month}月のウェル活")

t1, t2, t3, t4 = st.tabs(["🛒 買い物", "🏠 在庫", "➕ 追加", "📁 設定"])

with t1:
    limit = int(data.get("points", 0) * 1.5)
    # 合計の動的計算
    spent = 0
    buying_indices = [i for i, item in enumerate(data["inventory"]) if item.get("to_buy")]
    for i in buying_indices:
        it = data["inventory"][i]
        p = it.get("current_price") if it.get("current_price") is not None else it.get("last_price", 0)
        spent += int(p)

    st.markdown(f"""
        <div class="money-summary">
            <div style="font-size:12px;opacity:0.9;">Tポイント: {data.get('points',0)}pt (×1.5倍)</div>
            <div class="money-val">あと {int(limit - spent)} 円</div>
            <div style="font-size:12px;opacity:0.9;">現在の合計: {int(spent)}円 / 予算: {limit}円</div>
        </div>
    """, unsafe_allow_html=True)

    if not buying_indices:
        st.info("「在庫」タブから買うものを選んでください")
    else:
        for i in buying_indices:
            item = data["inventory"][i]
            
            with st.container():
                st.markdown(f'<div class="item-name">{item["name"]}</div>', unsafe_allow_html=True)
                if item.get("real_name"):
                    st.markdown(f'<div class="real-name">{item["real_name"]}</div>', unsafe_allow_html=True)
                
                c1, c2, c3 = st.columns([1, 1, 1.2])
                
                # 1. 単価（店で書き換え可能！）
                # 前回の単価をデフォルトとして表示
                u_price = item.get("last_unit_price", item.get("last_price", 0))
                if item.get("quantity", 1) > 1 and item.get("current_price") is not None:
                     u_price = int(item["current_price"] / item["quantity"])
                
                new_u = c1.text_input("単価", value=str(int(u_price)), key=f"u_{i}")
                
                # 2. 個数
                new_q = c2.text_input("個数", value=str(item.get("quantity", 1)), key=f"q_{i}")
                
                # 3. 合計（自動連動計算）
                # 単価か個数が変わったら合計を自動更新
                auto_total = int(int(new_u) * int(new_q)) if new_u.isdigit() and new_q.isdigit() else 0
                new_p = c3.text_input("合計金額", value=str(auto_total), key=f"p_{i}")
                
                # 反映ロジック
                changed = False
                if new_u.isdigit() and int(new_u) != u_price:
                    item["last_unit_price"] = int(new_u)
                    item["current_price"] = int(new_u) * int(item.get("quantity", 1))
                    changed = True
                if new_q.isdigit() and int(new_q) != item.get("quantity", 1):
                    item["quantity"] = int(new_q)
                    item["current_price"] = int(item.get("last_unit_price", u_price)) * int(new_q)
                    changed = True
                if new_p.isdigit() and int(new_p) != auto_total:
                    item["current_price"] = int(new_p)
                    # 金額を直接変えた場合は単価を逆算して保持
                    if int(new_q) > 0:
                        item["last_unit_price"] = int(int(new_p) / int(new_q))
                    changed = True
                
                if changed:
                    st.rerun()
                
                st.markdown('<hr style="margin:5px 0 15px 0; border-top:1px solid #eee;">', unsafe_allow_html=True)

        if st.button("🎉 お買い物完了・保存", type="primary", use_container_width=True):
            for item in data["inventory"]:
                if item.get("to_buy"):
                    # 今回の最終単価を次回の「last_price」として保存
                    q = item.get("quantity", 1)
                    total = item.get("current_price") if item.get("current_price") is not None else (item.get("last_price", 0) * q)
                    item["last_price"] = int(total / q) if q > 0 else total
                    item["current_price"] = None; item["quantity"] = 1; item["to_buy"] = False
            save_data(data); st.balloons(); st.rerun()

# 🏠 在庫タブ (デザイン統一)
with t2:
    sel_cat = st.selectbox("絞り込み", ["すべて"] + data["categories"])
    for cat in (data["categories"] if sel_cat == "すべて" else [sel_cat]):
        items = [i for i, x in enumerate(data["inventory"]) if x["cat"] == cat]
        if items:
            st.markdown(f'<div style="background:#eee; padding:5px 10px; border-radius:8px; font-weight:bold; margin-bottom:10px;">{cat}</div>', unsafe_allow_html=True)
            for i in items:
                it = data["inventory"][i]
                c1, c2 = st.columns([1, 8])
                if c1.checkbox("", value=bool(it.get("to_buy")), key=f"inv_{i}"):
                    if not it.get("to_buy"): it["to_buy"] = True; save_data(data); st.rerun()
                else:
                    if it.get("to_buy"): it["to_buy"] = False; save_data(data); st.rerun()
                c2.markdown(f"**{it['name']}** <small style='color:#666;'>(単価:{int(it.get('last_price',0))}円)</small><br><span style='font-size:12px; color:#999;'>{it.get('real_name','')}</span>", unsafe_allow_html=True)

# ➕ 追加タブ
with t3:
    with st.form("add_new"):
        st.subheader("新しい商品を追加")
        n = st.text_input("分類名（例：ハンドソープ）")
        rn = st.text_input("実際の商品名（例：キレイキレイ 詰替）")
        c = st.selectbox("カテゴリ", data["categories"])
        if st.form_submit_button("登録") and n:
            data["inventory"].append({"name": n, "real_name": rn, "cat": c, "to_buy": False, "last_price": 0})
            save_data(data); st.rerun()

# 📁 設定タブ
with t4:
    st.subheader("基本設定")
    pts = st.text_input("保有ポイント", value=str(data.get("points", 0)))
    if st.button("ポイント更新"):
        data["points"] = int(pts) if pts.isdigit() else 0; save_data(data); st.rerun()
    
    new_c = st.text_input("新しいカテゴリ名")
    if st.button("カテゴリ追加") and new_c:
        data["categories"].append(new_c); save_data(data); st.rerun()
