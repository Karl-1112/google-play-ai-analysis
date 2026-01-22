import streamlit as st
import pandas as pd
from google_play_scraper import search, app
import plotly.express as px
import os
from datetime import datetime
import requests

# --- 1. 页面配置与美化 ---
st.set_page_config(page_title="AI 市场智库", layout="wide", initial_sidebar_state="expanded")
# 荧光深色主题注入
st.markdown("""
    <style>
    /* 全局背景与文字 */
    .stApp {
        background-color: #050505;
        color: #e0e0e0;
    }
    
    /* 侧边栏 */
    [data-testid="stSidebar"] {
        background-color: #0d0d0d;
        border-right: 1px solid #333;
    }

    /* 指标卡片美化 */
    [data-testid="stMetricValue"] {
        color: #00ffcc !important; /* 荧光青 */
        text-shadow: 0 0 10px rgba(0,255,204,0.5);
    }
    
    /* 标题颜色 */
    h1, h2, h3 {
        color: #ffffff !important;
        letter-spacing: 1px;
    }
    
    /* 自定义荧光标签样式 */
    .highlight-s { color: #39ff14; font-weight: bold; text-shadow: 0 0 5px #39ff14; } /* 荧光绿 */
    .highlight-a { color: #00f5ff; font-weight: bold; text-shadow: 0 0 5px #00f5ff; } /* 荧光蓝 */
    .highlight-b { color: #fff01f; font-weight: bold; text-shadow: 0 0 5px #fff01f; } /* 荧光黄 */
    .highlight-c { color: #ff3131; font-weight: bold; text-shadow: 0 0 5px #ff3131; } /* 霓虹红 */
    </style>
    """, unsafe_allow_html=True)

