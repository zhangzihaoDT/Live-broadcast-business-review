
import pandas as pd
import re
import argparse
import os
from datetime import datetime, timedelta

def parse_duration(duration_str):
    if not isinstance(duration_str, str) or duration_str == '--':
        return timedelta(0)
    
    hours = 0
    minutes = 0
    seconds = 0
    
    # Regex to extract hours, minutes, seconds
    h_match = re.search(r'(\d+)时', duration_str)
    m_match = re.search(r'(\d+)分', duration_str)
    s_match = re.search(r'(\d+)秒', duration_str)
    
    if h_match:
        hours = int(h_match.group(1))
    if m_match:
        minutes = int(m_match.group(1))
    if s_match:
        seconds = int(s_match.group(1))
        
    return timedelta(hours=hours, minutes=minutes, seconds=seconds)

def parse_session_time(time_str):
    # Format: 2月26日19点 -> 2026-02-26 19:00:00
    try:
        match = re.match(r'(\d+)月(\d+)日(\d+)点', time_str)
        if match:
            month = int(match.group(1))
            day = int(match.group(2))
            hour = int(match.group(3))
            return datetime(2026, month, day, hour, 0, 0)
    except:
        pass
    return None

def main():
    parser = argparse.ArgumentParser(description='Calculate leads per session.')
    parser.add_argument('--excel', required=True, help='Path to the session Excel file')
    parser.add_argument('--csv', required=True, help='Path to the leads CSV file')
    parser.add_argument('--output', default='session_leads_count.csv', help='Path to the output CSV file')
    
    args = parser.parse_args()
    
    excel_path = args.excel
    csv_path = args.csv
    output_path = args.output

    print(f"Processing sessions from: {excel_path}")
    print(f"Processing leads from: {csv_path}")

    # Load Excel
    df_sessions = pd.read_excel(excel_path)

    # Filter valid sessions
    sessions = []
    for index, row in df_sessions.iterrows():
        session_name = row['指标/场次']
        duration_str = row['直播时长']
        
        if session_name in ['场均', '总计', '自然流量', '自然流量/非直播时段']:
            continue
            
        start_time = parse_session_time(session_name)
        if start_time:
            duration = parse_duration(duration_str)
            end_time = start_time + duration
            
            # Extract additional metrics
            ad_spend = row.get('广告消耗', 0)
            business_opps = row.get('全场景商机数', 0)
            exposure = row.get('曝光人数', 0)
            views = row.get('场观', 0)
            clicks = row.get('小风车点击次数', 0)
            
            sessions.append({
                'session_name': session_name,
                'start_time': start_time,
                'end_time': end_time,
                'duration': duration,
                'ad_spend': ad_spend,
                'business_opps': business_opps,
                'exposure': exposure,
                'views': views,
                'clicks': clicks,
                'leads_count': 0,
                'leads': set()
            })

    # Sort sessions by start time to ensure consistent attribution
    sessions.sort(key=lambda x: x['start_time'])

    print(f"Loaded {len(sessions)} valid sessions.")
    if not sessions:
        print("No valid sessions found in Excel. Exiting.")
        return

    # Load CSV
    # Try utf-16 with tab separator first based on previous inspection
    try:
        df_leads = pd.read_csv(csv_path, encoding='utf-16', sep='\t')
    except:
        # Fallback
        df_leads = pd.read_csv(csv_path, encoding='gbk')

    print(f"Loaded {len(df_leads)} leads records.")

    # Parse lead times
    df_leads['parsed_time'] = pd.to_datetime(df_leads['lc_create_time'], errors='coerce')

    start_date = pd.Timestamp(sessions[0]['start_time'])
    end_date = pd.Timestamp(max(s['end_time'] for s in sessions))
    print(f"Using cohort time range (from Excel sessions): {start_date} to {end_date}")
    
    # Extract channel name from filename or use default
    # If the CSV filename contains "IM智己|未来智舱", we might want to use that as channel name?
    # Or we should check what's in the CSV 'lc_small_channel_name' column.
    
    # Check available channels
    available_channels = df_leads['lc_small_channel_name'].unique()
    print(f"Available channels in CSV: {available_channels}")
    
    # Try to determine target channel
    target_channel = "IM智己汽车" # Default
    if "IM智己|未来智舱" in os.path.basename(csv_path):
         if "IM智己|未来智舱" in available_channels:
             target_channel = "IM智己|未来智舱"
         elif "IM智己｜未来智舱" in available_channels: # Check for different pipe character
             target_channel = "IM智己｜未来智舱"
    elif "智己生活家" in os.path.basename(csv_path):
        target_channel = "智己生活家"
    elif "智己汽车官方直播" in os.path.basename(csv_path):
        target_channel = "智己汽车官方直播"
    elif "智己生活家" in os.path.basename(csv_path):
        target_channel = "智己生活家"

    print(f"Using target channel: {target_channel}")

    mask_time = (df_leads['parsed_time'] >= start_date) & (df_leads['parsed_time'] <= end_date)
    mask_channel = df_leads['lc_small_channel_name'] == target_channel

    df_leads_filtered = df_leads[mask_time & mask_channel].copy()
    print(f"Filtered {len(df_leads_filtered)} leads in cohort ({start_date} to {end_date}, {target_channel}).")

    # Match leads to sessions
    for index, lead in df_leads_filtered.iterrows():
        lead_time = lead['parsed_time']
        lead_id = lead['lc_main_code']
        
        if pd.isna(lead_time):
            continue
            
        for session in sessions:
            if session['start_time'] <= lead_time <= session['end_time']:
                session['leads'].add(lead_id)
                # A lead can belong to multiple sessions? Usually not if they don't overlap.
                # But let's assume it belongs to the first one it matches or all?
                # Given sessions are distinct, it should match one.
                break

    # Calculate counts and derived metrics
    results = []
    total_assigned_leads = 0
    assigned_leads_set = set()

    for session in sessions:
        unique_leads_count = len(session['leads'])
        total_assigned_leads += unique_leads_count
        assigned_leads_set.update(session['leads'])
        
        ad_spend = session['ad_spend']
        business_opps = session['business_opps']
        clicks = session['clicks']
        exposure = session['exposure']
        
        # Calculate derived metrics with zero division protection
        cpl = ad_spend / unique_leads_count if unique_leads_count > 0 else 0
        cplo = ad_spend / business_opps if business_opps > 0 else 0
        click_conversion_rate = unique_leads_count / clicks if clicks > 0 else 0
        exposure_conversion_rate = unique_leads_count / exposure if exposure > 0 else 0
        
        results.append({
            'session': session['session_name'],
            'start_time': session['start_time'],
            'end_time': session['end_time'],
            'duration': session['duration'],
            'unique_leads': unique_leads_count,
            '全场景商机数': business_opps,
            '曝光人数': exposure,
            '场观': session['views'],
            '小风车点击次数': clicks,
            '广告消耗': ad_spend,
            'CPL': cpl,
            'CPLO': cplo,
            '点击转化率': click_conversion_rate,
            '曝光转化率': exposure_conversion_rate
        })

    print(f"Total leads assigned across all sessions: {total_assigned_leads}")
    print(f"Total unique leads assigned: {len(assigned_leads_set)}")

    # Create DataFrame for results
    df_results = pd.DataFrame(results)
    print("\nResults:")
    print(df_results[['session', 'unique_leads', 'CPL', 'CPLO', '点击转化率', '曝光转化率']].to_string())

    # Save results to CSV
    df_results.to_csv(output_path, index=False)
    print(f"\nSaved results to {output_path}")

if __name__ == "__main__":
    main()
