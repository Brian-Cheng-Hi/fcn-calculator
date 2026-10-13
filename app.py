import streamlit as st
import yfinance as yf
import pandas as pd
import datetime
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials

st.set_page_config(page_title="FCN 籃子風險追蹤器 Pro", layout="wide")
st.title("📈 FCN 一籃子風險追蹤器 (全雲端 Google Sheets 版)")

# ==========================================
# 🌟 Google Sheets 資料庫連線模組
# ==========================================
try:
    # 從 Streamlit Secrets 讀取金鑰並驗證
    creds_json = json.loads(st.secrets["GCP_CREDS_JSON"])
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
    client = gspread.authorize(creds)
    # 連線到指定的 Google Sheet
    sheet = client.open_by_url(st.secrets["SHEET_URL"]).sheet1
except Exception as e:
    st.error(f"⚠️ 資料庫連線失敗，詳細錯誤原因：{e}")
    st.write("如果錯誤包含 'API' 或 'Permission'，代表 Google 端權限未開通。")
    st.write("如果錯誤包含 'JSON' 或 'Decode'，代表 Secrets 的金鑰格式貼錯了。")
    st.stop()

@st.cache_data(ttl=300) # 暫存資料5分鐘，加快網頁載入速度
def load_portfolios():
    """從 Google Sheets 讀取所有客戶存檔"""
    try:
        records = sheet.get_all_records()
        portfolios = {}
        for row in records:
            portfolios[row['ClientName']] = json.loads(row['DataJSON'])
        return portfolios
    except:
        return {}

def save_portfolio(client_name, data_dict):
    """將客戶資料寫入 Google Sheets"""
    data_json = json.dumps(data_dict, ensure_ascii=False)
    names = sheet.col_values(1) # 取得 A 欄所有的客戶名稱
    if client_name in names:
        row_idx = names.index(client_name) + 1 # 找到存在的列數 (1-based)
        sheet.update_cell(row_idx, 2, data_json) # 更新該列的 B 欄
    else:
        sheet.append_row([client_name, data_json]) # 如果是新客戶，直接新增一列

# ==========================================
# 🌟 初始化網頁暫存記憶體
# ==========================================
if "form_data" not in st.session_state:
    st.session_state.form_data = {
        "principal": 300000,
        "coupon_rate": 22.07,
        "tenor_months": 3,
        "guaranteed_months": 1,
        "basket": pd.DataFrame({
            "股票代碼 (Ticker)": ["NVDA", "TSM", "COHR", "LITE"],
            "期初價 (Initial)": [228.38, 456.19, 287.81, 971.26],
            "出場價 (KO 95%)": [216.96, 433.38, 273.42, 922.70],
            "履約價 (Strike 75%)": [171.28, 342.14, 215.86, 728.44],
            "接貨價 (KI 70%)": [159.86, 319.33, 201.46, 679.88]
        })
    }

# ==========================================
# 📂 側邊欄：雲端客戶資料庫管理
# ==========================================
with st.sidebar:
    st.header("📂 雲端客戶資料庫")
    
    # 1. 載入舊客戶
    st.subheader("讀取已儲存的組合")
    all_portfolios = load_portfolios()
    client_names = ["-- 請選擇 --"] + list(all_portfolios.keys())
    selected_client = st.selectbox("選擇客戶", client_names)
    
    if selected_client != "-- 請選擇 --":
        if st.button("📥 從雲端載入此客戶", use_container_width=True):
            loaded_data = all_portfolios[selected_client]
            # 將字典轉回 DataFrame
            loaded_data["basket"] = pd.DataFrame(loaded_data["basket"])
            st.session_state.form_data = loaded_data
            st.success(f"已成功載入 {selected_client} 的資料！")
    
    st.divider()
    
    # 2. 儲存新客戶
    st.subheader("儲存目前的組合")
    new_client_name = st.text_input("輸入客戶或組合名稱 (例如: 陳先生-台積電FCN):")
    if st.button("☁️ 備份至 Google Sheets", use_container_width=True):
        if new_client_name and "form_data" in st.session_state:
            with st.spinner("正在上傳至雲端資料庫..."):
                # 將 DataFrame 轉為 dict 才能存入 JSON
                data_to_save = st.session_state.form_data.copy()
                data_to_save["basket"] = data_to_save["basket"].to_dict('records')
                
                save_portfolio(new_client_name, data_to_save)
                st.cache_data.clear() # 清除暫存，讓下拉選單立刻更新
                st.success(f"✅ {new_client_name} 已安全儲存至雲端！")
        else:
            st.error("請先輸入名稱，並確保右側有合約資料。")
            
    st.divider()
    st.caption("🔒 您的資料已加密連線至私人的 Google Sheets，安全無虞。")

