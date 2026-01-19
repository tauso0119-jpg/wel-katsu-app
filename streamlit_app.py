import streamlit as st

# アプリの見た目設定
st.set_page_config(page_title="ウェル活Vibes", page_icon="🛍️")

# スタイル調整（スマホで押しやすいデカボタン）
st.markdown("""
    <style>
    .stButton > button { width: 100%; height: 3em; border-radius: 10px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛍️ ウェル活在庫管理")

# 初期データ
if 'items' not in st.session_state:
    st.session_state.items = [
        {"name": "洗濯洗剤", "cat": "洗剤", "stock": True},
        {"name": "柔軟剤", "cat": "洗剤", "stock": True},
        {"name": "食器洗剤", "cat": "キッチン", "stock": True},
        {"name": "トイレットペーパー", "cat": "消耗品", "stock": False},
        {"name": "おむつ/生理用品", "cat": "消耗品", "stock": True},
    ]

# 買うものリストを表示
st.subheader("🛒 20日に買うもの")
buy_list = [i for i, item in enumerate(st.session_state.items) if not item["stock"]]

if not buy_list:
    st.success("完璧！買うものはありません✨")
else:
    for idx in buy_list:
        col1, col2 = st.columns([3, 1])
        col1.warning(f"**{st.session_state.items[idx]['name']}**")
        if col2.button("買った！", key=f"buy_{idx}"):
            st.session_state.items[idx]["stock"] = True
            st.rerun()

st.divider()

# 在庫管理（全アイテム）
st.subheader("🏠 お家チェック")
categories = sorted(list(set(item["cat"] for item in st.session_state.items)))
selected_cat = st.radio("場所で絞り込み", ["すべて"] + categories, horizontal=True)

for idx, item in enumerate(st.session_state.items):
    if selected_cat != "すべて" and item["cat"] != selected_cat:
        continue
    
    col1, col2 = st.columns([3, 1])
    status = "✅ あり" if item["stock"] else "🚨 なし"
    col1.write(f"{item['name']}  \n({status})")
    
    btn_label = "切らす" if item["stock"] else "補充"
    if col2.button(btn_label, key=f"check_{idx}"):
        st.session_state.items[idx]["stock"] = not st.session_state.items[idx]["stock"]
        st.rerun()
