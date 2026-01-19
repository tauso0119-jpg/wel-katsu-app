import streamlit as st
import pandas as pd

# アプリ設定
st.set_page_config(page_title="ウェル活Vibes", page_icon="🛍️")

# スタイル
st.markdown("""
    <style>
    .stButton > button { width: 100%; height: 3.5em; border-radius: 15px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛍️ 我が家のウェル活在庫管理")

# --- 修正ポイント：URLを「CSV書き出し用」に作り変える ---
# これにより、面倒な認証なしで中身を読み込めます
SHEET_ID = "1sDjWjmALGpzHX24ol_eHj8GNQ7nvQQ0iQVI0bBobiF4"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

@st.cache_data(ttl=0) # 常に最新を読み込む
def load_data():
    try:
        # CSVとしてスプシを直接読み込む
        return pd.read_csv(CSV_URL)
    except Exception as e:
        st.error(f"読み込み失敗: {e}")
        return pd.DataFrame()

df = load_data()

# データが空の場合のケア
if df.empty:
    st.warning("スプレッドシートにデータが見つかりません。A1:name, B1:cat, C1:stock が入っているか確認してね！")
else:
    # 買うものリスト
    st.subheader("🛒 20日に買うもの")
    # stockがFALSE（またはFalse）のものを探す
    to_buy = df[df['stock'].astype(str).str.upper() == 'FALSE']
    
    if to_buy.empty:
        st.info("✨ 買うものはありません！")
    else:
        for idx, row in to_buy.iterrows():
            st.warning(f"**{row['name']}**")

    st.divider()

    # 在庫一覧
    st.subheader("🏠 お家在庫チェック")
    for idx, row in df.iterrows():
        col1, col2 = st.columns([3, 1])
        status = "✅" if str(row['stock']).upper() == 'TRUE' else "🚨"
        col1.write(f"{status} **{row['name']}** ({row['cat']})")
        if col2.button("切替", key=f"btn_{idx}"):
            st.info("スプシを直接書き換えてね！(※更新機能は後ほど追加しましょう)")

# カウントダウン
from datetime import datetime
today = datetime.now()
st.sidebar.metric("ウェル活まで", f"あと {20 - today.day if today.day <= 20 else '??'} 日")
