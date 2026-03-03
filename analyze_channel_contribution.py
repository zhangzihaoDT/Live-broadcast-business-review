import pandas as pd
import os
import numpy as np

def analyze_channel_contribution(file_path):
    print(f"Loading {file_path}...")
    try:
        # Load data (handling utf-16 and potential BOM)
        df = pd.read_csv(file_path, encoding='utf-16', sep='\t')
        
        # Normalize column names (strip BOM if present)
        df.columns = [c.strip().replace('\ufeff', '') for c in df.columns]
        
        print("Columns found:", df.columns.tolist())
        
        # Check required columns
        required_cols = ['lc_small_channel_name', '度量名称', '度量值']
        if not all(col in df.columns for col in required_cols):
            print(f"Error: Missing one of required columns {required_cols}")
            return

        # Pivot the table
        # We want one row per channel, with columns for each metric
        # Assuming '直播业务分组' is also a dimension we might want to keep or just drop if we aggregate by channel
        
        # If '直播业务分组' exists, let's include it in index to be safe, then we can aggregate later
        index_cols = ['lc_small_channel_name']
        if '直播业务分组' in df.columns:
            index_cols.insert(0, '直播业务分组')
            
        print(f"Pivoting data... Index: {index_cols}")
        
        # Pivot
        df_pivot = df.pivot_table(
            index=index_cols, 
            columns='度量名称', 
            values='度量值', 
            aggfunc='sum', # Use sum in case there are duplicates, though likely 'first' is enough if unique
            fill_value=0
        ).reset_index()
        
        # Clean up column names (remove name of columns index)
        df_pivot.columns.name = None
        
        # Ensure numeric columns
        metric_cols = ['主锁单标记', 'md5_辅助锁单']
        for col in metric_cols:
            if col in df_pivot.columns:
                df_pivot[col] = pd.to_numeric(df_pivot[col], errors='coerce').fillna(0)
            else:
                df_pivot[col] = 0
                
        # Group by channel (in case '直播业务分组' split the same channel into multiple rows)
        # The user asked for "different lc_small_channel_name", so we aggregate by channel.
        df_channel = df_pivot.groupby('lc_small_channel_name')[metric_cols].sum().reset_index()
        
        # Calculate Metrics
        df_channel['Total Contribution'] = df_channel['主锁单标记'] + df_channel['md5_辅助锁单']
        
        # Avoid division by zero
        df_channel['Assist Ratio'] = df_channel.apply(
            lambda row: row['md5_辅助锁单'] / row['Total Contribution'] if row['Total Contribution'] > 0 else 0, 
            axis=1
        )
        
        # Sort by Total Contribution desc
        df_channel = df_channel.sort_values('Total Contribution', ascending=False)
        
        # Add Assessment
        def assess_channel(row):
            total = row['Total Contribution']
            ratio = row['Assist Ratio']
            
            if total == 0:
                return "No Contribution"
            
            if ratio < 0.3:
                role = "Strong Closer (Direct Lock dominant)"
            elif ratio > 0.7:
                role = "Strong Assister (Assisted Lock dominant)"
            else:
                role = "Balanced Contributor"
                
            return role

        df_channel['Role Assessment'] = df_channel.apply(assess_channel, axis=1)
        
        # Print Results
        print("\n=== Channel Contribution Analysis ===")
        print(df_channel[['lc_small_channel_name', '主锁单标记', 'md5_辅助锁单', 'Total Contribution', 'Assist Ratio', 'Role Assessment']].to_string(index=False))
        
        # Generate a summary CSV
        output_file = file_path.replace('.csv', '_contribution_analysis.csv')
        df_channel.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"\nDetailed analysis saved to: {output_file}")
        
        # --- Module 4: Analyze '直播业务分组' = A ---
        print("\n=== Module 4: '直播业务分组' = A Analysis ===")
        
        # Calculate Grand Totals (All Groups)
        grand_total_direct = df_pivot['主锁单标记'].sum()
        grand_total_assisted = df_pivot['md5_辅助锁单'].sum()
        grand_total_contribution = grand_total_direct + grand_total_assisted
        
        print(f"Grand Total (All Groups):")
        print(f"  - Total Direct Locks: {grand_total_direct}")
        print(f"  - Total Assisted Locks: {grand_total_assisted}")
        print(f"  - Total Contribution: {grand_total_contribution}")
        
        if '直播业务分组' in df_pivot.columns:
            # Filter for Group A
            # Handle potential case sensitivity or extra spaces
            df_group_a = df_pivot[df_pivot['直播业务分组'].astype(str).str.strip().str.upper() == 'A'].copy()
            
            if df_group_a.empty:
                print("No data found for '直播业务分组' = A")
            else:
                # Aggregate metrics for Group A
                group_a_direct = df_group_a['主锁单标记'].sum()
                group_a_assisted = df_group_a['md5_辅助锁单'].sum()
                group_a_total = group_a_direct + group_a_assisted
                
                assist_ratio = group_a_assisted / group_a_total if group_a_total > 0 else 0
                
                # Calculate Share of Grand Total
                share_direct = group_a_direct / grand_total_direct if grand_total_direct > 0 else 0
                share_assisted = group_a_assisted / grand_total_assisted if grand_total_assisted > 0 else 0
                share_total = group_a_total / grand_total_contribution if grand_total_contribution > 0 else 0

                print(f"\nGroup A Contribution to Overall Business:")
                print(f"  - Share of Total Direct Locks: {share_direct:.2%} ({group_a_direct}/{grand_total_direct})")
                print(f"  - Share of Total Assisted Locks: {share_assisted:.2%} ({group_a_assisted}/{grand_total_assisted})")
                print(f"  - Share of Total Contribution: {share_total:.2%} ({group_a_total}/{grand_total_contribution})")
                
                # Breakdown by Channel within Group A with Global Share
                print("\nGroup A - Channel Breakdown (with Global Share):")
                df_group_a['Total Contribution'] = df_group_a['主锁单标记'] + df_group_a['md5_辅助锁单']
                
                # Internal Assist Ratio
                df_group_a['Assist Ratio'] = df_group_a.apply(
                    lambda row: row['md5_辅助锁单'] / row['Total Contribution'] if row['Total Contribution'] > 0 else 0, 
                    axis=1
                )
                
                # Global Share Metrics
                df_group_a['Global Direct Share'] = df_group_a['主锁单标记'] / grand_total_direct
                df_group_a['Global Assisted Share'] = df_group_a['md5_辅助锁单'] / grand_total_assisted
                
                # Formatting for display
                display_cols = ['lc_small_channel_name', '主锁单标记', 'md5_辅助锁单', 'Total Contribution', 'Assist Ratio', 'Global Direct Share', 'Global Assisted Share']
                
                # Sort by Global Assisted Share (since it seems to be the main value prop)
                df_group_a = df_group_a.sort_values('Global Assisted Share', ascending=False)
                
                # Format percentages for display
                df_display = df_group_a[display_cols].copy()
                df_display['Assist Ratio'] = df_display['Assist Ratio'].apply(lambda x: f"{x:.2%}")
                df_display['Global Direct Share'] = df_display['Global Direct Share'].apply(lambda x: f"{x:.2%}")
                df_display['Global Assisted Share'] = df_display['Global Assisted Share'].apply(lambda x: f"{x:.2%}")
                
                print(df_display.to_string(index=False))
                
                # Save this specific view
                group_a_file = file_path.replace('.csv', '_group_a_analysis.csv')
                df_group_a.to_csv(group_a_file, index=False, encoding='utf-8-sig')
                print(f"\nGroup A detailed analysis saved to: {group_a_file}")

        else:
             print("Column '直播业务分组' not found in pivoted data. Check input file columns.")

    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    file_path = '/Users/zihao_/Documents/github/直播运营复盘/直播业务_data_2025.csv'
    analyze_channel_contribution(file_path)
