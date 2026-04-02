
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import os
import sys
import argparse

# Append current directory to path to allow import
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
try:
    from Dashboard_Step2_Conversion import analyze_conversion
except ImportError:
    print("Warning: Could not import Dashboard_Step2_Conversion.py")
    analyze_conversion = None

# Set style for charts - using a built-in style that supports Chinese characters might be tricky
# so we'll try to use a default and handle fonts if possible, or just use English labels for safety
plt.style.use('ggplot')
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'sans-serif'] # Try to support Chinese on MacOS/Windows
plt.rcParams['axes.unicode_minus'] = False

def load_data(filepath):
    df = pd.read_csv(filepath)
    # Ensure start_time is datetime
    df['start_time'] = pd.to_datetime(df['start_time'])
    if 'end_time' in df.columns:
        df['end_time'] = pd.to_datetime(df['end_time'])
    return df

def generate_html_report(df, scale_fig, scenario_fig, marginal_fig, daily_fig, stats_html, scale_insights, scenario_insights, marginal_insights, daily_insights, output_file='dashboard_report.html'):
    # Derive title from output filename if possible, otherwise default
    title = "直播业务仪表盘 (Live Stream Economic Dashboard)"
    if output_file:
        basename = os.path.basename(output_file)
        # Expected format: Dashboard_Filename.html
        if basename.startswith("Dashboard_") and basename.endswith(".html"):
            raw_name = basename[10:-5] # Remove prefix and suffix
            title = f"{raw_name} - 直播业务仪表盘"
            
    report_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            max-width: 1200px;
            margin: 0 auto;
            padding: 40px 20px;
            color: #24292e;
            background-color: #ffffff;
        }}
        h1 {{ 
            border-bottom: 1px solid #eaecef; 
            padding-bottom: 0.3em; 
            color: #24292e;
        }}
        h2 {{ 
            color: #0366d6; 
            margin-top: 30px; 
            margin-bottom: 15px;
        }}
        .stats-container {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            background-color: #f6f8fa;
            padding: 20px;
            border-radius: 6px;
            border: 1px solid #e1e4e8;
            margin-bottom: 30px;
        }}
        .stat-box {{
            padding: 10px;
        }}
        .stat-box h3 {{
            margin-top: 0;
            font-size: 1.1em;
            color: #24292e;
            border-bottom: 1px solid #eaecef;
            padding-bottom: 8px;
        }}
        .stat-box ul {{
            padding-left: 20px;
            margin: 10px 0;
        }}
        .chart-container {{
            margin: 20px 0; 
            border: 1px solid #e1e4e8; 
            border-radius: 6px;
            padding: 20px;
            background-color: #ffffff;
        }}
        .analysis-text {{
            background-color: #ffffff;
            border-left: 4px solid #0366d6;
            padding: 15px;
            margin-top: 15px;
            border-radius: 4px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 10px 0;
        }}
        th, td {{
            padding: 8px 12px;
            border: 1px solid #dfe2e5;
        }}
        th {{
            background-color: #f6f8fa;
        }}
    </style>
</head>
<body>

<h1>{title}</h1>
<p style="color: #586069;">Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

<div class="stats-container">
    {stats_html}
</div>

<h2>1. 规模敏感性分析 (Scale Sensitivity)</h2>
<div class="chart-container">
    {scale_fig.to_html(full_html=False, include_plotlyjs='cdn')}
    <div class="analysis-text">
        <strong>分析结论：</strong><br>
        {scale_insights}
    </div>
</div>

<h2>2. 场景差异分析 (Scenario: Promotion vs Daily)</h2>
<div class="chart-container">
    {scenario_fig.to_html(full_html=False, include_plotlyjs=False)}
    <div class="analysis-text">
        <strong>分析结论：</strong><br>
        {scenario_insights}
    </div>
</div>

<h2>3. 投放边际收益分析 (Marginal Return)</h2>
<div class="chart-container">
    {marginal_fig.to_html(full_html=False, include_plotlyjs=False)}
    <div class="analysis-text">
        <strong>分析结论：</strong><br>
        {marginal_insights}
    </div>