# 注入一点自定义 CSS，让指标卡片更醒目
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 28px; color: #007bff; }
    .main { background-color: #f8f9fa; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心函数定义 ---
def fetch_data_via_api(keyword, num):
    try:
        api_key = st.secrets["SERPAPI_KEY"]
        url = f"https://serpapi.com/search.json?engine=google_play&q={keyword}&store=apps&api_key={api_key}&hl=en&gl=us"
        
        st.info(f"🚀 正在深度解析 JSON 数据流...")
        response = requests.get(url, timeout=15)
        data = response.json()
        
        if "error" in data:
            st.error(f"❌ API 报错: {data['error']}")
            return pd.DataFrame()

        # --- [关键修复]：根据你的 JSON 结构重新定位路径 ---
        # 路径是：data -> organic_results (list) -> [0] -> items (list)
        organic = data.get('organic_results', [])
        items = []
        if organic and isinstance(organic, list):
            items = organic[0].get('items', [])
        
        # 如果上面没找到，尝试备选路径
        if not items:
            items = data.get('apps', [])

        processed_apps = []
        for item in items:
            # 提取下载量字段 'downloads'，并清洗非数字字符
            raw_downloads = str(item.get('downloads', '0'))
            clean_downloads = "".join(filter(str.isdigit, raw_downloads))
            
            processed_apps.append({
                "名称": item.get('title', 'Unknown'),
                "开发者": item.get('author', 'Unknown Dev'),
                "评分": float(item.get('rating', 0.0)),
                "评分数": 0, # 搜索页若没提供 ratings_total，先设为0
                "下载量": int(clean_downloads) if clean_downloads else 0,
                "评论数": 0,
                "发布日期": "2024-06-01", # 搜索页不带日期，设为去年中旬作为基准
                "更新日期": 1735689600
            })

        df = pd.DataFrame(processed_apps)

        if not df.empty:
            st.success(f"✅ 成功！已抓取到 {len(df)} 个真实应用数据。")
            # 调试完可以把下面这行删掉
            # st.write("前三条解析样板：", df.head(3)) 
        else:
            st.warning("⚠️ 路径正确但 items 列表为空，请检查 SerpApi 额度。")
                
        return df

    except Exception as e:
        st.error(f"🚨 解析逻辑崩溃: {e}")
        return pd.DataFrame()
        
def show_methodology():
    with st.expander("查看商业建模逻辑与决策方法论"):
        st.info("本模型旨在通过统计学手段，从海量应用中筛选出适合个人或轻量级团队切入的『蓝海赛道』。")
        
        st.markdown("### 1. 市场拥挤度 (Market Density)")
        st.latex(r"Density = \frac{N_{Apps}}{N_{Developers}}")
        st.write("""
        * **逻辑**：衡量平均每个开发者维护的应用数。
        * **商业洞察**：比值过高（如 1.8+）意味着职业团队在利用矩阵产品占位，个人获客成本高。
        """)
        st.markdown("---")
        
        st.markdown("### 2. 市场成熟度 (Market Maturity)")
        st.latex(r"Maturity = \text{Median}(\text{Installs})")
        st.write("""
        * **逻辑**：使用中位数排除巨头干扰。
        * **商业洞察**：中位数过高说明是存量市场，适合差异化切入。
        """)
        st.markdown("---")
        
        st.markdown("### 3. 个人机会度 (Niche Opportunity Score)")
        st.latex(r"Target = \{ App \mid Installs \le Q1 \ \& \ Score \ge 4.2 \}")
        st.write("""
        * **逻辑**：锚定 Q1 (25% 分位数) 且评分 > 4.2 的应用。
        * **商业洞察**：寻找口碑好但尚未推广开的明珠，适合个人开发者模仿或超越。
        """)

def run_analysis_model(df):
    """数学建模分析 (修复除以零报错版)"""
    app_count = len(df)
    developer_count = df["开发者"].nunique()
    
    # --- [修复点] 增加除数检查 ---
    if developer_count > 0:
        crowding = round(app_count / developer_count, 2)
    else:
        crowding = 0  # 或者设为 1，避免报错
        
    median_installs = int(df["下载量"].median()) if not df.empty else 0
    q25_installs = df["下载量"].quantile(0.25) if not df.empty else 0
    
    # 避免空数据导致报错
    if not df.empty:
        opportunity_apps = df[(df["下载量"] <= q25_installs) & (df["评分"] >= 4.2)]
    else:
        opportunity_apps = pd.DataFrame() # 空表
    
    return {
        "app_count": app_count, "dev_count": developer_count,
        "crowding": crowding, "median_installs": median_installs,
        "opp_count": len(opportunity_apps), "opp_list": opportunity_apps
    }
    
def generate_tier_list(df):
    """【补充：评级逻辑】根据下载量和评分，给应用打上 S/A/B/C 评级标签"""
    def categorize(row):
        installs = row['下载量']
        score = row['评分']
        # 门槛设定 (根据你的截图，下载量中位数很大，我们设定为 100万)
        high_traffic = 1000000  
        high_score = 4.3       
        
        if installs >= high_traffic and score >= high_score:
            return "👑 S级 (王者)"
        elif installs < high_traffic and score >= high_score:
            return "💎 A级 (潜力)"
        elif installs >= high_traffic and score < high_score:
            return "⚠️ B级 (风险)"
        else:
            return "🌑 C级 (末流)"
            
    df['评级'] = df.apply(categorize, axis=1)
    return df

def get_color_styled_df(df):
    """【美化函数】为数据框应用荧光色样式"""
    def apply_tier_style(val):
        if not isinstance(val, str): return ''
        if "S级" in val: return 'color: #39ff14; font-weight: bold; text-shadow: 0 0 5px #39ff14;'
        if "A级" in val: return 'color: #00f5ff; font-weight: bold; text-shadow: 0 0 5px #00f5ff;'
        if "B级" in val: return 'color: #fff01f; font-weight: bold; text-shadow: 0 0 5px #fff01f;'
        if "C级" in val: return 'color: #ff3131; font-weight: bold; text-shadow: 0 0 5px #ff3131;'
        return ''

    # 确保'评级'列存在
    if '评级' not in df.columns:
        df = generate_tier_list(df)

    return df.style.map(apply_tier_style, subset=['评级'])

def run_spider(keyword, num):
    st.info(f"正在深度检索 '{keyword}' 的市场存量数据 (爬虫模式)...")
    results = search(keyword, lang="en", country="us", n_hits=num)
    apps_data = []
    
    progress_bar = st.progress(0)
    for i, result in enumerate(results):
        try:
            detail = app(result['appId'], lang="en", country="us")
            apps_data.append({
                "名称": detail['title'],
                "开发者": detail['developer'],
                "评分": detail['score'],
                "评分数": detail['ratings'],
                "评论数": detail['reviews'],
                "下载量": detail['minInstalls'],
                "发布日期": detail.get('released', '未知'),
                "更新日期": detail.get('updated', 0)
            })
        except:
            continue
        progress_bar.progress((i + 1) / len(results))
    
    # --- 数据加固与清洗 ---
    df = pd.DataFrame(apps_data)
    
    if not df.empty:
        cols_to_fix = ['下载量', '评分数', '评分', '评论数']
        for col in cols_to_fix:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    else:
        st.warning("未能抓取到有效数据，请尝试更换关键词。")
        df = pd.DataFrame(columns=["名称", "开发者", "评分", "评分数", "评论数", "下载量", "发布日期", "更新日期"])

    df.to_csv("ai_apps.csv", index=False, encoding="utf-8-sig")
    return df

# --- 3. 侧边栏与数据流 ---
st.sidebar.title("AI 市场监测系统")
st.sidebar.markdown("---")
search_kw = st.sidebar.text_input("目标赛道关键词", "AI Chatbot")
search_num = st.sidebar.slider("样本抓取规模", 20, 150, 40)

# [新增] 数据源选择
data_source = st.sidebar.selectbox("数据源切换", ["基础爬虫 (免费)", "高级 API (高质量)"])

click_scrape = st.sidebar.button("同步云端数据", use_container_width=True)

df = None

# [逻辑修改] 根据按钮点击和选择的数据源来决定执行哪个函数
if click_scrape:
    if data_source == "高级 API (高质量)":
        df = fetch_data_via_api(search_kw, search_num)
    else:
        df = run_spider(search_kw, search_num)
elif os.path.exists("ai_apps.csv"):
    # 如果没点击按钮但有本地缓存，则读取缓存
    try:
        df = pd.read_csv("ai_apps.csv")
    except:
        st.sidebar.error("缓存数据加载失败，请重新同步。")

# --- 4. 主界面展示 ---
if df is not None and not df.empty:
    st.title(f"📊 {search_kw} 市场准入深度分析")
    
    # 顶部 KPI 指标卡
    metrics = run_analysis_model(df)
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("市场拥挤度", metrics['crowding'], delta="Density", delta_color="inverse")
    kpi2.metric("下载中位数", f"{metrics['median_installs']:,}", delta="Maturity")
    kpi3.metric("机会应用数", metrics['opp_count'], delta="Niche App")
    kpi4.metric("覆盖开发者", metrics['dev_count'], delta="Players")

    # 创建标签页
    tab1, tab2, tab3 = st.tabs(["决策建议", "增长趋势", "原始数据"])

    with tab1:
        st.subheader("市场准入评估")
        
        # 绘图前的数据清洗 (针对 Plotly size 参数)
        df_plot = df.copy()
        if '评分数' in df_plot.columns:
            df_plot['评分数'] = pd.to_numeric(df_plot['评分数'], errors='coerce').fillna(0)
            df_plot['展示尺寸'] = df_plot['评分数'].apply(lambda x: x if x > 0 else 0.1)
        else:
            df_plot['评分数'] = 0
            df_plot['展示尺寸'] = 0.1

        if metrics['crowding'] > 1.8:
            st.error("🔴 **高风险区域**：开发者矩阵排位明显，新手入场获客成本极高，建议寻找更细分的切入点。")
        elif metrics['opp_count'] > 3:
            st.success("🟢 **蓝海机会窗**：发现高评分低下载应用。建议调研这些『潜力黑马』的功能差异化。")
        else:
            st.warning("🟡 **观望区域**：市场分布均匀，建议通过独特的技术壁垒或垂直行业深度结合再入场。")
        
        # 象限图
        if '评分' in df_plot.columns and '下载量' in df_plot.columns:
            fig_qx = px.scatter(
                df_plot,
                x="下载量", 
                y="评分", 
                hover_name="名称", 
                log_x=True, 
                color="评分", 
                size="展示尺寸",
                template="plotly_white",
                title="市场竞争象限 (气泡大小代表评分热度)",
                hover_data={"评分数": True, "展示尺寸": False} 
            )
            fig_qx.add_hline(y=4.2, line_dash="dash", line_color="green")
            st.plotly_chart(fig_qx, use_container_width=True)

    with tab2:
        st.subheader("分析维度：赛道迭代趋势")
        
        # 注意：API 模式下可能没有发布日期或更新日期，做兼容处理
        df_trend = df.copy()
        
        # 检查是否有更新日期列
        if '更新日期' in df_trend.columns and df_trend['更新日期'].iloc[0] != 0:
            df_trend['更新日期_dt'] = pd.to_datetime(df_trend['更新日期'], unit='s', errors='coerce')
            df_trend['更新年份'] = df_trend['更新日期_dt'].dt.year
        else:
            df_trend['更新年份'] = "无数据"

        # 检查是否有发布日期列
        if '发布日期' in df_trend.columns and df_trend['发布日期'].iloc[0] != "未知":
            df_trend['发布日期_dt'] = pd.to_datetime(df_trend['发布日期'], errors='coerce')
            df_trend['发布年份'] = df_trend['发布日期_dt'].dt.year
        else:
            df_trend['发布年份'] = "无数据"

        col_t1, col_t2 = st.columns(2)
        
        with col_t1:
            st.write("**新应用入场年份**")
            if '发布年份' in df_trend.columns and df_trend['发布年份'].dtype != 'O': # 检查是否为数字类型
                release_count = df_trend.groupby('发布年份').size().reset_index(name='数量')
                fig_rel = px.bar(release_count, x='发布年份', y='数量', color_discrete_sequence=['#AB63FA'])
                st.plotly_chart(fig_rel, use_container_width=True)
            else:
                st.info("当前数据源暂未提供发布日期信息（API 模式可能不包含此数据）。")

        with col_t2:
            st.write("**最近一次更新年份**")
            if '更新年份' in df_trend.columns and df_trend['更新年份'].dtype != 'O':
                update_count = df_trend.groupby('更新年份').size().reset_index(name='数量')
                fig_upd = px.bar(update_count, x='更新年份', y='数量', color_discrete_sequence=['#00CC96'])
                st.plotly_chart(fig_upd, use_container_width=True)
            else:
                st.info("当前数据源暂未提供更新日期信息。")

    with tab3:
        st.subheader("全量样本：黑金数据终端")
    
        # 假设 df 已经包含了之前计算的'评级'列
        styled_df = get_color_styled_df(df)
    
        st.dataframe(
            styled_df,
            use_container_width=True,
            column_config={
                "名称": st.column_config.TextColumn("应用名"),
                "下载量": st.column_config.NumberColumn("下载量", format="%d 📥"),
                "评分": st.column_config.ProgressColumn("用户满意度", min_value=0, max_value=5, format="%.1f ⭐"),
                "评级": st.column_config.TextColumn("商业价值评级"),
            }
        )

elif df is not None and df.empty:
    st.warning("未找到有效数据，请检查关键词或 API 配额。")

else:
    st.info("欢迎！请在左侧侧边栏输入你想调研的 AI 关键词，点击『同步云端数据』开启实时建模。")
