"""
Dashboard_Step2_Conversion.py - 渠道转化归因分析

Usage:
    python Dashboard_Step2_Conversion.py <file_path> [options]

Arguments:
    file_path               CSV 数据文件路径（必填）

Options:
    -o, --output FILE       输出 HTML 报告路径（默认：{输入文件名}_report.html）
    -s, --start-date DATE   Cohort 开始日期，格式 YYYY-MM-DD（默认：2026-02-01）
    -e, --end-date DATE     Cohort 结束日期，格式 YYYY-MM-DD（默认：2026-02-27）
    -c, --channel CHANNEL   目标渠道名称（默认：根据文件名自动推断）

渠道自动推断规则:
    根据文件名自动匹配目标渠道：
    - 包含 "IM智己|未来智舱" → IM智己|未来智舱
    - 包含 "智己生活家" → 智己生活家
    - 包含 "智己汽车官方直播" → 智己汽车官方直播
    - 包含 "快慢闪" 或 "CM2" → Popup（门店）
    - 其他 → IM智己汽车（默认）

Cohort 时间窗口说明:
    --start-date 和 --end-date 定义 Cohort 时间窗口，用于筛选目标渠道用户：
    
    筛选逻辑：在指定时间范围内，通过目标渠道留资的用户 → 构成 Cohort
    
    具体流程：
    1. 筛选 lc_create_time 在 [start_date, end_date] 范围内的记录
    2. 且 lc_small_channel_name 等于目标渠道
    3. 提取这些用户的 lc_user_phone_md5 作为 Cohort 用户集
    4. 追溯这些用户的全局历史进行归因分析
    
    注意：如果数据源时间范围与默认值不匹配，可能导致 Cohort 用户数为 0 或结果偏差

Examples:
    # 基本用法（自动推断渠道，使用默认日期范围）
    python Dashboard_Step2_Conversion.py source/data.csv

    # 指定日期范围
    python Dashboard_Step2_Conversion.py source/data.csv -s 2025-08-15 -e 2025-08-17

    # 指定渠道名称
    python Dashboard_Step2_Conversion.py source/data.csv -c "Popup（门店）" -s 2025-08-15 -e 2025-08-17

    # 完整参数
    python Dashboard_Step2_Conversion.py source/data.csv -o reports/my_report.html -s 2025-08-15 -e 2025-08-17 -c "IM智己汽车"
    eg:python Dashboard_Step2_Conversion.py source/快慢闪_LS8_5.csv -o reports/LS8_start5_report.html -s 2026-03-26 -e 2026-03-30 -c "快慢闪"

Output:
    生成包含以下内容的 HTML 报告：
    - Cohort 统计（用户数、全局记录数）
    - 归因分析（锁单用户数、小订用户数）
    - 影响力分解（直接转化、归因转化、首触辅助、过程助攻、转化后触达）
    - Mermaid 流程图可视化
    - 用户详细分类表格
"""

import pandas as pd
import os
import re
from datetime import datetime
import numpy as np
import plotly.graph_objects as go
import difflib

def normalize_channel_name(value):
    if value is None:
        return None
    return str(value).replace('\u3000', ' ').strip()

def parse_cn_date(value):
    if value is None:
        return pd.NaT
    if isinstance(value, float) and np.isnan(value):
        return pd.NaT
    s = str(value).strip()
    if not s:
        return pd.NaT
    clean = s.replace('年', '-').replace('月', '-').replace('日', '')
    return pd.to_datetime(clean, errors='coerce')

