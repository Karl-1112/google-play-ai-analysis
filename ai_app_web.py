import streamlit as st
import pandas as pd
from google_play_scraper import search, app
import plotly.express as px
import os
from datetime import datetime
import requests

st.markdown("""
    <style>
    .stApp {
        background-color: #050505;
        color: #e0e0e0;
    }
    
    [data-testid="stWidgetLabel"], .stMarkdown p, label {
        color: #ffffff !important;
        font-weight: 500 !important;
    }

    [data-testid="stSidebar"] {
        background-color: #0d0d0d;
        border-right: 1px solid #333;
    }

    [data-testid="stMetricValue"] {
        color: #00ffcc !important; 
        text-shadow: 0 0 10px rgba(0,255,204,0.5);
    }
    
    h1, h2, h3 {
        color: #ffffff !important;
        text-shadow: 0 0 5px rgba(255,255,255,0.2);
    }
    </style>
    """, unsafe_allow_html=True)

#These are the essential functions -_-
def fetch_data_via_api(keyword, num):
    try:
        api_key = st.secrets["SERPAPI_KEY"]
    #somehow the API went wrong, dunno QaQ
        url = f"https://serpapi.com/search.json?engine=google_play&q={keyword}&store=apps&api_key={api_key}&hl=en&gl=us"
        
        st.info(f"Analyzing JSON Data Flow HAHA")
        response = requests.get(url, timeout=15)
        data = response.json()
        
        if "error" in data:
            st.error(f"API Wrong:{data['error']}")
            return pd.DataFrame()

    #okay so I tried recovering my route
        # the route is：data -> organic_results (list) -> [0] -> items (list)
        organic = data.get('organic_results', [])
        items = []
        if organic and isinstance(organic, list):
            items = organic[0].get('items', [])
        
    #and this is the second try if the first didn't work
        if not items:
            items = data.get('apps', [])

        processed_apps = []
        for item in items:
            raw_downloads = str(item.get('downloads', '0'))
            clean_downloads = "".join(filter(str.isdigit, raw_downloads))
            
            processed_apps.append({
                "Name": item.get('title', 'Unknown'),
                "Developer": item.get('author', 'Unknown Dev'),
                "Ratings": float(item.get('rating', 0.0)),
                "Rating Numbers": 0, # 搜索页若没提供 ratings_total，先设为0
                "Downloads": int(clean_downloads) if clean_downloads else 0,
                "Comment Numbers": 0,
                "Posting Date": "2024-06-01", 
                "Updating Date": 1735689600
            })

        df = pd.DataFrame(processed_apps)

        if not df.empty:
            st.success(f"Yeah! Successfully retrieved {len(df)} reliable data. `v`")
        else:
            st.warning("right route, maybe something wrong with API")
                
        return df

    except Exception as e:
        st.error(f"Wrong logic: {e}")
        return pd.DataFrame()
        
def show_methodology():
    with st.expander("See methodology"):
        st.info("This model uses statistical analysis to identify promising “blue ocean” opportunities that are accessible to individuals and small teams.")
        st.markdown("1. Market Density")
        st.latex(r"Density = \frac{N_{Apps}}{N_{Developers}}")
        st.write("""
        **Logic:** Measures the average number of applications maintained by each developer.
        **Business Insight:** A high ratio (e.g., 1.8+) may indicate that professional teams dominate the market through multi-product portfolios, making user acquisition more costly for individual developers.
        """)
        st.markdown("---")
        
        st.markdown("2. Market Maturity")
        st.latex(r"Maturity = \text{Median}(\text{Installs})")
        st.write("""
        **Logic:** Uses the median to reduce the influence of dominant market players.
        **Business Insight:** A high median suggests a mature market, where differentiation may be a more effective entry strategy.
        """)
        st.markdown("---")
        
        st.markdown("3. Niche Opportunity Score")
        st.latex(r"Target = \{ App \mid Installs \le Q1 \ \& \ Score \ge 4.2 \}")
        st.write("""
        **Logic:** Identifies apps in the first quartile (Q1) with ratings above 4.2.
        **Business Insight:** Highlights well-rated but underexposed apps, revealing opportunities for individual developers to learn from or outperform them.
        """)