# ==========================================
# 🪄 區塊 0：AI JSON 快速匯入區 (僅建立新合約時使用)
# ==========================================
with st.expander("🪄 建立新合約：貼上 AI 產生的 JSON (點擊展開)", expanded=False):
    st.markdown("""
    **使用步驟：**
    1. 點擊下方黑框右上角的「複製」按鈕，複製通關密語 (Prompt)。
    2. 將委託書照片傳給 ChatGPT 或 Gemini，並貼上剛剛複製的密語。
    3. 將 AI 產生的 JSON 完整貼在最下方的白框內，點擊載入！
    
    **👇 請複製以下通關密語：**
    """)
    ai_prompt = """你是一位華爾街結算專家。請閱讀我上傳的 FCN 委託書照片，並將合約條件萃取出來。嚴格只能輸出純 JSON 格式，不要加上 Markdown 標記或任何廢話。數字去除千分位，百分比轉為純數字。
JSON 格式範本：
{"coupon_rate": 22.07, "tenor_months": 3, "guaranteed_months": 1, "basket": [{"ticker": "NVDA", "initial": 228.38, "ko": 216.96, "strike": 171.28, "ki": 159.86}]}"""
    
    st.code(ai_prompt, language="text")
    st.markdown("**👇 貼上 AI 產出的結果：**")
    json_input = st.text_area("請在此貼上 JSON 程式碼：", height=150, label_visibility="collapsed")
    
    if st.button("✨ 一鍵載入新合約資料"):
        if json_input:
            try:
                clean_json = json_input.replace('\\_', '_').replace('[', '[').replace(']', ']')
                ai_data = json.loads(clean_json)
                
                new_basket = pd.DataFrame(ai_data["basket"])
                new_basket.columns = ["股票代碼 (Ticker)", "期初價 (Initial)", "出場價 (KO 95%)", "履約價 (Strike 75%)", "接貨價 (KI 70%)"]
                
                st.session_state.form_data["coupon_rate"] = float(ai_data["coupon_rate"])
                st.session_state.form_data["tenor_months"] = int(ai_data["tenor_months"])
                st.session_state.form_data["guaranteed_months"] = int(ai_data["guaranteed_months"])
                st.session_state.form_data["basket"] = new_basket
                st.success("✅ 資料載入成功！您現在可以到左側邊欄將此組合「備份至雲端」。")
            except Exception as e:
                st.error("❌ 載入失敗！請確認 JSON 格式。")
        else:
            st.warning("請先貼上 JSON 內容喔！")

st.write("---")

# ==========================================
# 區塊 1：合約基本條件
# ==========================================
st.header("1. 合約基本條件 (Contract Terms)")
col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    principal = st.number_input("本金金額 (Principal)", min_value=0, value=st.session_state.form_data.get("principal", 300000), step=10000)
with col2:
    currency = st.selectbox("幣別", ["USD (美元)", "TWD (台幣)", "HKD (港幣)"])
with col3:
    coupon_rate = st.number_input("年化配息率 (%)", min_value=0.0, value=float(st.session_state.form_data["coupon_rate"]), step=0.1)
with col4:
    tenor_months = st.number_input("總天期 (個月)", min_value=1, value=int(st.session_state.form_data["tenor_months"]))
with col5:
    guaranteed_months = st.number_input("保息期數 (個月)", min_value=0, value=int(st.session_state.form_data["guaranteed_months"]))

st.session_state.form_data["principal"] = principal
st.session_state.form_data["coupon_rate"] = coupon_rate
st.session_state.form_data["tenor_months"] = tenor_months
st.session_state.form_data["guaranteed_months"] = guaranteed_months

# ==========================================
# 區塊 2：籃子標的設定
# ==========================================
st.write("---")
st.header("2. 籃子標的設定 (Basket Underlying)")
st.info("💡 提示：您可以直接在表格內修改數字。修改後若想永久保留，請記得點擊左側邊欄的「備份至雲端」。")

edited_basket = st.data_editor(st.session_state.form_data["basket"], num_rows="dynamic", use_container_width=True)
st.session_state.form_data["basket"] = edited_basket 

submitted = st.button("🚀 執行即時運算與風險掃描", use_container_width=True, type="primary")

