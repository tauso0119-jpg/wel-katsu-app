import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# 1. アプリ設定
st.set_page_config(page_title="ウェル活マスター", page_icon="🛍️")

# スマホ向けのデザイン
st.markdown("""
    <style>
    .stButton > button { width: 100%; border-radius: 12px; font-weight: bold; height: 3.5em; }
    [data-testid="stMetricValue"] { font-size: 24px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛒 ウェル活・在庫管理")

# 2. スプレッドシート接続
conn = st.connection("gsheets", type=GSheetsConnection)

# データを読み込む（常に最新を取得）
def load_data():
    data = conn.read(ttl="0m")
    # 必要な列がない場合は作成
    for col in ['name', 'cat', 'stock', 'last_price', 'last_bought']:
        if col not in data.columns:
            data[col] = ""
    return data

df = load_data()

# 3. タブで機能を分ける
tab1, tab2, tab3 = st.tabs(["📋 買い物リスト", "➕ 品目追加", "⏳ 購入履歴"])

# --- タブ1: 買い物 & 在庫チェック ---
with tab1:
    # 買うものリスト
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
                    st.rerun()
    else:
        st.success("買うものリストは空です。完璧！")

    st.divider()
    
    # 在庫一覧
    st.subheader("🏠 お家在庫チェック")
    sel_cat = st.selectbox("場所で絞り込み", ["すべて"] + list(df['cat'].unique()))
    display_df = df if sel_cat == "すべて" else df[df['cat'] == sel_cat]
    
    for idx, row in display_df.iterrows():
        col_n, col_s = st.columns([3, 1])
        status_icon = "✅" if str(row['stock']).upper() == 'TRUE' else "🚨"
        col_n.write(f"{status_icon} **{row['name']}**")
        if col_s.button("切替", key=f"tog_{idx}"):
            df.at[idx, 'stock'] = not (str(row['stock']).upper() == 'TRUE')
            conn.update(data=df)
            st.rerun()

# --- タブ2: 新しい品目を追加 ---
with tab2:
    st.subheader("リストに新しい品物を追加")
    with st.form("add_item"):
        new_name = st.text_input("品名 (例: トイレットペーパー)")
        new_cat = st.text_input("場所 (例: 洗面所)")
        submitted = st.form_submit_button("追加する")
        if submitted and new_name and new_cat:
            new_data = pd.DataFrame([{"name": new_name, "cat": new_cat, "stock": True, "last_price": 0, "last_bought": "" }])
            updated_df = pd.concat([df, new_data], ignore_index=True)
            conn.update(data=updated_df)
            st.success(f"「{new_name}」を追加しました！")
            st.rerun()

# --- タブ3: 購入履歴 ---
with tab3:
    st.subheader("最近購入したもの")
    history = df[df['last_bought'] != ""].sort_values('last_bought', ascending=False)
    if not history.empty:
        st.dataframe(history[['last_bought', 'name', 'last_price']], use_container_width=True)
    else:
        st.write("履歴はまだありません。")

# サイドバー：ウェル活情報
today = datetime.now()
st.sidebar.metric("ウェル活まで", "本日開催！" if today.day == 20 else f"あと {20-today.day} 日")