def run_analysis_model(df):
    """Mathematics Model Analysis"""
    app_count = len(df)
    developer_count = df["Developer"].nunique()
    
    if developer_count > 0:
        crowding = round(app_count / developer_count, 2)
    else:
        crowding = 0  #um, this could also be 1, but I don't think it matters
        
    median_installs = int(df["Download Numbers"].median()) if not df.empty else 0
    q25_installs = df["Download Numbers"].quantile(0.25) if not df.empty else 0
    
    if not df.empty:
        opportunity_apps = df[(df["Download Numbers"] <= q25_installs) & (df["Ratings"] >= 4.2)]
    else:
        opportunity_apps = pd.DataFrame() 
    
    return {
        "app_count": app_count, "dev_count": developer_count,
        "crowding": crowding, "median_installs": median_installs,
        "opp_count": len(opportunity_apps), "opp_list": opportunity_apps
    }
    
def generate_tier_list(df):
    def categorize(row):
        installs = row['Download Numbers']
        score = row['Ratings']
        high_traffic = 1000000  
        high_score = 4.3       
        
        if installs >= high_traffic and score >= high_score:
            return "S-Dude this is Superior"
        elif installs < high_traffic and score >= high_score:
            return "A-This is gonna score a straight A"
        elif installs >= high_traffic and score < high_score:
            return "B-Gotta watch out"
        else:
            return "C-Duh, don't waste your time"
            
    df['Rates'] = df.apply(categorize, axis=1)
    return df

def get_color_styled_df(df):
    def apply_tier_style(val):
        if not isinstance(val, str): return ''
        if "S" in val: return 'color: #39ff14; font-weight: bold; text-shadow: 0 0 5px #39ff14;'
        if "A" in val: return 'color: #00f5ff; font-weight: bold; text-shadow: 0 0 5px #00f5ff;'
        if "B" in val: return 'color: #fff01f; font-weight: bold; text-shadow: 0 0 5px #fff01f;'
        if "C" in val: return 'color: #ff3131; font-weight: bold; text-shadow: 0 0 5px #ff3131;'
        return ''


    if 'Rates' not in df.columns:
        df = generate_tier_list(df)

    return df.style.map(apply_tier_style, subset=['Rates'])

def run_spider(keyword, num):
    st.info(f"Looking form '{keyword}' market data through python.")
    results = search(keyword, lang="en", country="us", n_hits=num)
    apps_data = []
    
    progress_bar = st.progress(0)
    for i, result in enumerate(results):
        try:
            detail = app(result['appId'], lang="en", country="us")
            apps_data.append({
                "Name": detail['title'],
                "Developer": detail['developer'],
                "Ratings": detail['score'],
                "Rating Numbers": detail['ratings'],
                "Comment Numbers": detail['reviews'],
                "Download Numbers": detail['minInstalls'],
                "Posting Date": detail.get('released', 'unknown'),
                "Updating Date": detail.get('updated', 0)
            })
        except:
            continue
        progress_bar.progress((i + 1) / len(results))
    
    df = pd.DataFrame(apps_data)
    
    if not df.empty:
        cols_to_fix = ['Download Numbers', 'Comment Numbers', 'Ratings', 'Rating Numbers']
        for col in cols_to_fix:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    else:
        st.warning("Unable to find usable data, please change your route")
        df = pd.DataFrame(columns=["Name", "Developer", "Ratings", "Rating Numbers", "Comment Numbers", "Download Numbers", "Posting Date", "Updating Date"])

    df.to_csv("ai_apps.csv", index=False, encoding="utf-8-sig")
    return df


st.sidebar.title("AI Looking Out for the Market")
st.sidebar.markdown("---")
search_kw = st.sidebar.text_input("Keywords", "AI Chatbot")
search_num = st.sidebar.slider("Size of Data scraped", 20, 150, 40)


data_source = st.sidebar.selectbox("Change your route", ["Python", "API"])

click_scrape = st.sidebar.button("Update", use_container_width=True)

df = None


if click_scrape:
    if data_source == "API":
        df = fetch_data_via_api(search_kw, search_num)
    else:
        df = run_spider(search_kw, search_num)
elif os.path.exists("ai_apps.csv"):
    try:
        df = pd.read_csv("ai_apps.csv")
    except:
        st.sidebar.error("Oops, not working.")

