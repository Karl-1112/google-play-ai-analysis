import streamlit as st
import pandas as pd
from google_play_scraper import search, app
import plotly.express as px
import os

def show_methodology():
    with st.expander("查看【算法建模说明与数学公式】"):
        st.markdown("""
        ### 1. 市场拥挤度 (Market Crowding)
        **数学公式：**
        """)
        st.latex(r"Crowding = \frac{Total\ Apps}{Unique\ Developers}")
        st.write("""
        * **解释**：如果数值远大于 1（例如 1000 个应用只有 200 个开发者），说明少数开发者占据了大量位置，市场竞争异常激烈。
        """)

        st.markdown("---")
        st.markdown("### 2. 市场成熟度 (Market Maturity)")
        st.latex(r"Maturity = Median(Installs)")
        st.write("""
        * **解释**：中位数反映了市场 50% 的应用所处的水平。如果中位数非常大，说明该赛道已经被大公司/成熟应用占据，个人创业者进入门槛极高。
        """)

        st.markdown("---")
        st.markdown("### 3. 个人机会度 (Opportunity Score)")
        st.markdown("**数学逻辑：**")
        st.latex(r"Q1_{installs} = 25^{th}\ Percentile\ of\ Installs")
        st.latex(r"Condition: (Installs \le Q1_{installs}) \ \& \ (Rating \ge 4.2)")
        st.write("""
        * **解释**：我们特意避开了会被头部应用拉高的“中位数”，转而使用 **Q1（25%分位数）** 来寻找市场底部的“生存空间”。
        * **标准**：下载量处于后 25% 但评分却超过 4.2 的应用，代表了**“高质量、低竞争”**的利基市场，是个人或小团队的最佳切入点。
        """)

# --- 1. 页面配置 ---
st.set_page_config(page_title="AI 市场调研助手", layout="wide")
st.title("AI 应用市场大数据看板")

# --- 2. 数学建模分析函数 ---
def run_analysis_model(df):
    """
    数学建模：从抓取到的 DataFrame 中提取市场咨询指标
    """
    # 指标 1：市场拥挤度 (Crowding)
    app_count = len(df)
    developer_count = df["开发者"].nunique()
    crowding = round(app_count / developer_count, 2)

    # 指标 2：市场成熟度 (基于下载量中位数)
    median_installs = int(df["下载量"].median())

    # 指标 3：利基市场机会 (评分 > 4.2 且下载量在后 25%)
    q25_installs = df["下载量"].quantile(0.25)
    opportunity_apps = df[
        (df["下载量"] <= q25_installs) & 
        (df["评分"] >= 4.2)
    ]
    
    return {
        "app_count": app_count,
        "dev_count": developer_count,
        "crowding": crowding,
        "median_installs": median_installs,
        "opp_count": len(opportunity_apps),
        "opp_list": opportunity_apps
    }

# --- 3. 爬虫核心功能 ---
def run_spider(keyword, num):
    st.info(f"正在抓取关于 '{keyword}' 的数据，请稍候...")
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
                "发布日期": detail.get('released', '未知')
            })
        except:
            continue
        progress_bar.progress((i + 1) / len(results))
    
    df = pd.DataFrame(apps_data)
    # 保存本地缓存 (相对路径，兼容云端)
    df.to_csv("ai_apps.csv", index=False, encoding="utf-8-sig")
    return df

# --- 4. 侧边栏交互 ---
st.sidebar.header("配置选项")
search_kw = st.sidebar.text_input("搜索关键词", "AI Chatbot")
search_num = st.sidebar.slider("抓取数量", 10, 100, 30)
click_scrape = st.sidebar.button("立即更新数据")

# --- 5. 数据加载逻辑 ---
df = None

# 如果点击按钮或本地无文件，触发爬虫
if click_scrape or not os.path.exists("ai_apps.csv"):
    df = run_spider(search_kw, search_num)
else:
    try:
        df = pd.read_csv("ai_apps.csv")
        if df.empty:
            st.warning("本地数据文件为空，请点击左侧按钮抓取。")
            df = None
    except:
        st.warning("尚未获取数据，请点击左侧按钮。")
        df = None

# --- 6. 执行分析与界面展示 ---
if df is not None:
    # 运行数学模型
    metrics = run_analysis_model(df)
    
    # A. 核心咨询报告区
    st.markdown("---")
    st.header("💡 市场准入深度咨询报告")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("市场拥挤度", f"{metrics['crowding']}")
    c2.metric("下载中位数", f"{metrics['median_installs']:,}")
    c3.metric("潜力机会数", metrics['opp_count'])
    c4.metric("开发者总数", metrics['dev_count'])
    
    # 动态建议逻辑
    if metrics['crowding'] > 1.8:
        st.error("🔴 **市场极度拥挤**：大厂垄断明显，平均每个开发者拥有多个应用，不建议个人尝试该领域。")
    elif metrics['opp_count'] > 3:
        st.success("🟢 **发现蓝海机会**：存在评分高但下载量尚小的应用，说明细分需求未被满足，建议深入调研。")
    else:
        st.warning("🟡 **市场观望**：成熟度较高，竞争环境平稳，需寻找极其独特的差异化切入点。")

    # B. 潜力黑马表
    with st.expander("查看【个人机会】潜力黑马名单"):
        st.write("这些应用拥有极佳的用户口碑（评分>4.2），但目前的市场渗透率较低（下载量处于后25%）：")
        st.table(metrics['opp_list'][["名称", "评分", "下载量"]].sort_values(by="评分", ascending=False).head(10))

    # C. 可视化分析区
    st.markdown("---")
    st.subheader("市场竞争象限分析")
    
    fig_qx = px.scatter(
        df, x="下载量", y="评分", 
        hover_name="名称", 
        log_x=True, 
        color="评分",
        template="plotly_white",
        title="横轴: 下载规模 (对数) | 轴轴: 用户评分"
    )
    fig_qx.add_hline(y=4.2, line_dash="dash", line_color="green", annotation_text="优质应用门槛")
    st.plotly_chart(fig_qx, use_container_width=True)

    # D. 详细数据展示区
    st.markdown("---")
    col_a, col_b = st.columns([2, 1])
    
    with col_a:
        st.subheader("应用评分分布")
        fig_hist = px.histogram(df, x="评分", nbins=15, color_discrete_sequence=['#636EFA'])
        st.plotly_chart(fig_hist, use_container_width=True)
    
    with col_b:
        st.subheader("数据概览")
        st.write(f"平均评分: {df['评分'].mean():.2f}")
        st.write(f"最大评论数: {df['评论数'].max():,}")
        csv_data = df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
        st.download_button("导出全量 CSV 报告", data=csv_data, file_name="ai_analysis_report.csv")

    st.subheader("详细原始数据表")
    st.dataframe(df, use_container_width=True)
    
    st.markdown("---")
    show_methodology()

else:
    st.info("请在左侧侧边栏输入关键词并点击『立即更新数据』开始分析。")

