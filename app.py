import streamlit as st
import yfinance as yf
import pandas as pd
import datetime

st.set_page_config(page_title="FCN 籃子風險追蹤器 Pro", layout="wide")
st.title("📈 FCN 一籃子風險追蹤器 (Worst-Of 旗艦版)")
st.write("依照真實 FCN 委託書邏輯設計，支援多檔標的同時監控，並自動計算最弱勢標的與配息金額。")

# === 區塊 1：合約基本條件與資金試算 ===
st.header("1. 合約基本條件 (Contract Terms)")
col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    principal = st.number_input("本金金額 (Principal)", min_value=0, value=300000, step=10000)
with col2:
    currency = st.selectbox("幣別", ["USD (美元)", "TWD (台幣)", "HKD (港幣)"])
with col3:
    coupon_rate = st.number_input("年化配息率 (%)", min_value=0.0, value=22.07, step=0.1)
with col4:
    tenor_months = st.number_input("總天期 (個月)", min_value=1, value=3)
with col5:
    guaranteed_months = st.number_input("保息期數 (個月)", min_value=0, value=1)

col_d1, col_d2 = st.columns(2)
with col_d1:
    first_obs_date = st.date_input("首次比價日 (First Observation)", datetime.date(2026, 11, 9))
with col_d2:
    final_obs_date = st.date_input("最終比價日 (Final Observation)", datetime.date(2027, 1, 7))

# === 區塊 2：籃子標的設定 (可編輯表格) ===
st.write("---")
st.header("2. 籃子標的設定 (Basket Underlying)")
st.info("💡 提示：您可直接在下方表格內修改代碼與價位，或點擊下方新增/刪除標的。系統已為您預先帶入範例數據。")

# 預設帶入委託書上的 4 檔股票數據
default_basket = pd.DataFrame({
    "股票代碼 (Ticker)": ["NVDA", "TSM", "COHR", "LITE"],
    "期初價 (Initial)": [228.38, 456.19, 287.81, 971.26],
    "出場價 (KO 95%)": [216.96, 433.38, 273.42, 922.70],
    "履約價 (Strike 75%)": [171.28, 342.14, 215.86, 728.44],
    "接貨價 (KI 70%)": [159.86, 319.33, 201.46, 679.88]
})

# 使用 Streamlit 的資料編輯器，讓使用者可以自由增刪改
edited_basket = st.data_editor(default_basket, num_rows="dynamic", use_container_width=True)

submitted = st.button("🚀 執行即時運算與風險掃描", use_container_width=True, type="primary")

# === 區塊 3：運算與即時監控儀表板 ===
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
    
    # 3-2: 抓取股價與尋找最弱勢標的 (Worst-Of)
    st.write("---")
    st.subheader("📊 籃子標的風險掃描 (Worst-Of 機制)")
    
    worst_performer_ticker = ""
    worst_drop_pct = float('inf') # 記錄跌幅最深的值
    
    # 建立與標的數量相等的欄位來顯示卡片
    cols = st.columns(len(edited_basket))
    
    for idx, row in edited_basket.iterrows():
        ticker = row["股票代碼 (Ticker)"]
        init_price = row["期初價 (Initial)"]
        ko_price = row["出場價 (KO 95%)"]
        ki_price = row["接貨價 (KI 70%)"]
        
        with cols[idx]:
            try:
                # 抓取即時股價
                stock = yf.Ticker(ticker)
                hist = stock.history(period="1d")
                if hist.empty:
                    raise ValueError("無資料")
                current_price = hist['Close'].iloc[-1]
                
                # 計算與期初的漲跌幅
                change_from_init = (current_price - init_price) / init_price
                
                # 判斷是否為目前最弱勢標的
                if change_from_init < worst_drop_pct:
                    worst_drop_pct = change_from_init
                    worst_performer_ticker = ticker
                
                # 計算距離接貨價 (KI) 的安全緩衝
                dist_to_ki = ((current_price - ki_price) / current_price) * 100
                
                # 顯示單一標的卡片
                st.markdown(f"### **{ticker}**")
                st.metric("即時股價", f"${current_price:.2f}", f"{change_from_init*100:.2f}% (距期初)")
                
                if current_price >= ko_price:
                    st.success("🎉 已達出場價 (KO)")
                elif current_price <= ki_price:
                    st.error("🔴 已跌破接貨價 (KI)")
                elif dist_to_ki < 10:
                    st.warning(f"⚠️ 距 KI 僅剩 {dist_to_ki:.1f}%")
                else:
                    st.info(f"🟢 距 KI 還有 {dist_to_ki:.1f}%")
                    
            except Exception as e:
                st.error(f"{ticker} 報價讀取失敗，請確認代碼是否為標準美股代碼 (如 TSM)")

    # 3-3: 警示最弱勢標的
    st.write("---")
    if worst_performer_ticker:
        st.error(f"🚨 **目前最弱勢標的 (Worst-Of) 為：【 {worst_performer_ticker} 】**")
        st.caption("FCN 合約的命運由籃子中表現最差的標的決定。請密切關注該檔股票是否逼近 KI 或順利突破 KO。")

# === 區塊 4：說明與注意事項區塊 ===
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
