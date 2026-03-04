
import os
import re
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Configuration: List of report files to compare
REPORT_FILES = [
    "/Users/zihao_/Documents/github/直播运营复盘/reports/Dashboard_IM智己汽车直播复盘表2026-02-27.html",
    "/Users/zihao_/Documents/github/直播运营复盘/reports/Dashboard_智己官方直播间直播复盘表2026-03-03.html",
    "/Users/zihao_/Documents/github/直播运营复盘/reports/Dashboard_智己未来智舱直播复盘表2026-03-03 .html",
    "/Users/zihao_/Documents/github/直播运营复盘/reports/Dashboard_智己生活家直播复盘表2026-03-03 .html"
]

def extract_metrics(file_path):
    """
    Extracts key metrics from the HTML dashboard report using Regex.
    """
    if not os.path.exists(file_path):
        print(f"Warning: File not found: {file_path}")
        return None

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Extract Title/Channel Name
    filename = os.path.basename(file_path)
    # Remove 'Dashboard_' and '.html' and date parts to get a cleaner name
    # E.g., Dashboard_IM智己汽车直播复盘表2026-02-27.html -> IM智己汽车
    name_match = re.search(r'Dashboard_(.*?)直播复盘表', filename)
    if name_match:
        channel_name = name_match.group(1).strip()
    else:
        channel_name = filename.replace('Dashboard_', '').replace('.html', '')

    # Helper regex for extracting numbers (handling commas and currency symbols)
    def get_value(pattern):
        match = re.search(pattern, content)
        if match:
            val_str = match.group(1).replace(',', '').replace('¥', '').strip()
            return float(val_str)
        return 0.0

    # Extract Metrics
    # <li><strong>总场次:</strong> 84</li>
    sessions = get_value(r'<li><strong>总场次:</strong>\s*([\d,]+)</li>')
    
    # <li><strong>总消耗:</strong> ¥656,848.40</li>
    spend = get_value(r'<li><strong>总消耗:</strong>\s*([¥\d,.]+)</li>')
    
    # <li><strong>全量线索 (Total):</strong> 2,112
    leads = get_value(r'<li><strong>全量线索 \(Total\):</strong>\s*([\d,]+)')
    
    # <li>直播归因 (Broadcast): 1,868</li>
    broadcast_leads = get_value(r'<li>直播归因 \(Broadcast\): s*([\d,]+)</li>') # This might be tricky due to newlines, let's try a safer regex
    # Since HTML structure is multiline, we might need dotall or just search generally
    broadcast_match = re.search(r'直播归因 \(Broadcast\):\s*([\d,]+)', content)
    broadcast_leads = float(broadcast_match.group(1).replace(',', '')) if broadcast_match else 0
    
    off_air_leads = leads - broadcast_leads
    
    # <li><strong>全场景商机数 (Opportunities):</strong> 3,911</li>
    opportunities = get_value(r'<li><strong>全场景商机数 \(Opportunities\):</strong>\s*([\d,]+)</li>')
    
    # <li><strong>CPLO (商机成本):</strong> ¥167.95</li>
    cplo = get_value(r'<li><strong>CPLO \(商机成本\):</strong>\s*([¥\d,.]+)</li>')
    
    # <li><strong>CPL (线索成本):</strong> ¥351.63</li>
    cpl = get_value(r'<li><strong>CPL \(线索成本\):</strong>\s*([¥\d,.]+)</li>')

    return {
        'Channel': channel_name,
        'Sessions': int(sessions),
        'Spend': spend,
        'Leads': int(leads),
        'Broadcast Leads': int(broadcast_leads),
        'Off-Air Leads': int(off_air_leads),
        'Opportunities': int(opportunities),
        'CPL': cpl,
        'CPLO': cplo,
        'Filename': filename
    }

