import streamlit as st
import pandas as pd
from google_play_scraper import search, app
import plotly.express as px
import os
from datetime import datetime

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

def show_methodology():
    """方法论折叠说明"""
    with st.expander("查看商业建模逻辑与决策方法论"):
        st.info("本模型旨在通过统计学手段，从海量应用中筛选出适合个人或轻量级团队切入的『蓝海赛道』。")
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.markdown("#### 1. 市场拥挤度 (Density)")
            st.latex(r"Density = \frac{N_{Apps}}{N_{Devs}}")
            st.caption("解释：衡量开发者矩阵排位程度。比值越高，个人入场获客成本越高。")
        with col_m2:
            st.markdown("#### 2. 市场成熟度 (Maturity)")
            st.latex(r"Maturity = \text{Med}(Installs)")
            st.caption("解释：中位数代表市场中坚力量。过高则意味着存量市场已被巨头统治。")
        st.markdown("---")
        st.markdown("#### 3. 个人机会度 (Opportunity)")
        st.latex(r"Target = \{ App \mid Installs \le Q1 \ \& \ Score \ge 4.2 \}")
        st.write("寻找口碑极好（Rating>4.2）但尚未破圈（下载量后25%）的明珠。")

def run_analysis_model(df):
    """数学建模分析"""
    app_count = len(df)
    developer_count = df["开发者"].nunique()
    crowding = round(app_count / developer_count, 2)
    median_installs = int(df["下载量"].median())
    q25_installs = df["下载量"].quantile(0.25)
    opportunity_apps = df[(df["下载量"] <= q25_installs) & (df["评分"] >= 4.2)]
    
    return {
        "app_count": app_count, "dev_count": developer_count,
        "crowding": crowding, "median_installs": median_installs,
        "opp_count": len(opportunity_apps), "opp_list": opportunity_apps
    }

def run_spider(keyword, num):
    """爬虫逻辑"""
    st.info(f"正在深度检索 '{keyword}' 的市场存量数据...")
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
        except: continue
        progress_bar.progress((i + 1) / len(results))
    df = pd.DataFrame(apps_data)
    df.to_csv("ai_apps.csv", index=False, encoding="utf-8-sig")
    return df

# --- 3. 侧边栏与数据流 ---
st.sidebar.title("AI 市场监测系统")
st.sidebar.markdown("---")
search_kw = st.sidebar.text_input("目标赛道关键词", "AI Chatbot")
search_num = st.sidebar.slider("样本抓取规模", 20, 150, 40)
click_scrape = st.sidebar.button("同步云端数据", use_container_width=True)

df = None
if click_scrape or not os.path.exists("ai_apps.csv"):
    df = run_spider(search_kw, search_num)
else:
    try:
        df = pd.read_csv("ai_apps.csv")
    except:
        st.sidebar.error("数据加载失败，请重新同步。")

# --- 4. 主界面展示 (UI 质感提升核心：Tabs) ---
if df is not None:
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
        if metrics['crowding'] > 1.8:
            st.error("🔴 **高风险区域**：开发者矩阵排位明显，新手入场获客成本极高，建议寻找更细分的切入点。")
        elif metrics['opp_count'] > 3:
            st.success("🟢 **蓝海机会窗**：发现高评分低下载应用。建议调研这些『潜力黑马』的功能差异化。")
        else:
            st.warning("🟡 **观望区域**：市场分布均匀，建议通过独特的技术壁垒或垂直行业深度结合再入场。")
        
        # 象限图
        fig_qx = px.scatter(df, x="下载量", y="评分", hover_name="名称", log_x=True, 
                          color="评分", size="评分数", template="plotly_white",
                          title="市场竞争象限 (气泡大小代表评分热度)")
        fig_qx.add_hline(y=4.2, line_dash="dash", line_color="green")
        st.plotly_chart(fig_qx, use_container_width=True)

    with tab2:
        st.subheader("分析维度：赛道迭代趋势")
        
        # 预处理：确保日期格式正确
        df_trend = df.copy()
        # 处理更新日期（通常是时间戳，需要转换）
        df_trend['更新日期_dt'] = pd.to_datetime(df_trend['更新日期'], unit='s', errors='coerce')
        df_trend['更新年份'] = df_trend['更新日期_dt'].dt.year
        
        # 处理发布日期
        df_trend['发布日期_dt'] = pd.to_datetime(df_trend['发布日期'], errors='coerce')
        df_trend['发布年份'] = df_trend['发布日期_dt'].dt.year

        # --- 布局：左右对比 ---
        col_t1, col_t2 = st.columns(2)
        
        with col_t1:
            st.write("**新应用入场年份**")
            release_count = df_trend.groupby('发布年份').size().reset_index(name='数量')
            fig_rel = px.bar(release_count, x='发布年份', y='数量', 
                           color_discrete_sequence=['#AB63FA'], title="各年份新上线应用数")
            st.plotly_chart(fig_rel, use_container_width=True)
            st.caption("注：搜索结果前排通常被23-24年的成熟产品占据，25年新品可能排在搜索结果后段。")

        with col_t2:
            st.write("**最近一次更新年份**")
            update_count = df_trend.groupby('更新年份').size().reset_index(name='数量')
            fig_upd = px.bar(update_count, x='更新年份', y='数量', 
                           color_discrete_sequence=['#00CC96'], title="应用最后维护时间分布")
            st.plotly_chart(fig_upd, use_container_width=True)
            st.caption("注：这里能反映市场活跃度，2025/2026年更新越多，说明竞争越激烈。")

        # --- 深度洞察说明 ---
        st.markdown("---")
        st.info("**深度咨询结论：**")
        
        # 逻辑判断：如果2025/2026更新占比高
        active_25_26 = len(df_trend[df_trend['更新年份'] >= 2025])
        active_rate = (active_25_26 / len(df_trend)) * 100
        
        st.write(f"在当前的样本中，有 **{active_rate:.1f}%** 的应用在 2025 年及以后进行过版本迭代。")
        if active_rate > 70:
            st.markdown("✅ **结论**：这是一个**『超高频竞争赛道』**。老应用通过 2025 年的疯狂更新死守排位，新玩家若无巨大创新，很难靠自然流量突围。")
        else:
            st.markdown("⚠️ **结论**：部分老应用已进入维护停滞期，这可能是你通过『功能迭代』实现弯道超车的机会点。")

    with tab3:
        st.subheader("全量样本观测站")
        st.dataframe(df, use_container_width=True)
        csv_data = df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
        st.download_button("导出分析报告 (.csv)", data=csv_data, file_name=f"{search_kw}_report.csv")

    st.markdown("---")
    show_methodology()

else:
    st.info("欢迎！请在左侧侧边栏输入你想调研的 AI 关键词，点击『同步云端数据』开启实时建模。")