</div>

<h2>4. 每日表现分析 (Daily Performance)</h2>
<div class="chart-container">
    {daily_fig.to_html(full_html=False, include_plotlyjs=False)}
    <div class="analysis-text">
        <strong>分析结论：</strong><br>
        {daily_insights}
    </div>
</div>

</body>
</html>
    """
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report_content)
    print(f"HTML Report generated: {os.path.abspath(output_file)}")

def scale_sensitivity_analysis_plotly(df):
    # Scatter plot with Plotly
    fig = px.scatter(df, 
                     x='曝光人数', 
                     y='unique_leads', 
                     size='广告消耗', 
                     color='广告消耗',
                     hover_name='session',
                     hover_data=['CPL', '点击转化率'],
                     title='规模敏感性: 曝光 vs 线索 (Size=Ad Spend)',
                     labels={'曝光人数': 'Exposure', 'unique_leads': 'Unique Leads'},
                     template='plotly_white')
    
    # Add trendline
    fig.add_trace(px.scatter(df, x='曝光人数', y='unique_leads', trendline="ols").data[1])
    
    return fig

def scenario_difference_analysis_plotly(df):
    # Define scenarios
    threshold = df['广告消耗'].quantile(0.8)
    df['Scenario'] = np.where(df['广告消耗'] >= threshold, '大促/高投 (High Spend)', '日常 (Daily)')
    
    # Create subplots
    fig = make_subplots(rows=1, cols=3, 
                        subplot_titles=('Leads Distribution', 'CPL Distribution', 'Click Conversion Rate'))
    
    # Box plots
    fig.add_trace(go.Box(x=df['Scenario'], y=df['unique_leads'], name='Leads', marker_color='#636EFA'), row=1, col=1)
    fig.add_trace(go.Box(x=df['Scenario'], y=df['CPL'], name='CPL', marker_color='#EF553B'), row=1, col=2)
    fig.add_trace(go.Box(x=df['Scenario'], y=df['点击转化率'], name='CTR', marker_color='#00CC96'), row=1, col=3)
    
    fig.update_layout(title_text="场景差异分析 (Scenario Analysis)", showlegend=False, template='plotly_white', height=500)
    return fig

def marginal_return_analysis_plotly(df):
    # Binning
    try:
        df['Spend_Bin'] = pd.qcut(df['广告消耗'], q=5, labels=['Very Low', 'Low', 'Medium', 'High', 'Very High'])
    except ValueError:
        df['Spend_Bin'] = pd.cut(df['广告消耗'], bins=5, labels=['Very Low', 'Low', 'Medium', 'High', 'Very High'])

    marginal = df.groupby('Spend_Bin', observed=True)[['广告消耗', 'unique_leads', 'CPL']].mean().reset_index()
    
    # Dual axis chart
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    fig.add_trace(
        go.Scatter(x=marginal['Spend_Bin'], y=marginal['unique_leads'], name="Avg Leads", marker_color='#636EFA', mode='lines+markers'),
        secondary_y=False,
    )
    
    fig.add_trace(
        go.Scatter(x=marginal['Spend_Bin'], y=marginal['CPL'], name="Avg CPL", marker_color='#EF553B', mode='lines+markers', line=dict(dash='dash')),
        secondary_y=True,
    )
    
    fig.update_layout(
        title_text="投放边际收益分析 (Marginal Return)",
        template='plotly_white'
    )
    
    fig.update_xaxes(title_text="Ad Spend Tier")
    fig.update_yaxes(title_text="Avg Leads", secondary_y=False)
    fig.update_yaxes(title_text="Avg CPL", secondary_y=True)
    
    return fig

def scale_sensitivity_analysis(df):
    print("\n" + "="*30)
    print("1. 规模敏感性分析 (Scale Sensitivity Analysis)")
    print("="*30)
    
    # Correlation Analysis
    cols = ['曝光人数', '场观', '广告消耗', 'unique_leads', '全场景商机数']
    corr = df[cols].corr()
    print("\n相关性矩阵 (Correlation Matrix):")
    print(corr.round(2))
    
    # Generate insights text
    lead_corr_exposure = corr.loc['unique_leads', '曝光人数']
    lead_corr_spend = corr.loc['unique_leads', '广告消耗']
    
    conclusion = ""
    if lead_corr_exposure > 0.8:
        conclusion = "流量规模对线索产出有极强驱动力，流量红利明显。"
    elif lead_corr_exposure > 0.5:
        conclusion = "流量规模与线索产出正相关，但存在转化瓶颈。"
    else:
        conclusion = "单纯堆流量无法有效带来线索，需优化转化链路。"

    # Format correlation matrix as HTML table
    corr_html = corr.round(2).to_html(classes='table', border=0)
        
    insights = f"""
    通过曝光人数与线索量的散点分布，可以观察到流量规模对转化产出的直接驱动力。气泡大小代表广告消耗，颜色深浅反映消耗力度。<br><br>
    <strong>关键发现：</strong>
    <ul>
        <li>线索量与曝光人数的相关性: <strong>{lead_corr_exposure:.2f}</strong></li>
        <li>线索量与广告消耗的相关性: <strong>{lead_corr_spend:.2f}</strong></li>
    </ul>
    <strong>相关性矩阵 (Correlation Matrix):</strong>
    <div style="overflow-x: auto; margin: 10px 0;">
        {corr_html}
    </div>
    <strong>结论：</strong>{conclusion}
    """
    
    return scale_sensitivity_analysis_plotly(df), insights

def scenario_difference_analysis(df):
    print("\n" + "="*30)
    print("2. 场景差异分析 (Scenario Analysis: Promotion vs Daily)")
    print("="*30)
    
    # Define scenarios
    threshold = df['广告消耗'].quantile(0.8)
    df['Scenario'] = np.where(df['广告消耗'] >= threshold, '大促/高投 (High Spend)', '日常 (Daily)')
    
    grouped = df.groupby('Scenario')[['unique_leads', 'CPL', '点击转化率', '曝光转化率', '广告消耗']].mean()
    print("\n场景对比数据 (Average Metrics):")
    print(grouped.round(4).to_string())
    
    insights = f"""
    对比大促/高投场景与日常场景的核心指标（线索量、CPL、转化率）。箱线图展示了数据的分布离散程度，帮助识别异常表现。<br><br>
    <strong>分类标准：</strong>广告消耗 >= <strong>{threshold:.2f}</strong> (Top 20%) 定义为大促/高投场景。<br><br>
    <strong>关键数据对比：</strong>
    <ul>
        <li><strong>大促/高投场景：</strong>场均线索 {grouped.loc['大促/高投 (High Spend)', 'unique_leads']:.1f}，CPL ¥{grouped.loc['大促/高投 (High Spend)', 'CPL']:.2f}</li>
        <li><strong>日常场景：</strong>场均线索 {grouped.loc['日常 (Daily)', 'unique_leads']:.1f}，CPL ¥{grouped.loc['日常 (Daily)', 'CPL']:.2f}</li>
    </ul>
    """
    
    return scenario_difference_analysis_plotly(df), insights

def marginal_return_analysis(df):
    print("\n" + "="*30)
    print("3. 投放边际收益分析 (Marginal Return Analysis)")
    print("="*30)
    
    insights = """
    随着广告消耗层级的提升，观察线索产出（蓝色）与CPL成本（红色）的边际变化。
    如果CPL曲线陡峭上升而线索增长平缓，说明进入了边际效益递减区间。
    """
    
    return marginal_return_analysis_plotly(df), insights

def daily_performance_analysis_plotly(df, start_date=None, end_date=None):
    # Extract date from start_time
    df['date'] = df['start_time'].dt.date
    
    # Filter by date range if provided
    if start_date:
        start_date_dt = pd.to_datetime(start_date).date()
        df = df[df['date'] >= start_date_dt]
    
    if end_date:
        end_date_dt = pd.to_datetime(end_date).date()
        df = df[df['date'] <= end_date_dt]
    
    # Group by date
    daily_stats = df.groupby('date').agg({
        'unique_leads': 'sum',
        '广告消耗': 'sum',
        'session': 'count'
    }).reset_index()
    
    # Calculate daily CPL
    daily_stats['CPL'] = daily_stats.apply(
        lambda row: row['广告消耗'] / row['unique_leads'] if row['unique_leads'] > 0 else 0,
        axis=1
    )
    
    # Rename columns for clarity
    daily_stats = daily_stats.rename(columns={
        'unique_leads': '每日线索数',
        '广告消耗': '每日消耗',
        'session': '直播场数',
        'CPL': '每日CPL'
    })
    
    # Create subplots: 3 rows, 1 column
    fig = make_subplots(
        rows=3, cols=1,
        subplot_titles=('每日线索数 (Daily Leads)', '每日CPL (Daily CPL)', '每日直播场数 (Daily Sessions)'),
        vertical_spacing=0.1
    )
    
    # Add traces for each metric
    fig.add_trace(
        go.Bar(x=daily_stats['date'], y=daily_stats['每日线索数'], name='线索数', marker_color='#636EFA'),
        row=1, col=1
    )
    
    fig.add_trace(
        go.Scatter(x=daily_stats['date'], y=daily_stats['每日CPL'], name='CPL', mode='lines+markers', marker_color='#EF553B'),
        row=2, col=1
    )
    
    fig.add_trace(
        go.Bar(x=daily_stats['date'], y=daily_stats['直播场数'], name='场数', marker_color='#00CC96'),
        row=3, col=1
    )
    
    # Update layout
    fig.update_layout(
        title_text="每日表现分析 (Daily Performance Analysis)",
        height=900,
        showlegend=True,
        template='plotly_white'
    )
    
    # Update y-axis labels
    fig.update_yaxes(title_text="线索数", row=1, col=1)
    fig.update_yaxes(title_text="CPL (¥)", row=2, col=1)
    fig.update_yaxes(title_text="场数", row=3, col=1)
    
    # Update x-axis labels
    fig.update_xaxes(title_text="日期", row=3, col=1)
    
    return fig, daily_stats

def daily_performance_analysis(df, start_date=None, end_date=None):
    print("\n" + "="*30)
    print("4. 每日表现分析 (Daily Performance Analysis)")
    print("="*30)
    
    # Extract date from start_time
    df['date'] = df['start_time'].dt.date
    
    # Filter by date range if provided
    if start_date:
        start_date_dt = pd.to_datetime(start_date).date()
        df = df[df['date'] >= start_date_dt]
        print(f"筛选开始日期: {start_date}")
    
    if end_date:
        end_date_dt = pd.to_datetime(end_date).date()
        df = df[df['date'] <= end_date_dt]
        print(f"筛选结束日期: {end_date}")
    
    # Group by date
    daily_stats = df.groupby('date').agg({
        'unique_leads': 'sum',
        '广告消耗': 'sum',
        'session': 'count'
    }).reset_index()
    
    # Calculate daily CPL
    daily_stats['CPL'] = daily_stats.apply(
        lambda row: row['广告消耗'] / row['unique_leads'] if row['unique_leads'] > 0 else 0,
        axis=1
    )
    
    # Rename columns for clarity
    daily_stats = daily_stats.rename(columns={
        'unique_leads': '每日线索数',
        '广告消耗': '每日消耗',
        'session': '直播场数',
        'CPL': '每日CPL'
    })
    
    # Print daily statistics
    print("\n每日表现统计 (Daily Performance Statistics):")
    print("="*60)
    print(f"{'日期':<12} {'线索数':<8} {'消耗(¥)':<12} {'CPL(¥)':<10} {'场数':<6}")
    print("-"*60)
    
    for _, row in daily_stats.iterrows():
        date_str = row['date'].strftime('%Y-%m-%d')
        leads = int(row['每日线索数'])
        spend = f"{row['每日消耗']:,.2f}"
        cpl = f"{row['每日CPL']:.2f}"
        sessions = int(row['直播场数'])
        print(f"{date_str:<12} {leads:<8} {spend:<12} {cpl:<10} {sessions:<6}")
    
    # Calculate summary statistics
    total_days = len(daily_stats)
    avg_leads = daily_stats['每日线索数'].mean()
    avg_cpl = daily_stats['每日CPL'].mean()
    avg_sessions = daily_stats['直播场数'].mean()
    
    # Find best and worst performing days
    if not daily_stats.empty:
        best_day = daily_stats.loc[daily_stats['每日线索数'].idxmax()]
        worst_day = daily_stats.loc[daily_stats['每日线索数'].idxmin()]
        
        insights = f"""
    分析时间范围: {start_date if start_date else '数据起始'} 至 {end_date if end_date else '数据结束'}
    总分析天数: {total_days} 天
    
    <strong>关键统计指标:</strong>
    <ul>
        <li>平均每日线索数: <strong>{avg_leads:.1f}</strong></li>
        <li>平均每日CPL: <strong>¥{avg_cpl:.2f}</strong></li>
        <li>平均每日直播场数: <strong>{avg_sessions:.1f}</strong></li>
    </ul>
    
    <strong>最佳表现日:</strong> {best_day['date'].strftime('%Y-%m-%d')}
    <ul>
        <li>线索数: <strong>{int(best_day['每日线索数'])}</strong></li>
        <li>CPL: <strong>¥{best_day['每日CPL']:.2f}</strong></li>
        <li>直播场数: <strong>{int(best_day['直播场数'])}</strong></li>
    </ul>
    
    <strong>最差表现日:</strong> {worst_day['date'].strftime('%Y-%m-%d')}
    <ul>
        <li>线索数: <strong>{int(worst_day['每日线索数'])}</strong></li>
        <li>CPL: <strong>¥{worst_day['每日CPL']:.2f}</strong></li>
        <li>直播场数: <strong>{int(worst_day['直播场数'])}</strong></li>
    </ul>
    
    <strong>分析结论:</strong>
    通过每日趋势分析，可以识别出表现波动模式。线索数的峰值通常与特定营销活动或高消耗场次相关。
    如果CPL在特定日期异常升高，需要检查该日的转化效率或流量质量。
        """
    else:
        insights = "在指定时间范围内没有找到数据。"
    
    # Generate plot
    fig, _ = daily_performance_analysis_plotly(df, start_date, end_date)
    
    return fig, insights

def generate_stats_html(df, conversion_stats=None, conversion_report_url=None):
    total_sessions = len(df)
    total_leads = df['unique_leads'].sum()
    total_spend = df['广告消耗'].sum()
    avg_cpl = total_spend / total_leads if total_leads > 0 else 0
    
    # Calculate funnel metrics
    total_exposure = df['曝光人数'].sum()
    total_business_opps = df['全场景商机数'].sum()
    
    # Calculate global CPLO (Cost Per Lead Opportunity)
    global_cplo = total_spend / total_business_opps if total_business_opps > 0 else 0
    
    total_cohort = conversion_stats.get('cohort_size', 0) if conversion_stats else 0
    non_broadcast = total_cohort - total_leads

    # Find extremes safely
    if total_leads > 0:
        max_leads_idx = df['unique_leads'].idxmax()
        max_leads_session = df.loc[max_leads_idx, 'session']
        max_leads_val = df['unique_leads'].max()
        max_leads_cpl = df.loc[max_leads_idx, 'CPL']
        
        min_leads_df = df[df['unique_leads'] > 0]
        if not min_leads_df.empty:
            min_leads_idx = min_leads_df['unique_leads'].idxmin()
            min_leads_session = df.loc[min_leads_idx, 'session']
            min_leads_val = min_leads_df['unique_leads'].min()
            min_leads_cpl = df.loc[min_leads_idx, 'CPL']
        else:
             min_leads_session = "N/A"
             min_leads_val = 0
             min_leads_cpl = 0
    else:
        max_leads_session = "N/A"
        max_leads_val = 0
        max_leads_cpl = 0
        min_leads_session = "N/A"
        min_leads_val = 0
        min_leads_cpl = 0

    # Conversion Stats Block
    conversion_html = ""
    if conversion_stats:
        report_link = conversion_report_url if conversion_report_url else 'IM智己汽车 0201～0227_report.html'
        conversion_html = f"""
    <div class="stat-box">
        <h3>转化归因 (Attribution & Influence)</h3>
        <ul>
            <li><strong>Cohort Users:</strong> {conversion_stats.get('cohort_size', 'N/A')}</li>
            <li><strong>Locked Users:</strong> {conversion_stats.get('locked_users', 'N/A')}</li>
            <hr style="margin: 8px 0; border: 0; border-top: 1px dashed #eee;">
            <li><strong>本渠道锁单 (IM Lock):</strong> {conversion_stats.get('im_lock_count', 0)}
                <ul style="margin-top: 5px; font-size: 0.9em; color: #586069;">
                    <li>直接 (Direct): {conversion_stats.get('direct_lock_count', 0)}</li>
                    <li>归因 (Attributed): {conversion_stats.get('attributed_lock_count', 0)}</li>
                </ul>
            </li>
            <li><strong>辅助锁单 (Assisted):</strong> {conversion_stats.get('assisted_count', 0)}
                <ul style="margin-top: 5px; font-size: 0.9em; color: #586069;">
                    <li>首触 (First): {conversion_stats.get('first_touch_assist_count', 0)}</li>
                    <li>过程 (Middle): {conversion_stats.get('middle_assist_count', 0)}</li>
                    <li>锁后 (Post): {conversion_stats.get('post_lock_count', 0)}</li>
                </ul>
            </li>
        </ul>
        <div style="margin-top: 15px; text-align: center;">
            <a href="{report_link}" target="_blank" style="color: #0366d6; text-decoration: none; font-size: 0.9em;">
                View Detailed Conversion Report →
            </a>
        </div>
    </div>
        """

    html = f"""
    <div class="stat-box">
        <h3>核心指标 (Key Metrics)</h3>
        <ul>
            <li><strong>总场次:</strong> {total_sessions}</li>
            <li><strong>总消耗:</strong> ¥{total_spend:,.2f}</li>
            <li><strong>全量线索 (Total):</strong> {total_cohort:,.0f}
                <ul style="margin-top: 5px; font-size: 0.9em; color: #586069;">
                    <li>直播归因 (Broadcast): {total_leads:,.0f}</li>
                    <li>非直播时段 (Off-Air): {non_broadcast:,.0f}</li>
                </ul>
            </li>
            <hr style="margin: 8px 0; border: 0; border-top: 1px dashed #eee;">
            <li><strong>全场景商机数 (Opportunities):</strong> {total_business_opps:,.0f}</li>
            <li><strong>CPLO (商机成本):</strong> ¥{global_cplo:.2f}</li>
            <li><strong>CPL (线索成本):</strong> ¥{avg_cpl:.2f}</li>
        </ul>
    </div>

    {conversion_html}

    <div class="stat-box">
        <h3>场次极值 (Session Extremes)</h3>
        <p><strong>🔥 最高表现 (Top Performance):</strong></p>
        <ul style="margin-bottom: 15px;">
            <li>场次: {max_leads_session}</li>
            <li>线索数: {max_leads_val} (CPL: ¥{max_leads_cpl:.2f})</li>
        </ul>
        <p><strong>❄️ 最低表现 (Lowest Performance):</strong></p>
        <ul>
            <li>场次: {min_leads_session}</li>
            <li>线索数: {min_leads_val} (CPL: ¥{min_leads_cpl:.2f})</li>
        </ul>
    </div>
    """
    return html

def main():
    parser = argparse.ArgumentParser(description='Generate dashboard report.')
    parser.add_argument('--input', required=True, help='Path to the session leads CSV')
    parser.add_argument('--raw', required=True, help='Path to the raw leads CSV')
    parser.add_argument('--output', default='dashboard_report.html', help='Path to the output dashboard HTML')
    parser.add_argument('--conversion-output', help='Path to the output conversion HTML (optional, to link correctly)')
    parser.add_argument('--channel', '-c', help='Target channel name for conversion analysis (auto-detected from filename if not specified)')
    parser.add_argument('--start-date', '-s', help='Cohort start date (YYYY-MM-DD), default: from session data')
    parser.add_argument('--end-date', '-e', help='Cohort end date (YYYY-MM-DD), default: from session data')
    
    args = parser.parse_args()
    
    input_file = args.input
    raw_data_file = args.raw
    output_file = args.output
    conversion_output_file = args.conversion_output
    target_channel = args.channel
    start_date = args.start_date
    end_date = args.end_date
    
    df = load_data(input_file)
    print(f"Loaded {len(df)} sessions for analysis.")
    
    # Get Conversion Stats
    conversion_stats = None
    if analyze_conversion and os.path.exists(raw_data_file):
        print("Running conversion analysis...")
        try:
            # If we know the output path for conversion report, pass it
            # But wait, Dashboard_Step3_Report calls analyze_conversion...
            # We should probably pass the output path to analyze_conversion if we want it to save there
            
            # If conversion_output_file is provided, we tell analyze_conversion to save there
            # AND we use the filename (relative path) for the link in the dashboard
            
            # Check if analyze_conversion accepts output_file argument
            import inspect
            sig = inspect.signature(analyze_conversion)
            c_kwargs = {}
            if 'output_file' in sig.parameters and conversion_output_file:
                 c_kwargs['output_file'] = conversion_output_file

            # Use user-specified dates if provided, otherwise use dates from session data
            if start_date:
                cohort_start_date = start_date
            else:
                cohort_start_date = df['start_time'].min()
            
            if end_date:
                cohort_end_date = end_date
            else:
                if 'end_time' in df.columns:
                    cohort_end_date = df['end_time'].max()
                else:
                    cohort_end_date = df['start_time'].max()

            if 'start_date' in sig.parameters:
                c_kwargs['start_date'] = cohort_start_date
            if 'end_date' in sig.parameters:
                c_kwargs['end_date'] = cohort_end_date
            if 'target_channel' in sig.parameters and target_channel:
                c_kwargs['target_channel'] = target_channel
            
            conversion_stats = analyze_conversion(raw_data_file, **c_kwargs)
        except Exception as e:
            print(f"Error running conversion analysis: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("Skipping conversion analysis (module not found or file missing).")

    # Determine the link URL (relative filename)
    conversion_report_url = None
    if conversion_output_file:
        conversion_report_url = os.path.basename(conversion_output_file)
    elif raw_data_file:
        conversion_report_url = os.path.basename(raw_data_file).replace('.csv', '_report.html')

    # Generate Stats HTML
    stats_html = generate_stats_html(df, conversion_stats, conversion_report_url)
    
    # 1. Scale Sensitivity
    scale_fig, scale_insights = scale_sensitivity_analysis(df)
    
    # 2. Scenario Difference
    scenario_fig, scenario_insights = scenario_difference_analysis(df)
    
    # 3. Marginal Return
    marginal_fig, marginal_insights = marginal_return_analysis(df)
    
    # 4. Daily Performance Analysis
    daily_fig, daily_insights = daily_performance_analysis(df, start_date, end_date)
    
    # Generate HTML Report
    generate_html_report(df, scale_fig, scenario_fig, marginal_fig, daily_fig, stats_html, scale_insights, scenario_insights, marginal_insights, daily_insights, output_file)
    
    print("\nAnalysis Complete.")

if __name__ == "__main__":
    main()
