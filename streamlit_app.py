import streamlit as st
import pandas as pd
import json
import requests
import base64
from datetime import datetime

# 1. ページ設定
st.set_page_config(page_title="ウェル活マスター", page_icon="🛒")

# 【魔法のCSS】スマホでも絶対にボタンを縦に並ばせない設定
st.markdown("""
    <style>
    /* 1行の中の要素を横並びに強制固定 */
    [data-testid="column"] {
        display: flex;
        align-items: center;
        width: fit-content !important;
        min-width: 0px !important;
    }
    
    /* ボタンの余白を削ってスリムにする */
    .stButton > button {
        width: 100% !important;
        border-radius: 8px;
        font-weight: bold;
        padding: 0px 8px !important;
        height: 2.5em !important;
        line-height: 2.5em !important;
        min-width: 50px !important;
    }

    /* 鉛筆ボタン専用：枠だけにする */
    div[data-testid="column"]:nth-child(2) button {
        background-color: transparent;
        border: 1px solid #ddd;
    }

    /* カテゴリ見出しの装飾 */
    .cat-header { 
        background-color: #f0f2f6; padding: 5px 12px; border-radius: 8px; 
        border-left: 5px solid #005bac; margin: 15px 0 5px 0; font-size: 14px; font-weight: bold;
    }
    
    /* お金計算エリア */
    .money-box {
        background-color: #fff1f1; padding: 12px; border-radius: 12px; 
        border: 2px solid #ff4b4b; margin-bottom: 15px;
    }
    .money-font { color: #ff4b4b; font-size: 22px; font-weight: bold; }
    
    /* 商品名のスタイル */
    .item-info { flex-grow: 1; min-width: 0; margin-right: 5px; }
    .item-name { font-size: 16px; font-weight: bold; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    </style>
    """, unsafe_allow_html=True)

# GitHub接続情報
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
    return {"inventory": [], "categories": ["未分類"], "points": 0, "last_month": 1}

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
df = pd.DataFrame(data["inventory"])
if df.empty:
    df = pd.DataFrame(columns=["name", "cat", "to_buy", "last_price", "current_price"])

# --- モーダル編集 ---
@st.dialog("商品の編集")
def edit_item_dialog(idx, row):
    new_name = st.text_input("商品名", value=row['name'])
    new_cat = st.selectbox("カテゴリ", data["categories"], index=data["categories"].index(row['cat']) if row['cat'] in data["categories"] else 0)
    c_s, c_d = st.columns(2)
    if c_s.button("✅ 保存", type="primary"):
        df.at[idx, 'name'] = new_name
        df.at[idx, 'cat'] = new_cat
        data["inventory"] = df.to_dict(orient="records")
        save_all_data(data)
        st.rerun()
    if c_d.button("🗑️ 削除"):
        df.drop(idx, inplace=True)
        data["inventory"] = df.to_dict(orient="records")
        save_all_data(data)
        st.rerun()

# --- メイン ---
now = datetime.now()
st.title(f"🛍️ {now.month}月 ウェル活")
tab1, tab2, tab3, tab4 = st.tabs(["🛒 買い物", "🏠 在庫", "➕ 追加", "📁 設定"])

# --- 買い物タブ ---
with tab1:
    with st.expander("💰 ポイント設定"):
        pts_str = st.text_input("ポイント", value=str(data.get("points", 0)))
        if st.button("保存"):
            data["points"] = int(pts_str) if pts_str.isdigit() else 0
            save_all_data(data)
            st.rerun()
    
    limit = int(data.get("points", 0) * 1.5)
    buying_df = df[df['to_buy'] == True]
    spent = sum([int(row.get('current_price') or row['last_price']) for _, row in buying_df.iterrows()])
    
    st.markdown(f'<div class="money-box"><div style="font-size:14px;">予算:{limit} / 合計:{int(spent)}</div><div class="money-font">残り {int(limit - spent)} 円</div></div>', unsafe_allow_html=True)
    
    if buying_df.empty: st.info("リストは空です")
    else:
        for idx, row in buying_df.iterrows():
            c1, c2 = st.columns([3, 1])
            c1.markdown(f"**{row['name']}**")
            cur_p = row.get('current_price') if pd.notnull(row.get('current_price')) else row['last_price']
            p_in = c2.text_input("円", value=str(cur_p), key=f"t_{idx}", label_visibility="collapsed")
            if p_in != str(cur_p):
                df.at[idx, 'current_price'] = int(p_in) if p_in.isdigit() else 0
                data["inventory"] = df.to_dict(orient="records")
                save_all_data(data)
                st.rerun()
        if st.button("🎉 買い物完了", type="primary"):
            for idx in df[df['to_buy'] == True].index:
                df.at[idx, 'last_price'] = df.at[idx, 'current_price'] or df.at[idx, 'last_price']
                df.at[idx, 'current_price'] = None
            df.loc[df['to_buy'] == True, 'to_buy'] = False
            data["inventory"] = df.to_dict(orient="records")
            save_all_data(data)
            st.balloons(); st.rerun()

# --- 在庫タブ ---
with tab2:
    if not df.empty:
        sel_cat = st.selectbox("絞込", ["すべて"] + data["categories"])
        target_cats = data["categories"] if sel_cat == "すべて" else [sel_cat]
        for category in target_cats:
            cat_df = df[df['cat'] == category]
            if not cat_df.empty:
                st.markdown(f'<div class="cat-header">{category}</div>', unsafe_allow_html=True)
                for idx, row in cat_df.iterrows():
                    # スマホでも絶対に横並びにさせるためのカラム設定
                    cols = st.columns([6, 1.5, 2.5])
                    is_buying = row['to_buy']
                    icon = "🛒" if is_buying else "🏠"
                    
                    # 1: 名前と金額
                    cols[0].markdown(f'<div class="item-info"><div class="item-name">{icon} {row["name"]}</div><div style="font-size:10px;color:#888;">前:{row["last_price"]}円</div></div>', unsafe_allow_html=True)
                    
                    # 2: ✏️
                    if cols[1].button("✏️", key=f"e_{idx}"):
                        edit_item_dialog(idx, row)
                    
                    # 3: 買う/取消
                    btn_txt = "取消" if is_buying else "買う"
                    if cols[2].button(btn_txt, key=f"a_{idx}"):
                        df.at[idx, 'to_buy'] = not is_buying
                        df.at[idx, 'current_price'] = None
                        data["inventory"] = df.to_dict(orient="records")
                        save_all_data(data)
                        st.rerun()
    else:
        st.write("「追加」から登録してね")

# タブ3・4 は省略せずに統合
with tab3:
    with st.form("new"):
        n = st.text_input("商品名")
        c = st.selectbox("カテゴリ", data["categories"])
        if st.form_submit_button("登録"):
            if n:
                data["inventory"].append({"name": n, "cat": c, "to_buy": False, "last_price": 0, "current_price": None})
                save_all_data(data); st.rerun()
with tab4:
    new_cat = st.text_input("新カテゴリ")
    if st.button("追加"):
        if new_cat and new_cat not in data["categories"]:
            data["categories"].append(new_cat); save_all_data(data); st.rerun()
    for cat in data["categories"]:
        c_l, c_r = st.columns([3, 1])
        c_l.write(cat)
        if c_r.button("削", key=f"dc_{cat}"):
            data["categories"].remove(cat); save_all_data(data); st.rerun()

if data.get("last_month") != now.month:
    for item in data["inventory"]: item["to_buy"] = False; item["current_price"] = None
    data["last_month"] = now.month; save_all_data(data); st.rerun()
