from datetime import datetime
import sqlite3
import pandas as pd
import streamlit as st

# --- 1. 定義價格表 ---
PRICE_MAIN = {
    "經典火雞肉便當 (絲)": 95,
    "經典火雞肉便當 (片)": 105,
    "雙拼便當 (肉+魯肉)": 110,
    "特製火雞翅便當": 130,
}

PRICE_EXTRAS = {
    "招牌火雞肉切盤": 80,
    "燙青菜": 40,
    "黃金半熟蛋": 20,
    "虱目魚丸湯": 45,
    "蛤蜊排骨湯": 60,
    "味噌湯": 30,
}

# --- 2. 資料庫初始化與結構檢查 ---


def init_db():
  conn = sqlite3.connect("orders.db")
  c = conn.cursor()
  c.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_no TEXT,
            order_time TEXT,
            order_type TEXT,
            table_no TEXT,
            main_dish TEXT,
            customization TEXT,
            sides TEXT,
            extras TEXT,
            total_price INTEGER,
            status TEXT DEFAULT '未付款/待確認'
        )
    """)

  # 欄位相容性檢查（防呆）
  c.execute("PRAGMA table_info(orders)")
  columns = [col[1] for col in c.fetchall()]
  if "order_no" not in columns:
    c.execute("ALTER TABLE orders ADD COLUMN order_no TEXT")
  if "total_price" not in columns:
    c.execute("ALTER TABLE orders ADD COLUMN total_price INTEGER DEFAULT 0")

  conn.commit()
  conn.close()


init_db()

# --- 3. 側邊欄：系統導覽與權限切換 ---
st.sidebar.title("🔥 鄉村火雞肉飯系統")
app_mode = st.sidebar.radio("選擇操作介面", ["📱 顧客線上點餐", "👨‍🍳 商家管理後台"])

# --- 4. 介面一：顧客點餐前台 ---
if app_mode == "📱 顧客線上點餐":
  st.title("🔥 鄉村火雞肉飯 - 自助點餐系統")
  st.write("歡迎光臨！請選擇餐點，送出後將為您產生專屬訂單編號進行繳費。")

  # 用餐方式
  order_type = st.radio("請選擇用餐方式：", ["內用", "外帶"], horizontal=True)
  table_no = ""
  if order_type == "內用":
    table_no = st.text_input("請輸入桌號：")
  else:
    table_no = "外帶"

  st.divider()

  # 主餐與價格
  st.subheader("🍱 主餐選擇（含價格）")
  main_dish_options = [
      f"{k} (NT$ {v})" for k, v in PRICE_MAIN.items()
  ]
  selected_main_display = st.selectbox("選擇主餐：", main_dish_options)
  #還原真實品名與計算價格
  main_dish_name = selected_main_display.split(" (NT$")[0]
  main_price = PRICE_MAIN[main_dish_name]

  col1, col2 = st.columns(2)
  with col1:
    oil_pref = st.radio("雞油/醬汁多寡：", ["正常", "偏多", "偏少"], horizontal=True)
  with col2:
    pepper_pref = st.radio("胡椒粉：", ["加胡椒", "不加胡椒"], horizontal=True)

  no_cilantro = st.checkbox("不要香菜")
  no_shallots = st.checkbox("不要油蔥酥")

  st.divider()

  # 配菜多選 (限制選 2 項)
  st.subheader("🥬 配菜區（請任選 2 項，內含於便當）")
  sides = ["蒜炒高麗菜", "時令青菜", "滷豆腐", "筍絲", "菜脯蛋", "油豆腐"]
  selected_sides = []

  for side in sides:
    if st.checkbox(side, key=f"side_{side}"):
      selected_sides.append(side)

  st.divider()

  # 單點小吃與湯品（含價格）
  st.subheader("🍢 加點小吃與湯品（自由選購）")
  selected_extras = []
  extras_total = 0

  for item, price in PRICE_EXTRAS.items():
    if st.checkbox(f"{item} — NT$ {price}", key=f"extra_{item}"):
      selected_extras.append(item)
      extras_total += price

  # 即時計算總金額
  current_total = main_price + extras_total
  st.info(f"💰 **目前預估總金額：NT$ {current_total} 元**")

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
      # 產生專屬訂單編號 (格式: TK + 年月日時分秒)
      order_no = "TK" + datetime.now().strftime("%Y%m%d%H%M%S")
      order_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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
      c.execute(
          """
                INSERT INTO orders (order_no, order_time, order_type, table_no, main_dish, customization, sides, extras, total_price, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, '未付款/待確認')
            """,
          (
              order_no,
              order_time,
              order_type,
              table_no,
              main_dish_name,
              custom_str,
              ", ".join(selected_sides),
              ", ".join(selected_extras) if selected_extras else "無",
              current_total,
          ),
      )
      conn.commit()
      conn.close()

      # 顯示成功通知與訂單編號
      st.success("🎉 訂單已成功送出！")
      st.balloons()

      st.markdown(
          f"""
            <div style="padding: 20px; border: 2px dashed #ff4b4b; border-radius: 10px; background-color: #f9f9f9;">
                <h3 style="color: #ff4b4b; margin-top: 0;">您的專屬訂單編號</h3>
                <h1 style="font-family: monospace; color: #333;">{order_no}</h1>
                <p><b>應付金額：</b>NT$ {current_total} 元</p>
                <p><b>繳費方式：</b>請憑此訂單編號至櫃檯現金付款，或掃描店內 LINE Pay 完成繳費後，店家將為您安排製作。</p>
            </div>
            """,
          unsafe_allow_html=True,
      )

# --- 5. 介面二：商家管理後台（需密碼驗證） ---
elif app_mode == "👨‍🍳 商家管理後台":
  st.title("👨‍🍳 商家管理與對帳後台")

  password = st.text_input("請輸入管理員密碼：", type="password")

  if password == "1234":
    st.success("🔓 驗證成功！")

    if st.button("🔄 重新整理資料"):
      st.rerun()

    conn = sqlite3.connect("orders.db")
    df = pd.read_sql_query("SELECT * FROM orders ORDER BY id DESC", conn)
    conn.close()

    if df.empty:
      st.info("目前尚無任何訂單紀錄。")
    else:
      # 營運與營收概況
      st.subheader("📊 今日營運概況")
      col1, col2, col3, col4 = st.columns(4)
      total_orders = len(df)
      total_revenue = df["total_price"].sum() if "total_price" in df.columns else 0
      paid_orders = (
          len(df[df["status"] == "已付款/製作中"])
          + len(df[df["status"] == "已完成"])
      )
      unpaid_orders = len(df[df["status"] == "未付款/待確認"])

      col1.metric("總訂單數", f"{total_orders} 單")
      col2.metric("總營業額", f"NT$ {total_revenue}")
      col3.metric("未付款訂單", f"{unpaid_orders} 單")
      col4.metric("已完成訂單", f"{len(df[df['status'] == '已完成'])} 單")

      st.divider()

      # 訂單管理看板
      st.subheader("📋 訂單與繳費狀態管理")

      for index, row in df.iterrows():
        current_status = (
            row["status"] if pd.notna(row["status"]) else "未付款/待確認"
        )
        status_color = (
            "🔴"
            if current_status == "未付款/待確認"
            else "🟡"
            if current_status == "已付款/製作中"
            else "🟢"
        )
        order_no_display = (
            row["order_no"] if "order_no" in row and pd.notna(row["order_no"]) else f"ID#{row['id']}"
        )

        with st.expander(
            f"{status_color} [{order_no_display}] 【{row['order_type']}】{row['main_dish']} (NT$ {row['total_price']})"
        ):
          c1, c2 = st.columns(2)
          with c1:
            st.write(f"**訂單編號**：{order_no_display}")
            st.write(f"**下單時間**：{row['order_time']}")
            st.write(f"**桌號/類型**：{row['table_no']}")
            st.write(f"**主餐**：{row['main_dish']}")
            st.write(f"**客製化備註**：{row['customization']}")
          with c2:
            st.write(f"**自選配菜**：{row['sides']}")
            st.write(f"**加點小吃/湯品**：{row['extras']}")
            st.write(f"**總金額**：NT$ {row['total_price']} 元")

          st.markdown("---")

          status_options = ["未付款/待確認", "已付款/製作中", "已完成"]
          safe_index = (
              status_options.index(current_status)
              if current_status in status_options
              else 0
          )

          new_status = st.radio(
              f"更改訂單 {order_no_display} 狀態：",
              status_options,
              index=safe_index,
              horizontal=True,
              key=f"status_radio_{row['id']}",
          )

          if st.button(f"更新訂單狀態", key=f"btn_{row['id']}"):
            conn = sqlite3.connect("orders.db")
            c = conn.cursor()
            c.execute(
                "UPDATE orders SET status = ? WHERE id = ?",
                (new_status, row["id"]),
            )
            conn.commit()
            conn.close()
            st.success(f"訂單 {order_no_display} 狀態已更新為：{new_status}")
            st.rerun()

      st.divider()
      with st.expander("查看完整資料庫表格 (Raw Data)"):
        st.dataframe(df, use_container_width=True)

  elif password == "":
    st.info("請輸入管理員密碼以解鎖後台管理。")
  else:
    st.error("❌ 密碼錯誤，請重新輸入！")
