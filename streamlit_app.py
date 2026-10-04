from datetime import datetime
import sqlite3
import streamlit as st


# --- 1. 資料庫初始化設定 ---
def init_db():
  conn = sqlite3.connect("orders.db")
  c = conn.cursor()
  c.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_time TEXT,
            order_type TEXT,
            table_no TEXT,
            main_dish TEXT,
            customization TEXT,
            sides TEXT,
            extras TEXT
        )
    """)
  conn.commit()
  conn.close()


# 寫入訂單至資料庫
def save_order(
    order_type, table_no, main_dish, customization, sides, extras
):
  conn = sqlite3.connect("orders.db")
  c = conn.cursor()
  order_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
  c.execute(
      """
        INSERT INTO orders (order_time, order_type, table_no, main_dish, customization, sides, extras)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """,
      (
          order_time,
          order_type,
          table_no,
          main_dish,
          customization,
          ", ".join(sides),
          ", ".join(extras) if extras else "無",
      ),
  )
  conn.commit()
  conn.close()


init_db()

# --- 2. 前端介面設計 ---
st.title("🔥 鄉村火雞肉飯 - 智慧點餐與管理系統")

# 設計分頁：前台點餐 vs 後台訂單管理
tab1, tab2 = st.tabs(["📱 顧客點餐系統", "👨‍🍳 櫃檯訂單後台"])

with tab1:
  st.subheader("📝 請填寫您的點餐內容")

  # 用餐方式
  order_type = st.radio("請選擇用餐方式：", ["內用", "外帶"], horizontal=True)
  table_no = ""
  if order_type == "內用":
    table_no = st.text_input("請輸入桌號：")
  else:
    table_no = "外帶"

  st.divider()

  # 主餐與客製化
  st.subheader("🍱 主餐與客製化設定")
  main_dish = st.selectbox(
      "選擇主餐：",
      ["經典火雞肉便當 (絲)", "經典火雞肉便當 (片)", "雙拼便當", "特製火雞翅便當"],
  )

  col1, col2 = st.columns(2)
  with col1:
    oil_pref = st.radio("雞油/醬汁多寡：", ["正常", "偏多", "偏少"], horizontal=True)
  with col2:
    pepper_pref = st.radio("胡椒粉：", ["加胡椒", "不加胡椒"], horizontal=True)

  no_cilantro = st.checkbox("不要香菜")
  no_shallots = st.checkbox("不要油蔥酥")

  st.divider()

  # 配菜多選 (限制選 2 項)
  st.subheader("🥬 配菜區（請任選 2 項）")
  sides = ["蒜炒高麗菜", "時令青菜", "滷豆腐", "筍絲", "菜脯蛋", "油豆腐"]
  selected_sides = []

  for side in sides:
    if st.checkbox(side, key=f"side_{side}"):
      selected_sides.append(side)

  st.divider()

  # 單點小吃與湯品
  st.subheader("🍢 加點小吃與湯品（可複選）")
  extras = [
      "招牌火雞肉切盤",
      "燙青菜",
      "黃金半熟蛋",
      "虱目魚丸湯",
      "蛤蜊排骨湯",
      "味噌湯",
  ]
  selected_extras = [
      item for item in extras if st.checkbox(item, key=f"extra_{item}")
  ]

  st.divider()

  # 送出訂單與驗證
  if st.button("確認送出訂單", type="primary"):
    if len(selected_sides) != 2:
      st.error(
          f"⚠️️ 配菜必須剛好選擇 2 項！您目前選了 {len(selected_sides)} 項。"
      )
    elif order_type == "內用" and not table_no.strip():
      st.error("⚠️ 內用請務必輸入桌號！")
    else:
      # 組合備註
      customizations = [f"雞油:{oil_pref}", pepper_pref]
      if no_cilantro:
        customizations.append("不要香菜")
      if no_shallots:
        customizations.append("不要油蔥酥")
      custom_str = ", ".join(customizations)

      # 儲存至資料庫
      save_order(
          order_type,
          table_no,
          main_dish,
          custom_str,
          selected_sides,
          selected_extras,
      )

      st.success("✅ 點餐成功！廚房已收到您的訂單。")
      st.info(
          f"**明細**：{order_type} "
          + (f"(桌號: {table_no})" if order_type == "內用" else "")
          + f" | {main_dish} | 配菜：{', '.join(selected_sides)}"
      )

with tab2:
  st.subheader("📋 歷史訂單總覽")
  if st.button("重新整理訂單列表"):
    st.rerun()

  conn = sqlite3.connect("orders.db")
  import pandas as pd

  df = pd.read_sql_query(
      "SELECT * FROM orders ORDER BY id DESC", conn
  )
  conn.close()

  if not df.empty:
    st.dataframe(df, use_container_width=True)
  else:
    st.info("目前尚無任何訂單紀錄。")
