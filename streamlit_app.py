import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. アプリの基本設定
st.set_page_config(page_title="ウェル活Vibes DB版", page_icon="🛍️", layout="centered")

# スマホ向けデザイン調整
st.markdown("""
    <style>
    .stButton > button { width: 100%; height: 3.5em; border-radius: 15px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛍️ 我が家のウェル活在庫管理")

# 2. スプレッドシートへの接続設定（URLを直接組み込み）
# ※本来はSecretsに書くのが推奨ですが、まずは動かすバイブスでここに書きます
SHEET_URL = "https://docs.google.com/spreadsheets/d/1sDjWjmALGpzHX24ol_eHj8GNQ7nvQQ0iQVI0bBobiF4/edit?usp=sharing"

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # データを読み込む関数
    def load_data():
        # TTL=0にすることで、開くたびに最新のスプシを取りに行きます
        return conn.read(spreadsheet=SHEET_URL, worksheet="sheet1", ttl="0m")

    # データを保存する関数
    def update_data(df):
        conn.update(spreadsheet=SHEET_URL, worksheet="sheet1", data=df)
        st.cache_data.clear()

    df = load_data()

    # 3. 買うものリスト表示
    st.subheader("🛒 20日に買うものリスト")
    # stock列がFalse（または0）のものを抽出
    to_buy = df[df['stock'] == False]

    if to_buy.empty:
        st.info("✨ 今のところ買うものはありません。平和です。")
    else:
        for idx, row in to_buy.iterrows():
            col1, col2 = st.columns([3, 1])
            col1.warning(f"**{row['name']}**")
            if col2.button("補充完了", key=f"buy_{idx}"):
                df.at[idx, 'stock'] = True
                update_data(df)
                st.rerun()

    st.divider()

    # 4. 在庫チェック
    st.subheader("🏠 お家在庫チェック")
    categories = sorted(df['cat'].unique())
    selected_cat = st.radio("場所を選択", ["すべて環境"] + list(categories), horizontal=True)

    display_df = df if selected_cat == "すべて環境" else df[df['cat'] == selected_cat]

    for idx, row in display_df.iterrows():
        col_name, col_btn = st.columns([3, 1])
        status_emoji = "✅" if row['stock'] else "🚨"
        col_name.write(f"{status_emoji} **{row['name']}**")
        
        btn_label = "切らした" if row['stock'] else "復活"
        if col_btn.button(btn_label, key=f"check_{idx}"):
            df.at[idx, 'stock'] = not row['stock']
            update_data(df)
            st.rerun()

except Exception as e:
    st.error(f"接続エラーが発生しました。スプレッドシートの1行目に name, cat, stock という見出しがあるか確認してください！ \nエラー詳細: {e}")

# おまけ：ウェル活カウントダウン
from datetime import datetime
today = datetime.now()
if today.day <= 20:
    st.sidebar.metric("ウェル活まで", f"あと {20 - today.day} 日")
