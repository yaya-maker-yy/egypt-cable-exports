import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import openpyxl
from collections import defaultdict

# Plotly config for touch/iPad compatibility
PLOTLY_CONFIG = {
    'displayModeBar': True,
    'scrollZoom': False,
    'responsive': True,
    'modeBarButtonsToRemove': ['lasso2d', 'select2d'],
}

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Egyptian Cable Exports Dashboard",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS (iPad/Safari compatible) ──────────────────────────────────────
st.markdown("""
<style>
    /* Base layout - avoid vh units that break on iPad Safari */
    .main .block-container {
        padding-top: 1.5rem;
        padding-bottom: 1rem;
        max-width: 100%;
    }

    /* KPI cards */
    div[data-testid="stMetric"] {
        background-color: #0f2a52;
        padding: 12px 16px;
        border-radius: 10px;
        border-left: 4px solid #d4af37;
        color: white;
    }
    div[data-testid="stMetric"] label { color: #ccc !important; font-size: 0.8rem !important; }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] { color: white !important; font-size: 1.4rem !important; }
    div[data-testid="stMetric"] div[data-testid="stMetricDelta"] { font-size: 0.8rem !important; }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        overflow-x: auto;
        -webkit-overflow-scrolling: touch;
        flex-wrap: nowrap;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #f0f2f6;
        border-radius: 6px 6px 0 0;
        padding: 8px 14px;
        font-weight: 600;
        white-space: nowrap;
        flex-shrink: 0;
    }
    .stTabs [aria-selected="true"] {
        background-color: #0f2a52 !important;
        color: white !important;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #0f2a52;
    }
    section[data-testid="stSidebar"] * { color: white !important; }
    section[data-testid="stSidebar"] .stMultiSelect div[data-baseweb="tag"] { background-color: #d4af37; }
    section[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,0.2); }

    /* Fix iframe/plotly rendering on iPad */
    iframe { max-width: 100% !important; }
    .stPlotlyChart { overflow: hidden !important; }

    /* Responsive columns - stack on smaller screens */
    @media (max-width: 1024px) {
        div[data-testid="stMetric"] { padding: 10px 12px; }
        div[data-testid="stMetric"] div[data-testid="stMetricValue"] { font-size: 1.1rem !important; }
        .stTabs [data-baseweb="tab"] { padding: 6px 10px; font-size: 0.85rem; }
    }
</style>
""", unsafe_allow_html=True)

# ── Load & process data ──────────────────────────────────────────────────────
@st.cache_data
def load_data():
    wb = openpyxl.load_workbook('ES/Countries_Translated_Full_Reviewed.xlsx')
    ws = wb['Sheet1']

    rows = []
    for row in ws.iter_rows(min_row=4, max_row=197, values_only=True):
        code = row[0]
        desc = row[1]
        country = row[2]
        region = row[3]
        unit = row[4]
        qty_2024 = row[5] or 0.0
        egp_2024 = row[6] or 0.0
        usd_2024 = row[7] or 0.0
        qty_2025 = row[8] or 0.0
        egp_2025 = row[9] or 0.0
        usd_2025 = row[10] or 0.0
        total_qty = row[11] or 0.0
        total_egp = row[12] or 0.0
        total_usd = row[13] or 0.0
        if country and region:
            rows.append({
                'HS Code': str(code) if code else '',
                'Description': desc or '',
                'Country': country,
                'Region': region,
                'Unit': unit or '',
                'QTY 2024': qty_2024,
                'M-EGP 2024': egp_2024,
                'M-USD 2024': usd_2024,
                'QTY 2025': qty_2025,
                'M-EGP 2025': egp_2025,
                'M-USD 2025': usd_2025,
                'Total QTY': total_qty,
                'Total M-EGP': total_egp,
                'Total M-USD': total_usd,
            })
    return pd.DataFrame(rows)

df_raw = load_data()

# Aggregated views
df_country = df_raw.groupby(['Region', 'Country']).agg({
    'M-USD 2024': 'sum', 'M-USD 2025': 'sum', 'Total M-USD': 'sum',
    'M-EGP 2024': 'sum', 'M-EGP 2025': 'sum', 'Total M-EGP': 'sum',
    'QTY 2024': 'sum', 'QTY 2025': 'sum', 'Total QTY': 'sum',
}).reset_index()

