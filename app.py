"""도시공원 이용 및 만족도 대시보드 (수업 예제 응용).

실행: python -m streamlit run app.py
배포: app.py, data.csv, requirements.txt를 같은 폴더에 올립니다.
"""
from pathlib import Path

import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import pandas as pd
import plotly.express as px
import streamlit as st

HERE = Path(__file__).parent
COLORS = {"한강공원": "#0072B2", "서울숲": "#D55E00", "북서울꿈의숲": "#009E73"}

st.set_page_config(page_title="도시공원 이용 현황", layout="wide")


@st.cache_data
def load_data():
    return pd.read_csv(HERE / "data.csv")


def korean_font():
    names = {f.name for f in fm.fontManager.ttflist}
    return next((name for name in ["Pretendard", "Malgun Gothic", "AppleGothic", "NanumGothic"] if name in names), None)


st.title("도시공원별 이용과 만족도는 어떻게 다를까?")
st.caption("출처: 수업 프로젝트용 가상 데이터(data.csv) · 2026년 1~12월 · 방문객: 명 / 만족도: 5점 만점")
st.info("이 데이터는 실제 공원 조사 결과가 아닌 학습용 가상 데이터입니다.")

try:
    data = load_data()
except FileNotFoundError:
    st.error("app.py와 같은 폴더에 data.csv를 넣어 주세요.")
    st.stop()

st.sidebar.header("조회 조건")
parks = st.sidebar.multiselect("공원", list(COLORS), default=list(COLORS))
months = st.sidebar.slider("월 범위", 1, 12, (1, 12))
metric_label = st.sidebar.selectbox("표시 지표", ["방문객 수", "평균 만족도"])
metric = {"방문객 수": "visitors", "평균 만족도": "satisfaction"}[metric_label]

view = data.loc[data["park"].isin(parks) & data["month"].between(months[0], months[1])].copy()
if view.empty:
    st.warning("표시할 데이터가 없습니다. 공원을 하나 이상 선택하세요.")
    st.stop()

st.subheader(f"{months[0]}~{months[1]}월 {metric_label} · {', '.join(parks)}")

# 만족도는 응답자 수로 가중평균합니다. 방문객 수와 설문 응답자 수는 서로 다른 개념입니다.
weighted_score = (view["satisfaction"] * view["responses"]).sum() / view["responses"].sum()
c1, c2, c3 = st.columns(3)
c1.metric("기간 방문객 합계", f"{view['visitors'].sum():,} 명")
c2.metric("표시 관측 수", f"{len(view)} 행")
c3.metric("기간 평균 만족도", f"{weighted_score:.2f} / 5점")
st.caption("한 행은 한 공원의 한 달입니다. 기간 평균 만족도는 설문 응답자 수로 가중평균했습니다.")

# 차트 1: 선택 지표의 월별 변화 (Plotly)
trend = px.line(
    view.sort_values(["park", "month"]), x="month", y=metric, color="park",
    markers=True, color_discrete_map=COLORS, title="월별 추이",
    labels={"month": "월", "park": "공원", "visitors": "방문객 (명)", "satisfaction": "만족도 (5점 만점)"},
)
trend.update_xaxes(dtick=1)
trend.update_yaxes(range=[0, 5] if metric == "satisfaction" else None, rangemode="tozero")

# 차트 2: 방문객은 합계, 만족도는 설문 응답자 가중평균 (Matplotlib)
if metric == "visitors":
    totals = view.groupby("park", as_index=False)["visitors"].sum()
else:
    totals = view.assign(weighted=view["satisfaction"] * view["responses"]).groupby("park", as_index=False)[["weighted", "responses"]].sum()
    totals["satisfaction"] = totals["weighted"] / totals["responses"]

kfont = korean_font()
with plt.rc_context({"font.family": kfont or "DejaVu Sans", "axes.unicode_minus": False}):
    fig, ax = plt.subplots(figsize=(6, 3.6))
    # 서버에 한글 글꼴이 없으면 Matplotlib 축에 영문 이름을 사용합니다.
    english = {"한강공원": "Hangang", "서울숲": "Seoul Forest", "북서울꿈의숲": "Dream Forest"}
    labels = totals["park"] if kfont else totals["park"].map(english)
    bars = ax.bar(labels, totals[metric], color=[COLORS[p] for p in totals["park"]])
    ax.bar_label(bars, fmt="%.0f" if metric == "visitors" else "%.2f", padding=3)
    ax.set(title="기간별 공원 비교" if kfont else "Park comparison",
           ylabel=("방문객 (명)" if metric == "visitors" else "만족도 (5점)") if kfont else ("Visitors" if metric == "visitors" else "Satisfaction (1-5)"))
    ax.set_ylim(0, max(totals[metric].max() * 1.2, 1) if metric == "visitors" else 5.5)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()

# 차트 3: 공원별 설문 만족도 (Plotly)
summary = view.assign(weighted=view["satisfaction"] * view["responses"]).groupby("park", as_index=False)[["weighted", "responses"]].sum()
summary["average_satisfaction"] = summary["weighted"] / summary["responses"]
satisfaction_fig = px.bar(
    summary, x="park", y="average_satisfaction", color="park", color_discrete_map=COLORS,
    title="기간 평균 만족도", labels={"park": "공원", "average_satisfaction": "평균 만족도 (5점 만점)"},
)
satisfaction_fig.update_layout(showlegend=False)
satisfaction_fig.update_yaxes(range=[0, 5])

left, middle, right = st.columns(3)
with left:
    st.plotly_chart(trend, use_container_width=True)
with middle:
    st.pyplot(fig, use_container_width=True)
with right:
    st.plotly_chart(satisfaction_fig, use_container_width=True)
plt.close(fig)
if not kfont:
    st.caption("서버에 한글 글꼴이 없어 가운데 Matplotlib 그래프의 글자는 영어로 표시합니다.")

st.subheader("현재 선택한 데이터")
st.dataframe(view, hide_index=True, use_container_width=True)
st.download_button("현재 선택 CSV 저장", data=view.to_csv(index=False).encode("utf-8-sig"),
                   file_name="selected_park_data.csv", mime="text/csv")
st.caption("가상 데이터의 수치로 실제 공원 이용 현황이나 만족도를 판단할 수 없습니다.")
