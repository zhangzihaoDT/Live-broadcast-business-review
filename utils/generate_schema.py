import pandas as pd
import os
import re
from datetime import datetime

def parse_custom_date(val):
    """
    Parses date from string values like "2月26日19点" or standard formats.
    Returns datetime object or None.
    """
    val_str = str(val).strip()
    
    # Skip summary rows
    if any(x in val_str for x in ["场均", "汇总", "总计"]):
        return None
    
    # Regex patterns
    # Pattern 1: M月D日H点 (e.g., 2月26日19点)
    match_time = re.search(r'(\d{1,2})月(\d{1,2})日\s*(\d{1,2})点', val_str)
    # Pattern 2: YYYY/MM/DD or YYYY-MM-DD
    match_date = re.search(r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})', val_str)
    # Pattern 3: MM/DD
    match_short_date = re.search(r'(\d{1,2})[-/](\d{1,2})', val_str)
    
    try:
        if match_time:
            month, day, hour = map(int, match_time.groups())
            return datetime(2026, month, day, hour) # Assuming 2026
        elif match_date:
            year, month, day = map(int, match_date.groups())
            return datetime(year, month, day)
        elif match_short_date:
            month, day = map(int, match_short_date.groups())
            return datetime(2026, month, day) # Assuming 2026
    except:
        return None
    
    return None

def analyze_time_dimension(df, col_name="指标/场次"):
    """
    Analyzes a specific column for time dimension properties.
    """
    if col_name not in df.columns:
        return None

    dates = []
    for val in df[col_name]:
        dt = parse_custom_date(val)
        if dt:
            dates.append(dt)
            
    if not dates:
        return None
        
    dates.sort()
    unique_days = sorted(list(set(d.date() for d in dates)))
    
    # Calculate granularity
    day_counts = {}
    for d in dates:
        day_str = d.strftime('%Y-%m-%d')
        day_counts[day_str] = day_counts.get(day_str, 0) + 1
    
    max_records_per_day = max(day_counts.values()) if day_counts else 0
    granularity = "Sub-daily (Session/Hour)" if max_records_per_day > 1 else "Daily"
    
    return {
        "start": dates[0],
        "end": dates[-1],
        "days_covered": len(unique_days),
        "total_records": len(dates),
        "granularity": granularity,
        "max_records_per_day": max_records_per_day
    }

def generate_schema(file_path, output_file):
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' not found.")
        return

    try:
        # Load the Excel file
        xls = pd.ExcelFile(file_path)
        
        markdown_content = f"# Schema for {os.path.basename(file_path)}\n\n"
        markdown_content += f"> Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        for sheet_name in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name=sheet_name)
            
            markdown_content += f"## Sheet: {sheet_name}\n\n"
            
            # --- Time Dimension Analysis ---
            time_stats = analyze_time_dimension(df)
            if time_stats:
                markdown_content += "### 🕒 Time Dimension Analysis\n"
                markdown_content += f"- **Time Range:** {time_stats['start']} to {time_stats['end']}\n"
                markdown_content += f"- **Granularity:** {time_stats['granularity']}\n"
                markdown_content += f"- **Coverage:** {time_stats['days_covered']} days ({time_stats['total_records']} sessions)\n"
                markdown_content += f"- **Max Sessions/Day:** {time_stats['max_records_per_day']}\n\n"
            # -------------------------------

            markdown_content += f"### 📋 Data Structure\n"
            markdown_content += f"- **Rows:** {df.shape[0]}\n"
            markdown_content += f"- **Columns:** {df.shape[1]}\n\n"
            
            markdown_content += "| Column Name | Data Type | Non-Null Count | Sample Value |\n"
            markdown_content += "|---|---|---|---|\n"
            
            for col in df.columns:
                dtype = df[col].dtype
                non_null_count = df[col].count()
                # Get a sample value (first non-null)
                sample_val = df[col].dropna().iloc[0] if not df[col].dropna().empty else "N/A"
                # Truncate long sample values
                sample_str = str(sample_val)
                if len(sample_str) > 50:
                    sample_str = sample_str[:47] + "..."
                
                markdown_content += f"| {col} | {dtype} | {non_null_count} | {sample_str} |\n"
            
            markdown_content += "\n"
            
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
            
        print(f"Schema generated successfully: {output_file}")
        
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    excel_file = "/Users/zihao_/Documents/github/直播运营复盘/直播复盘表2026-02-27.xlsx"
    output_md = "schema.md"
    generate_schema(excel_file, output_md)