df_country['YoY Growth %'] = df_country.apply(
    lambda r: ((r['M-USD 2025'] - r['M-USD 2024']) / r['M-USD 2024'] * 100)
    if r['M-USD 2024'] > 0.001 else (100.0 if r['M-USD 2025'] > 0 else 0.0), axis=1
)

df_region = df_country.groupby('Region').agg({
    'M-USD 2024': 'sum', 'M-USD 2025': 'sum', 'Total M-USD': 'sum',
    'M-EGP 2024': 'sum', 'M-EGP 2025': 'sum', 'Total M-EGP': 'sum',
    'Country': 'count',
}).reset_index().rename(columns={'Country': 'Countries'})

REGION_COLORS = {
    'Europe': '#2E86AB',
    'GCC': '#1B998B',
    'Africa': '#E8963E',
    'Asia': '#C73E1D',
    'North America': '#5C4D7D',
    'South America': '#8EAF3E',
}

# ── Sidebar filters ──────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🌍 Egyptian Cable Exports")
    st.markdown("**Interactive Dashboard**")
    st.markdown("HS Codes 854449 & 854460")
    st.markdown("Jan 2024 - Dec 2025")
    st.markdown("---")

    st.markdown("### Filters")

    all_regions = sorted(df_country['Region'].unique())
    selected_regions = st.multiselect(
        "Select Regions",
        options=all_regions,
        default=all_regions,
    )

    available_countries = sorted(df_country[df_country['Region'].isin(selected_regions)]['Country'].unique())
    selected_countries = st.multiselect(
        "Select Countries",
        options=available_countries,
        default=available_countries,
    )

    st.markdown("---")

    currency = st.radio("Currency", ["USD (Millions)", "EGP (Millions)"], index=0)
    usd_mode = currency.startswith("USD")

    val_2024 = 'M-USD 2024' if usd_mode else 'M-EGP 2024'
    val_2025 = 'M-USD 2025' if usd_mode else 'M-EGP 2025'
    val_total = 'Total M-USD' if usd_mode else 'Total M-EGP'
    currency_symbol = '$' if usd_mode else 'E£'
    currency_label = 'M-USD' if usd_mode else 'M-EGP'

    st.markdown("---")
    top_n = st.slider("Top N countries in charts", 5, 25, 12)

# Apply filters
mask = df_country['Region'].isin(selected_regions) & df_country['Country'].isin(selected_countries)
df_filtered = df_country[mask].copy()
df_region_filtered = df_filtered.groupby('Region').agg({
    val_2024: 'sum', val_2025: 'sum', val_total: 'sum', 'Country': 'count',
}).reset_index().rename(columns={'Country': 'Countries'})

# ── Header ───────────────────────────────────────────────────────────────────
st.markdown("# 🇪🇬 Egyptian Cable Exports Dashboard")

# ── KPI row ──────────────────────────────────────────────────────────────────
total_all = df_filtered[val_total].sum()
total_2024 = df_filtered[val_2024].sum()
total_2025 = df_filtered[val_2025].sum()
yoy_overall = ((total_2025 - total_2024) / total_2024 * 100) if total_2024 > 0 else 0
num_countries = df_filtered['Country'].nunique()
num_regions = df_filtered['Region'].nunique()
top_country = df_filtered.sort_values(val_total, ascending=False).iloc[0]['Country'] if len(df_filtered) > 0 else 'N/A'
top_country_val = df_filtered.sort_values(val_total, ascending=False).iloc[0][val_total] if len(df_filtered) > 0 else 0

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Total Exports", f"{currency_symbol}{total_all:,.2f}M")
k2.metric("2024 Exports", f"{currency_symbol}{total_2024:,.2f}M")
k3.metric("2025 Exports", f"{currency_symbol}{total_2025:,.2f}M", delta=f"{yoy_overall:+.1f}% YoY")
k4.metric("Markets", f"{num_countries} countries", delta=f"{num_regions} regions")
k5.metric("Top Market", top_country, delta=f"{currency_symbol}{top_country_val:,.1f}M")

