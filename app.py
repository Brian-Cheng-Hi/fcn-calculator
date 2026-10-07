import streamlit as st
import yfinance as yf
import pandas as pd
import datetime

# 設定網頁標題與排版佈局 (改為寬版)
st.set_page_config(page_title="FCN 持倉風險追蹤器 Pro", layout="wide")
st.title("📈 FCN 持倉風險追蹤器 (進階視覺版)")
st.write("手動輸入合約條件，系統將自動抓取即時股價、計算風險距離，並繪製走勢圖。")

# 將畫面分為左右兩欄 (比例 1:2)
col_input, col_result = st.columns([1, 2])

with col_input:
    st.subheader("📝 輸入合約參數")
    with st.form("fcn_form"):
        ticker = st.text_input("股票代碼 (例如: TSLA, AAPL, NVDA)", "TSLA")
        ko_price = st.number_input("出場價 (KO)", min_value=0.0, value=250.0)
        strike_price = st.number_input("履約價 (Strike)", min_value=0.0, value=200.0)
        ki_price = st.number_input("接貨價 (KI)", min_value=0.0, value=150.0)
        
        # 新增功能：合約到期日
        maturity_date = st.date_input("合約到期日", datetime.date.today() + datetime.timedelta(days=90))
        
        submitted = st.form_submit_button("執行運算與繪圖")

# 當使用者按下按鈕後的執行邏輯
if submitted:
    with col_result:
        st.subheader(f"📊 {ticker} 即時分析報告")
        st.info("正在連線抓取最新報價與歷史數據...")
        
        try:
            # 抓取過去半年的股價資料來畫圖
            stock = yf.Ticker(ticker)
            hist = stock.history(period="6mo")
            current_price = hist['Close'].iloc[-1]
            
            # 計算到期天數
            today = datetime.date.today()
            days_left = (maturity_date - today).days
            
            # 計算距離百分比
            dist_to_ko = ((ko_price - current_price) / current_price) * 100
            dist_to_ki = ((current_price - ki_price) / current_price) * 100
            
            # 合約狀態判定邏輯
            status = "🟢 安全區間"
            if current_price >= ko_price:
                status = "🎉 達標出場 (KO)"
            elif current_price <= ki_price:
                status = "🔴 已跌破接貨價 (KI)"
            elif dist_to_ki < 10:
                status = "⚠️ 逼近接貨危險區"
            
            # 顯示主要數據卡片 (4格)
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("最新即時股價", f"${current_price:.2f}")
            m2.metric("目前合約狀態", status)
            m3.metric("距離 KO 還有", f"{dist_to_ko:.2f}%")
            m4.metric("距離到期天數", f"{days_left} 天" if days_left >= 0 else "已到期")
            
            st.write("---")
            st.write(f"**📈 近半年股價與合約價位走勢圖 ({ticker})**")
            
            # 整理圖表資料：將歷史股價與三條水平線合併
            chart_data = pd.DataFrame({
                "歷史股價": hist['Close'],
                "KO 出場價": ko_price,
                "Strike 履約價": strike_price,
                "KI 接貨價": ki_price
            })
            
            # 繪製折線圖
            st.line_chart(chart_data)
            
        except Exception as e:
            st.error("資料抓取失敗，請確認代碼是否正確（美股請直接輸入代碼）。")

# === 新增：說明與注意事項區塊 ===
st.write("---")
with st.expander("ℹ️ 數據來源、名詞定義與注意事項 (點擊展開)"):
    st.markdown("""
    ### 🔍 數據來源
    * **報價來源**：本系統使用 Yahoo Finance 公開 API 抓取歷史與即時股價資料。
    * **時間落差**：美股盤中可能有約 15 分鐘延遲；若於台灣時間白天觀看，所顯示之即時股價為「前一交易日收盤價」或「盤後價格」。

    ### 📖 資料定義
    * **出場價 (KO / Knock-Out)**：若標的股價漲至或超過此價位，合約將提前結算出場，並賺取約定之高額配息。
    * **履約價 (Strike)**：若發生接貨事件（跌破 KI），投資人必須以此價格買入該股票。
    * **接貨價 (KI / Knock-In)**：安全底線。若標的股價跌破此價位，合約保護機制失效，投資人將面臨以履約價買入股票的風險。

    ### ⚠️ 注意事項
    * **非正式對帳單**：本工具僅供個人輔助追蹤與試算參考，非金融機構之正式對帳單。
    * **合約條款差異**：實際合約的 KO/KI 判定標準（如：每日收盤觀察或盤中觸價觀察）可能因各家銀行與發行商而異，請以您的實際委託書條款為準。
    * **免責聲明**：本系統不提供任何投資建議，亦不保證資料之絕對精準度，投資決策與盈虧責任由使用者自行承擔。
    """)