# ==========================================
# 區塊 3：運算與即時監控儀表板
# ==========================================
if submitted:
    st.write("---")
    st.header("3. 即時監控與試算結果")
    
    monthly_coupon_rate = (coupon_rate / 100) / 12
    monthly_payout = principal * monthly_coupon_rate
    guaranteed_payout = monthly_payout * guaranteed_months
    max_payout = monthly_payout * tenor_months
    
    st.subheader("💰 配息收益試算")
    c1, c2, c3 = st.columns(3)
    c1.metric(f"每期 (月) 配息金額", f"${monthly_payout:,.2f}")
    c2.metric(f"保證最低收益 ({guaranteed_months}個月)", f"${guaranteed_payout:,.2f}")
    c3.metric(f"安全下莊最高總領 ({tenor_months}個月)", f"${max_payout:,.2f}")
    
    st.write("---")
    st.subheader("📊 籃子標的風險掃描 (Worst-Of 機制)")
    
    worst_performer_ticker = ""
    worst_drop_pct = float('inf')
    current_worst_pct = 0
    dist_to_ki_of_worst = 0
    chart_data = pd.DataFrame()
    
    first_row = edited_basket.iloc[0]
    ko_pct = (first_row["出場價 (KO 95%)"] / first_row["期初價 (Initial)"]) * 100
    ki_pct = (first_row["接貨價 (KI 70%)"] / first_row["期初價 (Initial)"]) * 100
    strike_pct = (first_row["履約價 (Strike 75%)"] / first_row["期初價 (Initial)"]) * 100

    is_all_ko = True # 預設為全數 KO，只要有一檔沒達標就改為 False

    cols = st.columns(len(edited_basket))
    for idx, row in edited_basket.iterrows():
        ticker = row["股票代碼 (Ticker)"]
        init_price = row["期初價 (Initial)"]
        ko_price = row["出場價 (KO 95%)"]
        ki_price = row["接貨價 (KI 70%)"]
        
        with cols[idx]:
            try:
                stock = yf.Ticker(ticker)
                hist = stock.history(period="3mo")['Close']
                if hist.empty:
                    raise ValueError("無資料")
                
                current_price = hist.iloc[-1]
                normalized_hist = (hist / init_price) * 100
                chart_data[ticker] = normalized_hist
                
                change_from_init = (current_price - init_price) / init_price
                current_relative_pct = (current_price / init_price) * 100
                dist_to_ki = ((current_price - ki_price) / current_price) * 100
                
                # 只要有一檔股價小於 KO 價，全數 KO 條件就不成立
                if current_price < ko_price:
                    is_all_ko = False
                
                if change_from_init < worst_drop_pct:
                    worst_drop_pct = change_from_init
                    worst_performer_ticker = ticker
                    current_worst_pct = current_relative_pct
                    dist_to_ki_of_worst = dist_to_ki
                
                st.markdown(f"### **{ticker}**")
                st.metric("即時股價", f"${current_price:.2f}", f"{change_from_init*100:.2f}% (距期初)")
                
                if current_price >= ko_price:
                    st.success("🎉 達出場價")
                elif current_price <= ki_price:
                    st.error("🔴 跌破 KI")
                else:
                    st.info(f"🟢 距 KI {dist_to_ki:.1f}%")
                    
            except Exception as e:
                st.error(f"{ticker} 報價讀取失敗")

    # 3-3: 綜合狀態總結與 KO 結算看板
    st.write("---")
    if worst_performer_ticker:
        # 優先判斷是否全面 KO
        if is_all_ko:
            status_color = "#00cc66" # 綠色
            ko_payout = principal + monthly_payout
            status_title = "🎉 恭喜！達標提早出場 (KO)"
            status_text = f"所有標的皆已突破 KO 價！若今日為結算比價日，您將拿回本金與當期配息，共計：<strong>${ko_payout:,.2f}</strong>"
        else:
            status_title = "📉 合約狀態總結"
            if dist_to_ki_of_worst <= 0:
                status_color = "#ff4b4b" # 紅色
                status_text = f"<strong>目前最差標的：</strong> {worst_performer_ticker} ({current_worst_pct:.1f}%) | 🚨 已觸及 KI (接貨風險極高)！"
            elif dist_to_ki_of_worst < 10:
                status_color = "#ffcc00" # 黃色
                status_text = f"<strong>目前最差標的：</strong> {worst_performer_ticker} ({current_worst_pct:.1f}%) | ⚠️ 尚未 KI (距 KI 僅剩 {dist_to_ki_of_worst:.1f}%) - 請密切關注！"
            else:
                status_color = "#1f77b4" # 藍色 (安全)
                status_text = f"<strong>目前最差標的：</strong> {worst_performer_ticker} ({current_worst_pct:.1f}%) | 🟢 尚未 KI (距 KI 剩 {dist_to_ki_of_worst:.1f}%)"
            
        st.markdown(f"""
        <div style="padding: 15px; border-radius: 5px; background-color: #f0f2f6; border-left: 5px solid {status_color};">
            <h4 style="margin:0;">{status_title}</h4>
            <p style="margin:5px 0 0 0; font-size: 16px;">
                {status_text}
            </p>
        </div>
        """, unsafe_allow_html=True)

    st.write("<br>", unsafe_allow_html=True)
    st.subheader("📈 籃子標的相對走勢圖 (基準: 期初價 = 100%)")
    chart_data["出場線 (KO)"] = ko_pct
    chart_data["履約線 (Strike)"] = strike_pct
    chart_data["接貨線 (KI)"] = ki_pct
    chart_data = chart_data.dropna()
    
    # === 新增：使用 Altair 繪製防誤觸的靜態圖表 ===
    import altair as alt
    
    # 1. 確保時間格式乾淨並移除時區 (避免 Altair 報錯)
    chart_data.index = pd.to_datetime(chart_data.index)
    if chart_data.index.tz is not None:
        chart_data.index = chart_data.index.tz_localize(None)
    chart_data.index.name = 'Date'

    # 2. 將寬資料表轉為 Altair 需要的「長格式 (Long format)」
    df_melted = chart_data.reset_index().melt('Date', var_name='標的/基準線', value_name='價格比例 (%)')

    # 3. 繪製圖表 (重點：保留 tooltip 游標提示，但不開啟 .interactive() 縮放功能)
    chart = alt.Chart(df_melted).mark_line().encode(
        x=alt.X('Date:T', title='日期'),
        y=alt.Y('價格比例 (%):Q', title='相對比例 (%)', scale=alt.Scale(zero=False)),
        color=alt.Color('標的/基準線:N', title='圖例'),
        tooltip=[
            alt.Tooltip('Date:T', title='日期', format='%Y-%m-%d'),
            alt.Tooltip('標的/基準線:N', title='標的'),
            alt.Tooltip('價格比例 (%):Q', title='比例 (%)', format='.1f')
        ]
    ).properties(height=400)

    st.altair_chart(chart, use_container_width=True)