st.markdown("")

# ── Tabs ─────────────────────────────────────────────────────────────────────
tab_overview, tab_regions, tab_countries, tab_compare, tab_data = st.tabs([
    "📊 Overview", "🌎 By Region", "🏳 By Country", "📈 Year Comparison", "📋 Data Table"
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1: OVERVIEW
# ══════════════════════════════════════════════════════════════════════════════
with tab_overview:
    col1, col2 = st.columns(2)

    with col1:
        fig_pie = px.pie(
            df_region_filtered, values=val_total, names='Region',
            title='Export Share by Region',
            color='Region', color_discrete_map=REGION_COLORS,
            hole=0.4,
        )
        fig_pie.update_traces(textinfo='percent+label', textfont_size=12)
        fig_pie.update_layout(height=420, margin=dict(t=50, b=20, l=20, r=20))
        st.plotly_chart(fig_pie, use_container_width=True, config=PLOTLY_CONFIG)

    with col2:
        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            name='2024', x=df_region_filtered['Region'], y=df_region_filtered[val_2024],
            marker_color='#2E86AB', text=df_region_filtered[val_2024].apply(lambda v: f'{currency_symbol}{v:,.1f}M'),
            textposition='outside', textfont_size=9,
        ))
        fig_bar.add_trace(go.Bar(
            name='2025', x=df_region_filtered['Region'], y=df_region_filtered[val_2025],
            marker_color='#E8963E', text=df_region_filtered[val_2025].apply(lambda v: f'{currency_symbol}{v:,.1f}M'),
            textposition='outside', textfont_size=9,
        ))
        fig_bar.update_layout(
            barmode='group', title='Regional Exports: 2024 vs 2025',
            yaxis_title=currency_label, height=420,
            margin=dict(t=50, b=20, l=60, r=20),
        )
        st.plotly_chart(fig_bar, use_container_width=True, config=PLOTLY_CONFIG)

    # Treemap
    st.markdown("#### Export Treemap - Region & Country Breakdown")
    df_tree = df_filtered[df_filtered[val_total] > 0].copy()
    if len(df_tree) > 0:
        fig_tree = px.treemap(
            df_tree, path=['Region', 'Country'], values=val_total,
            color='Region', color_discrete_map=REGION_COLORS,
            hover_data={val_2024: ':.2f', val_2025: ':.2f'},
        )
        fig_tree.update_layout(height=500, margin=dict(t=20, b=20, l=20, r=20))
        fig_tree.update_traces(textinfo='label+value+percent parent',
                               texttemplate='%{label}<br>%{value:.2f}M<br>%{percentParent:.1%}')
        st.plotly_chart(fig_tree, use_container_width=True, config=PLOTLY_CONFIG)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2: BY REGION
