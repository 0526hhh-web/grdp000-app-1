#######################
# Import libraries
import streamlit as st
import pandas as pd
import altair as alt
import plotly.express as px

#######################
# Page configuration
st.set_page_config(
    page_title="지역별 GRDP/소득 대시보드",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)
alt.themes.enable("default")

#######################
# CSS styling
st.markdown("""
<style>
[data-testid="block-container"] {
    padding-left: 2rem; padding-right: 2rem;
    padding-top: 1rem;  padding-bottom: 0rem;
    margin-bottom: -7rem;
}
[data-testid="stVerticalBlock"] { padding-left: 0rem; padding-right: 0rem; }

/* Metric 카드 글자/배경 */
[data-testid="stMetric"]{
    background-color:#393939; text-align:center; padding:15px 0;
    border-radius:12px; color:white;
}
[data-testid="stMetricLabel"]{ display:flex; justify-content:center; align-items:center; color:white; }
[data-testid="stMetricValue"]{ color:white !important; }
[data-testid="stMetricDelta"]{ color:white !important; }
[data-testid="stMetricDeltaIcon-Up"],
[data-testid="stMetricDeltaIcon-Down"]{
    position:relative; left:38%; transform:translateX(-50%);
}
</style>
""", unsafe_allow_html=True)

#######################
# Load data
df_reshaped = pd.read_csv(
    "시도별_1인당_지역내총생산__지역총소득__개인소득_20250829110847.csv",
    encoding="cp949"
)

#######################
# Sidebar
with st.sidebar:
    st.title("지역별 GRDP/소득 대시보드")
    st.caption("연도·지표·테마를 선택해 시각화를 제어하세요.")

    # 연도 컬럼 자동 인식 (예: '2023 p)')
    def _year_pairs(cols):
        pairs=[]
        for c in cols:
            s=str(c).strip(); y=s[:4]
            if y.isdigit(): pairs.append((int(y), c))
        return sorted(list(set(pairs)), key=lambda x:x[0])

    year_pairs = _year_pairs(df_reshaped.columns)
    if year_pairs:
        year_labels = [str(y) for y,_ in year_pairs]
        year_label  = st.selectbox("연도 선택", year_labels, index=len(year_labels)-1)
        selected_year_col = {str(y):raw for y,raw in year_pairs}[year_label]
    else:
        st.warning("연도형 컬럼을 찾지 못했습니다.")
        year_label, selected_year_col = None, None

    # 지표 선택
    if "항목" in df_reshaped.columns:
        metric_options = sorted(df_reshaped["항목"].dropna().unique().tolist())
    else:
        metric_options = []
        st.warning("`항목` 컬럼을 찾지 못했습니다.")
    selected_metric = st.selectbox("지표 선택", metric_options, index=0 if metric_options else None)

    # 시도 필터
    if "시도별" in df_reshaped.columns:
        regions = df_reshaped["시도별"].dropna().unique().tolist()
        selected_regions = st.multiselect("시도 선택 (선택 안 하면 전체)", options=regions, default=[])
    else:
        selected_regions = []

    # 테마 (Plotly는 대문자, Altair는 소문자)
    theme_label = st.selectbox("색상 테마",
                               ["Blues","Reds","Greens","Viridis","Plasma","Cividis","Turbo"],
                               index=0)
    # 매핑
    ALT_SCHEME_MAP = {
        "Blues":"blues", "Reds":"reds", "Greens":"greens",
        "Viridis":"viridis", "Plasma":"plasma", "Cividis":"cividis", "Turbo":"turbo"
    }
    theme_plotly = theme_label
    theme_altair = ALT_SCHEME_MAP.get(theme_label, "blues")

    # 기타 옵션
    c1, c2 = st.columns(2)
    with c1:
        show_labels = st.checkbox("값 라벨 표시", value=True)
    with c2:
        top_n = st.number_input("Top N (랭킹)", min_value=3, max_value=20, value=10, step=1)

    # 상태 저장
    st.session_state.update({
        "selected_year_col": selected_year_col,
        "selected_year_display": year_label,
        "selected_metric": selected_metric,
        "selected_regions": selected_regions,
        "theme_plotly": theme_plotly,
        "theme_altair": theme_altair,
        "show_labels": show_labels,
        "top_n": int(top_n),
    })

#######################
# Dashboard Main Panel
col = st.columns((1.5, 4.5, 2), gap='medium')

# ---------- Col[0]: 요약 지표 ----------
with col[0]:
    st.subheader("요약 지표")
    year_col = st.session_state.get("selected_year_col")
    metric   = st.session_state.get("selected_metric")

    if year_col and metric and {"항목","시도별"}.issubset(df_reshaped.columns):
        df_sel = df_reshaped[df_reshaped["항목"]==metric][["시도별", year_col]].copy()
        df_sel[year_col] = pd.to_numeric(df_sel[year_col], errors="coerce")
        df_sel = df_sel.dropna(subset=[year_col])

        if not df_sel.empty:
            max_idx = df_sel[year_col].idxmax(); min_idx = df_sel[year_col].idxmin()
            region_max = df_sel.loc[max_idx, "시도별"]; val_max = float(df_sel.loc[max_idx, year_col])
            region_min = df_sel.loc[min_idx, "시도별"]; val_min = float(df_sel.loc[min_idx, year_col])
            val_avg = float(df_sel[year_col].mean())

            m1, m2 = st.columns(2)
            with m1: st.metric(f"최고값 시도 • {region_max}", f"{val_max:,.1f}")
            with m2: st.metric(f"최저값 시도 • {region_min}", f"{val_min:,.1f}")
            st.metric("전국 평균", f"{val_avg:,.1f}")
        else:
            st.info("선택한 조건에 데이터가 없습니다.")
    else:
        st.info("사이드바에서 지표와 연도를 선택하세요.")