def perform_attribution_analysis(df_cohort_global, conversion_col_name, target_channel, conversion_type="锁单", conversion_end_date=None):
    """
    执行归因分析的核心函数
    
    Parameters:
    - df_cohort_global: Cohort 用户的全局数据
    - conversion_col_name: 转化时间列名（如 lc_order_lock_time_min 或 lc_order_intention_pay_time_min）
    - target_channel: 目标渠道名称
    - conversion_type: 转化类型标签（"锁单" 或 "小订"）
    
    Returns:
    - dict: 包含归因分析结果的字典
    """
    if conversion_end_date is None:
        converted_md5s = df_cohort_global[df_cohort_global[conversion_col_name].notna()]['lc_user_phone_md5'].unique()
    else:
        conversion_end_date = pd.Timestamp(conversion_end_date)
        conv_dt = df_cohort_global[conversion_col_name].apply(parse_cn_date)
        eligible = df_cohort_global[df_cohort_global[conversion_col_name].notna() & conv_dt.notna() & (conv_dt <= conversion_end_date)]
        converted_md5s = eligible['lc_user_phone_md5'].unique()
    
    print(f"  {conversion_type}用户数: {len(converted_md5s)}")
    
    if len(converted_md5s) == 0:
        return None
    
    df_converted = df_cohort_global[df_cohort_global['lc_user_phone_md5'].isin(converted_md5s)].copy()
    if conversion_end_date is not None:
        df_converted['_conversion_dt'] = df_converted[conversion_col_name].apply(parse_cn_date)
    
    df_converted['IM 顺位'] = pd.to_numeric(df_converted['IM 顺位'], errors='coerce')
    df_converted['Md5 Clue 总数'] = pd.to_numeric(df_converted['Md5 Clue 总数'], errors='coerce')
    
    df_converted = df_converted.sort_values(['lc_user_phone_md5', 'parsed_create_time'])
    
    stats = []
    
    for md5, group in df_converted.groupby('lc_user_phone_md5'):
        total_clues_metric = group['Md5 Clue 总数'].max()
        actual_rows = len(group)
        
        im_clues = group[group['lc_small_channel_name'] == target_channel]
        
        if im_clues.empty:
            continue
            
        im_ranks = im_clues['IM 顺位'].dropna().tolist()
        min_rank = min(im_ranks) if im_ranks else -1
        max_rank = max(im_ranks) if im_ranks else -1
        
        is_first_touch = (min_rank == 1)
        
        user_conversion_dates = group[conversion_col_name].dropna().unique()
        
        is_last_touch = False
        has_pre_conversion_im = False
        conversion_date = None
        
        if conversion_end_date is not None:
            conv_dates = group['_conversion_dt'].dropna()
            conv_dates = conv_dates[conv_dates <= conversion_end_date]
            if not conv_dates.empty:
                conversion_date = conv_dates.min()
                cutoff_time = conversion_date + pd.Timedelta(days=1)
                pre_conversion_interactions = group[group['parsed_create_time'] < cutoff_time]
                if not pre_conversion_interactions.empty:
                    im_pre_conversion = pre_conversion_interactions[pre_conversion_interactions['lc_small_channel_name'] == target_channel]
                    has_pre_conversion_im = not im_pre_conversion.empty
                    last_interaction = pre_conversion_interactions.sort_values('parsed_create_time').iloc[-1]
                    if last_interaction['lc_small_channel_name'] == target_channel:
                        is_last_touch = True
            else:
                is_last_touch = (max_rank == total_clues_metric) or (max_rank == actual_rows)
                has_pre_conversion_im = True
        elif len(user_conversion_dates) > 0:
            try:
                conversion_date = parse_cn_date(user_conversion_dates[0])
                cutoff_time = conversion_date + pd.Timedelta(days=1)
                pre_conversion_interactions = group[group['parsed_create_time'] < cutoff_time]
                if not pre_conversion_interactions.empty:
                    im_pre_conversion = pre_conversion_interactions[pre_conversion_interactions['lc_small_channel_name'] == target_channel]
                    has_pre_conversion_im = not im_pre_conversion.empty
                    last_interaction = pre_conversion_interactions.sort_values('parsed_create_time').iloc[-1]
                    if last_interaction['lc_small_channel_name'] == target_channel:
                        is_last_touch = True
            except Exception:
                is_last_touch = (max_rank == total_clues_metric) or (max_rank == actual_rows)
                has_pre_conversion_im = True 
        else:
             is_last_touch = (max_rank == total_clues_metric) or (max_rank == actual_rows)
             has_pre_conversion_im = True
        
        if conversion_end_date is not None:
            rows_with_conversion = group[group['_conversion_dt'].notna() & (group['_conversion_dt'] <= conversion_end_date)]
        else:
            rows_with_conversion = group[group[conversion_col_name].notna()]
        conversion_channels = rows_with_conversion['lc_small_channel_name'].unique().tolist()
        is_im_conversion = target_channel in conversion_channels

        stats.append({
            'md5': md5,
            'total_clues': total_clues_metric,
            'im_clue_count': len(im_clues),
            'min_im_rank': min_rank,
            'max_im_rank': max_rank,
            'is_first_touch': is_first_touch,
            'is_last_touch': is_last_touch,
            'has_pre_conversion_im': has_pre_conversion_im,
            'conversion_channels': conversion_channels,
            'is_im_conversion': is_im_conversion
        })
    
    stats_df = pd.DataFrame(stats)
    
    im_conversion_df = stats_df[stats_df['is_im_conversion']]
    direct_count = im_conversion_df[im_conversion_df['is_last_touch']].shape[0]
    attributed_count = im_conversion_df[~im_conversion_df['is_last_touch']].shape[0]
    
    assisted_df = stats_df[~stats_df['is_im_conversion']]
    
    first_touch_assist_count = assisted_df[assisted_df['is_first_touch']].shape[0]
    
    middle_assist_df = assisted_df[
        (~assisted_df['is_first_touch']) & (assisted_df['has_pre_conversion_im'])
    ]
    middle_assist_count = middle_assist_df.shape[0]
    
    post_conversion_df = assisted_df[
        (~assisted_df['is_first_touch']) & (~assisted_df['has_pre_conversion_im'])
    ]
    post_conversion_count = post_conversion_df.shape[0]
    
    print(f"    - 本渠道{conversion_type} ({len(im_conversion_df)}): 直接 ({direct_count}) + 归因 ({attributed_count})")
    print(f"    - 辅助{conversion_type} ({len(assisted_df)}): 首触 ({first_touch_assist_count}) + 过程 ({middle_assist_count}) + {conversion_type}后 ({post_conversion_count})")
    
    def classify(row):
        if row['is_im_conversion']:
            return 'Direct' if row['is_last_touch'] else 'Attributed'
        else:
            if row['is_first_touch']:
                return 'First Touch Assist'
            elif row['has_pre_conversion_im']:
                return 'Middle Assist'
            else:
                return f'Post-{conversion_type} Interaction'
            
    stats_df['Category'] = stats_df.apply(classify, axis=1)
    
    return {
        'conversion_type': conversion_type,
        'converted_users': len(converted_md5s),
        'im_conversion_count': len(im_conversion_df),
        'direct_count': direct_count,
        'attributed_count': attributed_count,
        'assisted_count': len(assisted_df),
        'first_touch_assist_count': first_touch_assist_count,
        'middle_assist_count': middle_assist_count,
        'post_conversion_count': post_conversion_count,
        'stats_df': stats_df
    }