def generate_comparison_report(data):
    df = pd.DataFrame(data)
    
    # Sort by Spend descending
    df = df.sort_values('Spend', ascending=False)
    
    # Create Visualizations
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=("各渠道总消耗与线索产出 (Spend vs Leads)", "各渠道成本效能对比 (CPL & CPLO)", "线索构成分析 (Broadcast vs Off-Air)", "商机转化漏斗 (Leads to Opportunities)"),
        specs=[[{"secondary_y": True}, {"secondary_y": False}],
               [{"type": "bar"}, {"secondary_y": True}]]
    )

    # Chart 1: Spend vs Leads (Dual Axis)
    fig.add_trace(
        go.Bar(name='总消耗 (Spend)', x=df['Channel'], y=df['Spend'], marker_color='#636EFA'),
        row=1, col=1, secondary_y=False
    )
    fig.add_trace(
        go.Scatter(name='线索量 (Leads)', x=df['Channel'], y=df['Leads'], mode='lines+markers', marker_color='#EF553B', line=dict(width=3)),
        row=1, col=1, secondary_y=True
    )

    # Chart 2: Cost Efficiency (Grouped Bar)
    fig.add_trace(
        go.Bar(name='CPL (线索成本)', x=df['Channel'], y=df['CPL'], marker_color='#00CC96'),
        row=1, col=2
    )
    fig.add_trace(
        go.Bar(name='CPLO (商机成本)', x=df['Channel'], y=df['CPLO'], marker_color='#AB63FA'),
        row=1, col=2
    )

    # Chart 3: Lead Composition (Stacked Bar)
    fig.add_trace(
        go.Bar(name='直播归因 (Broadcast)', x=df['Channel'], y=df['Broadcast Leads'], marker_color='#19D3F3'),
        row=2, col=1
    )
    fig.add_trace(
        go.Bar(name='非直播时段 (Off-Air)', x=df['Channel'], y=df['Off-Air Leads'], marker_color='#FF6692'),
        row=2, col=1
    )
    
    # Chart 4: Opportunities vs Leads
    fig.add_trace(
        go.Bar(name='全量线索 (Leads)', x=df['Channel'], y=df['Leads'], marker_color='#EF553B', opacity=0.6),
        row=2, col=2, secondary_y=False
    )
    fig.add_trace(
        go.Bar(name='全场景商机 (Opportunities)', x=df['Channel'], y=df['Opportunities'], marker_color='#FFA15A', opacity=0.6),
        row=2, col=2, secondary_y=False
    )

    # Update Layout
    fig.update_layout(
        height=900, 
        width=1200, 
        title_text="直播渠道横向对比分析 (Channel Comparison Overview)",
        barmode='group',
        template='plotly_white'
    )
    
    # Specific layout adjustments
    fig.update_layout(barmode='stack', overwrite=True) # Reset barmode for specific subplots if needed, but simple group/stack is global in plotly express usually. 
    # Actually make_subplots handles types. For row 2 col 1 we want stack.
    # It's easier to just use 'group' globally or 'stack' globally. 
    # Let's keep it simple: group for CPL/CPLO, group for Spend/Leads is mixed. 
    # Stack is best for Composition.
    # We will use 'group' as default and manually stack traces if needed, but Plotly requires one global barmode.
    # So we will use 'group' and for composition we just accept it grouped or use relative.
    fig.update_layout(barmode='group')

    # Generate HTML Table
    table_html = df.to_html(classes='table', index=False, float_format=lambda x: '{:,.2f}'.format(x) if isinstance(x, float) else str(x))

    # Calculate Totals
    total_spend = df['Spend'].sum()
    total_leads = df['Leads'].sum()
    avg_cpl = total_spend / total_leads if total_leads else 0
    total_opps = df['Opportunities'].sum()
    
    # Calculate best efficiency (Lowest CPL)
    df_cpl_sorted = df.sort_values('CPL', ascending=True)
    best_cpl_channel = df_cpl_sorted.iloc[0]

    # Calculate biggest scale (Highest Leads)
    df_leads_sorted = df.sort_values('Leads', ascending=False)
    biggest_scale_channel = df_leads_sorted.iloc[0]

    # Calculate best CPLO
    df_cplo_sorted = df.sort_values('CPLO', ascending=True)
    best_cplo_channel = df_cplo_sorted.iloc[0]
    
    # Generate Full HTML Report
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>直播业务全渠道总览报告 (Global Channel Overview)</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif; max-width: 1400px; margin: 0 auto; padding: 20px; color: #333; }}
        h1 {{ border-bottom: 2px solid #eaecef; padding-bottom: 10px; }}
        .summary-cards {{ display: flex; gap: 20px; margin-bottom: 30px; flex-wrap: wrap; }}
        .card {{ flex: 1; min-width: 200px; background: #f6f8fa; padding: 20px; border-radius: 8px; border: 1px solid #e1e4e8; text-align: center; }}
        .card h3 {{ margin: 0 0 10px 0; color: #586069; font-size: 14px; text-transform: uppercase; }}
        .card .value {{ font-size: 24px; font-weight: bold; color: #0366d6; }}
        .table-container {{ overflow-x: auto; margin-bottom: 40px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
        th, td {{ padding: 12px; border: 1px solid #dfe2e5; text-align: right; }}
        th {{ background: #f6f8fa; text-align: center; }}
        td:first-child {{ text-align: left; font-weight: bold; }}
        .chart-container {{ margin-bottom: 40px; border: 1px solid #e1e4e8; border-radius: 8px; padding: 20px; }}
        .insights {{ background: #e6ffed; border: 1px solid #bef5cb; padding: 20px; border-radius: 8px; margin-top: 20px; }}
        .insights h3 {{ margin-top: 0; color: #22863a; }}
    </style>
</head>
<body>
    <h1>直播业务全渠道总览报告 (Global Channel Overview)</h1>
    
    <div class="summary-cards">
        <div class="card">
            <h3>总消耗 (Total Spend)</h3>
            <div class="value">¥{total_spend:,.2f}</div>
        </div>
        <div class="card">
            <h3>总线索 (Total Leads)</h3>
            <div class="value">{total_leads:,}</div>
        </div>
        <div class="card">
            <h3>平均 CPL (Avg Cost Per Lead)</h3>
            <div class="value">¥{avg_cpl:,.2f}</div>
        </div>
        <div class="card">
            <h3>总商机 (Total Opportunities)</h3>
            <div class="value">{total_opps:,}</div>
        </div>
    </div>

    <h2>1. 渠道核心指标对比 (Channel Metrics Comparison)</h2>
    <div class="table-container">
        {table_html}
    </div>

    <h2>2. 可视化分析 (Visual Analysis)</h2>
    <div class="chart-container">
        {fig.to_html(full_html=False, include_plotlyjs='cdn')}
    </div>
    
    <div class="insights">
        <h3>💡 核心洞察 (Key Insights)</h3>
        <ul>
            <li><strong>效能之王:</strong> {best_cpl_channel['Channel']} 拥有最低的 CPL (¥{best_cpl_channel['CPL']:.2f})，成本控制表现最优。</li>
            <li><strong>规模之王:</strong> {biggest_scale_channel['Channel']} 贡献了最多的线索 ({biggest_scale_channel['Leads']}条) 和商机，是业务规模的基石。</li>
            <li><strong>商机转化:</strong> 观察 "商机转化漏斗"，{best_cplo_channel['Channel']} 的 CPLO 最低 (¥{best_cplo_channel['CPLO']:.2f})，说明其线索到商机的流转效率最高。</li>
        </ul>
    </div>
</body>
</html>
    """
    
    output_path = "/Users/zihao_/Documents/github/直播运营复盘/reports/Global_Overview_Report.html"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"Report generated: {output_path}")

if __name__ == "__main__":
    data = []
    for f in REPORT_FILES:
        metrics = extract_metrics(f)
        if metrics:
            data.append(metrics)
    
    if data:
        generate_comparison_report(data)
    else:
        print("No data extracted.")
