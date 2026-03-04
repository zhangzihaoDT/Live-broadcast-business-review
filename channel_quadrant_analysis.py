import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

# 配置
output_html = "channel_impact_quadrant_analysis.html"

# 1. 读取 Contribution Analysis (包含主锁单标记)
contrib_file = "/Users/zihao_/Documents/github/直播运营复盘/直播业务_data_2025_contribution_analysis.csv"
print(f"读取文件: {contrib_file}")
df_contrib = pd.read_csv(contrib_file)

# --- 应用直播业务分组 ---
group_file = "/Users/zihao_/Documents/github/直播运营复盘/直播业务_group_2025.csv"
if os.path.exists(group_file):
    print(f"读取分组文件: {group_file}")
    try:
        try:
            group_df = pd.read_csv(group_file)
        except UnicodeDecodeError:
            group_df = pd.read_csv(group_file, encoding='gbk')
        
        if 'lc_small_channel_name' in group_df.columns:
            live_channels = set(group_df['lc_small_channel_name'].unique())
            print(f"应用分组: {len(live_channels)} 个渠道 -> '直播业务(Group)'")
            
            # 将属于直播业务的渠道重命名为 '直播业务(Group)'
            df_contrib['lc_small_channel_name'] = df_contrib['lc_small_channel_name'].apply(
                lambda x: '直播业务(Group)' if x in live_channels else x
            )
            
            # 重新聚合 (Group By + Sum)
            df_contrib = df_contrib.groupby('lc_small_channel_name', as_index=False)[['主锁单标记']].sum()
            print(f"分组后行数: {len(df_contrib)}")
            
        else:
            print("警告: 分组文件中未找到 'lc_small_channel_name' 列")
    except Exception as e:
        print(f"分组处理出错: {e}")
else:
    print(f"提示: 未找到分组文件 {group_file}，跳过分组步骤")

# 计算主锁单标记总和及份额
total_direct_locks = df_contrib['主锁单标记'].sum()
df_contrib['Direct Share'] = df_contrib['主锁单标记'] / total_direct_locks
print(f"总主锁单数: {total_direct_locks}")

# 提取需要的列: 渠道名, Direct Share
df_direct = df_contrib[['lc_small_channel_name', 'Direct Share', '主锁单标记']].copy()
df_direct = df_direct.set_index('lc_small_channel_name')

# 2. 读取 Attribution Matrix (包含助攻数)
matrix_file = "/Users/zihao_/Documents/github/直播运营复盘/Attribution_Step2_Data.csv"
print(f"读取文件: {matrix_file}")
df_matrix = pd.read_csv(matrix_file)

# 计算助攻占比 (全链路影响力)
assist_cols = [col for col in df_matrix.columns if col.startswith('助攻数_')]
assist_sums = df_matrix[assist_cols].sum()
total_assists = assist_sums.sum()
print(f"总助攻数: {total_assists}")

# 构建助攻份额 DataFrame
df_assist = pd.DataFrame({
    'Total Assists': assist_sums.values,
    'Assist Share': assist_sums.values / total_assists
}, index=[col.replace('助攻数_', '') for col in assist_sums.index])

# 3. 合并对比
df_comparison = df_direct.join(df_assist, how='outer').fillna(0)

# 计算差异
# Difference > 0: Assist Share > Direct Share -> 若仅看 Direct Share，其价值被“低估”
# Difference < 0: Direct Share > Assist Share -> 若仅看 Direct Share，其价值可能被“高估”（或者是单纯的收割者）
df_comparison['Difference'] = df_comparison['Assist Share'] - df_comparison['Direct Share']

# 4. 业务解读标签
def get_label(row):
    direct = row['Direct Share']
    assist = row['Assist Share']
    diff = row['Difference']
    
    # 阈值设定 (可根据数据分布调整，这里用简单的相对比较)
    # 使用中位数或特定阈值来划分象限可能会更好，这里先简单分类
    
    if diff > 0.005: # 助攻显著高于直锁 (差异 > 0.5%)
        return "被低估的幕后英雄 (Hidden Gem)" # 高助攻，低直锁
    elif diff < -0.005: # 直锁显著高于助攻
        return "被高估的收割者 (Overvalued Closer)" # 高直锁，低助攻 (相对而言)
    else:
        return "价值匹配 (Fairly Valued)" # 两者相当

df_comparison['Status'] = df_comparison.apply(get_label, axis=1)

