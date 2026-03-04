import pandas as pd
import os
import re
from datetime import datetime
import numpy as np
import plotly.graph_objects as go

def analyze_conversion(file_path, output_file=None):
    print(f"Loading {file_path}...")
    try:
        # Load with same logic
        try:
            df = pd.read_csv(file_path, encoding='utf-16', sep='\t')
            if df.shape[1] <= 1:
                 df = pd.read_csv(file_path, encoding='utf-16', sep=',')
        except:
            df = pd.read_csv(file_path, encoding='utf-16', sep=None, engine='python')
    except Exception as e:
        print(f"Error loading file: {e}")
        return

    # Normalize column names
    df.columns = [c.strip().replace('\ufeff', '') for c in df.columns]
    
    # Identify lock time column
    lock_col_name = [c for c in df.columns if 'lc_order_lock_time_min' in c][0]
    
    # --- Pivot: Long to Wide ---
    print("\nPivoting data from Long to Wide format...")
    
    index_cols = [c for c in df.columns if c not in ['度量名称', '度量值']]
    
    # To avoid losing rows where some index columns might be NaN, we fill them temporarily
    df_temp = df.copy()
    for col in index_cols:
        # Convert to string to safely fill NaNs for grouping
        df_temp[col] = df_temp[col].fillna('__NAN_PLACEHOLDER__')

    try:
        # Pivot based on the temp dataframe
        df_wide = df_temp.pivot_table(index=index_cols, columns='度量名称', values='度量值', aggfunc='first').reset_index()
        
        # Restore NaNs - robustly
        for col in index_cols:
            # Replace the placeholder with actual np.nan
            df_wide[col] = df_wide[col].replace('__NAN_PLACEHOLDER__', np.nan)
                
        print(f"Pivot successful. New shape: {df_wide.shape}")
        df = df_wide
    except Exception as e:
        print(f"Pivot failed: {e}")
        return

    # ---------------------------
    
    # Parse dates
    df['parsed_create_time'] = pd.to_datetime(df['lc_create_time'], errors='coerce')
    
    # Define Cohort Criteria: Time Range (0201-0227) AND Channel (IM智己汽车)
    start_date = pd.Timestamp("2026-02-01")
    end_date = pd.Timestamp("2026-02-27 23:59:59")
    
    # Extract channel name from filename or use default
    # Check available channels
    available_channels = df['lc_small_channel_name'].unique()
    print(f"Available channels in CSV: {available_channels}")
    
    target_channel = "IM智己汽车" # Default
    if "IM智己|未来智舱" in os.path.basename(file_path):
         if "IM智己|未来智舱" in available_channels:
             target_channel = "IM智己|未来智舱"
         elif "IM智己｜未来智舱" in available_channels: # Check for different pipe character
             target_channel = "IM智己｜未来智舱"
    elif "智己生活家" in os.path.basename(file_path):
        target_channel = "智己生活家"
    elif "智己汽车官方直播" in os.path.basename(file_path):
        target_channel = "智己汽车官方直播"
    elif "智己生活家" in os.path.basename(file_path):
        target_channel = "智己生活家"
        
    print(f"Using target channel for analysis: {target_channel}")
    
    # --- 1. Identify Cohort Users ---
    mask_time = (df['parsed_create_time'] >= start_date) & (df['parsed_create_time'] <= end_date)
    mask_channel = df['lc_small_channel_name'] == target_channel
    
    cohort_md5s = df[mask_time & mask_channel]['lc_user_phone_md5'].unique()
    
    # --- 1.5 Cohort Statistics (Added) ---
    # Calculate unique main codes for cohort in time range
    cohort_rows = df[mask_time & mask_channel]
    
    # --- 2. Global History for Cohort ---
    df_cohort_global = df[df['lc_user_phone_md5'].isin(cohort_md5s)].copy()
    
    # Calculate global stats
    total_records_global = len(df_cohort_global)
    
    print(f"1. Cohort Statistics : {len(cohort_md5s)} Users -> {total_records_global} Global Records.")

    # --- 3. Identify Locked Users ---

    # Users who have ANY lock time in their history
    locked_md5s = df_cohort_global[df_cohort_global[lock_col_name].notna()]['lc_user_phone_md5'].unique()
    
    print(f"2. Attribution Analysis : {len(locked_md5s)} Locked Users.")
    
    if len(locked_md5s) == 0:
        print("No locked users found.")
        return

    # Filter for locked users only
    df_locked = df_cohort_global[df_cohort_global['lc_user_phone_md5'].isin(locked_md5s)].copy()
    
    # Ensure 'IM 顺位' and 'Md5 Clue 总数' are numeric
    df_locked['IM 顺位'] = pd.to_numeric(df_locked['IM 顺位'], errors='coerce')
    df_locked['Md5 Clue 总数'] = pd.to_numeric(df_locked['Md5 Clue 总数'], errors='coerce')
    
    # Sort by User and Time
    df_locked = df_locked.sort_values(['lc_user_phone_md5', 'parsed_create_time'])
    
    stats = []
    
    for md5, group in df_locked.groupby('lc_user_phone_md5'):
        # Get total clues count for this user (max of 'Md5 Clue 总数' or count of rows)
        # Using max() of the column is safer if it's a pre-calc value
        total_clues_metric = group['Md5 Clue 总数'].max()
        actual_rows = len(group)
        
        # Identify IM智己汽车 clues
        im_clues = group[group['lc_small_channel_name'] == target_channel]
        
        if im_clues.empty:
            # Should not happen since these are cohort users
            continue
            
        im_ranks = im_clues['IM 顺位'].dropna().tolist()
        min_rank = min(im_ranks) if im_ranks else -1
        max_rank = max(im_ranks) if im_ranks else -1
        
        # Check roles
        is_first_touch = (min_rank == 1)
        
        # Get lock date for this user
        # Since lc_order_lock_time_min is likely the same for the user (or we take the min/first valid one)
        user_lock_dates = group[lock_col_name].dropna().unique()
        
        is_last_touch = False
        has_pre_lock_im = False
        lock_date = None
        
        if len(user_lock_dates) > 0:
            # Parse the Chinese date format: YYYY年MM月DD日
            try:
                # Take the first one (assuming min lock time as per column name)
                lock_date_str = str(user_lock_dates[0])
                # Replace Chinese characters with standard delimiters
                clean_date_str = lock_date_str.replace('年', '-').replace('月', '-').replace('日', '')
                lock_date = pd.to_datetime(clean_date_str)
                
                # Filter interactions that happened BEFORE or ON the lock date (end of day)
                # Add 1 day to include the lock day itself fully
                cutoff_time = lock_date + pd.Timedelta(days=1)
                
                pre_conversion_interactions = group[group['parsed_create_time'] < cutoff_time]
                
                if not pre_conversion_interactions.empty:
                    # Check if IM was present before lock
                    im_pre_lock = pre_conversion_interactions[pre_conversion_interactions['lc_small_channel_name'] == target_channel]
                    has_pre_lock_im = not im_pre_lock.empty

                    # The "Last Touch" is the latest interaction in this filtered set
                    last_interaction = pre_conversion_interactions.sort_values('parsed_create_time').iloc[-1]
                    if last_interaction['lc_small_channel_name'] == target_channel:
                        is_last_touch = True
            except Exception as e:
                # Fallback to simple rank logic if parsing fails
                # print(f"Date parse error: {e}")
                is_last_touch = (max_rank == total_clues_metric) or (max_rank == actual_rows)
                # Assume if they are in the list, they have IM interaction, but can't verify time without date
                has_pre_lock_im = True 
        else:
             # Fallback if no lock date found (shouldn't happen in this filtered df)
             is_last_touch = (max_rank == total_clues_metric) or (max_rank == actual_rows)
             has_pre_lock_im = True
        
        # Determine Lock Channel (The channel associated with the row that has the lock time)
        rows_with_lock = group[group[lock_col_name].notna()]
        lock_channels = rows_with_lock['lc_small_channel_name'].unique().tolist()
        is_im_lock = target_channel in lock_channels

        stats.append({
            'md5': md5,
            'total_clues': total_clues_metric,
            'im_clue_count': len(im_clues),
            'min_im_rank': min_rank,
            'max_im_rank': max_rank,
            'is_first_touch': is_first_touch,
            'is_last_touch': is_last_touch,
            'has_pre_lock_im': has_pre_lock_im,
            'lock_channels': lock_channels,
            'is_im_lock': is_im_lock
        })
    
    stats_df = pd.DataFrame(stats)
    
    # --- Hierarchical Analysis ---
    # 1. 本渠道锁单 (IM Lock)
    im_lock_df = stats_df[stats_df['is_im_lock']]
    # -- 直接锁单 (Direct Lock: IM Lock + IM Last Touch)
    direct_lock_count = im_lock_df[im_lock_df['is_last_touch']].shape[0]
    # -- 归因锁单 (Attributed Lock: IM Lock + NOT IM Last Touch)
    attributed_lock_count = im_lock_df[~im_lock_df['is_last_touch']].shape[0]
    
    # 2. 辅助锁单 (Assisted Lock: NOT IM Lock)
    assisted_df = stats_df[~stats_df['is_im_lock']]
    
    # -- 首触辅助 (First Touch Assist: NOT IM Lock + IM First Touch)
    first_touch_assist_count = assisted_df[assisted_df['is_first_touch']].shape[0]
    
    # -- 过程助攻 (Middle Assist: NOT IM Lock + NOT IM First Touch + Has Pre-Lock IM)
    # These users started elsewhere, touched IM, then locked elsewhere.
    middle_assist_df = assisted_df[
        (~assisted_df['is_first_touch']) & (assisted_df['has_pre_lock_im'])
    ]
    middle_assist_count = middle_assist_df.shape[0]
    
    # -- 锁单后触达 (Post-Lock Interaction: NOT IM Lock + NOT IM First Touch + NO Pre-Lock IM)
    # These users locked elsewhere BEFORE ever touching IM.
    post_lock_df = assisted_df[
        (~assisted_df['is_first_touch']) & (~assisted_df['has_pre_lock_im'])
    ]
    post_lock_count = post_lock_df.shape[0]
    
    print(f"3. Influence Breakdown :")
    print(f"   - 本渠道锁单 ({len(im_lock_df)}): 直接 ({direct_lock_count}) + 归因 ({attributed_lock_count})")
    print(f"   - 辅助锁单 ({len(assisted_df)}): 首触 ({first_touch_assist_count}) + 过程 ({middle_assist_count}) + 锁后 ({post_lock_count})")
    
    # Detail table
    print(f"4. Detailed Sample : {len(stats_df)} 个用户的详细分类表格。")
    # Add classification column
    def classify(row):
        if row['is_im_lock']:
            return 'Direct Lock' if row['is_last_touch'] else 'Attributed Lock'
        else:
            if row['is_first_touch']:
                return 'First Touch Assist'
            elif row['has_pre_lock_im']:
                return 'Middle Assist'
            else:
                return 'Post-Lock Interaction'
            
    stats_df['Category'] = stats_df.apply(classify, axis=1)
    print(stats_df[['md5', 'total_clues', 'min_im_rank', 'is_first_touch', 'is_last_touch', 'is_im_lock', 'Category']].to_string())

    # --- Generate HTML Report ---
    generate_html_report(
        cohort_size=len(cohort_md5s),
        global_records=total_records_global,
        locked_users=len(locked_md5s),
        im_lock_count=len(im_lock_df),
        direct_lock_count=direct_lock_count,
        attributed_lock_count=attributed_lock_count,
        assisted_count=len(assisted_df),
        first_touch_assist_count=first_touch_assist_count,
        middle_assist_count=middle_assist_count,
        post_lock_count=post_lock_count,
        stats_df=stats_df,
        file_path=file_path,
        output_file=output_file
    )
    
    return {
        'cohort_size': len(cohort_md5s),
        'locked_users': len(locked_md5s),
        'im_lock_count': len(im_lock_df),
        'direct_lock_count': direct_lock_count,
        'attributed_lock_count': attributed_lock_count,
        'assisted_count': len(assisted_df),
        'first_touch_assist_count': first_touch_assist_count,
        'middle_assist_count': middle_assist_count,
        'post_lock_count': post_lock_count
    }

