import argparse
import subprocess
import os
import sys
from datetime import datetime

def run_command(command):
    print(f"Executing: {' '.join(command)}")
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='Run the Live Stream Analysis Pipeline.')
    parser.add_argument('--excel', required=True, help='Path to the session Excel file (e.g., 直播复盘表2026-02-27.xlsx)')
    parser.add_argument('--csv', required=True, help='Path to the leads CSV file (e.g., IM智己汽车 0201～0227.csv)')
    parser.add_argument('--channel', '-c', help='Target channel name for conversion analysis (auto-detected from filename if not specified)')
    parser.add_argument('--start-date', '-s', help='Cohort start date (YYYY-MM-DD), default: from Excel sessions')
    parser.add_argument('--end-date', '-e', help='Cohort end date (YYYY-MM-DD), default: from Excel sessions')
    
    args = parser.parse_args()
    
    excel_path = os.path.abspath(args.excel)
    csv_path = os.path.abspath(args.csv)
    target_channel = args.channel
    start_date = args.start_date
    end_date = args.end_date
    
    # Generate timestamp for unique reports (Removed for overwrite logic)
    # timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Define output directory
    reports_dir = os.path.join(os.getcwd(), 'reports')
    if not os.path.exists(reports_dir):
        os.makedirs(reports_dir)
        
    # Get base filenames without extension
    excel_name = os.path.splitext(os.path.basename(excel_path))[0]
    csv_name = os.path.splitext(os.path.basename(csv_path))[0]
    
    # Define output filenames
    # 1. Intermediate CSV
    # Include input filenames to avoid confusion, but no timestamp to allow overwrite
    intermediate_csv_name = f"session_leads_{excel_name}.csv"
    intermediate_csv = os.path.join(reports_dir, intermediate_csv_name)
    
    # 2. Dashboard Report
    dashboard_report_name = f"Dashboard_{excel_name}.html"
    dashboard_report_path = os.path.join(reports_dir, dashboard_report_name)
    
    # 3. Conversion Report
    conversion_report_name = f"Conversion_{csv_name}.html"
    conversion_report_path = os.path.join(reports_dir, conversion_report_name)
    
    print("="*50)
    print("Step 1: Calculate Leads per Session")
    print("="*50)
    
    # Get the directory of the current script to find other scripts
    base_dir = os.path.dirname(os.path.abspath(__file__))
    calculate_script = os.path.join(base_dir, 'Dashboard_Step1_Leads.py')
    dashboard_script = os.path.join(base_dir, 'Dashboard_Step3_Report.py')
    
    # Run Dashboard_Step1_Leads.py
    cmd1 = [
        sys.executable, calculate_script,
        '--excel', excel_path,
        '--csv', csv_path,
        '--output', intermediate_csv
    ]
    run_command(cmd1)
    
    print("\n" + "="*50)
    print("Step 2: Generate Dashboard & Conversion Reports")
    print("="*50)
    
    # Run dashboard_analysis.py
    # This script will also call analyze_im_conversion internally to generate the second report
    cmd2 = [
        sys.executable, dashboard_script,
        '--input', intermediate_csv,
        '--raw', csv_path,
        '--output', dashboard_report_path,
        '--conversion-output', conversion_report_path
    ]
    if target_channel:
        cmd2.extend(['--channel', target_channel])
    if start_date:
        cmd2.extend(['--start-date', start_date])
    if end_date:
        cmd2.extend(['--end-date', end_date])
    run_command(cmd2)
    
    print("\n" + "="*50)
    print("Pipeline Complete!")
    print(f"Generated Reports in '{reports_dir}':")
    print(f"1. Dashboard: {dashboard_report_name}")
    print(f"2. Conversion Analysis: {conversion_report_name}")
    print(f"3. Intermediate Data: {intermediate_csv_name}")
    print("="*50)

if __name__ == "__main__":
    main()