if df is not None and not df.empty:
    st.title(f" {search_kw} ")
    show_methodology() 
    metrics = run_analysis_model(df)

    metrics = run_analysis_model(df)
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Market density", metrics['crowding'], delta="Density", delta_color="inverse")
    kpi2.metric("Download medians", f"{metrics['median_installs']:,}", delta="Maturity")
    kpi3.metric("Possibility numbers", metrics['opp_count'], delta="Niche App")
    kpi4.metric("Covered developers", metrics['dev_count'], delta="Players")

    tab1, tab2, tab3 = st.tabs(["decision advice", "growing trend", "basic data"])

    with tab1:
        st.subheader("Startup Analysis")
        
        df_plot = df.copy()
        if 'Rating Numbers' in df_plot.columns:
            df_plot['Rating Numbers'] = pd.to_numeric(df_plot['Rating Numbers'], errors='coerce').fillna(0)
            df_plot['size'] = df_plot['Rating Numbers'].apply(lambda x: x if x > 0 else 0.1)
        else:
            df_plot['Rating Numbers'] = 0
            df_plot['size'] = 0.1

        if metrics['crowding'] > 1.8:
            st.error("🔴oops, dense")
        elif metrics['opp_count'] > 3:
            st.success("🟢still got a chance")
        else:
            st.warning("🟡watch out for density signals")
        
        if 'Ratings' in df_plot.columns and 'Download Numbers' in df_plot.columns:
            fig_qx = px.scatter(
                df_plot,
                x="Download Numbers", 
                y="Ratings", 
                hover_name="Name", 
                log_x=True, 
                color="Ratings", 
                size="size",
                template="plotly_white",
                title="Market competition quadrat",
                hover_data={"Comment Numbers": True, "size": False} 
            )
            fig_qx.add_hline(y=4.2, line_dash="dash", line_color="green")
            st.plotly_chart(fig_qx, use_container_width=True)

    with tab2:
        st.subheader("Analyze different Aspects")
        
        df_trend = df.copy()

        # We also gotta look out for updates
        if 'Updating Date' in df_trend.columns and df_trend['Updating Date'].iloc[0] != 0:
            df_trend['Updating Date_dt'] = pd.to_datetime(df_trend['Updating Date'], unit='s', errors='coerce')
            df_trend['Updating Date'] = df_trend['Updating Date_dt'].dt.year
        else:
            df_trend['Updating Date'] = "No Data"

        if 'Posting Date' in df_trend.columns and df_trend['Posting Date'].iloc[0] != "Unknown":
            df_trend['Posting Date_dt'] = pd.to_datetime(df_trend['Posting Date'], errors='coerce')
            df_trend['Posting Year'] = df_trend['Posting Date_dt'].dt.year
        else:
            df_trend['Posting Year'] = "Unknown"

        col_t1, col_t2 = st.columns(2)
        
        with col_t1:
            st.write("**Year for New APPs**")
            if 'Posting Year' in df_trend.columns and df_trend['Posting Year'].dtype != 'O': 
                release_count = df_trend.groupby('Posting Year').size().reset_index(name='Number')
                fig_rel = px.bar(release_count, x='Posting Year', y='Number', color_discrete_sequence=['#AB63FA'])
                st.plotly_chart(fig_rel, use_container_width=True)
            else:
                st.info("Unknown. API does not have related data.")

        with col_t2:
            st.write("**Recent updates**")
            if 'Updating Year' in df_trend.columns and df_trend['Updating Year'].dtype != 'O':
                update_count = df_trend.groupby('Updating Year').size().reset_index(name='Number')
                fig_upd = px.bar(update_count, x='Updating Year', y='Number', color_discrete_sequence=['#00CC96'])
                st.plotly_chart(fig_upd, use_container_width=True)
            else:
                st.info("Unknown. API does not have related data.")

    with tab3:
        st.subheader("Complete Data set")
    
        styled_df = get_color_styled_df(df)
    
        st.dataframe(
            styled_df,
            use_container_width=True,
            column_config={
                "Name": st.column_config.TextColumn("APP Name"),
                "Download Number": st.column_config.NumberColumn("Downloads", format="%d 📥"),
                "Ratings": st.column_config.ProgressColumn("Ratings by Users", min_value=0, max_value=5, format="%.1f ⭐"),
            }
        )

elif df is not None and df.empty:
    st.warning("Did not find data, please check API.")

else:
    st.info("Welcome to the AI APP Analysis Website!")

