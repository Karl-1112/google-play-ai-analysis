import streamlit as st
import pandas as pd
from google_play_scraper import search, app
import plotly.express as px
import os
from datetime import datetime
import requests

# --- 1. 页面配置与美化 ---
st.set_page_config(page_title="AI 市场智库", layout="wide", initial_sidebar_state="expanded")

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
        # 增加 num 参数给 API，确保它返回足够多的数据页
        url = f"https://serpapi.com/search.json?engine=google_play&q={keyword}&store=apps&api_key={api_key}&hl=en&gl=us&num={num}"
        
        st.info(f"高级 API 正在全力检索 '{keyword}' ...")
        response = requests.get(url)
        data = response.json()
        
        # 检查 API 是否返回了错误（如 Key 错误或欠费）
        if "error" in data:
            st.error(f"❌ API 报错: {data['error']}")
            return pd.DataFrame()

        # --- 核心修复：多字段兼容抓取 ---
        # SerpApi 的数据可能藏在 'organic_results' 或 'apps' 字段中
        items = data.get('organic_results', [])
        if not items:
            items = data.get('apps', []) # 备选字段
            
        processed_apps = []
        for item in items:
            # 这里的提取逻辑更加健壮，增加了默认值
            processed_apps.append({
                "名称": item.get('title', 'Unknown App'),
                "开发者": item.get('author', item.get('developer', 'Unknown Dev')),
                "评分": item.get('rating', 0.0),
                "评分数": item.get('ratings_total', item.get('reviews', 0)),
                "下载量": item.get('installs', '0'), 
                "评论数": item.get('reviews', 0),
                "发布日期": item.get('released', '2025-01-01'), # API 有时在 detail 中才给，这里给个保底
                "更新日期": 1735689600 # 2025-01-01 的时间戳，作为保底
            })
        
        df = pd.DataFrame(processed_apps)
        
        if not df.empty:
            # 清洗下载量：将 "5,000,000+" 转化为 5000000
            df['下载量'] = df['下载量'].astype(str).str.replace(r'[^\d]', '', regex=True)
            df['下载量'] = pd.to_numeric(df['下载量'], errors='coerce').fillna(0)
            
            # 清洗评分和评分数
            df['评分'] = pd.to_numeric(df['评分'], errors='coerce').fillna(0.0)
            df['评分数'] = pd.to_numeric(df['评分数'], errors='coerce').fillna(0)
            
            st.success(f"✅ 成功抓取到 {len(df)} 条深度数据！")
        else:
            st.warning("⚠️ API 返回了空列表，请检查关键词或尝试增加样本规模。")
            
        return df
    except Exception as e:
        st.error(f"🚨 致命错误: {e}")
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
        st.subheader("全量样本观测站")
        st.dataframe(df, use_container_width=True)
        csv_data = df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
        st.download_button("导出分析报告 (.csv)", data=csv_data, file_name=f"{search_kw}_report.csv")

    st.markdown("---")
    show_methodology()

elif df is not None and df.empty:
    st.warning("未找到有效数据，请检查关键词或 API 配额。")

else:
    st.info("欢迎！请在左侧侧边栏输入你想调研的 AI 关键词，点击『同步云端数据』开启实时建模。")



