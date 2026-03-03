import pandas as pd
import numpy as np

def load_and_process(file_path):
    print(f"Loading {file_path}...")
    try:
        df = pd.read_csv(file_path, encoding='utf-16', sep='\t')
        df.columns = [c.strip().replace('\ufeff', '') for c in df.columns]
        
        # Pivot
        df_pivot = df.pivot_table(
            index=['直播业务分组', 'lc_small_channel_name'], 
            columns='度量名称', 
            values='度量值', 
            aggfunc='sum',
            fill_value=0
        ).reset_index()
        df_pivot.columns.name = None
        
        # Ensure numeric
        metric_cols = ['主锁单标记', 'md5_辅助锁单']
        for col in metric_cols:
            if col in df_pivot.columns:
                df_pivot[col] = pd.to_numeric(df_pivot[col], errors='coerce').fillna(0)
            else:
                df_pivot[col] = 0
                
        # Calculate derived metrics
        df_pivot['Total Contribution'] = df_pivot['主锁单标记'] + df_pivot['md5_辅助锁单']
        df_pivot['Assist Ratio'] = df_pivot.apply(
            lambda row: row['md5_辅助锁单'] / row['Total Contribution'] if row['Total Contribution'] > 0 else 0, 
            axis=1
        )
        return df_pivot
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return None

def compare_periods():
    file_2025 = '/Users/zihao_/Documents/github/直播运营复盘/直播业务_data_2025.csv'
    file_new = '/Users/zihao_/Documents/github/直播运营复盘/直播业务_data_20260201~0227.csv'
    
    df_2025 = load_and_process(file_2025)
    df_new = load_and_process(file_new)
    
    if df_2025 is None or df_new is None:
        return

    # Filter for Group A (Live Streaming Business)
    group_a_2025 = df_2025[df_2025['直播业务分组'].astype(str).str.strip().str.upper() == 'A'].copy()
    group_a_new = df_new[df_new['直播业务分组'].astype(str).str.strip().str.upper() == 'A'].copy()
    
    # Rename columns for merge
    cols_to_keep = ['lc_small_channel_name', '主锁单标记', 'md5_辅助锁单', 'Total Contribution', 'Assist Ratio']
    
    group_a_2025 = group_a_2025[cols_to_keep].set_index('lc_small_channel_name')
    group_a_new = group_a_new[cols_to_keep].set_index('lc_small_channel_name')
    
    # Merge
    comparison = group_a_new.join(group_a_2025, lsuffix='_New', rsuffix='_2025', how='outer').fillna(0)
    
    # Calculate Changes
    comparison['Direct Lock Change'] = comparison['主锁单标记_New'] - comparison['主锁单标记_2025']
    comparison['Assisted Lock Change'] = comparison['md5_辅助锁单_New'] - comparison['md5_辅助锁单_2025'] # Note: comparing different time ranges directly might be misleading if not normalized, but user asked for "what changed" in the file content.
    # However, since 2025 is likely a full year and new file is 1 month, raw difference is expected to be negative.
    # The user likely wants to see the *structure* or *role* change, or maybe the new file IS the 2026 Feb data vs 2025 full year? 
    # Or maybe 2025 file was also a specific period? 
    # Let's assume we compare the metrics themselves.
    
    comparison['Ratio Change'] = comparison['Assist Ratio_New'] - comparison['Assist Ratio_2025']
    
    # Sort by Total Contribution New desc
    comparison = comparison.sort_values('Total Contribution_New', ascending=False)
    
    print("\n=== Comparison: New Period (Feb 2026) vs 2025 Data (Group A) ===")
    
    # 1. Overall Group A Stats Comparison
    total_2025 = group_a_2025['Total Contribution'].sum()
    total_new = group_a_new['Total Contribution'].sum()
    
    ratio_2025 = group_a_2025['md5_辅助锁单'].sum() / total_2025 if total_2025 > 0 else 0
    ratio_new = group_a_new['md5_辅助锁单'].sum() / total_new if total_new > 0 else 0
    
    print(f"\nOverall Group A Performance:")
    print(f"  - Total Contribution: 2025={total_2025} -> New={total_new}")
    print(f"  - Overall Assist Ratio: 2025={ratio_2025:.2%} -> New={ratio_new:.2%} (Change: {ratio_new - ratio_2025:+.2%})")
    
    # 2. Channel Level Comparison
    print("\nTop Channels in New Period:")
    display_cols = ['主锁单标记_New', 'md5_辅助锁单_New', 'Total Contribution_New', 'Assist Ratio_New', 'Assist Ratio_2025', 'Ratio Change']
    
    # Format for readability
    pd.set_option('display.max_rows', 100)
    pd.set_option('display.float_format', lambda x: '%.2f' % x)
    
    print(comparison[display_cols].head(20).to_string())
    
    # 3. Detect Role Shifts
    # Significant change in Assist Ratio (> 10%)
    shifts = comparison[abs(comparison['Ratio Change']) > 0.1]
    shifts = shifts[shifts['Total Contribution_New'] > 10] # Filter out small channels
    
    if not shifts.empty:
        print("\n\nSignificant Role Shifts (Channels with >10 contrib & >10% ratio change):")
        print(shifts[['Assist Ratio_2025', 'Assist Ratio_New', 'Ratio Change', 'Total Contribution_New']].sort_values('Ratio Change', ascending=False).to_string())

    # 4. New Entrants
    new_channels = comparison[(comparison['Total Contribution_2025'] == 0) & (comparison['Total Contribution_New'] > 0)]
    if not new_channels.empty:
        print("\n\nNew Channels (Present in New, 0 in 2025):")
        print(new_channels[['Total Contribution_New', 'Assist Ratio_New']].sort_values('Total Contribution_New', ascending=False).to_string())
        
    output_file = '/Users/zihao_/Documents/github/直播运营复盘/comparison_analysis.csv'
    comparison.to_csv(output_file, encoding='utf-8-sig')
    print(f"\nFull comparison saved to {output_file}")

if __name__ == "__main__":
    compare_periods()
