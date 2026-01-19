import streamlit as st

# 1. アプリの基本設定（ブラウザのタブに表示される名前とアイコン）
st.set_page_config(page_title="ウェル活Vibes", page_icon="🛍️", layout="centered")

# 2. スマホで操作しやすくするためのデザイン調整（CSS）
st.markdown("""
    <style>
    /* ボタンを大きく、角を丸くする */
    .stButton > button {
        width: 100%;
        height: 3.5em;
        border-radius: 15px;
        font-weight: bold;
        font-size: 16px;
        margin-bottom: 10px;
    }
    /* ステータス表示の文字サイズ調整 */
    .stText {
        font-size: 18px;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🛍️ 我が家のウェル活在庫管理")

# 3. データの初期化（アプリが起動した時に一度だけ実行）
# ここに「普段買うもの」をリストアップしておくと便利です！
if 'items' not in st.session_state:
    st.session_state['items'] = [
        {"name": "洗濯洗剤", "cat": "洗面所", "stock": True},
        {"name": "柔軟剤", "cat": "洗面所", "stock": True},
        {"name": "食器用洗剤", "cat": "キッチン", "stock": True},
        {"name": "食洗機洗剤", "cat": "キッチン", "stock": True},
        {"name": "お風呂掃除洗剤", "cat": "お風呂", "stock": True},
        {"name": "シャンプー", "cat": "お風呂", "stock": True},
        {"name": "トイレットペーパー", "cat": "トイレ", "stock": True},
        {"name": "ボックスティッシュ", "cat": "リビング", "stock": True},
        {"name": "おむつ/生理用品", "cat": "消耗品", "stock": True},
    ]

# データの読み込み
items = st.session_state['items']

# 4. メイン機能：20日に買うものリスト（「なし」のものだけを表示）
st.subheader("🛒 20日に買うものリスト")
buy_list = [i for i, item in enumerate(items) if not item["stock"]]

if not buy_list:
    st.info("✨ 今のところ買うものはありません。平和です。")
else:
    for idx in buy_list:
        col1, col2 = st.columns([3, 1])
        col1.warning(f"**{items[idx]['name']}**")
        if col2.button("補充完了", key=f"buy_{idx}"):
            st.session_state.items[idx]["stock"] = True
            st.rerun()

st.divider()

# 5. 在庫チェック機能（場所ごとに絞り込める）
st.subheader("🏠 お家在庫チェック")

# カテゴリ一覧を取得
categories = sorted(list(set(item["cat"] for item in items)))
selected_cat = st.segmented_control("場所を選択", categories, default=None)

for idx, item in enumerate(items):
    # カテゴリ選択されている場合は、一致するものだけ表示
    if selected_cat and item["cat"] != selected_cat:
        continue
    
    col_name, col_btn = st.columns([3, 1])
    
    # 在庫状況によって絵文字を変える
    status_emoji = "✅" if item["stock"] else "🚨"
    col_name.write(f"{status_emoji} **{item['name']}**")
    
    # ボタンのラベルを状況に合わせて変える
    btn_label = "切らした！" if item["stock"] else "復活"
    if col_btn.button(btn_label, key=f"check_{idx}"):
        st.session_state.items[idx]["stock"] = not st.session_state.items[idx]["stock"]
        st.rerun()

# 6. ウェル活までのカウントダウン（おまけ）
from datetime import datetime
today = datetime.now()
if today.day <= 20:
    days_left = 20 - today.day
    st.sidebar.metric("ウェル活まで", f"あと {days_left} 日")
else:
    st.sidebar.write("今月のウェル活は終了！来月に向けて貯めよう！")
