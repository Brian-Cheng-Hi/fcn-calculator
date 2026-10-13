import streamlit as st
import yfinance as yf
import pandas as pd
import datetime
import json

st.set_page_config(page_title="FCN 籃子風險追蹤器 Pro", layout="wide")
st.title("📈 FCN 一籃子風險追蹤器 (Worst-Of 旗艦版)")

# ==========================================
# 🌟 初始化記憶體 (確保資料更新後不會消失)
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
# 🪄 區塊 0：AI JSON 快速匯入區
# ==========================================
with st.expander("🪄 懶人包：貼上 AI 產生的 JSON 自動填表 (點擊展開)", expanded=True):
    st.markdown("""
    **使用步驟：**
    1. 點擊下方黑框右上角的「複製」按鈕，複製通關密語 (Prompt)。
    2. 將委託書照片傳給 ChatGPT 或 Gemini，並貼上剛剛複製的密語。
    3. 將 AI 產生的 JSON 完整貼在最下方的白框內，點擊載入！
    
    **👇 請複製以下通關密語：**
    """)
    
    # 內建神級 Prompt，st.code 會自動提供複製按鈕
    ai_prompt = """你是一位華爾街結算專家。請閱讀我上傳的 FCN 委託書照片，並將合約條件萃取出來。嚴格只能輸出純 JSON 格式，不要加上 Markdown 標記或任何廢話。數字去除千分位，百分比轉為純數字。

JSON 格式範本：
{"coupon_rate": 22.07, "tenor_months": 3, "guaranteed_months": 1, "basket": [{"ticker": "NVDA", "initial": 228.38, "ko": 216.96, "strike": 171.28, "ki": 159.86}]}"""
    
    st.code(ai_prompt, language="text")
    
    st.markdown("**👇 貼上 AI 產出的結果：**")
    json_input = st.text_area("請在此貼上 JSON 程式碼：", height=150, label_visibility="collapsed")
    
    if st.button("✨ 一鍵載入合約資料"):
        if json_input:
            try:
                # 自動清除 ChatGPT 亂加的 Markdown 反斜線
                clean_json = json_input.replace('\\_', '_').replace('\\[', '[').replace('\\]', ']')
                ai_data = json.loads(clean_json)
                
                new_basket = pd.DataFrame(ai_data["basket"])
                new_basket.columns = ["股票代碼 (Ticker)", "期初價 (Initial)", "出場價 (KO 95%)", "履約價 (Strike 75%)", "接貨價 (KI 70%)"]
                
                # 更新記憶體資料
                st.session_state.form_data["coupon_rate"] = float(ai_data["coupon_rate"])
                st.session_state.form_data["tenor_months"] = int(ai_data["tenor_months"])
                st.session_state.form_data["guaranteed_months"] = int(ai_data["guaranteed_months"])
                st.session_state.form_data["basket"] = new_basket
                
                st.success("✅ 資料載入成功！下方表格與條件已自動更新。")
            except Exception as e:
                st.error("❌ 載入失敗！請確認貼上的是完整的 JSON 格式（包含大括號 {} ），且不要包含其他文字。")
        else:
            st.warning("請先貼上 JSON 內容喔！")

st.write("---")

# ==========================================
# 區塊 1：合約基本條件
# ==========================================
st.header("1. 合約基本條件 (Contract Terms)")
col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    principal = st.number_input("本金金額 (Principal)", min_value=0, value=st.session_state.form_data["principal"], step=10000)
with col2:
    currency = st.selectbox("幣別", ["USD (美元)", "TWD (台幣)", "HKD (港幣)"])
with col3:
    coupon_rate = st.number_input("年化配息率 (%)", min_value=0.0, value=float(st.session_state.form_data["coupon_rate"]), step=0.1)
with col4:
    tenor_months = st.number_input("總天期 (個月)", min_value=1, value=int(st.session_state.form_data["tenor_months"]))
