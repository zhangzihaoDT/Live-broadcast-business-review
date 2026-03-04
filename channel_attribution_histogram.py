import pandas as pd
import plotly.express as px
import plotly.io as pio
import os

# Set Plotly to render to browser or save to html
pio.renderers.default = "browser"

def load_data(file_path):
    print(f"Loading data from {file_path}...")
    try:
        # Try reading with utf-16 (common for this project's exports)
        df = pd.read_csv(file_path, sep='\t', encoding='utf-16')
    except UnicodeError:
        try:
            # Fallback to utf-8
            df = pd.read_csv(file_path, sep='\t', encoding='utf-8')
        except Exception as e:
            print(f"Error reading file: {e}")
            return None
    except Exception as e:
        print(f"Error reading file: {e}")
        return None
    
    # Clean column names (remove potential BOM or whitespace)
    df.columns = [c.strip().replace('\ufeff', '') for c in df.columns]
    print(f"Columns: {df.columns.tolist()}")
    return df

def load_live_business_group(group_file):
    print(f"Loading Live Business group from {group_file}...")
    try:
        # Try reading with utf-8 (standard)
        group_df = pd.read_csv(group_file)
    except UnicodeError:
        try:
            # Fallback
            group_df = pd.read_csv(group_file, encoding='gbk')
        except Exception as e:
            print(f"Error reading group file: {e}")
            return []
    except Exception as e:
        print(f"Error reading group file: {e}")
        return []
        
    if 'lc_small_channel_name' in group_df.columns:
        channels = group_df['lc_small_channel_name'].unique().tolist()
        print(f"Found {len(channels)} channels in Live Business group")
        return channels
    else:
        print("Warning: 'lc_small_channel_name' not found in group file")
        return []

