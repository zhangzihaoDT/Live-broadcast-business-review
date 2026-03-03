import pandas as pd
import os
import re
from datetime import datetime
import numpy as np

def generate_pivoted_schema(file_path, output_file):
    print(f"Loading {file_path}...")
    try:
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
    
    # --- Pivot Logic ---
    print("Pivoting data...")
    index_cols = [c for c in df.columns if c not in ['度量名称', '度量值']]
    
    df_temp = df.copy()
    for col in index_cols:
        if df_temp[col].dtype == 'object':
            df_temp[col] = df_temp[col].fillna('__NAN_PLACEHOLDER__')
        else:
            df_temp[col] = df_temp[col].fillna(-999999)

    try:
        df_wide = df_temp.pivot_table(index=index_cols, columns='度量名称', values='度量值', aggfunc='first').reset_index()
        
        for col in index_cols:
            if df_wide[col].dtype == 'object':
                df_wide[col] = df_wide[col].replace('__NAN_PLACEHOLDER__', np.nan)
            else:
                df_wide[col] = df_wide[col].replace(-999999, np.nan)
        
        df = df_wide
        print(f"Pivot successful. New shape: {df.shape}")
    except Exception as e:
        print(f"Pivot failed: {e}")
        return

    # --- Generate Schema Content ---
    
    # Time Analysis on Pivoted Data
    time_stats = None
    date_col = None
    possible_cols = ["lc_create_time", "create_time", "time", "date"]
    for col in df.columns:
        if any(p in str(col).lower() for p in possible_cols):
             # Check if it has valid dates
             try:
                 pd.to_datetime(df[col], errors='raise')
                 date_col = col
                 break
             except:
                 continue
    
    if date_col:
        dates = pd.to_datetime(df[date_col], errors='coerce').dropna().sort_values()
        if not dates.empty:
            unique_days = sorted(list(set(d.date() for d in dates)))
            day_counts = dates.dt.date.value_counts()
            
            time_stats = {
                "col_name": date_col,
                "start": dates.iloc[0],
                "end": dates.iloc[-1],
                "days_covered": len(unique_days),
                "total_records": len(dates),
                "granularity": "Sub-daily" if day_counts.max() > 1 else "Daily",
                "max_records_per_day": day_counts.max()
            }

    markdown_content = f"\n\n# Schema for {os.path.basename(file_path)} (Pivoted Wide Format)\n\n"
    markdown_content += f"> Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    markdown_content += f"> Note: Data was pivoted from Long to Wide format using '度量名称' as columns.\n\n"
    
    markdown_content += f"## File Content\n\n"
    
    if time_stats:
        markdown_content += "### 🕒 Time Dimension Analysis\n"
        markdown_content += f"- **Date Column:** {time_stats['col_name']}\n"
        markdown_content += f"- **Time Range:** {time_stats['start']} to {time_stats['end']}\n"
        markdown_content += f"- **Granularity:** {time_stats['granularity']}\n"
        markdown_content += f"- **Coverage:** {time_stats['days_covered']} days ({time_stats['total_records']} records)\n"
        markdown_content += f"- **Max Records/Day:** {time_stats['max_records_per_day']}\n\n"

    markdown_content += f"### 📋 Data Structure\n"
    markdown_content += f"- **Rows:** {df.shape[0]}\n"
    markdown_content += f"- **Columns:** {df.shape[1]}\n\n"
    
    markdown_content += "| Column Name | Data Type | Non-Null Count | Sample Value |\n"
    markdown_content += "|---|---|---|---|\n"
    
    for col in df.columns:
        dtype = df[col].dtype
        non_null_count = df[col].count()
        sample_val = df[col].dropna().iloc[0] if not df[col].dropna().empty else "N/A"
        sample_str = str(sample_val)
        if len(sample_str) > 50:
            sample_str = sample_str[:47] + "..."
        
        clean_col = str(col).strip()
        markdown_content += f"| {clean_col} | {dtype} | {non_null_count} | {sample_str} |\n"
    
    markdown_content += "\n"
    
    # Read existing schema
    with open(output_file, 'r', encoding='utf-8') as f:
        existing_content = f.read()
        
    # Split to keep the first part (Excel schema) and replace the second part
    # Assuming the second part starts with "# Schema for IM智己汽车"
    split_marker = "# Schema for IM智己汽车"
    if split_marker in existing_content:
        base_content = existing_content.split(split_marker)[0]
    else:
        base_content = existing_content
        
    final_content = base_content + markdown_content
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(final_content)
        
    print(f"Schema updated successfully: {output_file}")

if __name__ == "__main__":
    csv_file = "/Users/zihao_/Documents/github/直播运营复盘/IM智己汽车 0201～0227.csv"
    output_md = "schema.md"
    generate_pivoted_schema(csv_file, output_md)
