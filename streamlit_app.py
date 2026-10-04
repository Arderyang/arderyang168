from datetime import datetime
import sqlite3
import pandas as pd
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
            extras TEXT,
            status TEXT DEFAULT '新訂單'
        )
    """)
  conn.commit()
  conn.close()


init_db()

# --- 2. 側邊欄：系統導覽與權限切換 ---
st.sidebar.title("🔥 鄉村火雞肉飯系統")
app_mode = st.sidebar.radio("選擇操作介面", ["📱 顧客線上點餐", "👨‍🍳 商家管理後台"])

# --- 3. 介面一：顧客點餐前台 ---
if app_mode == "📱 顧客線上點餐":
  st.title("🔥 鄉村火雞肉飯 - 自助點餐")
  st.write("歡迎光臨！請依照您的喜好點選餐點。")

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
          f"⚠️ 配菜必須剛好選擇 2 項！您目前選了 {len(selected_sides)} 項。"
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

      # 寫入資料庫
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
              custom_str,
              ", ".join(selected_sides),
              ", ".join(selected_extras) if selected_extras else "無",
          ),
      )
      conn.commit()
      conn.close()

      st.success("✅ 點餐成功！廚房已收到您的訂單，請至櫃檯等候叫號或送餐。")

# --- 4. 介面二：商家管理後台（需密碼驗證） ---
elif app_mode == "👨‍🍳 商家管理後台":
  st.title("👨‍🍳 商家管理後台")

  # 簡單的密碼保護機制（預設密碼設為 1234，您可以自行更改）
  password = st.text_input("請輸入管理員密碼：", type="password")

  if password == "1234":
    st.success("🔓 驗證成功，歡迎進入管理介面！")

    if st.button("🔄 重新整理資料"):
      st.rerun()

    conn = sqlite3.connect("orders.db")
    df = pd.read_sql_query("SELECT * FROM orders ORDER BY id DESC", conn)
    conn.close()

    if df.empty:
      st.info("目前尚無任何訂單紀錄。")
    else:
      # 營運概況指標
      st.subheader("📊 今日營運概況")
      col1, col2, col3 = st.columns(3)
      total_orders = len(df)
      completed_orders = len(df[df["status"] == "已完成"])
      pending_orders = len(df[df["status"] != "已完成"])

      col1.metric("總訂單數", f"{total_orders} 單")
      col2.metric("處理中訂單", f"{pending_orders} 單")
      col3.metric("已完成訂單", f"{completed_orders} 單")

      st.divider()

      # 即時訂單狀態管理清單
      st.subheader("📋 即時訂單管理")

      for index, row in df.iterrows():
        status_color = (
            "🔴"
            if row["status"] == "新訂單"
            else "🟡"
            if row["status"] == "製作中"
            else "🟢"
        )

        with st.expander(
            f"{status_color} 訂單 #{row['id']} | 【{row['order_type']}】{row['main_dish']} (時間: {row['order_time'][-8:]})"
        ):
          c1, c2 = st.columns(2)
          with c1:
            st.write(f"**桌號/類型**：{row['table_no']}")
            st.write(f"**主餐**：{row['main_dish']}")
            st.write(f"**客製化備註**：{row['customization']}")
          with c2:
            st.write(f"**自選配菜**：{row['sides']}")
            st.write(f"**加點小吃/湯品**：{row['extras']}")

          st.markdown("---")
          new_status = st.radio(
              f"更改訂單 #{row['id']} 狀態：",
              ["新訂單", "製作中", "已完成"],
              index=["新訂單", "製作中", "已完成"].index(row["status"]),
              horizontal=True,
              key=f"status_radio_{row['id']}",
          )

          if st.button(f"更新訂單 #{row['id']} 狀態", key=f"btn_{row['id']}"):
            conn = sqlite3.connect("orders.db")
            c = conn.cursor()
            c.execute(
                "UPDATE orders SET status = ? WHERE id = ?",
                (new_status, row["id"]),
            )
            conn.commit()
            conn.close()
            st.success(f"訂單 #{row['id']} 狀態已更新為：{new_status}")
            st.rerun()

      st.divider()
      # 完整資料表格檢視
      with st.expander("查看完整資料庫表格 (Raw Data)"):
        st.dataframe(df, use_container_width=True)

  elif password == "":
    st.info("請輸入管理員密碼以解鎖後台管理。")
  else:
    st.error("❌ 密碼錯誤，請重新輸入！")
