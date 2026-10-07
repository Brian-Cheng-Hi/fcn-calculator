import streamlit as st
import yfinance as yf

# 設定網頁標題
st.set_page_config(page_title="FCN 持倉風險追蹤器", layout="centered")
st.title("📈 FCN 持倉風險追蹤器 (測試版)")
st.write("手動輸入合約條件，系統將自動抓取即時股價並計算風險距離。")

# 建立資料輸入表單
with st.form("fcn_form"):
    ticker = st.text_input("1. 股票代碼 (例如: TSLA, AAPL)", "TSLA")
    
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        ko_price = st.number_input("2. 出場價 (KO)", min_value=0.0, value=250.0)
    with col_b:
        strike_price = st.number_input("3. 履約價 (Strike)", min_value=0.0, value=200.0)
    with col_c:
        ki_price = st.number_input("4. 接貨價 (KI)", min_value=0.0, value=150.0)

    # 送出按鈕
    submitted = st.form_submit_button("抓取最新股價並計算")

# 當使用者按下按鈕後的執行邏輯
if submitted:
    st.write("---")
    st.info(f"正在連線抓取 {ticker} 的最新報價...")
    
    try:
        # 抓取股價
        stock = yf.Ticker(ticker)
        current_price = stock.history(period="1d")['Close'].iloc[-1]
        
        # 計算距離百分比
        dist_to_ko = ((ko_price - current_price) / current_price) * 100
        dist_to_ki = ((current_price - ki_price) / current_price) * 100
        
        st.success("抓取成功！以下是即時運算數據：")
        
        # 顯示結果儀表板
        res1, res2, res3 = st.columns(3)
        res1.metric("最新即時股價", f"${current_price:.2f}")
        res2.metric("距離 KO (出場) 還有", f"{dist_to_ko:.2f}%")
        
        # 如果距離 KI 小於 10%，顯示紅色警告
        is_danger = dist_to_ki < 10
        res3.metric(
            "距離 KI (接貨) 還有", 
            f"{dist_to_ki:.2f}%", 
            delta="注意風險" if is_danger else "安全距離", 
            delta_color="inverse"
        )
        
    except Exception as e:
        st.error("抓取失敗！請確認「股票代碼」是否正確（美股請直接輸入代碼，如 NVDA）。")