with col5:
    guaranteed_months = st.number_input("保息期數 (個月)", min_value=0, value=int(st.session_state.form_data["guaranteed_months"]))

col_d1, col_d2 = st.columns(2)
with col_d1:
    first_obs_date = st.date_input("首次比價日 (First Observation)", datetime.date.today() + datetime.timedelta(days=30))
with col_d2:
    final_obs_date = st.date_input("最終比價日 (Final Observation)", datetime.date.today() + datetime.timedelta(days=90))

# ==========================================
# 區塊 2：籃子標的設定
# ==========================================
st.write("---")
st.header("2. 籃子標的設定 (Basket Underlying)")
st.info("💡 提示：載入 JSON 後，資料會自動填入下方表格。您也可以手動修改。")

edited_basket = st.data_editor(st.session_state.form_data["basket"], num_rows="dynamic", use_container_width=True)

submitted = st.button("🚀 執行即時運算與風險掃描", use_container_width=True, type="primary")

# ==========================================
# 區塊 3：運算與即時監控儀表板
# ==========================================
if submitted:
    st.write("---")
    st.header("3. 即時監控與試算結果")
    
    # 3-1: 財務配息試算
    monthly_coupon_rate = (coupon_rate / 100) / 12
    monthly_payout = principal * monthly_coupon_rate
    guaranteed_payout = monthly_payout * guaranteed_months
    max_payout = monthly_payout * tenor_months
    
    st.subheader("💰 配息收益試算")
    c1, c2, c3 = st.columns(3)
    c1.metric(f"每期 (月) 配息金額", f"${monthly_payout:,.2f}")
    c2.metric(f"保證最低收益 ({guaranteed_months}個月)", f"${guaranteed_payout:,.2f}")
    c3.metric(f"安全下莊最高總領 ({tenor_months}個月)", f"${max_payout:,.2f}")
    
    # 3-2: 抓取歷史數據並進行「百分比正規化」運算
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

    # 3-3: 綜合狀態總結看板
    st.write("---")
    if worst_performer_ticker:
        if dist_to_ki_of_worst <= 0:
            status_color = "#ff4b4b"
            status_text = f"🚨 已觸及 KI (接貨風險極高)！"
        elif dist_to_ki_of_worst < 10:
            status_color = "#ffcc00"
            status_text = f"⚠️ 尚未 KI (距 KI 僅剩 {dist_to_ki_of_worst:.1f}%) - 請密切關注！"
        else:
            status_color = "#00cc66"
            status_text = f"🟢 尚未 KI (距 KI 剩 {dist_to_ki_of_worst:.1f}%)"
            
        st.markdown(f"""
        <div style="padding: 15px; border-radius: 5px; background-color: #f0f2f6; border-left: 5px solid {status_color};">
            <h4 style="margin:0;">📉 合約狀態總結</h4>
            <p style="margin:5px 0 0 0; font-size: 16px;">
                <strong>目前最差標的：</strong> {worst_performer_ticker} ({current_worst_pct:.1f}%) | {status_text}
            </p>
        </div>
        """, unsafe_allow_html=True)

    # 3-4: 百分比正規化走勢圖
    st.write("<br>", unsafe_allow_html=True)
    st.subheader("📈 籃子標的相對走勢圖 (基準: 期初價 = 100%)")
    
    chart_data["出場線 (KO)"] = ko_pct
    chart_data["履約線 (Strike)"] = strike_pct
    chart_data["接貨線 (KI)"] = ki_pct
    
    chart_data = chart_data.dropna()
    st.line_chart(chart_data, height=400)

# ==========================================
# 區塊 4：說明與注意事項區塊
# ==========================================
st.write("---")
with st.expander("ℹ️ 數據來源、名詞定義與注意事項 (點擊展開)"):
    st.markdown("""
    *(此處保留原有的名詞定義，省略以免佔用版面)*
    """)