# ---------- Col[1]: 지도(대체 bar) & Altair 히트맵 ----------
with col[1]:
    st.subheader("지도 & 히트맵")
    year_col = st.session_state.get("selected_year_col")
    metric   = st.session_state.get("selected_metric")
    theme_plotly = st.session_state.get("theme_plotly", "Blues")
    theme_altair = st.session_state.get("theme_altair", "blues")

    if year_col and metric:
        # 데이터 준비
        df_metric = df_reshaped[df_reshaped["항목"]==metric].copy()
        df_metric[year_col] = pd.to_numeric(df_metric[year_col], errors="coerce")
        df_metric = df_metric.dropna(subset=[year_col])

        # (임시) 지도 대체: 시도별 bar
        st.markdown("**시도별 값 (지도 대체 Bar)**")
        fig_map = px.bar(
            df_metric.sort_values(year_col, ascending=False),
            x="시도별", y=year_col, color=year_col,
            color_continuous_scale=theme_plotly,
            labels={year_col: f"{st.session_state.get('selected_year_display', year_col)} 값"},
            title=f"{st.session_state.get('selected_year_display', year_col)} {metric}"
        )
        st.plotly_chart(fig_map, use_container_width=True)

        st.divider()

        # 연도 리스트 (Altair 히트맵)
        year_cols = [c for c in df_reshaped.columns if str(c).strip()[:4].isdigit()]
        df_heatmap = df_reshaped[df_reshaped["항목"]==metric][["시도별"]+year_cols].copy()
        for c in year_cols: df_heatmap[c] = pd.to_numeric(df_heatmap[c], errors="coerce")
        df_long = df_heatmap.melt(id_vars="시도별", value_vars=year_cols, var_name="연도", value_name="값")

        heatmap = alt.Chart(df_long).mark_rect().encode(
            x=alt.X("연도:O", title="연도"),
            y=alt.Y("시도별:O", title="시도"),
            color=alt.Color("값:Q", scale=alt.Scale(scheme=theme_altair)),
            tooltip=["시도별","연도","값"]
        ).properties(title=f"시도별 {metric} 연도별 히트맵")
        st.altair_chart(heatmap, use_container_width=True)
    else:
        st.info("사이드바에서 지표와 연도를 먼저 선택하세요.")

# ---------- Col[2]: Top/Bottom 랭킹 ----------
with col[2]:
    st.subheader("상세 분석 & 설명")
    year_col = st.session_state.get("selected_year_col")
    metric   = st.session_state.get("selected_metric")
    theme_plotly = st.session_state.get("theme_plotly", "Blues")
    show_labels = st.session_state.get("show_labels", True)
    top_n = int(st.session_state.get("top_n", 10))

    if year_col and metric:
        df_sel = df_reshaped[df_reshaped["항목"]==metric][["시도별", year_col]].copy()
        df_sel[year_col] = pd.to_numeric(df_sel[year_col], errors="coerce")
        df_sel = df_sel.dropna(subset=[year_col])

        st.markdown(f"**Top {top_n} 시도 (선택 연도 기준)**")
        df_top = df_sel.sort_values(year_col, ascending=False).head(top_n)
        fig_top = px.bar(
            df_top, x=year_col, y="시도별", orientation="h",
            color=year_col, color_continuous_scale=theme_plotly,
            text=year_col if show_labels else None,
            labels={year_col: f"{st.session_state.get('selected_year_display', year_col)} 값"},
        )
        fig_top.update_layout(yaxis=dict(categoryorder="total ascending"))
        st.plotly_chart(fig_top, use_container_width=True)

        st.divider()

        st.markdown(f"**하위 {top_n} 시도 (선택 연도 기준)**")
        df_bottom = df_sel.sort_values(year_col, ascending=True).head(top_n)
        fig_bottom = px.bar(
            df_bottom, x=year_col, y="시도별", orientation="h",
            color=year_col, color_continuous_scale=theme_plotly,
            text=year_col if show_labels else None,
            labels={year_col: f"{st.session_state.get('selected_year_display', year_col)} 값"},
        )
        fig_bottom.update_layout(yaxis=dict(categoryorder="total ascending"))
        st.plotly_chart(fig_bottom, use_container_width=True)
    else:
        st.info("사이드바에서 지표와 연도를 먼저 선택하세요.")

    st.divider()
    st.markdown("### ℹ️ About")
    st.markdown(
        """
        - **데이터 출처:** 통계청  
        - **지표 설명**
            - 1인당 GRDP: 지역 내 총생산 ÷ 인구  
            - 지역총소득: 지역 내 모든 소득 합계  
            - 개인소득: 주민 개인이 실제로 사용 가능한 소득  
        """
    )
