import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 1. 페이지 설정
st.set_page_config(page_title="주가 변동 분석 대시보드", layout="wide")
st.title("📈 최근 1년 주가 변동 분석")
st.write("삼성전자, SK하이닉스, 구글(Alphabet)의 최근 1개년 주가 추이를 비교합니다.")

# 2. 데이터 수집 설정 (최근 1년)
tickers = {
    "삼성전자": "005930.KS",
    "SK하이닉스": "000660.KS",
    "구글 (Google)": "GOOGL"
}

end_date = datetime.today()
start_date = end_date - timedelta(days=365)

@st.cache_data
def load_data(ticker_dict, start, end):
    df_list = []
    for name, ticker in ticker_dict.items():
        data = yf.download(ticker, start=start, end=end)
        if not data.empty:
            # yfinance 최신 버전의 MultiIndex 또는 SingleIndex 대응을 위해 'Close' 컬럼만 추출
            close_data = data['Close'].copy()
            # 종종 Series나 2D DataFrame으로 나오는 경우를 대비해 1차원 Series로 변환
            if isinstance(close_data, pd.DataFrame):
                close_data = close_data.iloc[:, 0]
                
            df = pd.DataFrame({"Date": close_data.index, "Price": close_data.values})
            df["Company"] = name
            df_list.append(df)
    return pd.concat(df_list, ignore_index=True)

with st.spinner("야후 파이낸스로부터 데이터를 불러오는 중..."):
    raw_data = load_data(tickers, start_date, end_date)

# 3. 데이터 가공 (기준일 대비 수익률 계산)
# 각 기업별 첫 거래일 주가를 기준으로 누적 수익률(%) 계산
processed_list = []
for name in tickers.keys():
    comp_df = raw_data[raw_data["Company"] == name].sort_values("Date").reset_index(drop=True)
    if not comp_df.empty:
        base_price = comp_df["Price"].iloc[0]
        comp_df["Return (%)"] = ((comp_df["Price"] - base_price) / base_price) * 100
        processed_list.append(comp_df)

data = pd.concat(processed_list, ignore_index=True)

# 4. 레이아웃 나누기 (탭 구성)
tab1, tab2, tab3 = st.tabs(["📊 수익률 비교 (추천)", "💵 절대 주가 추이", "📑 데이터 원본"])

with tab1:
    st.subheader("1년 전 대비 누적 수익률 (%)")
    st.caption("주가 절대값이 다르므로, 1년 전 시작점(0%) 기준 상승/하락률로 비교하는 것이 가장 정확합니다.")
    
    fig_return = go.Figure()
    for name in tickers.keys():
        comp_data = data[data["Company"] == name]
        fig_return.add_trace(go.Scatter(
            x=comp_data["Date"], 
            y=comp_data["Return (%)"], 
            mode='lines', 
            name=name,
            hovertemplate='%{x}<br>' + name + ': %{y:.2f}%<extra></extra>'
        ))
    
    fig_return.update_layout(
        hovermode="x unified",
        xaxis_title="날짜",
        yaxis_title="수익률 (%)",
        template="plotly_white"
    )
    st.plotly_chart(fig_return, use_container_width=True)

with tab2:
    st.subheader("기업별 절대 주가 추이")
    st.warning("삼성전자/하이닉스는 원화(KRW), 구글은 달러(USD) 기준이므로 단순 수치 비교는 불가능합니다.")
    
    selected_company = st.selectbox("조회할 기업을 선택하세요:", list(tickers.keys()))
    comp_data = data[data["Company"] == selected_company]
    
    fig_price = go.Figure()
    fig_price.add_trace(go.Scatter(
        x=comp_data["Date"], 
        y=comp_data["Price"], 
        mode='lines', 
        name=selected_company,
        line=dict(color='#ff7f0e' if selected_company=="SK하이닉스" else '#1f77b4' if selected_company=="삼성전자" else '#2ca02c')
    ))
    
    currency = "USD" if selected_company == "구글 (Google)" else "KRW"
    fig_price.update_layout(
        hovermode="x unified",
        xaxis_title="날짜",
        yaxis_title=f"주가 ({currency})",
        template="plotly_white"
    )
    st.plotly_chart(fig_price, use_container_width=True)

with tab3:
    st.subheader("최근 1개년 데이터 표")
    # 피벗 테이블 형태로 변환하여 가시성 확보
    df_pivot = data.pivot(index="Date", columns="Company", values="Price").sort_index(ascending=False)
    st.dataframe(df_pivot, use_container_width=True)
