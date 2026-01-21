import streamlit as st
import pandas as pd
from google_play_scraper import search, app
import plotly.express as px
import os

# --- 1. 页面配置 ---
st.set_page_config(page_title="AI 市场调研助手", layout="wide")
st.title("🚀 AI 应用市场大数据看板")

# --- 2. 爬虫核心功能 ---
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
    # 保存一份副本，防止下次进来报错
    df.to_csv("ai_apps.csv", index=False, encoding="utf-8-sig")
    return df

# --- 3. 侧边栏交互 ---
st.sidebar.header("配置选项")
search_kw = st.sidebar.text_input("搜索关键词", "AI Chatbot")
search_num = st.sidebar.slider("抓取数量", 10, 50, 20)
click_scrape = st.sidebar.button("立即更新数据")

# --- 4. 数据加载逻辑 ---
df = None

# 如果用户点击了按钮，或者本地还没有 csv 文件
if click_scrape or not os.path.exists("ai_apps.csv"):
    df = run_spider(search_kw, search_num)
else:
    # 尝试读取本地文件
    try:
        df = pd.read_csv("ai_apps.csv")
        if df.empty: # 如果文件是空的
            st.warning("本地数据文件为空，请点击左侧按钮抓取。")
            df = None
    except:
        st.warning("尚未获取数据，请点击左侧按钮。")
        df = None

# --- 5. 数据展示界面 ---
if df is not None:
    # KPI 指标
    col1, col2, col3 = st.columns(3)
    col1.metric("分析应用数", len(df))
    col2.metric("平均评分", f"{df['评分'].mean():.2f}")
    col3.metric("最高下载量", f"{df['下载量'].max():,}")

    # 图表：评分分布
    st.subheader("应用评分分布图")
    fig = px.histogram(df, x="评分", nbins=10, color_discrete_sequence=['#636EFA'])
    st.plotly_chart(fig, use_container_width=True)

    # 数据表
    st.subheader("详细数据表")
    st.dataframe(df, use_container_width=True)
    
    # 下载按钮
    csv_data = df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
    st.download_button("📥 导出分析报告 (CSV)", data=csv_data, file_name="ai_analysis.csv")