def analyze_conversion(file_path, output_file=None, start_date=None, end_date=None, target_channel=None):
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
    
    # Identify conversion time columns
    lock_col_name = [c for c in df.columns if 'lc_order_lock_time_min' in c][0]
    intention_col_name = [c for c in df.columns if 'lc_order_intention_pay_time_min' in c]
    intention_col_name = intention_col_name[0] if intention_col_name else None
    
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
    
    if start_date is None:
        start_date = pd.Timestamp("2026-02-01")
    else:
        start_date = pd.Timestamp(start_date)

    if end_date is None:
        end_date = pd.Timestamp("2026-02-27 23:59:59")
    else:
        end_date = pd.Timestamp(end_date)

    print(f"Using cohort time range: {start_date} to {end_date}")
    
    available_channels = df['lc_small_channel_name'].unique()
    print(f"Available channels in CSV: {available_channels}")

    available_channels_list = [str(c) for c in list(available_channels)]
    normalized_available = {normalize_channel_name(c): c for c in available_channels_list}

    if target_channel is None:
        target_channel = "IM智己汽车"
        if "IM智己|未来智舱" in os.path.basename(file_path):
             if "IM智己|未来智舱" in available_channels:
                 target_channel = "IM智己|未来智舱"
             elif "IM智己｜未来智舱" in available_channels:
                 target_channel = "IM智己｜未来智舱"
        elif "智己生活家" in os.path.basename(file_path):
            target_channel = "智己生活家"
        elif "智己汽车官方直播" in os.path.basename(file_path):
            target_channel = "智己汽车官方直播"
        elif "快慢闪" in os.path.basename(file_path) or "CM2" in os.path.basename(file_path):
            if "Popup（门店）" in available_channels:
                target_channel = "Popup（门店）"
    else:
        target_channel = normalize_channel_name(target_channel)

    alias_map = {
        "快慢闪": "Popup（门店）",
        "popup（门店）": "Popup（门店）",
        "Popup（门店）": "Popup（门店）",
        "popup": "Popup（门店）",
        "Popup": "Popup（门店）",
    }

    normalized_target = normalize_channel_name(target_channel)
    if normalized_target in alias_map:
        normalized_target = normalize_channel_name(alias_map[normalized_target])

    if normalized_target in normalized_available:
        target_channel = normalized_available[normalized_target]
    else:
        suggestions = difflib.get_close_matches(
            normalized_target,
            [k for k in normalized_available.keys() if k is not None],
            n=5,
            cutoff=0.6,
        )
        if suggestions:
            suggestion_text = ", ".join([normalized_available[s] for s in suggestions if s in normalized_available])
            print(f"Warning: Channel '{target_channel}' not found in data. Did you mean: {suggestion_text}")
        else:
            print(f"Warning: Channel '{target_channel}' not found in data.")
        return
        
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

    # --- 2. Attribution Analysis: 锁单 ---
    print(f"\n2. Attribution Analysis (锁单):")
    lock_result = perform_attribution_analysis(df_cohort_global, lock_col_name, target_channel, "锁单")
    
    # --- 3. Attribution Analysis: 小订 ---
    print(f"\n3. Attribution Analysis (小订):")
    intention_result = None
    if intention_col_name:
        intention_result = perform_attribution_analysis(df_cohort_global, intention_col_name, target_channel, "小订", conversion_end_date=end_date)
    else:
        print("  小订时间列不存在，跳过小订分析。")

    # --- Generate HTML Report ---
    generate_html_report(
        cohort_size=len(cohort_md5s),
        global_records=total_records_global,
        lock_result=lock_result,
        intention_result=intention_result,
        file_path=file_path,
        output_file=output_file,
        target_channel=target_channel
    )
    
    result = {
        'cohort_size': len(cohort_md5s),
    }
    
    # Add lock statistics if available
    if lock_result:
        result.update({
            'locked_users': lock_result['converted_users'],
            'im_lock_count': lock_result['im_conversion_count'],
            'direct_lock_count': lock_result['direct_count'],
            'attributed_lock_count': lock_result['attributed_count'],
            'assisted_count': lock_result['assisted_count'],
            'first_touch_assist_count': lock_result['first_touch_assist_count'],
            'middle_assist_count': lock_result['middle_assist_count'],
            'post_lock_count': lock_result['post_conversion_count']
        })
    
    # Add intention statistics if available
    if intention_result:
        result.update({
            'intention_users': intention_result['converted_users'],
            'im_intention_count': intention_result['im_conversion_count'],
            'direct_intention_count': intention_result['direct_count'],
            'attributed_intention_count': intention_result['attributed_count'],
            'assisted_intention_count': intention_result['assisted_count'],
            'first_touch_assist_intention_count': intention_result['first_touch_assist_count'],
            'middle_assist_intention_count': intention_result['middle_assist_count'],
            'post_intention_count': intention_result['post_conversion_count']
        })
    
    return result