# ══════════════════════════════════════════════════════════════════════════════
with tab_regions:
    region_pick = st.selectbox("Select a region to explore", sorted(df_filtered['Region'].unique()))

    df_reg = df_filtered[df_filtered['Region'] == region_pick].sort_values(val_total, ascending=False)
    reg_total = df_reg[val_total].sum()
    reg_2024 = df_reg[val_2024].sum()
    reg_2025 = df_reg[val_2025].sum()
    reg_yoy = ((reg_2025 - reg_2024) / reg_2024 * 100) if reg_2024 > 0 else 0

    r1, r2, r3, r4 = st.columns(4)
    r1.metric(f"{region_pick} Total", f"{currency_symbol}{reg_total:,.2f}M")
    r2.metric("2024", f"{currency_symbol}{reg_2024:,.2f}M")
    r3.metric("2025", f"{currency_symbol}{reg_2025:,.2f}M", delta=f"{reg_yoy:+.1f}%")
    r4.metric("Countries", f"{len(df_reg)}")

    col1, col2 = st.columns(2)

    with col1:
        df_top = df_reg.head(top_n)
        fig_h = px.bar(
            df_top, x=val_total, y='Country', orientation='h',
            title=f'Top {min(top_n, len(df_top))} Countries in {region_pick}',
            color_discrete_sequence=[REGION_COLORS.get(region_pick, '#2E86AB')],
            text=df_top[val_total].apply(lambda v: f'{currency_symbol}{v:,.2f}M'),
        )
        fig_h.update_layout(yaxis={'categoryorder': 'total ascending'}, height=450,
                            margin=dict(t=50, b=20, l=10, r=20), xaxis_title=currency_label)
        fig_h.update_traces(textposition='outside', textfont_size=10)
        st.plotly_chart(fig_h, use_container_width=True, config=PLOTLY_CONFIG)

    with col2:
        df_top2 = df_reg.head(top_n)
        fig_comp = go.Figure()
        fig_comp.add_trace(go.Bar(
            name='2024', y=df_top2['Country'], x=df_top2[val_2024],
            orientation='h', marker_color='#2E86AB',
        ))
        fig_comp.add_trace(go.Bar(
            name='2025', y=df_top2['Country'], x=df_top2[val_2025],
            orientation='h', marker_color='#E8963E',
        ))
        fig_comp.update_layout(
            barmode='group', title=f'{region_pick}: 2024 vs 2025 by Country',
            yaxis={'categoryorder': 'total ascending'}, height=450,
            margin=dict(t=50, b=20, l=10, r=20), xaxis_title=currency_label,
        )
        st.plotly_chart(fig_comp, use_container_width=True, config=PLOTLY_CONFIG)

    # Region pie for country shares
    fig_reg_pie = px.pie(
        df_reg, values=val_total, names='Country',
        title=f'Country Share within {region_pick}',
        hole=0.35,
    )
    fig_reg_pie.update_traces(textinfo='percent+label', textfont_size=10)
    fig_reg_pie.update_layout(height=400, margin=dict(t=50, b=20))
    st.plotly_chart(fig_reg_pie, use_container_width=True, config=PLOTLY_CONFIG)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3: BY COUNTRY
