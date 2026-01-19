import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# ページ設定
st.set_page_config(page_title="ウェル活マスター", page_icon="🛒")

st.markdown("""
    <style>
    .stButton > button { width: 100%; border-radius: 12px; font-weight: bold; height: 3.5em; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛒 ウェル活・在庫管理")

# 接続設定
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    # Secretsに書かれたスプシを読みに行く
    return conn.read(ttl="0m")

df = load_data()

# タブ機能
tab1, tab2, tab3 = st.tabs(["📋 買い物/在庫", "➕ 追加", "⏳ 履歴"])

with tab1:
    st.subheader("🏠 在庫チェック・切り替え")
    for idx, row in df.iterrows():
        col_n, col_s = st.columns([3, 1])
        # stockがTRUEなら✅、FALSEなら🚨
        is_stock = str(row['stock']).upper() == 'TRUE'
        status_icon = "✅" if is_stock else "🚨"
        col_n.write(f"{status_icon} **{row['name']}** ({row['cat']})")
        
        if col_s.button("切替", key=f"tog_{idx}"):
            df.at[idx, 'stock'] = not is_stock
            # ここでスプシに保存
            conn.update(data=df)
            st.rerun()

with tab2:
    st.subheader("新しい品物を追加")
    with st.form("add_item"):
        n = st.text_input("品名")
        c = st.text_input("場所")
        if st.form_submit_button("追加"):
            if n and c:
                new_row = pd.DataFrame([{"name": n, "cat": c, "stock": True, "last_price": 0, "last_bought": ""}])
                updated_df = pd.concat([df, new_row], ignore_index=True)
                conn.update(data=updated_df)
                st.success(f"{n}を追加したよ！")
                st.rerun()

with tab3:
    st.subheader("購入履歴")
    st.dataframe(df[['name', 'last_price', 'last_bought']])