def generate_mermaid_graph(result, conversion_type="锁单"):
    """
    生成归因分析的 Mermaid 流程图
    
    Parameters:
    - result: 归因分析结果字典
    - conversion_type: 转化类型标签
    
    Returns:
    - str: Mermaid 图定义字符串
    """
    if not result:
        return ""
    
    converted_users = result['converted_users']
    im_count = result['im_conversion_count']
    direct = result['direct_count']
    attributed = result['attributed_count']
    assisted = result['assisted_count']
    first_touch = result['first_touch_assist_count']
    middle = result['middle_assist_count']
    post = result['post_conversion_count']
    
    conversion_label = "Lock" if conversion_type == "锁单" else "Intention"
    
    return f"""
graph TD
    Start[Global {conversion_type}<br/>{converted_users} Users]
    
    Start --> A{{{conversion_type} Channel?}}
    
    A -->|IM {conversion_label}: {im_count}| B{{Last Touch?}}
    B -->|IM Last Touch: {direct}| C[Direct {conversion_label}<br/>{direct} Users]
    B -->|Other Last Touch: {attributed}| D[Attributed {conversion_label}<br/>{attributed} Users]
    
    A -->|Other {conversion_label}: {assisted}| E{{First Touch?}}
    E -->|IM First Touch: {first_touch}| F[First Touch Assist<br/>{first_touch} Users]
    E -->|Other First Touch| G{{Pre-{conversion_label} Interaction?}}
    
    G -->|Has IM Pre-{conversion_label}: {middle}| H[Middle Assist<br/>{middle} Users]
    G -->|No IM Pre-{conversion_label}: {post}| I[Post-{conversion_label} Interaction<br/>{post} Users]
    
    style Start fill:#f9f,stroke:#333,stroke-width:2px
    style C fill:#bfb,stroke:#333,stroke-width:2px
    style D fill:#dfd,stroke:#333,stroke-width:2px
    style F fill:#ff9,stroke:#333,stroke-width:2px
    style H fill:#ff9,stroke:#333,stroke-width:2px
    style I fill:#eee,stroke:#999,stroke-width:1px,stroke-dasharray: 5 5
    """