# ══════════════════════════════════════════════════════════════════════════════
with tab_countries:
    country_pick = st.selectbox("Select a country", sorted(df_filtered['Country'].unique()))

    df_ctry = df_raw[(df_raw['Country'] == country_pick)].copy()
    ctry_val_2024 = 'M-USD 2024' if usd_mode else 'M-EGP 2024'
    ctry_val_2025 = 'M-USD 2025' if usd_mode else 'M-EGP 2025'
    ctry_val_total = 'Total M-USD' if usd_mode else 'Total M-EGP'

    ctry_total = df_ctry[ctry_val_total].sum()
    ctry_2024 = df_ctry[ctry_val_2024].sum()
    ctry_2025 = df_ctry[ctry_val_2025].sum()
    ctry_yoy = ((ctry_2025 - ctry_2024) / ctry_2024 * 100) if ctry_2024 > 0.001 else 0
    ctry_region = df_ctry['Region'].iloc[0] if len(df_ctry) > 0 else ''

    # Overall rank
    rank = df_country.sort_values(val_total, ascending=False).reset_index(drop=True)
    rank['Rank'] = range(1, len(rank)+1)
    country_rank = rank[rank['Country'] == country_pick]['Rank'].values
    country_rank = country_rank[0] if len(country_rank) > 0 else '-'

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Region", ctry_region)
    c2.metric("Total Exports", f"{currency_symbol}{ctry_total:,.2f}M")
    c3.metric("2024", f"{currency_symbol}{ctry_2024:,.2f}M")
    c4.metric("2025", f"{currency_symbol}{ctry_2025:,.2f}M", delta=f"{ctry_yoy:+.1f}%")
    c5.metric("Global Rank", f"#{country_rank}")

    col1, col2 = st.columns(2)

    with col1:
        fig_ctry = go.Figure(go.Bar(
            x=['2024', '2025'],
            y=[ctry_2024, ctry_2025],
            marker_color=['#2E86AB', '#E8963E'],
            text=[f'{currency_symbol}{ctry_2024:,.2f}M', f'{currency_symbol}{ctry_2025:,.2f}M'],
            textposition='outside',
        ))
        fig_ctry.update_layout(
            title=f'{country_pick}: Year-over-Year Exports',
            yaxis_title=currency_label, height=380,
            margin=dict(t=50, b=20, l=60, r=20),
        )
        st.plotly_chart(fig_ctry, use_container_width=True, config=PLOTLY_CONFIG)

    with col2:
        # Waterfall showing change
        fig_wf = go.Figure(go.Waterfall(
            x=['2024 Exports', 'Change', '2025 Exports'],
            y=[ctry_2024, ctry_2025 - ctry_2024, ctry_2025],
            measure=['absolute', 'relative', 'total'],
            text=[f'{currency_symbol}{ctry_2024:,.2f}M',
                  f'{currency_symbol}{ctry_2025-ctry_2024:+,.2f}M',
                  f'{currency_symbol}{ctry_2025:,.2f}M'],
            textposition='outside',
            connector_line_color='#888',
            increasing_marker_color='#2ecc71',
            decreasing_marker_color='#e74c3c',
            totals_marker_color='#d4af37',
        ))
        fig_wf.update_layout(
            title=f'{country_pick}: Export Value Waterfall',
            yaxis_title=currency_label, height=380,
            margin=dict(t=50, b=20, l=60, r=20),
        )
        st.plotly_chart(fig_wf, use_container_width=True, config=PLOTLY_CONFIG)

    # Breakdown by HS code for this country
    if len(df_ctry) > 1:
        st.markdown(f"#### {country_pick}: Breakdown by Product Line")
        df_ctry_agg = df_ctry.groupby(['HS Code', 'Unit']).agg({
            ctry_val_2024: 'sum', ctry_val_2025: 'sum', ctry_val_total: 'sum',
        }).reset_index().sort_values(ctry_val_total, ascending=False)

        fig_prod = px.bar(
            df_ctry_agg, x='HS Code', y=[ctry_val_2024, ctry_val_2025],
            barmode='group', title='Exports by HS Code & Year',
            labels={'value': currency_label, 'variable': 'Year'},
            color_discrete_map={ctry_val_2024: '#2E86AB', ctry_val_2025: '#E8963E'},
        )
        fig_prod.update_layout(height=350, margin=dict(t=50, b=20))
        st.plotly_chart(fig_prod, use_container_width=True, config=PLOTLY_CONFIG)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4: YEAR COMPARISON
