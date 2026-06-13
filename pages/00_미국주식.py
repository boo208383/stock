import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 1. 페이지 설정
st.set_page_config(page_title="글로벌 주요 주식 분석 대시보드", layout="wide")
st.title("📈 글로벌 주요 주식 1년 변동 분석")
st.write("삼성전자, SK하이닉스, 구글에 더해 테슬라, 애플, 엔비디아의 최근 1개년 주가 추이를 비교합니다.")

# 2. 데이터 수집 설정 (총 6개 종목)
tickers = {
    "삼성전자": "005930.KS",
    "SK하이닉스": "000660.KS",
    "구글 (Alphabet)": "GOOGL",
    "테슬라 (Tesla)": "TSLA",
    "애플 (Apple)": "AAPL",
    "엔비디아 (NVIDIA)": "NVDA"
}

end_date = datetime.today()
start_date = end_date - timedelta(days=365)

@st.cache_data
def load_data(ticker_dict, start, end):
    df_list = []
    for name, ticker in ticker_dict.items():
        data = yf.download(ticker, start=start, end=end)
        if not data.empty:
            # yfinance 최신 버전 컬럼 구조 대응
            close_data = data['Close'].copy()
            if isinstance(close_data, pd.DataFrame):
                close_data = close_data.iloc[:, 0]
                
            df = pd.DataFrame({"Date": close_data.index, "Price": close_data.values})
            df["Company"] = name
            df_list.append(df)
    return pd.concat(df_list, ignore_index=True)

with st.spinner("야후 파이낸스로부터 데이터를 불러오는 중..."):
    raw_data = load_data(tickers, start_date, end_date)

# 3. 데이터 가공 (기준일 대비 수익률 계산)
processed_list = []
for name in tickers.keys():
    comp_df = raw_data[raw_data["Company"] == name].sort_values("Date").reset_index(drop=True)
    if not comp_df.empty:
        base_price = comp_df["Price"].iloc[0]
        comp_df["Return (%)"] = ((comp_df["Price"] - base_price) / base_price) * 100
        processed_list.append(comp_df)

data = pd.concat(processed_list, ignore_index=True)

# 4. 사이드바 - 분석할 주식 선택 기능 추가
st.sidebar.header("⚙️ 주식 선택")
selected_stocks = st.sidebar.multiselect(
    "그래프에 표시할 주식을 선택하세요:",
    options=list(tickers.keys()),
    default=list(tickers.keys()) # 기본값은 전체 선택
)

if not selected_stocks:
    st.warning("왼쪽 사이드바에서 최소 하나의 주식을 선택해 주세요!")
else:
    # 5. 레이아웃 나누기 (탭 구성)
    tab1, tab2, tab3 = st.tabs(["📊 수익률 비교 (추천)", "💵 절대 주가 추이", "📑 데이터 원본"])

    with tab1:
        st.subheader("1년 전 대비 누적 수익률 (%)")
        st.caption("서로 다른 통화(원화 vs 달러)와 주가 규모를 가진 주식들을 공정하게 비교하기 위해 1년 전 시작점(0%) 기준의 상승/하락률을 보여줍니다.")
        
        fig_return = go.Figure()
        for name in selected_stocks:
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
        st.caption("선택한 기업의 실제 주가 금액 추이를 확인합니다.")
        
        # 사이드바에서 선택된 주식들 중에서만 고를 수 있도록 연동
        selected_company = st.selectbox("조회할 기업을 선택하세요:", selected_stocks)
        comp_data = data[data["Company"] == selected_company]
        
        fig_price = go.Figure()
        fig_price.add_trace(go.Scatter(
            x=comp_data["Date"], 
            y=comp_data["Price"], 
            mode='lines', 
            name=selected_company
        ))
        
        # 한국 주식과 미국 주식의 화폐 단위 구분
        currency = "KRW" if selected_company in ["삼성전자", "SK하이닉스"] else "USD"
        fig_price.update_layout(
            hovermode="x unified",
            xaxis_title="날짜",
            yaxis_title=f"주가 ({currency})",
            template="plotly_white"
        )
        st.plotly_chart(fig_price, use_container_width=True)

    with tab3:
        st.subheader("최근 1개년 데이터 표")
        # 선택한 주식들만 필터링하여 피벗 테이블로 보여줌
        filtered_data = data[data["Company"].isin(selected_stocks)]
        df_pivot = filtered_data.pivot(index="Date", columns="Company", values="Price").sort_index(ascending=False)
        st.dataframe(df_pivot, use_container_width=True)
