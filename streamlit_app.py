import streamlit as st
import pandas as pd
import json
import requests
import base64
from datetime import datetime

# 1. ページ設定
st.set_page_config(page_title="ウェル活マスター", page_icon="🛒", layout="centered")

# 2. スマホ特化CSS
st.markdown("""
    <style>
    .block-container { padding: 1rem 1rem !important; }
    
    /* 在庫リストの1行 */
    .custom-row {
        display: flex; align-items: center; padding: 10px 0;
        border-bottom: 1px solid #eee; width: 100%;
    }
    .item-info-box { flex: 1; min-width: 0; }
    .item-title { font-weight: bold; font-size: 16px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .item-sub-info { font-size: 11px; color: #888; }

    /* アイコンボタン（在庫タブ用） */
    div.stButton > button {
        border-radius: 8px !important; padding: 0 !important;
        height: 38px !important; width: 46px !important;
        font-size: 20px !important; margin: 0 !important;
    }
    
    /* 編集・削除用ボタン（追加/設定タブ用） */
    .small-btn div.stButton > button {
        height: 30px !important; width: 100% !important; font-size: 14px !important;
    }

    .cat-label {
        background-color: #005bac; color: white; padding: 4px 12px;
        border-radius: 6px; font-size: 13px; font-weight: bold; margin: 20px 0 10px 0;
    }

    .money-summary {
        background-color: #fff1f1; padding: 12px; border-radius: 12px; 
        border: 2px solid #ff4b4b; margin-bottom: 15px; text-align: center;
    }
    .money-val { color: #ff4b4b; font-size: 24px; font-weight: bold; }
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

# --- 編集用ダイアログ ---
@st.dialog("商品の編集")
def edit_dialog(idx, row):
    n = st.text_input("商品名", value=row['name'])
    c = st.selectbox("カテゴリ", data["categories"], index=data["categories"].index(row['cat']) if row['cat'] in data["categories"] else 0)
    c1, c2 = st.columns(2)
    if c1.button("✅ 保存", type="primary"):
        df.at[idx, 'name'], df.at[idx, 'cat'] = n, c
        data["inventory"] = df.to_dict(orient="records")
        save_all_data(data); st.rerun()
    if c2.button("🗑️ 商品を削除"):
        df.drop(idx, inplace=True)
        data["inventory"] = df.to_dict(orient="records")
        save_all_data(data); st.rerun()

# --- メイン画面 ---
now = datetime.now()
st.title(f"🛍️ {now.month}月 ウェル活")
t1, t2, t3, t4 = st.tabs(["🛒 買い物", "🏠 在庫", "➕ 追加・編集", "📁 設定"])

# --- タブ1: 買い物 ---
with t1:
    limit = int(data.get("points", 0) * 1.5)
    buying_df = df[df['to_buy'] == True]
    spent = sum([int(row.get('current_price') or row['last_price']) for _, row in buying_df.iterrows()])
    st.markdown(f'<div class="money-summary">予算:{limit} / 合計:{int(spent)}<br><span class="money-val">残り {int(limit - spent)} 円</span></div>', unsafe_allow_html=True)
    
    if buying_df.empty: st.info("買い物リストは空です")
    else:
        for idx, row in buying_df.iterrows():
            c1, c2 = st.columns([3, 1])
            c1.markdown(f"**{row['name']}**")
            cur_p = row.get('current_price') if pd.notnull(row.get('current_price')) else row['last_price']
            p_in = c2.text_input("円", value=str(cur_p), key=f"buy_{idx}", label_visibility="collapsed")
            if p_in != str(cur_p):
                df.at[idx, 'current_price'] = int(p_in) if p_in.isdigit() else 0
                data["inventory"] = df.to_dict(orient="records"); save_all_data(data); st.rerun()
        if st.button("🎉 買い物完了", type="primary"):
            for idx in df[df['to_buy'] == True].index:
                df.at[idx, 'last_price'] = df.at[idx, 'current_price'] or df.at[idx, 'last_price']
                df.at[idx, 'current_price'] = None
            df.loc[df['to_buy'] == True, 'to_buy'] = False
            data["inventory"] = df.to_dict(orient="records"); save_all_data(data); st.balloons(); st.rerun()

# --- タブ2: 在庫（買う操作のみ！） ---
with t2:
    if not df.empty:
        sel_cat = st.selectbox("カテゴリ絞込", ["すべて"] + data["categories"], key="filter_inv")
        cats = data["categories"] if sel_cat == "すべて" else [sel_cat]
        for category in cats:
            cat_df = df[df['cat'] == category]
            if not cat_df.empty:
                st.markdown(f'<div class="cat-label">{category}</div>', unsafe_allow_html=True)
                for idx, row in cat_df.iterrows():
                    is_b = row['to_buy']
                    c1, c2 = st.columns([8, 2])
                    with c1:
                        st.markdown(f'<div class="item-info-box"><div class="item-title">{"🛒" if is_b else "🏠"} {row["name"]}</div><div class="item-sub-info">前回: {row["last_price"]}円</div></div>', unsafe_allow_html=True)
                    with c2:
                        if st.button("🛒" if not is_b else "🏠", key=f"a_{idx}", type="primary" if not is_b else "secondary"):
                            df.at[idx, 'to_buy'] = not is_b
                            df.at[idx, 'current_price'] = None
                            data["inventory"] = df.to_dict(orient="records"); save_all_data(data); st.rerun()
    else: st.info("追加タブから商品を登録してください")

# --- タブ3: 追加・編集（管理用） ---
with t3:
    st.subheader("🆕 新しい商品を追加")
    with st.form("new_item_form", clear_on_submit=True):
        n = st.text_input("商品名")
        c = st.selectbox("カテゴリ", data["categories"])
        if st.form_submit_button("登録"):
            if n:
                data["inventory"].append({"name": n, "cat": c, "to_buy": False, "last_price": 0, "current_price": None})
                save_all_data(data); st.rerun()
    
    st.divider()
    st.subheader("✏️ 既存商品の編集")
    if not df.empty:
        # 編集対象を検索または選択
        search_edit = st.text_input("商品を検索", placeholder="商品名を入力...")
        edit_target_df = df[df['name'].str.contains(search_edit)] if search_edit else df
        
        for idx, row in edit_target_df.iterrows():
            ec1, ec2 = st.columns([7, 3])
            ec1.write(f"**{row['name']}** ({row['cat']})")
            with ec2:
                st.markdown('<div class="small-btn">', unsafe_allow_html=True)
                if st.button("✏️ 編集", key=f"edit_btn_{idx}"):
                    edit_dialog(idx, row)
                st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.write("商品がありません")

# --- タブ4: 設定（ポイント・カテゴリ管理） ---
with t4:
    st.subheader("💰 ポイント設定")
    pts = st.text_input("現在の保有ポイント", value=str(data.get("points", 0)))
    if st.button("ポイントを保存"):
        data["points"] = int(pts) if pts.isdigit() else 0
        save_all_data(data); st.rerun()
    
    st.divider()
    st.subheader("📁 カテゴリ管理")
    new_c = st.text_input("新しいカテゴリ名")
    if st.button("カテゴリを追加"):
        if new_c and new_c not in data["categories"]:
            data["categories"].append(new_c); save_all_data(data); st.rerun()
    
    st.write("---")
    for cat in data["categories"]:
        cl1, cl2 = st.columns([7, 3])
        cl1.write(cat)
        with cl2:
            st.markdown('<div class="small-btn">', unsafe_allow_html=True)
            if st.button("🗑️ 削除", key=f"del_cat_{cat}"):
                if len(data["categories"]) > 1:
                    data["categories"].remove(cat)
                    # 削除されたカテゴリに属していた商品を「未分類」へ移動
                    for item in data["inventory"]:
                        if item["cat"] == cat: item["cat"] = data["categories"][0]
                    save_all_data(data); st.rerun()
                else:
                    st.error("最後の1つは削除できません")
            st.markdown('</div>', unsafe_allow_html=True)

if data.get("last_month") != now.month:
    for item in data["inventory"]: item["to_buy"] = False; item["current_price"] = None
    data["last_month"] = now.month; save_all_data(data); st.rerun()