# ══════════════════════════════════════════════════════════════════════════════
with tab_compare:
    st.markdown("#### Year-over-Year Growth Analysis")

    col1, col2 = st.columns(2)

    with col1:
        # Scatter: 2024 vs 2025
        fig_scatter = px.scatter(
            df_filtered, x=val_2024, y=val_2025,
            color='Region', color_discrete_map=REGION_COLORS,
            hover_name='Country', size=val_total,
            title='2024 vs 2025 Exports (bubble size = total)',
            labels={val_2024: f'2024 ({currency_label})', val_2025: f'2025 ({currency_label})'},
        )
        # Add diagonal reference line
        max_val = max(df_filtered[val_2024].max(), df_filtered[val_2025].max()) * 1.1
        fig_scatter.add_shape(type='line', x0=0, y0=0, x1=max_val, y1=max_val,
                              line=dict(dash='dash', color='gray', width=1))
        fig_scatter.add_annotation(x=max_val*0.85, y=max_val*0.75, text='Equal line',
                                   showarrow=False, font=dict(color='gray', size=10))
        fig_scatter.update_layout(height=480, margin=dict(t=50, b=20, l=60, r=20))
        st.plotly_chart(fig_scatter, use_container_width=True, config=PLOTLY_CONFIG)

    with col2:
        # Growth bar chart
        df_growth = df_filtered.copy()
        df_growth['Growth'] = df_growth['YoY Growth %']
        df_growth = df_growth.sort_values('Growth', ascending=True).tail(top_n)
        df_growth['Color'] = df_growth['Growth'].apply(lambda x: '#2ecc71' if x >= 0 else '#e74c3c')

        fig_growth = go.Figure(go.Bar(
            x=df_growth['Growth'], y=df_growth['Country'],
            orientation='h',
            marker_color=df_growth['Color'],
            text=df_growth['Growth'].apply(lambda v: f'{v:+.1f}%'),
            textposition='outside',
        ))
        fig_growth.update_layout(
            title=f'Top {top_n} Countries by YoY Growth %',
            xaxis_title='Growth %', height=480,
            margin=dict(t=50, b=20, l=10, r=60),
        )
        st.plotly_chart(fig_growth, use_container_width=True, config=PLOTLY_CONFIG)

    # New vs existing markets
    st.markdown("#### Market Dynamics")
    col1, col2 = st.columns(2)

    with col1:
        new_markets = df_filtered[(df_filtered[val_2024] < 0.001) & (df_filtered[val_2025] > 0)]
        if len(new_markets) > 0:
            fig_new = px.bar(
                new_markets.sort_values(val_2025, ascending=True),
                x=val_2025, y='Country', orientation='h',
                title='New Markets in 2025 (no 2024 exports)',
                color='Region', color_discrete_map=REGION_COLORS,
                text=new_markets[val_2025].apply(lambda v: f'{currency_symbol}{v:,.2f}M'),
            )
            fig_new.update_traces(textposition='outside')
            fig_new.update_layout(height=400, margin=dict(t=50, b=20, l=10, r=80))
            st.plotly_chart(fig_new, use_container_width=True, config=PLOTLY_CONFIG)
        else:
            st.info("No new markets found with current filters.")

    with col2:
        lost_markets = df_filtered[(df_filtered[val_2024] > 0) & (df_filtered[val_2025] < 0.001)]
        if len(lost_markets) > 0:
            fig_lost = px.bar(
                lost_markets.sort_values(val_2024, ascending=True),
                x=val_2024, y='Country', orientation='h',
                title='Markets with no 2025 exports',
                color='Region', color_discrete_map=REGION_COLORS,
                text=lost_markets[val_2024].apply(lambda v: f'{currency_symbol}{v:,.2f}M'),
            )
            fig_lost.update_traces(textposition='outside')
            fig_lost.update_layout(height=400, margin=dict(t=50, b=20, l=10, r=80))
            st.plotly_chart(fig_lost, use_container_width=True, config=PLOTLY_CONFIG)
        else:
            st.info("No lost markets found with current filters.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 5: DATA TABLE
# ══════════════════════════════════════════════════════════════════════════════
with tab_data:
    st.markdown("#### Detailed Country Data")
    st.markdown("Click column headers to sort. Use sidebar filters to narrow results.")

    df_display = df_filtered[['Region', 'Country', val_2024, val_2025, val_total, 'YoY Growth %']].copy()
    df_display.columns = ['Region', 'Country', f'2024 ({currency_label})', f'2025 ({currency_label})',
                          f'Total ({currency_label})', 'YoY Growth %']
    df_display = df_display.sort_values(f'Total ({currency_label})', ascending=False).reset_index(drop=True)
    df_display.index = df_display.index + 1
    df_display.index.name = 'Rank'

    st.dataframe(
        df_display.style.format({
            f'2024 ({currency_label})': '{:,.2f}',
            f'2025 ({currency_label})': '{:,.2f}',
            f'Total ({currency_label})': '{:,.2f}',
            'YoY Growth %': '{:+.1f}%',
        }),
        height=600,
        use_container_width=True,
        column_config={
            f'Total ({currency_label})': st.column_config.ProgressColumn(
                f'Total ({currency_label})',
                format='%.2f',
                min_value=0,
                max_value=float(df_display[f'Total ({currency_label})'].max()),
            ),
        },
    )

    # Download button
    csv = df_display.to_csv()
    st.download_button(
        label="Download filtered data as CSV",
        data=csv,
        file_name="egyptian_cable_exports_filtered.csv",
        mime="text/csv",
    )

    st.markdown("---")
    st.markdown("#### Raw Transaction Data")
    df_raw_filtered = df_raw[df_raw['Region'].isin(selected_regions) & df_raw['Country'].isin(selected_countries)]
    st.dataframe(df_raw_filtered, height=400, use_container_width=True)
