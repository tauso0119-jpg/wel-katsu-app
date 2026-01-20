import streamlit as st
import pandas as pd
import json
import requests
import base64
from datetime import datetime

# 1. ページ設定
st.set_page_config(page_title="ウェル活マスター", page_icon="🛒")

# スマホの横幅いっぱいに横並びさせるためのスタイル調整
st.markdown("""
    <style>
    /* 全体的なボタンの角丸と文字サイズ */
    .stButton > button { width: 100%; border-radius: 8px; font-weight: bold; padding: 0.2rem 0.5rem; }
    
    /* 鉛筆ボタンを小さく、背景を透明っぽく */
    div[data-testid="column"]:nth-child(2) button {
        background-color: transparent;
        border: 1px solid #ddd;
        font-size: 14px;
        height: 2.5em;
    }
    
    /* 買う/取消ボタンの高さ調整 */
    div[data-testid="column"]:nth-child(3) button {
        height: 2.5em;
        font-size: 14px;
    }

    /* カテゴリ見出し */
    .cat-header { 
        background-color: #f0f2f6; padding: 3px 10px; border-radius: 8px; 
        border-left: 5px solid #005bac; margin: 15px 0 5px 0; font-size: 14px; font-weight: bold;
    }
    
    /* お金表示ボックス */
    .money-box {
        background-color: #fff1f1; padding: 12px; border-radius: 12px; 
        border: 2px solid #ff4b4b; margin-bottom: 15px;
    }
    .money-font { color: #ff4b4b; font-size: 22px; font-weight: bold; }
    
    /* 入力BOXの横幅 */
    div[data-testid="stTextInput"] { width: 70px !important; }
    input { text-align: right; padding: 2px !important; }

    /* 商品名の文字が溢れないように調整 */
    .item-name { font-size: 15px; font-weight: bold; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
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
    df = pd.DataFrame(columns=["name", "cat", "to_buy", "last_price"])

# --- 編集用ダイアログ ---
@st.dialog("商品の編集")
def edit_item_dialog(idx, row):
    st.write(f"**{row['name']}**")
    new_name = st.text_input("商品名", value=row['name'])
    new_cat = st.selectbox("カテゴリ", data["categories"], index=data["categories"].index(row['cat']) if row['cat'] in data["categories"] else 0)
    col_save, col_del = st.columns(2)
    if col_save.button("✅ 保存", type="primary"):
        df.at[idx, 'name'] = new_name
        df.at[idx, 'cat'] = new_cat
        data["inventory"] = df.to_dict(orient="records")
        save_all_data(data)
        st.rerun()
    if col_del.button("🗑️ 削除"):
        df.drop(idx, inplace=True)
        data["inventory"] = df.to_dict(orient="records")
        save_all_data(data)
        st.rerun()

# --- メイン ---
now = datetime.now()
st.title(f"🛍️ {now.month}月 ウェル活")
tab1, tab2, tab3, tab4 = st.tabs(["🛒 買い物", "🏠 在庫", "➕ 追加", "📁 📁"])

# --- 買い物タブ ---
with tab1:
    with st.expander("💰 ポイント設定"):
        points_str = st.text_input("ポイント", value=str(data.get("points", 0)))
        if st.button("保存", key="save_pts"):
            data["points"] = int(points_str) if points_str.isdigit() else 0
            save_all_data(data)
            st.rerun()
    limit_amount = int(data.get("points", 0) * 1.5)
    buying_df = df[df['to_buy'] == True]
    total_spent = sum(pd.to_numeric(buying_df['last_price'], errors='coerce').fillna(0))
    st.markdown(f'<div class="money-box"><div style="font-size:14px;">予算:{limit_amount} / 合計:{int(total_spent)}</div><div class="money-font">残り {int(limit_amount - total_spent)} 円</div></div>', unsafe_allow_html=True)
    
    if buying_df.empty: st.info("リストは空です")
    else:
        for idx, row in buying_df.iterrows():
            c1, c2 = st.columns([3, 1])
            c1.markdown(f"**{row['name']}**")
            p_input = c2.text_input("円", value=str(row['last_price']), key=f"t_{idx}", label_visibility="collapsed")
            if p_input != str(row['last_price']):
                df.at[idx, 'last_price'] = int(p_input) if p_input.isdigit() else 0
                data["inventory"] = df.to_dict(orient="records")
                save_all_data(data)
                st.rerun()
        if st.button("🎉 買い物完了", type="primary"):
            df.loc[df['to_buy'] == True, 'to_buy'] = False
            data["inventory"] = df.to_dict(orient="records")
            save_all_data(data)
            st.balloons()
            st.rerun()

# --- 在庫タブ（ここが重要！） ---
with tab2:
    if not df.empty:
        sel_cat = st.selectbox("絞込", ["すべて"] + data["categories"])
        target_cats = data["categories"] if sel_cat == "すべて" else [sel_cat]
        for category in target_cats:
            cat_df = df[df['cat'] == category]
            if not cat_df.empty:
                st.markdown(f'<div class="cat-header">{category}</div>', unsafe_allow_html=True)
                for idx, row in cat_df.iterrows():
                    # 比率を [名前: 5.5, 鉛筆: 1.5, 買う: 3] くらいにして横に並べる
                    cols = st.columns([5.5, 1.5, 3])
                    is_buying = row['to_buy']
                    icon = "🛒" if is_buying else "🏠"
                    
                    # 1: 商品名（とはみ出さない工夫）
                    cols[0].markdown(f'<div class="item-name">{icon} {row["name"]}</div><div style="font-size:10px;color:#888;">前:{row["last_price"]}円</div>', unsafe_allow_html=True)
                    
                    # 2: 鉛筆ボタン
                    if cols[1].button("✏️", key=f"e_{idx}"):
                        edit_item_dialog(idx, row)
                    
                    # 3: 買う/取消ボタン
                    btn_txt = "取消" if is_buying else "買う"
                    if cols[2].button(btn_txt, key=f"a_{idx}"):
                        df.at[idx, 'to_buy'] = not is_buying
                        data["inventory"] = df.to_dict(orient="records")
                        save_all_data(data)
                        st.rerun()
    else:
        st.write("「追加」から登録してね")

# --- タブ3・4（省略） ---
with tab3:
    with st.form("new"):
        n = st.text_input("商品名")
        c = st.selectbox("カテゴリ", data["categories"])
        if st.form_submit_button("登録"):
            if n:
                new_item = {"name": n, "cat": c, "to_buy": False, "last_price": 0}
                data["inventory"].append(new_item)
                save_all_data(data)
                st.rerun()
with tab4:
    new_c = st.text_input("新カテゴリ")
    if st.button("追加"):
        if new_c and new_c not in data["categories"]:
            data["categories"].append(new_c)
            save_all_data(data)
            st.rerun()
    for cat in data["categories"]:
        cl1, cl2 = st.columns([3, 1])
        cl1.write(cat)
        if cl2.button("削", key=f"dc_{cat}"):
            data["categories"].remove(cat)
            save_all_data(data)
            st.rerun()

# リセット処理
if data.get("last_month") != now.month:
    for item in data["inventory"]: item["to_buy"] = False
    data["last_month"] = now.month
    save_all_data(data)
    st.rerun()