def generate_html_report(cohort_size, global_records, locked_users, 
                         im_lock_count, direct_lock_count, attributed_lock_count,
                         assisted_count, first_touch_assist_count, middle_assist_count, post_lock_count,
                         stats_df, file_path, output_file=None):
    
    if output_file:
        report_filename = output_file
    else:
        report_filename = file_path.replace('.csv', '_report.html')

    # Derive title from output filename if possible, otherwise default
    title = "IM智己汽车 转化分析报告 (Conversion Analysis Report)"
    if output_file:
        basename = os.path.basename(output_file)
        # Expected format: Conversion_Filename.html
        if basename.startswith("Conversion_") and basename.endswith(".html"):
            raw_name = basename[11:-5] # Remove prefix and suffix
            title = f"{raw_name} - 转化分析报告"
    
    # Generate Mermaid Graph Definition
    mermaid_graph = f"""
graph TD
    Start[Global Converters<br/>{locked_users} Users]
    
    Start --> A{{Lock Channel?}}
    
    A -->|IM Lock: {im_lock_count}| B{{Last Touch?}}
    B -->|IM Last Touch: {direct_lock_count}| C[Direct Lock<br/>{direct_lock_count} Users]
    B -->|Other Last Touch: {attributed_lock_count}| D[Attributed Lock<br/>{attributed_lock_count} Users]
    
    A -->|Other Lock: {assisted_count}| E{{First Touch?}}
    E -->|IM First Touch: {first_touch_assist_count}| F[First Touch Assist<br/>{first_touch_assist_count} Users]
    E -->|Other First Touch| G{{Pre-Lock Interaction?}}
    
    G -->|Has IM Pre-Lock: {middle_assist_count}| H[Middle Assist<br/>{middle_assist_count} Users]
    G -->|No IM Pre-Lock: {post_lock_count}| I[Post-Lock Interaction<br/>{post_lock_count} Users]
    
    style Start fill:#f9f,stroke:#333,stroke-width:2px
    style C fill:#bfb,stroke:#333,stroke-width:2px
    style D fill:#dfd,stroke:#333,stroke-width:2px
    style F fill:#ff9,stroke:#333,stroke-width:2px
    style H fill:#ff9,stroke:#333,stroke-width:2px
    style I fill:#eee,stroke:#999,stroke-width:1px,stroke-dasharray: 5 5
    """
    
    # Generate Plotly Table
    table_df = stats_df[['md5', 'total_clues', 'min_im_rank', 'is_first_touch', 'is_last_touch', 'is_im_lock', 'Category']].head(50)
    
    # Format boolean columns for better readability
    bool_cols = ['is_first_touch', 'is_last_touch', 'is_im_lock']
    for col in bool_cols:
        table_df[col] = table_df[col].map({True: '✅', False: '❌'})
    
    # Create Plotly Table
    fig = go.Figure(data=[go.Table(
        header=dict(
            values=[f"<b>{c}</b>" for c in table_df.columns],
            fill_color='#373f4a',
            align=['left', 'right', 'right', 'center', 'center', 'center', 'left'],
            font=dict(color='white', size=12),
            height=40
        ),
        cells=dict(
            values=[table_df[k].tolist() for k in table_df.columns],
            fill=dict(color='white'),
            line=dict(color='#e1e4e8'),
            align=['left', 'right', 'right', 'center', 'center', 'center', 'left'],
            font=dict(color='#373f4a', size=12),
            height=32
        )
    )])
    
    # Update layout
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        height=min(400 + len(table_df) * 32, 800)  # Dynamic height based on new row height
    )
    
    # Get HTML string for the plot (include plotly.js from CDN)
    plotly_html = fig.to_html(full_html=False, include_plotlyjs='cdn')
    
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <script type="module">
        import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
        mermaid.initialize({{ 
            startOnLoad: true,
            theme: 'default',
            securityLevel: 'loose'
        }});
    </script>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            max-width: 1000px;
            margin: 0 auto;
            padding: 40px 20px;
            color: #24292e;
            background-color: #ffffff;
        }}
        h1 {{ border-bottom: 1px solid #eaecef; padding-bottom: 0.3em; }}
        h2 {{ color: #0366d6; margin-top: 30px; }}
        .stats-container {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            background-color: #f6f8fa;
            padding: 20px;
            border-radius: 6px;
            border: 1px solid #e1e4e8;
        }}
        .stat-box {{
            padding: 10px;
        }}
        .mermaid {{ margin: 30px 0; text-align: center; }}
        .plotly-graph-div {{ margin: 20px 0; border: 1px solid #e1e4e8; border-radius: 6px; }}
    </style>
</head>
<body>
    <h1>{title}</h1>
<p>Data Source: {os.path.basename(file_path)}</p>

<div class="stats-container">
    <div class="stat-box">
        <h3>1. Cohort Statistics</h3>
        <ul>
            <li><strong>Cohort Size:</strong> {cohort_size} Users</li>
            <li><strong>Global Records:</strong> {global_records} Records</li>
        </ul>
    </div>
    
    <div class="stat-box">
        <h3>2. Attribution Analysis</h3>
        <ul>
            <li><strong>Locked Users:</strong> {locked_users}</li>
        </ul>
    </div>
    
    <div class="stat-box">
        <h3>3. Influence Breakdown</h3>
        <ul>
            <li><strong>本渠道锁单 ({im_lock_count})</strong>
                <ul>
                    <li>直接锁单 (Direct): {direct_lock_count}</li>
                    <li>归因锁单 (Attributed): {attributed_lock_count}</li>
                </ul>
            </li>
            <li><strong>辅助锁单 ({assisted_count})</strong>
                <ul>
                    <li>首触辅助 (First Touch): {first_touch_assist_count}</li>
                    <li>过程助攻 (Middle): {middle_assist_count}</li>
                    <li>锁后触达 (Post-Lock): {post_lock_count}</li>
                </ul>
            </li>
        </ul>
    </div>
</div>

<h2>Conversion Flow Visualization</h2>
<div class="mermaid">
{mermaid_graph}
</div>

<h2>Detailed User Sample (Top 50)</h2>
{plotly_html}

</body>
</html>
    """
    
    with open(report_filename, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"\nReport generated: {report_filename}")

import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Analyze IM Conversion.')
    parser.add_argument('file_path', nargs='?', default="/Users/zihao_/Documents/github/直播运营复盘/IM智己汽车 0201～0227.csv", help='Path to the IM leads CSV')
    parser.add_argument('--output', help='Path to the output HTML report')
    
    args = parser.parse_args()
    file_path = args.file_path
    output_file = args.output
    analyze_conversion(file_path, output_file)