# ==========================================
# 區塊 4：說明與注意事項
# ==========================================
st.write("---")
with st.expander("ℹ️ 數據來源、名詞定義與注意事項 (點擊展開)"):
    st.markdown("""
    ### 🔍 數據來源
    * **報價來源**：本系統使用 Yahoo Finance 公開 API 抓取歷史與即時股價資料。
    * **時間落差**：美股盤中可能有約 15 分鐘延遲；若於台灣時間白天觀看，所顯示之即時股價為「前一交易日收盤價」或「盤後價格」。

    ### 📖 資料定義 (合約機制)
    * **期初價 (Initial Price)**：合約生效時各標的的基準價格。系統將以最新股價與此價格對比，計算漲跌幅以找出最弱勢標的。
    * **出場價 (KO / Knock-Out)**：若所有標的股價皆大於或等於此價位，合約將提前結算出場。
    * **接貨價 (KI / Knock-In)**：安全底線。若最弱勢標的跌破此價位，合約保護機制失效，投資人將面臨以「履約價」買入該弱勢股票的風險。
    * **履約價 (Strike)**：若發生接貨事件（跌破 KI）且直到到期日都未能漲回，投資人必須以此價格買入表現最差的那檔股票。
    * **最弱勢標的 (Worst-Of)**：一籃子 FCN 的核心機制。合約的提早出場 (KO) 或接貨 (KI) 命運，完全取決於籃子中「表現最差（跌幅最深或漲幅最小）」的那一檔標的。

    ### 💰 資料定義 (配息與收益)
    * **年化配息率 (Coupon Rate)**：計算每期固定收益的基準。本系統依據 `(本金 × 年化配息率) ÷ 12` 來估算每月配息金額。
    * **保息期數 (Guaranteed Months)**：發行商保證給付的配息期數。即使合約在第一個月就達標出場 (KO)，投資人仍可安全領滿此期數之總配息。

    ### ⚠️ 注意事項
    * **非正式對帳單**：本工具僅供個人輔助追蹤與試算參考，非金融機構之正式對帳單。
    * **合約條款差異**：實際合約的 KO/KI 判定標準（如：每日收盤觀察或盤中觸價觀察）、以及配息計算之計息天數（Day Count Convention）可能因各家銀行與發行商而異，請以您的實際委託書條款為準。
    * **免責聲明**：本系統不提供任何投資建議，亦不保證資料之絕對精準度，投資決策與盈虧責任由使用者自行承擔。
    """)
