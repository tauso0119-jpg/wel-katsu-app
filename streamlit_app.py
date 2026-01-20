import streamlit as st
import pandas as pd
import json
import requests
import base64
from datetime import datetime

# 1. ページ設定
st.set_page_config(page_title="ウェル活マスター", page_icon="🛒", layout="centered")

# 2. スマホ特化CSS（チェックボックスとレイアウトをピシッと整える）
st.markdown("""
    <style>
    .block-container { padding: 1rem 1rem !important; }
    
    /* 在庫リストの1行（チェックボックスとテキストを横並び） */
    .stCheckbox { margin-bottom: 0 !important; }
    div[data-testid="column"] { display: flex; align-items: center; }

    /* カテゴリラベル */
    .cat-label {
        background-color: #005bac; color: white; padding: 4px 12px;
        border-radius: 6px; font-size: 13px; font-weight: bold; margin: 15px 0 10px 0;
    }

    /* お金計算エリア */
    .money-summary {
        background-color: #fff1f1; padding: 12px; border-radius: 12px; 
        border: 2px solid #ff4b4b; margin-bottom: 15px; text-align: center;
    }
    .money-val { color: #ff4b4b; font-size: 24px; font-weight: bold; }
    
    /* 編集・削除ボタンを小さく */
    .small-btn div.stButton > button {
        height: 30px !important; width: 100% !important; font-size: 14px !important;
        padding: 0 !important; border-radius: 6px !important;
    }
    
    /* 買い物リストの金額入力欄 */
    div[data-testid="stTextInput"] input { text-align: right; }
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

# エラー防止：必要な列がない場合は作成
for col in ["name", "cat", "to_buy", "last_price", "current_price"]:
    if col not in df.columns:
        df[col] = False if col == "to_buy" else 0 if col == "last_price" else None

# --- 編集ダイアログ ---
@st.dialog("商品の編集")
def edit_dialog(idx, row):
    n = st.text_input("商品名", value=row['name'])
    c = st.selectbox("カテゴリ", data["categories"], index=data["categories"].index(row['cat']) if row['cat'] in data["categories"] else 0)
    c1, c2 = st.columns(2)
    if c1.button("✅ 保存", type="primary"):
        df.at[idx, 'name'], df.at[idx, 'cat'] = n, c
        data["inventory"] = df.to_dict(orient="records")
        save_all_data(data); st.rerun()
    if c2.button("🗑️ 削除"):
        df.drop(idx, inplace=True)
        data["inventory"] = df.to_dict(orient="records")
        save_all_data(data); st.rerun()

# --- メイン画面 ---
now = datetime.now()
st.title(f"🛍️ {now.month}月 ウェル活")
t1, t2, t3, t4 = st.tabs(["🛒 買い物", "🏠 在庫", "➕ 追加", "📁 設定"])

# --- タブ1: 買い物 ---
with t1:
    limit = int(data.get("points", 0) * 1.5)
    buying_df = df[df['to_buy'] == True]
    
    # エラー修正：Noneを0として扱い、確実に数値計算する
    spent = 0
    for _, row in buying_df.iterrows():
        val = row.get('current_price')
        if val is None or val == "": val = row.get('last_price', 0)
        try: spent += int(val)
        except: spent += 0

    st.markdown(f'<div class="money-summary">予算:{limit} / 合計:{int(spent)}<br><span class="money-val">残り {int(limit - spent)} 円</span></div>', unsafe_allow_html=True)
    
    if buying_df.empty: st.info("買い物リストは空です")
    else:
        for idx, row in buying_df.iterrows():
            c1, c2 = st.columns([3, 1])
            c1.markdown(f"**{row['name']}**")
            cur_p = row.get('current_price')
            if cur_p is None: cur_p = row['last_price']
            
            p_in = c2.text_input("円", value=str(cur_p), key=f"buy_p_{idx}", label_visibility="collapsed")
            if p_in != str(cur_p):
                df.at[idx, 'current_price'] = int(p_in) if p_in.isdigit() else 0
                data["inventory"] = df.to_dict(orient="records"); save_all_data(data); st.rerun()
        
        if st.button("🎉 買い物完了", type="primary"):
            for idx in df[df['to_buy'] == True].index:
                val = df.at[idx, 'current_price']
                if val is None: val = df.at[idx, 'last_price']
                df.at[idx, 'last_price'] = val
                df.at[idx, 'current_price'] = None
            df.loc[df['to_buy'] == True, 'to_buy'] = False
            data["inventory"] = df.to_dict(orient="records"); save_all_data(data); st.balloons(); st.rerun()

# --- タブ2: 在庫（チェックボックス形式） ---
with t2:
    if not df.empty:
        sel_cat = st.selectbox("絞込", ["すべて"] + data["categories"], key="f_inv")
        cats = data["categories"] if sel_cat == "すべて" else [sel_cat]
        for category in cats:
            cat_df = df[df['cat'] == category]
            if not cat_df.empty:
                st.markdown(f'<div class="cat-label">{category}</div>', unsafe_allow_html=True)
                for idx, row in cat_df.iterrows():
                    c1, c2 = st.columns([1, 9])
                    with c1:
                        checked = st.checkbox("", value=bool(row['to_buy']), key=f"ch_{idx}", label_visibility="collapsed")
                        if checked != row['to_buy']:
                            df.at[idx, 'to_buy'] = checked
                            df.at[idx, 'current_price'] = None
                            data["inventory"] = df.to_dict(orient="records"); save_all_data(data); st.rerun()
                    with c2:
                        st.markdown(f'<div><b>{row["name"]}</b><br><span style="font-size:11px;color:#888;">前回: {row["last_price"]}円</span></div>', unsafe_allow_html=True)
    else: st.info("追加タブから商品を登録してください")

# --- タブ3: 追加・編集 ---
with t3:
    st.subheader("🆕 新商品の追加")
    with st.form("add_form", clear_on_submit=True):
        n = st.text_input("商品名")
        c = st.selectbox("カテゴリ", data["categories"])
        if st.form_submit_button("登録") and n:
            data["inventory"].append({"name": n, "cat": c, "to_buy": False, "last_price": 0, "current_price": None})
            save_all_data(data); st.rerun()
    st.divider()
    st.subheader("✏️ 商品の編集・削除")
    search = st.text_input("検索...")
    edit_df = df[df['name'].str.contains(search)] if search else df
    for idx, row in edit_df.iterrows():
        ec1, ec2 = st.columns([7, 3])
        ec1.write(f"**{row['name']}** ({row['cat']})")
        with ec2:
            st.markdown('<div class="small-btn">', unsafe_allow_html=True)
            if st.button("✏️ 編集", key=f"ed_{idx}"): edit_dialog(idx, row)
            st.markdown('</div>', unsafe_allow_html=True)

# --- タブ4: 設定 ---
with t4:
    st.subheader("💰 ポイント設定")
    pts = st.text_input("保有ポイント", value=str(data.get("points", 0)))
    if st.button("ポイント保存", key="pts_save"):
        data["points"] = int(pts) if pts.isdigit() else 0
        save_all_data(data); st.rerun()
    st.divider()
    st.subheader("📁 カテゴリ管理")
    new_c = st.text_input("新しいカテゴリ名")
    if st.button("カテゴリ追加") and new_c:
        if new_c not in data["categories"]: data["categories"].append(new_c); save_all_data(data); st.rerun()
    for cat in data["categories"]:
        cl1, cl2 = st.columns([7, 3])
        cl1.write(cat)
        with cl2:
            st.markdown('<div class="small-btn">', unsafe_allow_html=True)
            if st.button("🗑️ 削除", key=f"del_{cat}"):
                if len(data["categories"]) > 1:
                    data["categories"].remove(cat)
                    for item in data["inventory"]:
                        if item["cat"] == cat: item["cat"] = data["categories"][0]
                    save_all_data(data); st.rerun()

if data.get("last_month") != now.month:
    for item in data["inventory"]: item["to_buy"] = False; item["current_price"] = None
    data["last_month"] = now.month; save_all_data(data); st.rerun()