# 5. 可视化：表格
print("生成可视化...")

# 过滤掉极小值，避免图表过于拥挤
plot_df = df_comparison[(df_comparison['Direct Share'] > 0.001) | (df_comparison['Assist Share'] > 0.001)].copy()
plot_df = plot_df.reset_index()
# 根据 index 重命名为 Channel
plot_df = plot_df.rename(columns={'index': 'Channel', 'lc_small_channel_name': 'Channel'})

# 排序：按差异降序（从最被低估到最被高估）
plot_df = plot_df.sort_values('Difference', ascending=False)

# 准备表格数据
header_values = ["<b>渠道 (Channel)</b>", "<b>直接锁单份额<br>(Direct Share)</b>", "<b>全链路影响份额<br>(Assist Share)</b>", "<b>差异 (Diff)<br>(Assist - Direct)</b>", "<b>业务评价 (Status)</b>"]
cell_values = [
    plot_df['Channel'],
    plot_df['Direct Share'].apply(lambda x: f"{x:.2%}"),
    plot_df['Assist Share'].apply(lambda x: f"{x:.2%}"),
    plot_df['Difference'].apply(lambda x: f"{x:+.2%}"),
    plot_df['Status']
]

# 设置颜色逻辑
# 根据 Status 设置行颜色
colors = []
for status in plot_df['Status']:
    if "被低估" in status:
        colors.append("#d4edda") # 浅绿
    elif "被高估" in status:
        colors.append("#f8d7da") # 浅红
    else:
        colors.append("white")

# 绘制表格
fig = go.Figure(data=[go.Table(
    header=dict(
        values=header_values,
        fill_color='paleturquoise',
        align='center',
        font=dict(color='black', size=12)
    ),
    cells=dict(
        values=cell_values,
        fill_color=[colors], # 为每一行设置颜色
        align=['left', 'center', 'center', 'center', 'left'],
        font=dict(color='black', size=11),
        height=30
    )
)])

fig.update_layout(
    title='渠道价值评估矩阵表 (Channel Valuation Matrix)',
    width=1000,
    height=max(600, len(plot_df) * 35) # 动态高度
)

# 保存报告
print(f"保存报告到: {output_html}")
with open(output_html, 'w') as f:
    f.write("<html><head><title>渠道价值评估矩阵</title>")
    f.write("<style>body{font-family: Arial, sans-serif; margin: 40px;} .analysis{background-color: #f9f9f9; padding: 20px; border-left: 5px solid #6610f2; margin-top: 20px;}</style>")
    f.write("</head><body>")
    f.write("<h1>渠道价值评估矩阵：直接锁单 vs 全链路影响</h1>")
    f.write(f"<p>生成时间: {pd.Timestamp.now()}</p>")
    
    f.write(fig.to_html(full_html=False, include_plotlyjs='cdn'))
    
    f.write("<div class='analysis'>")
    f.write("<h3>💡 业务解读：谁被低估了？</h3>")
    f.write("<p>该表格对比了各渠道的“直接锁单份额”和“全链路影响份额”，揭示了渠道的真实价值。</p>")
    f.write("<ul>")
    f.write("<li><span style='background-color: #d4edda; padding: 2px 5px;'><strong>绿色背景：被低估的渠道。</strong></span>这些渠道的实际影响力（Assist Share）远大于其表面业绩（Direct Share）。它们是关键的种草者和辅助者。</li>")
    f.write("<li><span style='background-color: #f8d7da; padding: 2px 5px;'><strong>红色背景：被高估/收割型渠道。</strong></span>这些渠道主要承接最后的转化。虽然账面业绩好看，但往往依赖于其他渠道的前期铺垫。</li>")
    f.write("<li><span style='background-color: white; border: 1px solid #ccc; padding: 2px 5px;'><strong>白色背景：价值匹配。</strong></span>表里如一，直接贡献与辅助贡献相当。</li>")
    f.write("</ul>")
    
    f.write("<h4>🚀 重点关注（被低估 Top 5）</h4>")
    f.write("<ul>")
    for _, row in plot_df.head(5).iterrows():
        f.write(f"<li><strong>{row['Channel']}</strong>: 直锁份额 {row['Direct Share']:.2%} vs 真实影响 {row['Assist Share']:.2%} (差异 {row['Difference']:+.2%})</li>")
    f.write("</ul>")
    
    f.write("</div>")
    f.write("</body></html>")

print("完成！")
