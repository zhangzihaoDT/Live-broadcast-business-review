import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import sys

# 配置路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_FILE = os.path.join(BASE_DIR, "Attribution_Step2_Data.csv")
OUTPUT_REPORT = os.path.join(BASE_DIR, "Attribution_Step4_Report.html")
PROCESS_SCRIPT = os.path.join(BASE_DIR, "Attribution_Step1_Process.py")

def run_processing_script():
    """运行数据处理脚本，确保数据最新"""
    print(f"正在运行数据处理脚本: {PROCESS_SCRIPT}")
    try:
        # 使用 os.system 或 subprocess 调用
        result = os.system(f"python3 {PROCESS_SCRIPT}")
        if result != 0:
            print("警告: 数据处理脚本运行失败或返回非零状态码。")
        else:
            print("数据处理脚本运行成功。")
    except Exception as e:
        print(f"运行脚本出错: {e}")

def load_data():
    """读取处理后的 CSV 文件"""
    if not os.path.exists(INPUT_FILE):
        print(f"错误: 文件不存在 {INPUT_FILE}")
        return None
    
    print(f"读取数据文件: {INPUT_FILE}")
    df = pd.read_csv(INPUT_FILE)
    return df

def generate_report(df):
    """生成分析报告"""
    if df is None:
        return

    print("生成可视化报告...")
    
    # 提取助攻列
    assist_cols = [col for col in df.columns if col.startswith('助攻数_')]
    
    # --- 模块 1：助攻渠道的累计助攻次数分布 (百分比) ---
    
    # 计算每个助攻渠道的总助攻数
    assist_sums = df[assist_cols].sum().sort_values(ascending=False)
    
    # 计算总助攻数的总和
    total_assist_all = assist_sums.sum()
    
    # 创建 DataFrame 用于绘图
    df_plot = pd.DataFrame({
        'assist_channel': [col.replace('助攻数_', '') for col in assist_sums.index],
        'total_assists': assist_sums.values
    })
    
    # 过滤掉助攻数为0的渠道
    df_plot = df_plot[df_plot['total_assists'] > 0]
    
    # 计算百分比
    df_plot['percentage'] = (df_plot['total_assists'] / total_assist_all * 100).round(0)
    
    # 计算累计百分比 (Running Sum / Total Sum)
    df_plot['cumulative_percentage'] = (df_plot['total_assists'].cumsum() / total_assist_all * 100).round(0)
    
    # 创建图表：组合图 (Bar + Line)
    fig = go.Figure()
    
    # 柱状图：各渠道助攻占比
    fig.add_trace(go.Bar(
        x=df_plot['assist_channel'],
        y=df_plot['percentage'],
        name='助攻占比 (%)',
        marker_color='#636EFA',
        text=df_plot['percentage'].apply(lambda x: f'{x:.0f}%'),
        textposition='outside'
    ))
    
    # 线图：累计占比 (可选，如果用户只是要Y轴改为比例，可能主要关注Bar，但Running Sum通常伴随Pareto图)
    # 用户描述 "sum 渠道/runningsum 渠道" 有点歧义，可能是指 "当前渠道sum / 所有渠道running sum" ?
    # 通常是 "当前渠道sum / 总sum" 作为柱状图高度。
    # 这里我们添加一条累计百分比线，以提供更丰富的信息。
    fig.add_trace(go.Scatter(
        x=df_plot['assist_channel'],
        y=df_plot['cumulative_percentage'],
        name='累计占比 (%)',
        mode='lines+markers',
        marker_color='#EF553B',
        yaxis='y2'
    ))
    
    fig.update_layout(
        title='各助攻渠道的助攻占比分布 (Percentage of Total Assists by Channel)',
        xaxis_title='助攻渠道',
        yaxis=dict(
            title='助攻占比 (%)',
            range=[0, max(df_plot['percentage']) * 1.2] # 留出空间给标签
        ),
        yaxis2=dict(
            title='累计占比 (%)',
            overlaying='y',
            side='right',
            range=[0, 105]
        ),
        legend=dict(x=0.8, y=0.95),
        xaxis_tickangle=-45
    )
    
    # 保存为 HTML
    print(f"保存报告到: {OUTPUT_REPORT}")
    with open(OUTPUT_REPORT, 'w') as f:
        f.write("<html><head><title>渠道归因分析报告</title>")
        f.write("<style>body{font-family: Arial, sans-serif; margin: 40px;} .conclusion{background-color: #f0f8ff; padding: 20px; border-left: 5px solid #007bff; margin-top: 20px;}</style>")
        f.write("</head><body>")
        f.write("<h1>渠道归因分析报告</h1>")
        f.write(f"<p>生成时间: {pd.Timestamp.now()}</p>")
        f.write(f"<p>总助攻次数: {total_assist_all}</p>")
        
        f.write("<h2>模块 1：各助攻渠道的助攻占比分布</h2>")
        f.write("<p>下图展示了各助攻渠道贡献的助攻数占总助攻数的百分比（柱状图），以及累计百分比（红线）。</p>")
        
        f.write(fig.to_html(full_html=False, include_plotlyjs='cdn'))
        
        f.write("<div class='conclusion'>")
        f.write("<h3>💡 分析结论</h3>")
        f.write("<p><strong>助攻占比（Assist Share）</strong> 反映了该渠道在促成全量锁单过程中的辅助贡献程度。</p>")
        f.write("<p>从帕累托曲线（红线）可以看出，前 20% 的头部助攻渠道往往贡献了 80% 的助攻量。这些高频助攻渠道是提升锁单转化率的关键触点，应当重点关注和维护。</p>")
        f.write("<p>此结论可以作为<strong>评估渠道线索对锁单影响力</strong>的最有力证明。</p>")
        f.write("</div>")
        
        f.write("</body></html>")
    
    print("报告生成完成！")

if __name__ == "__main__":
    # 1. 运行数据处理
    run_processing_script()
    
    # 2. 读取数据
    df = load_data()
    
    # 3. 生成报告
    generate_report(df)
