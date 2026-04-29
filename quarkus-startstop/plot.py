import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys
import os
from pathlib import Path
import glob

def find_native_measurements(base_folder):
    """Find all measurements.csv files in *Native directories"""
    pattern = os.path.join(base_folder, "archived-logs/io.quarkus.ts.startstop.StartStopTest/*Native/measurements.csv")
    return glob.glob(pattern)

def read_measurements_csv(csv_path):
    """Read measurements.csv and return DataFrame"""
    try:
        df = pd.read_csv(csv_path)
        return df
    except Exception as e:
        print(f"Error reading {csv_path}: {e}")
        return None

# Parse command line arguments
if len(sys.argv) < 2:
    print("Usage: python plot_native.py <folder1> [folder2] [folder3] ...")
    print("Example: python plot_native.py data/20260429-oracle-graal-13416/target3-33-1-jdk25-defaults data/20260429-oracle-graal-13416/target3-33-1-jdk25-complete-reflection")
    sys.exit(1)

folders = sys.argv[1:]

# Collect all data
all_data = []
config_names = []

for folder in folders:
    csv_files = find_native_measurements(folder)
    
    if not csv_files:
        print(f"Warning: No *Native measurements.csv files found in {folder}")
        continue
    
    # Use the folder name as the configuration name
    config_name = os.path.basename(folder.rstrip('/'))
    config_names.append(config_name)
    
    print(f"\nProcessing {config_name}:")
    
    for csv_file in csv_files:
        # Extract test name from path (e.g., fullMicroProfileNative)
        test_name = os.path.basename(os.path.dirname(csv_file))
        
        df = read_measurements_csv(csv_file)
        if df is not None:
            # Add metadata columns
            df['Configuration'] = config_name
            df['TestName'] = test_name
            all_data.append(df)
            print(f"  - {test_name}: {len(df)} measurements")

if not all_data:
    print("\nError: No data was loaded from any folder")
    sys.exit(1)

# Combine all data
combined_df = pd.concat(all_data, ignore_index=True)

# Strip common prefix from configuration names if there is one
if len(config_names) > 1:
    common_prefix = os.path.commonprefix(config_names)
    common_prefix = common_prefix.rstrip('-_. ')
    
    if common_prefix:
        print(f"\nStripping common prefix: '{common_prefix}'")
        combined_df['Configuration'] = combined_df['Configuration'].str[len(common_prefix):].str.lstrip('-_. ')
        config_names = [name[len(common_prefix):].lstrip('-_. ') for name in config_names]

# Get unique configurations and test names
configurations = combined_df['Configuration'].unique()
test_names = sorted(combined_df['TestName'].unique())

print(f"\nConfigurations: {', '.join(configurations)}")
print(f"Test names: {', '.join(test_names)}")

# Define pastel color palette
pastel_colors = [
    '#AEC7E8',  # pastel blue
    '#FFBB78',  # pastel orange
    '#98DF8A',  # pastel green
    '#FF9896',  # pastel red
    '#C5B0D5',  # pastel purple
    '#C49C94',  # pastel brown
    '#F7B6D2',  # pastel pink
    '#C7C7C7',  # pastel gray
    '#DBDB8D',  # pastel olive
    '#9EDAE5',  # pastel cyan
]

# Create color mapping for configurations
color_map = {config: pastel_colors[i % len(pastel_colors)] for i, config in enumerate(configurations)}

# Define metrics to plot
metrics = [
    ('buildTimeMs', 'Build Time (ms)', 'Build Time Distribution'),
    ('timeToFirstOKRequestMs', 'Time to First Request (ms)', 'Time to First Request Distribution'),
    ('startedInMs', 'Started In (ms)', 'Startup Time Distribution'),
    ('RSSkB', 'RSS (kB)', 'RSS Memory Distribution'),
]

# Create subplots - one row per test, one column per metric
num_tests = len(test_names)
num_metrics = len(metrics)

# Create subplot titles - show metric names in first row only
subplot_titles = []
for test_idx, test in enumerate(test_names):
    for metric_idx, metric in enumerate(metrics):
        # First row: show metric title
        subplot_titles.append(metric[2])

fig = make_subplots(
    rows=num_tests, cols=num_metrics,
    subplot_titles=subplot_titles,
    vertical_spacing=0.30,
    horizontal_spacing=0.05,
    specs=[[{"type": "violin"} for _ in range(num_metrics)] for _ in range(num_tests)],
    row_titles=test_names
)

# Add violin plots
for test_idx, test_name in enumerate(test_names, start=1):
    test_data = combined_df[combined_df['TestName'] == test_name]
    
    for metric_idx, (metric_col, metric_label, metric_title) in enumerate(metrics, start=1):
        for config in configurations:
            config_data = test_data[test_data['Configuration'] == config][metric_col]
            
            if len(config_data) > 0:
                fig.add_trace(
                    go.Violin(
                        y=config_data,
                        name=config,
                        box_visible=True,
                        meanline_visible=True,
                        fillcolor=color_map[config],
                        opacity=0.7,
                        x0=config,
                        legendgroup=config,
                        showlegend=(test_idx == 1 and metric_idx == 1)  # Only show legend once
                    ),
                    row=test_idx, col=metric_idx
                )

# Update axes labels
for test_idx, test_name in enumerate(test_names, start=1):
    for metric_idx, (metric_col, metric_label, metric_title) in enumerate(metrics, start=1):
        fig.update_xaxes(title_text="Configuration", tickangle=45, row=test_idx, col=metric_idx)
        fig.update_yaxes(title_text=metric_label, row=test_idx, col=metric_idx)

# Update overall layout
fig.update_layout(
    title_text="Quarkus StartStop Native Tests Performance Comparison",
    height=550 * num_tests,
    width=450 * num_metrics,
    showlegend=True,
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1
    )
)

# Save the plot
output_file = 'report.html'
fig.write_html(output_file, include_plotlyjs=True)

print(f"\nReport saved as {output_file}")
print(f"Total measurements: {len(combined_df)}")
print(f"Configurations: {', '.join(configurations)}")
print(f"Tests: {', '.join(test_names)}")

# Print summary statistics
print("\n" + "="*80)
print("SUMMARY STATISTICS")
print("="*80)

for test_name in test_names:
    print(f"\n{test_name}:")
    print("-" * 80)
    test_data = combined_df[combined_df['TestName'] == test_name]
    
    for config in configurations:
        config_data = test_data[test_data['Configuration'] == config]
        if len(config_data) > 0:
            print(f"\n  {config}:")
            print(f"    Build Time: {config_data['buildTimeMs'].mean():.1f} ms (±{config_data['buildTimeMs'].std():.1f})")
            print(f"    Time to First Request: {config_data['timeToFirstOKRequestMs'].mean():.1f} ms (±{config_data['timeToFirstOKRequestMs'].std():.1f})")
            print(f"    Started In: {config_data['startedInMs'].mean():.1f} ms (±{config_data['startedInMs'].std():.1f})")
            print(f"    RSS: {config_data['RSSkB'].mean():.1f} kB (±{config_data['RSSkB'].std():.1f})")
            print(f"    Measurements: {len(config_data)}")

print("\n" + "="*80)
