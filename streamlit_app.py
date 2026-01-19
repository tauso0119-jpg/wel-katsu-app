import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# 1. ページの設定
st.set_page_config(page_title="ウェル活マスター", page_icon="🛒")

# スマホで見やすいデカボタンのデザイン
st.markdown("""
    <style>
    .stButton > button { width: 100%; border-radius: 12px; font-weight: bold; height: 3.5em; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛒 ウェル活・在庫管理")

# 2. スプレッドシート接続（Secretsの設定を使用）
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    # キャッシュを0にして常に最新のスプシを取りに行く
    data = conn.read(ttl="0m")
    # 必要な列がスプシ側にない場合に備えて自動補完
    cols = ['name', 'cat', 'stock', 'last_price', 'last_bought']
    for col in cols:
        if col not in data.columns:
            data[col] = ""
    return data

# データの読み込み
df = load_data()

# 3. タブ機能
tab1, tab2, tab3 = st.tabs(["📋 買い物", "➕ 追加", "⏳ 履歴"])

# --- タブ1: 買い物 & 在庫チェック ---
with tab1:
    # stock列が FALSE（またはFalse文字列）のものを「買うもの」として表示
    # 判定を柔軟にするため大文字にして比較
    to_buy = df[df['stock'].astype(str).str.upper() == 'FALSE']
    
    if not to_buy.empty:
        st.subheader("🚨 今日買うもの")
        for idx, row in to_buy.iterrows():
            with st.expander(f"🛒 {row['name']} ({row['cat']})", expanded=True):
                col_p, col_b = st.columns([2, 1])
                price = col_p.number_input("購入金額", key=f"price_{idx}", value=0, step=10)
                if col_b.button("補充完了", key=f"buy_{idx}"):
                    df.at[idx, 'stock'] = True
                    df.at[idx, 'last_price'] = price
                    df.at[idx, 'last_bought'] = datetime.now().strftime('%Y-%m-%d')
                    conn.update(data=df)
                    st.success(f"{row['name']} を補充しました！")
                    st.rerun()
    else:
        st.success("買うものリストは空です✨")

    st.divider()
    
    st.subheader("🏠 在庫チェック")
    # 場所（cat）で絞り込み
    unique_cats = sorted(df['cat'].unique().tolist())
    sel_cat = st.selectbox("場所を選択", ["すべて"] + unique_cats)
    
    display_df = df if sel_cat == "すべて" else df[df['cat'] == sel_cat]
    
    for idx, row in display_df.iterrows():
        col_n, col_s = st.columns([3, 1])
        # stockの値を判定
        is_stock = str(row['stock']).upper() == 'TRUE'
        status_icon = "✅" if is_stock else "🚨"
        col_n.write(f"{status_icon} **{row['name']}**")
        
        btn_label = "切らした" if is_stock else "復活"
        if col_s.button(btn_label, key=f"tog_{idx}"):
            df.at[idx, 'stock'] = not is_stock
            conn.update(data=df)
            st.rerun()

# --- タブ2: 新しい品目を追加 ---
with tab2:
    st.subheader("新しい品物を追加")
    with st.form("add_item_form"):
        new_name = st.text_input("品名 (例: トイレットペーパー)")
        new_cat = st.text_input("場所 (例: 洗面所)")
        submitted = st.form_submit_button("リストに追加")
        
        if submitted:
            if new_name and new_cat:
                new_row = pd.DataFrame([{
                    "name": new_name, 
                    "cat": new_cat, 
                    "stock": True, 
                    "last_price": 0, 
                    "last_bought": ""
                }])
                updated_df = pd.concat([df, new_row], ignore_index=True)
                conn.update(data=updated_df)
                st.success(f"「{new_name}」を{new_cat}に追加したよ！")
                st.rerun()
            else:
                st.error("品名と場所を入力してね！")

# --- タブ3: 購入履歴 ---
with tab3:
    st.subheader("最近購入したもの")
    # 日付が入っているものだけを表示
    history = df[df['last_bought'].astype(str) != ""].sort_values('last_bought', ascending=False)
    if not history.empty:
        st.dataframe(history[['last_bought', 'name', 'last_price']], use_container_width=True)
    else:
        st.info("履歴はまだありません。")

# サイドバー：ウェル活情報
today = datetime.now()
if today.day == 20:
    st.sidebar.balloons()
    st.sidebar.success("今日はウェル活当日！🔥")
else:
    st.sidebar.metric("ウェル活まで", f"あと {20-today.day} 日" if today.day < 20 else "今月は終了！")