def generate_plotly_table(result, conversion_type="锁单"):
    """
    生成归因分析的 Plotly 表格
    
    Parameters:
    - result: 归因分析结果字典
    - conversion_type: 转化类型标签
    
    Returns:
    - str: Plotly 表格的 HTML 字符串
    """
    if not result or 'stats_df' not in result:
        return "<p>No data available</p>"
    
    stats_df = result['stats_df']
    
    is_im_col = 'is_im_conversion' if 'is_im_conversion' in stats_df.columns else 'is_im_lock'
    
    table_df = stats_df[['md5', 'total_clues', 'min_im_rank', 'is_first_touch', 'is_last_touch', is_im_col, 'Category']].head(50)
    
    bool_cols = ['is_first_touch', 'is_last_touch', is_im_col]
    for col in bool_cols:
        table_df[col] = table_df[col].map({True: '✅', False: '❌'})
    
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
    
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        height=min(400 + len(table_df) * 32, 800)
    )
    
    return fig.to_html(full_html=False, include_plotlyjs='cdn')

def generate_html_report(cohort_size, global_records, lock_result, intention_result, file_path, output_file=None, target_channel=None):
    
    if output_file:
        report_filename = output_file
    else:
        report_filename = file_path.replace('.csv', '_report.html')

    if target_channel is None:
        title = "转化分析报告 (Conversion Analysis Report)"
    else:
        title = f"{target_channel} 转化分析报告 (Conversion Analysis Report)"
    if output_file:
        basename = os.path.basename(output_file)
        if basename.startswith("Conversion_") and basename.endswith(".html"):
            raw_name = basename[11:-5]
            title = f"{raw_name} - 转化分析报告"
    
    lock_mermaid = generate_mermaid_graph(lock_result, "锁单") if lock_result else ""
    lock_table_html = generate_plotly_table(lock_result, "锁单") if lock_result else "<p>无锁单数据</p>"
    
    intention_mermaid = generate_mermaid_graph(intention_result, "小订") if intention_result else ""
    intention_table_html = generate_plotly_table(intention_result, "小订") if intention_result else "<p>无小订数据</p>"
    
    lock_stats_html = ""
    if lock_result:
        lock_stats_html = f"""
    <div class="stat-box">
        <h3>归因分析（锁单用户数）</h3>
        <ul>
            <li><strong>锁单用户:</strong> {lock_result['converted_users']}</li>
            <li><strong>本渠道锁单 ({lock_result['im_conversion_count']})</strong>
                <ul>
                    <li>直接锁单 (Direct): {lock_result['direct_count']}</li>
                    <li>归因锁单 (Attributed): {lock_result['attributed_count']}</li>
                </ul>
            </li>
            <li><strong>辅助锁单 ({lock_result['assisted_count']})</strong>
                <ul>
                    <li>首触辅助 (First Touch): {lock_result['first_touch_assist_count']}</li>
                    <li>过程助攻 (Middle): {lock_result['middle_assist_count']}</li>
                    <li>锁后触达 (Post-Lock): {lock_result['post_conversion_count']}</li>
                </ul>
            </li>
        </ul>
    </div>
"""
    
    intention_stats_html = ""
    if intention_result:
        intention_stats_html = f"""
    <div class="stat-box">
        <h3>归因分析（小订用户数）</h3>
        <ul>
            <li><strong>小订用户:</strong> {intention_result['converted_users']}</li>
            <li><strong>本渠道小订 ({intention_result['im_conversion_count']})</strong>
                <ul>
                    <li>直接小订 (Direct): {intention_result['direct_count']}</li>
                    <li>归因小订 (Attributed): {intention_result['attributed_count']}</li>
                </ul>
            </li>
            <li><strong>辅助小订 ({intention_result['assisted_count']})</strong>
                <ul>
                    <li>首触辅助 (First Touch): {intention_result['first_touch_assist_count']}</li>
                    <li>过程助攻 (Middle): {intention_result['middle_assist_count']}</li>
                    <li>小订后触达 (Post-Intention): {intention_result['post_conversion_count']}</li>
                </ul>
            </li>
        </ul>
    </div>
"""
    
    lock_section_html = ""
    if lock_result:
        lock_section_html = f"""
<h2>归因分析（锁单用户数）</h2>
<div class="mermaid">
{lock_mermaid}
</div>
<h3>锁单用户详细分类 (Top 50)</h3>
{lock_table_html}
"""
    
    intention_section_html = ""
    if intention_result:
        intention_section_html = f"""
<h2>归因分析（小订用户数）</h2>
<div class="mermaid">
{intention_mermaid}
</div>
<h3>小订用户详细分类 (Top 50)</h3>
{intention_table_html}
"""
    
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
        <h3>Cohort Statistics</h3>
        <ul>
            <li><strong>Cohort Size:</strong> {cohort_size} Users</li>
            <li><strong>Global Records:</strong> {global_records} Records</li>
        </ul>
    </div>
{lock_stats_html}{intention_stats_html}
</div>

{lock_section_html}
{intention_section_html}

</body>
</html>
    """
    
    report_dir = os.path.dirname(report_filename)
    if report_dir:
        os.makedirs(report_dir, exist_ok=True)

    with open(report_filename, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"\nReport generated: {report_filename}")

import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Analyze IM Conversion.')
    parser.add_argument('file_path', help='Path to the CSV data file')
    parser.add_argument('--output', '-o', help='Path to the output HTML report')
    parser.add_argument('--start-date', '-s', help='Cohort start date (YYYY-MM-DD), default: 2026-02-01')
    parser.add_argument('--end-date', '-e', help='Cohort end date (YYYY-MM-DD), default: 2026-02-27')
    parser.add_argument('--channel', '-c', help='Target channel name (auto-detected from filename if not specified)')
    
    args = parser.parse_args()
    analyze_conversion(args.file_path, args.output, args.start_date, args.end_date, args.channel)