def analyze_and_plot(df, live_group_channels=None):
    # Ensure required columns exist
    required_cols = ['lc_small_channel_name', 'md5_锁单渠道', '度量值']
    for col in required_cols:
        if col not in df.columns:
            print(f"Missing required column: {col}")
            return

    # Filter out 0 values to reduce noise
    df_filtered = df[df['度量值'] > 0].copy()
    
    print(f"Original rows: {len(df)}, Rows with value > 0: {len(df_filtered)}")

    # Apply grouping if provided
    if live_group_channels:
        print("\nApplying Live Business grouping...")
        # Replace in Source
        mask_source = df_filtered['lc_small_channel_name'].isin(live_group_channels)
        df_filtered.loc[mask_source, 'lc_small_channel_name'] = '直播业务(Group)'
        
        # Replace in Target
        mask_target = df_filtered['md5_锁单渠道'].isin(live_group_channels)
        df_filtered.loc[mask_target, 'md5_锁单渠道'] = '直播业务(Group)'
        
        # Re-aggregate
        df_filtered = df_filtered.groupby(['lc_small_channel_name', 'md5_锁单渠道'], as_index=False)['度量值'].sum()
        print(f"Rows after grouping: {len(df_filtered)}")
        
        # Recalculate n_source, n_target as they changed
        n_source = df_filtered['lc_small_channel_name'].nunique()
        n_target = df_filtered['md5_锁单渠道'].nunique()
        print(f"Unique Channels after grouping - Source: {n_source}, Target: {n_target}")

    # 1. Pivot Matrix: Row=Source (lc_small_channel_name), Col=Target (md5_锁单渠道), Value=Sum(度量值)
    # Aggregating just in case there are duplicates
    matrix = df_filtered.pivot_table(index='lc_small_channel_name', 
                                     columns='md5_锁单渠道', 
                                     values='度量值', 
                                     aggfunc='sum',
                                     fill_value=0)
    
    print("\nTop 5 contributing channels (Source):")
    print(matrix.sum(axis=1).sort_values(ascending=False).head())

    print("\nTop 5 beneficiary channels (Target):")
    print(matrix.sum(axis=0).sort_values(ascending=False).head())
    
    # Save matrix to CSV
    matrix_file = 'channel_attribution_matrix.csv'
    matrix.to_csv(matrix_file)
    print(f"\nMatrix saved to {matrix_file}")
    
    # Calculate top channel pairs (Source -> Target)
    print("\nTop 10 Source -> Target Channel Pairs (by Contribution):")
    pairs = df_filtered.sort_values('度量值', ascending=False).head(10)
    for _, row in pairs.iterrows():
        print(f"{row['lc_small_channel_name']} -> {row['md5_锁单渠道']}: {row['度量值']}")

    # 2. Visualization
    # User asked for: "Frequency histogram plotting 'Channel -> Channel' contribution" and "One channel per row"
    
    # Approach A: Faceted Histogram (Bar Chart)
    # Since "Frequency Histogram" in Plotly (px.histogram) creates a bar chart when x is categorical and y is provided.
    # If there are too many channels, we might need to filter or split.
    
    # Let's check number of channels
    n_source = df_filtered['lc_small_channel_name'].nunique()
    n_target = df_filtered['md5_锁单渠道'].nunique()
    print(f"\nUnique Source Channels: {n_source}")
    print(f"Unique Target Channels: {n_target}")

    # If too many source channels, we might want to focus on top contributors or create a very tall plot.
    # We will sort the dataframe by source channel total contribution for better plotting order
    source_totals = df_filtered.groupby('lc_small_channel_name')['度量值'].sum().sort_values(ascending=False)
    
    # Keep only top 10 sources as requested
    top_sources = source_totals.head(10).index.tolist()
    print(f"\nFiltering for Top 10 Source Channels: {top_sources}")
    
    df_filtered = df_filtered[df_filtered['lc_small_channel_name'].isin(top_sources)]
    
    # Sort target channels by contribution for better visualization within histograms
    # We want the bars to be sorted descending by value. 
    # Since px.histogram with facet_row shares the x-axis order, we should probably sort by the total contribution to the top source?
    # Or just global top targets? Let's try global top targets first.
    # User request: "Sort by TOP 1's order"
    # Find the top 1 source
    top_1_source = top_sources[0]
    print(f"Sorting x-axis by contribution to Top 1 Source: {top_1_source}")
    
    top_1_data = df_filtered[df_filtered['lc_small_channel_name'] == top_1_source]
    top_1_targets = top_1_data.sort_values('度量值', ascending=False)['md5_锁单渠道'].tolist()
    
    # Add any remaining targets that might not be in top 1 (unlikely but safe)
    all_targets = df_filtered['md5_锁单渠道'].unique().tolist()
    remaining = [t for t in all_targets if t not in top_1_targets]
    sorted_targets = top_1_targets + remaining
    
    # Reorder dataframe
    df_filtered['lc_small_channel_name'] = pd.Categorical(df_filtered['lc_small_channel_name'], categories=top_sources, ordered=True)
    df_filtered['md5_锁单渠道'] = pd.Categorical(df_filtered['md5_锁单渠道'], categories=sorted_targets, ordered=True)
    df_filtered = df_filtered.sort_values(['lc_small_channel_name', 'md5_锁单渠道'])
    
    # Update n_source after filtering
    n_source = df_filtered['lc_small_channel_name'].nunique()
    print(f"Plotting {n_source} channels...")

    # Create the plot
    # "One channel per row" implies facet_row.
    # We use height per row to ensure it's readable.
    
    height_per_row = 150 # Increased height slightly for better visibility
    total_height = max(600, n_source * height_per_row)
    
    print(f"Generating plot with height {total_height}px...")

    # Calculate safe vertical spacing
    # Use 5% of total height for spacing (more standard)
    if n_source > 1:
        safe_spacing = 0.05 / (n_source - 1) if (n_source - 1) > 0 else 0.1
    else:
        safe_spacing = 0.1

    fig = px.histogram(df_filtered, 
                       x='md5_锁单渠道', 
                       y='度量值', 
                       facet_row='lc_small_channel_name',
                       color='md5_锁单渠道', # Color by target channel to make it distinct
                       title='Top 10 Channel Contribution Attribution (Row Channel -> Col Channel)',
                       labels={'lc_small_channel_name': 'Source Channel', 'md5_锁单渠道': 'Target Channel', '度量值': 'Contribution'},
                       height=total_height,
                       facet_row_spacing=safe_spacing)
    
    # Update y-axes to match (unified scale)
    fig.update_yaxes(matches='y') 
    
    # Update x-axes to match sorting order
    fig.update_xaxes(categoryorder='array', categoryarray=sorted_targets)
    
    # Rotate facet labels to horizontal and adjust their position
    # By default, facet labels are rotated 90 degrees on the right.
    # We will rotate them to 0 degrees.
    fig.for_each_annotation(lambda a: a.update(textangle=0))
    
    # Adjust layout to make sure labels are visible and provide space for horizontal labels
    fig.update_layout(
        showlegend=False,
        margin=dict(l=200, r=150, t=80, b=50) # Increased right margin for horizontal labels
    )
    
    output_file = 'channel_attribution_histogram.html'
    fig.write_html(output_file)
    print(f"Plot saved to {output_file}")

if __name__ == "__main__":
    file_path = '渠道归因（行渠道给列渠道贡献了多少锁单用户）_data.csv'
    if os.path.exists(file_path):
        df = load_data(file_path)
        if df is not None:
            # Load group file
            group_file = '直播业务_group_2025.csv'
            live_channels = []
            if os.path.exists(group_file):
                live_channels = load_live_business_group(group_file)
            else:
                print(f"Group file not found: {group_file}")

            analyze_and_plot(df, live_group_channels=live_channels)
    else:
        print(f"File not found: {file_path}")
