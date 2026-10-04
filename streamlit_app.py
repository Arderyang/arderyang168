from datetime import datetime
import sqlite3
import pandas as pd
import streamlit as st

# --- 1. 資料庫初始化與結構檢查（包含產品資料表） ---


def init_db():
  conn = sqlite3.connect("orders.db")
  c = conn.cursor()

  # 訂單資料表
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

  # 產品與價格資料表
  c.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            name TEXT,
            price INTEGER
        )
    """)

  # 欄位相容性檢查（防呆）
  c.execute("PRAGMA table_info(orders)")
  columns = [col[1] for col in c.fetchall()]
  if "order_no" not in columns:
    c.execute("ALTER TABLE orders ADD COLUMN order_no TEXT")
  if "total_price" not in columns:
    c.execute("ALTER TABLE orders ADD COLUMN total_price INTEGER DEFAULT 0")

  # 如果 products 資料表是空的，先寫入預設菜單
  c.execute("SELECT COUNT(*) FROM products")
  if c.fetchone()[0] == 0:
    default_products = [
        ("main", "經典火雞肉便當 (絲)", 95),
        ("main", "經典火雞肉便當 (片)", 105),
        ("main", "雙拼便當 (肉+魯肉)", 110),
        ("main", "特製火雞翅便當", 130),
        ("extra", "招牌火雞肉切盤", 80),
        ("extra", "燙青菜", 40),
        ("extra", "黃金半熟蛋", 20),
        ("extra", "虱目魚丸湯", 45),
        ("extra", "蛤蜊排骨湯", 60),
        ("extra", "味噌湯", 30),
    ]
    c.executemany(
        "INSERT INTO products (category, name, price) VALUES (?, ?, ?)",
        default_products,
    )

  conn.commit()
  conn.close()


init_db()


# 從資料庫載入菜單的輔助函式
def load_menu_from_db():
  conn = sqlite3.connect("orders.db")
  c = conn.cursor()
  c.execute("SELECT category, name, price FROM products")
  rows = c.fetchall()
  conn.close()

  price_main = {}
  price_extras = {}
  for cat, name, price in rows:
    if cat == "main":
      price_main[name] = price
    elif cat == "extra":
      price_extras[name] = price
  return price_main, price_extras


# --- 2. 側邊欄：系統導覽與權限切換 ---
st.sidebar.title("🔥 鄉村火雞肉飯系統")
app_mode = st.sidebar.radio("選擇操作介面", ["📱 顧客線上點餐", "👨‍🍳 商家管理後台"])

# 動態從資料庫取得最新價格
PRICE_MAIN, PRICE_EXTRAS = load_menu_from_db()

# --- 3. 介面一：顧客點餐前台 ---
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
  if not PRICE_MAIN:
    st.warning("目前店家尚未上架主餐項目。")
  else:
    main_dish_options = [
        f"{k} (NT$ {v})" for k, v in PRICE_MAIN.items()
    ]
    selected_main_display = st.selectbox("選擇主餐：", main_dish_options)
    main_dish_name = selected_main_display.split(" (NT$")[0]
    main_price = PRICE_MAIN[main_dish_name]

    col1, col2 = st.columns(2)
    with col1:
      oil_pref = st.radio(
          "雞油/醬汁多寡：", ["正常", "偏多", "偏少"], horizontal=True
      )
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

    if PRICE_EXTRAS:
      for item, price in PRICE_EXTRAS.items():
        if st.checkbox(f"{item} — NT$ {price}", key=f"extra_{item}"):
          selected_extras.append(item)
          extras_total += price
    else:
      st.info("目前無加點項目。")

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
        order_no = "TK" + datetime.now().strftime("%Y%m%d%H%M%S")
        order_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        customizations = [f"雞油:{oil_pref}", pepper_pref]
        if no_cilantro:
          customizations.append("不要香菜")
        if no_shallots:
          customizations.append("不要油蔥酥")
        custom_str = ", ".join(customizations)

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

# --- 4. 介面二：商家管理後台（含菜單維護與訂單管理） ---
elif app_mode == "👨‍🍳 商家管理後台":
  st.title("👨‍🍳 商家管理與對帳後台")

  password = st.text_input("請輸入管理員密碼：", type="password")

  if password == "1234":
    st.success("🔓 驗證成功！")

    # 後台分頁：訂單管理 vs 菜單品種與價格維護
    admin_tab1, admin_tab2 = st.tabs(["📋 訂單與營運管理", "⚙️ 菜單品種與價格維護"])

    with admin_tab1:
      if st.button("🔄 重新整理訂單"):
        st.rerun()

      conn = sqlite3.connect("orders.db")
      df = pd.read_sql_query("SELECT * FROM orders ORDER BY id DESC", conn)
      conn.close()

      if df.empty:
        st.info("目前尚無任何訂單紀錄。")
      else:
        st.subheader("📊 今日營運概況")
        col1, col2, col3, col4 = st.columns(4)
        total_orders = len(df)
        total_revenue = (
            df["total_price"].sum() if "total_price" in df.columns else 0
        )
        unpaid_orders = len(df[df["status"] == "未付款/待確認"])

        col1.metric("總訂單數", f"{total_orders} 單")
        col2.metric("總營業額", f"NT$ {total_revenue}")
        col3.metric("未付款訂單", f"{unpaid_orders} 單")
        col4.metric("已完成訂單", f"{len(df[df['status'] == '已完成'])} 單")

        st.divider()
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
              row["order_no"]
              if "order_no" in row and pd.notna(row["order_no"])
              else f"ID#{row['id']}"
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

    with admin_tab2:
      st.subheader("🍔 現有菜單與價格列表")

      conn = sqlite3.connect("orders.db")
      products_df = pd.read_sql_query("SELECT * FROM products", conn)
      conn.close()

      if not products_df.empty:
        # 編輯或刪除現有產品
        for idx, prod in products_df.iterrows():
          col_a, col_b, col_c, col_d = st.columns([2, 2, 1, 1])
          with col_a:
            st.text(f"[{prod['category']}] {prod['name']}")
          with col_b:
            new_price = st.number_input(
                "價格",
                value=int(prod["price"]),
                step=5,
                key=f"p_price_{prod['id']}",
            )
          with col_c:
            if st.button("更新", key=f"update_p_{prod['id']}"):
              conn = sqlite3.connect("orders.db")
              c = conn.cursor()
              c.execute(
                  "UPDATE products SET price = ? WHERE id = ?",
                  (new_price, prod["id"]),
              )
              conn.commit()
              conn.close()
              st.success(f"已更新 {prod['name']} 價格為 NT$ {new_price}")
              st.rerun()
          with col_d:
            if st.button("刪除", key=f"del_p_{prod['id']}"):
              conn = sqlite3.connect("orders.db")
              c = conn.cursor()
              c.execute("DELETE FROM products WHERE id = ?", (prod["id"],))
              conn.commit()
              conn.close()
              st.warning(f"已刪除品項：{prod['name']}")
              st.rerun()
      else:
        st.info("目前尚無任何菜單品項。")

      st.divider()
      st.subheader("➕ 新增菜單品項")

      with st.form("add_product_form"):
        new_cat = st.selectbox(
            "選擇分類",
            options=["main", "extra"],
            format_func=lambda x: "主餐便當 (main)"
            if x == "main"
            else "加點小吃/湯品 (extra)",
        )
        new_name = st.text_input("品項名稱")
        new_item_price = st.number_input("價格 (NT$)", min_value=0, step=5, value=50)

        submit_add = st.form_submit_button("確認新增品項")

        if submit_add:
          if not new_name.strip():
            st.error("⚠️ 品項名稱不得為空！")
          else:
            conn = sqlite3.connect("orders.db")
            c = conn.cursor()
            c.execute(
                "INSERT INTO products (category, name, price) VALUES (?, ?, ?)",
                (new_cat, new_name.strip(), new_item_price),
            )
            conn.commit()
            conn.close()
            st.success(
                f"✅ 成功新增品項：{new_name.strip()} (NT$ {new_item_price})"
            )
            st.rerun()

  elif password == "":
    st.info("請輸入管理員密碼以解鎖後台管理。")
  else:
    st.error("❌ 密碼錯誤，請重新輸入！")
