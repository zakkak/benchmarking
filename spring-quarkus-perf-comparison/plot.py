import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import sys
import os
from pathlib import Path

def read_metrics_from_folder(folder_path):
    """Read metrics.json from folder/target-host/metrics.json"""
    metrics_file = Path(folder_path) / "target-host" / "metrics.json"
    
    if not metrics_file.exists():
        print(f"Warning: {metrics_file} does not exist, skipping...")
        return None
    
    try:
        with open(metrics_file, 'r') as f:
            data = json.load(f)
            quarkus_data = data.get('results', {}).get('quarkus3-native', {})
            
            # Extract TTFR timings from .results.quarkus3-native.startup.timings
            timings = quarkus_data.get('startup', {}).get('timings', [])
            
            # Extract RSS data from .results.quarkus3-native.rss
            rss_data = quarkus_data.get('rss', {})
            rss_startup = rss_data.get('startup', [])
            rss_first_request = rss_data.get('firstRequest', [])
            
            # Extract load data from .results.quarkus3-native.load
            load_data = quarkus_data.get('load', {})
            load_throughput = load_data.get('throughput', [])
            load_rss = load_data.get('rss', [])
            
            # Extract units configuration
            units = data.get('config', {}).get('units', {})
            
            # Extract config and env for printing
            config = data.get('config', {})
            env = data.get('env', {})
            
            return {
                'timings': timings,
                'rss_startup': rss_startup,
                'rss_first_request': rss_first_request,
                'load_throughput': load_throughput,
                'load_rss': load_rss,
                'units': units,
                'config': config,
                'env': env
            }
    except Exception as e:
        print(f"Error reading {metrics_file}: {e}")
        return None

# Parse command line arguments
if len(sys.argv) < 2:
    print("Usage: python plot_ttfr.py <folder1> [folder2] [folder3] ...")
    print("Example: python plot_ttfr.py 20260429-defaults 20260429-complete-reflection")
    sys.exit(1)

folders = sys.argv[1:]

# Read the data from all folders
ttfr_data = []
rss_startup_data = []
rss_first_request_data = []
load_throughput_data = []
load_rss_data = []
config_names = []
all_units = {}
all_configs = {}
all_envs = {}

for folder in folders:
    metrics = read_metrics_from_folder(folder)
    if metrics:
        # Use the folder name as the configuration name
        config_name = os.path.basename(folder.rstrip('/'))
        config_names.append(config_name)
        
        # Store units, config, and env for this folder
        all_units[config_name] = metrics.get('units', {})
        all_configs[config_name] = metrics.get('config', {})
        all_envs[config_name] = metrics.get('env', {})
        
        # Process TTFR timings
        for value in metrics['timings']:
            ttfr_data.append({'Configuration': config_name, 'value': value})
        
        # Process RSS startup data
        for value in metrics['rss_startup']:
            rss_startup_data.append({'Configuration': config_name, 'value': value})
        
        # Process RSS first request data
        for value in metrics['rss_first_request']:
            rss_first_request_data.append({'Configuration': config_name, 'value': value})
        
        # Process load throughput data
        for value in metrics['load_throughput']:
            load_throughput_data.append({'Configuration': config_name, 'value': value})
        
        # Process load RSS data
        for value in metrics['load_rss']:
            load_rss_data.append({'Configuration': config_name, 'value': value})
        
        print(f"Loaded {len(metrics['timings'])} TTFR, {len(metrics['rss_startup'])} RSS startup, "
              f"{len(metrics['rss_first_request'])} RSS first request, "
              f"{len(metrics['load_throughput'])} load throughput, "
              f"{len(metrics['load_rss'])} load RSS measurements from {folder}")
    else:
        print(f"No data loaded from {folder}")

# Get units from the first available configuration
units = next(iter(all_units.values())) if all_units else {}

# Strip common prefix from configuration names if there is one
if len(config_names) > 1:
    common_prefix = os.path.commonprefix(config_names)
    # Strip trailing non-alphanumeric characters from prefix
    common_prefix = common_prefix.rstrip('-_. ')
    
    if common_prefix:
        print(f"\nStripping common prefix: '{common_prefix}'")
        # Update all data with stripped names
        for item in ttfr_data:
            item['Configuration'] = item['Configuration'][len(common_prefix):].lstrip('-_. ')
        for item in rss_startup_data:
            item['Configuration'] = item['Configuration'][len(common_prefix):].lstrip('-_. ')
        for item in rss_first_request_data:
            item['Configuration'] = item['Configuration'][len(common_prefix):].lstrip('-_. ')
        for item in load_throughput_data:
            item['Configuration'] = item['Configuration'][len(common_prefix):].lstrip('-_. ')
        for item in load_rss_data:
            item['Configuration'] = item['Configuration'][len(common_prefix):].lstrip('-_. ')

# Check if we have any data at all
if not any([ttfr_data, rss_startup_data, rss_first_request_data, load_throughput_data, load_rss_data]):
    print("Error: No data was loaded from any folder")
    sys.exit(1)

# Create DataFrames for available metrics
df_ttfr = pd.DataFrame(ttfr_data) if ttfr_data else None
df_rss_startup = pd.DataFrame(rss_startup_data) if rss_startup_data else None
df_rss_first_request = pd.DataFrame(rss_first_request_data) if rss_first_request_data else None
df_load_throughput = pd.DataFrame(load_throughput_data) if load_throughput_data else None
df_load_rss = pd.DataFrame(load_rss_data) if load_rss_data else None

# Get configurations from the first available dataframe
configurations = None
for df in [df_ttfr, df_rss_startup, df_rss_first_request, df_load_throughput, df_load_rss]:
    if df is not None:
        configurations = df['Configuration'].unique()
        break

if configurations is None:
    print("Error: Could not determine configurations")
    sys.exit(1)

# Define pastel color palette (seaborn-like)
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

# Extract units from the units configuration
startup_unit = units.get('timings', {}).get('startup', 'ms')
rss_startup_unit = units.get('rss', {}).get('startup', 'MiB')
rss_first_request_unit = units.get('rss', {}).get('firstRequest', 'MiB')
load_throughput_unit = units.get('load', {}).get('throughput', 'tps')
load_rss_unit = units.get('rss', {}).get('load', 'MiB')

# Determine which metrics are available and build subplot configuration
available_metrics = []
subplot_titles = []

if df_ttfr is not None:
    available_metrics.append(('ttfr', df_ttfr, f'TTFR ({startup_unit})', 'Time to First Request (TTFR) Distribution by Configuration'))
    subplot_titles.append('Time to First Request (TTFR) Distribution by Configuration')

if df_rss_startup is not None:
    available_metrics.append(('rss_startup', df_rss_startup, f'RSS ({rss_startup_unit})', 'RSS at Startup Distribution by Configuration'))
    subplot_titles.append('RSS at Startup Distribution by Configuration')

if df_rss_first_request is not None:
    available_metrics.append(('rss_first_request', df_rss_first_request, f'RSS ({rss_first_request_unit})', 'RSS After First Request Distribution by Configuration'))
    subplot_titles.append('RSS After First Request Distribution by Configuration')

if df_load_throughput is not None:
    available_metrics.append(('load_throughput', df_load_throughput, f'Throughput ({load_throughput_unit})', 'Load Throughput Distribution by Configuration'))
    subplot_titles.append('Load Throughput Distribution by Configuration')

if df_load_rss is not None:
    available_metrics.append(('load_rss', df_load_rss, f'RSS ({load_rss_unit})', 'Load RSS Distribution by Configuration'))
    subplot_titles.append('Load RSS Distribution by Configuration')

num_plots = len(available_metrics)

if num_plots == 0:
    print("Error: No metrics available to plot")
    sys.exit(1)

# Create subplots dynamically based on available metrics
fig = make_subplots(
    rows=num_plots, cols=1,
    subplot_titles=tuple(subplot_titles),
    vertical_spacing=0.12 if num_plots <= 3 else 0.08,
    specs=[[{"type": "violin"}] for _ in range(num_plots)]
)

# Add violin plots for each available metric
for idx, (metric_name, df, y_label, title) in enumerate(available_metrics, start=1):
    for config in configurations:
        config_data = df[df['Configuration'] == config]['value']
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
                showlegend=(idx == 1)  # Only show legend for first subplot
            ),
            row=idx, col=1
        )

# Update axes labels
for idx, (metric_name, df, y_label, title) in enumerate(available_metrics, start=1):
    fig.update_xaxes(title_text="Configuration", tickangle=45, row=idx, col=1)
    fig.update_yaxes(title_text=y_label, row=idx, col=1)

# Build configuration HTML for appending
config_html_lines = ['<div style="font-family: Arial, sans-serif; padding: 20px; background-color: #f5f5f5; margin-top: 20px;">']
config_html_lines.append('<h2 style="color: #333; border-bottom: 2px solid #666; padding-bottom: 10px;">Configuration and Environment Information</h2>')

for config_name in config_names:
    # Strip prefix if it was applied
    display_name = config_name
    if len(config_names) > 1:
        common_prefix = os.path.commonprefix(config_names)
        common_prefix = common_prefix.rstrip('-_. ')
        if common_prefix:
            display_name = config_name[len(common_prefix):].lstrip('-_. ')
    
    config = all_configs.get(config_name, {})
    env = all_envs.get(config_name, {})
    
    config_html_lines.append(f'<div style="background-color: white; padding: 15px; margin: 15px 0; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">')
    config_html_lines.append(f'<h3 style="color: #2c5aa0; margin-top: 0;">{display_name}</h3>')
    config_html_lines.append(f'<p style="color: #666; font-size: 0.9em; margin-top: -10px;">Source: {config_name}</p>')
    
    # Configuration details
    if config:
        config_html_lines.append('<div style="margin-top: 15px;"><h4 style="color: #555; margin-bottom: 10px;">Configuration:</h4>')
        config_html_lines.append('<table style="width: 100%; border-collapse: collapse; font-size: 0.9em;">')
        
        jvm = config.get('jvm', {})
        if jvm.get('version'):
            config_html_lines.append(f'<tr><td style="padding: 5px; border-bottom: 1px solid #eee; width: 200px;"><strong>JVM Version:</strong></td><td style="padding: 5px; border-bottom: 1px solid #eee;">{jvm.get("version")}</td></tr>')
        if jvm.get('memory'):
            config_html_lines.append(f'<tr><td style="padding: 5px; border-bottom: 1px solid #eee;"><strong>JVM Memory:</strong></td><td style="padding: 5px; border-bottom: 1px solid #eee;">{jvm.get("memory")}</td></tr>')
        graalvm = jvm.get('graalvm', {})
        if graalvm and graalvm.get('version'):
            config_html_lines.append(f'<tr><td style="padding: 5px; border-bottom: 1px solid #eee;"><strong>GraalVM Version:</strong></td><td style="padding: 5px; border-bottom: 1px solid #eee;">{graalvm.get("version")}</td></tr>')
        
        quarkus = config.get('quarkus', {})
        if quarkus and quarkus.get('version'):
            config_html_lines.append(f'<tr><td style="padding: 5px; border-bottom: 1px solid #eee;"><strong>Quarkus Version:</strong></td><td style="padding: 5px; border-bottom: 1px solid #eee;">{quarkus.get("version")}</td></tr>')
        
        springboot3 = config.get('springboot3', {})
        if springboot3 and springboot3.get('version'):
            config_html_lines.append(f'<tr><td style="padding: 5px; border-bottom: 1px solid #eee;"><strong>Spring Boot 3 Version:</strong></td><td style="padding: 5px; border-bottom: 1px solid #eee;">{springboot3.get("version")}</td></tr>')
        
        springboot4 = config.get('springboot4', {})
        if springboot4 and springboot4.get('version'):
            config_html_lines.append(f'<tr><td style="padding: 5px; border-bottom: 1px solid #eee;"><strong>Spring Boot 4 Version:</strong></td><td style="padding: 5px; border-bottom: 1px solid #eee;">{springboot4.get("version")}</td></tr>')
        
        num_iterations = config.get('num_iterations')
        if num_iterations:
            config_html_lines.append(f'<tr><td style="padding: 5px; border-bottom: 1px solid #eee;"><strong>Iterations:</strong></td><td style="padding: 5px; border-bottom: 1px solid #eee;">{num_iterations}</td></tr>')
        
        resources = config.get('resources', {})
        if resources:
            cpu = resources.get('cpu', {})
            if cpu.get('app'):
                config_html_lines.append(f'<tr><td style="padding: 5px; border-bottom: 1px solid #eee;"><strong>App CPUs:</strong></td><td style="padding: 5px; border-bottom: 1px solid #eee;">{cpu.get("app")}</td></tr>')
            app_cpus = resources.get('app_cpus')
            if app_cpus:
                config_html_lines.append(f'<tr><td style="padding: 5px; border-bottom: 1px solid #eee;"><strong>Number of App CPUs:</strong></td><td style="padding: 5px; border-bottom: 1px solid #eee;">{app_cpus}</td></tr>')
        
        repo = config.get('repo', {})
        if repo:
            scenario = repo.get('scenarioName', repo.get('scenario'))
            if scenario:
                config_html_lines.append(f'<tr><td style="padding: 5px; border-bottom: 1px solid #eee;"><strong>Scenario:</strong></td><td style="padding: 5px; border-bottom: 1px solid #eee;">{scenario}</td></tr>')
            if repo.get('branch'):
                config_html_lines.append(f'<tr><td style="padding: 5px; border-bottom: 1px solid #eee;"><strong>Branch:</strong></td><td style="padding: 5px; border-bottom: 1px solid #eee;">{repo.get("branch")}</td></tr>')
            commit = repo.get('short_commit', repo.get('commit', '')[:7] if repo.get('commit') else '')
            if commit:
                config_html_lines.append(f'<tr><td style="padding: 5px; border-bottom: 1px solid #eee;"><strong>Commit:</strong></td><td style="padding: 5px; border-bottom: 1px solid #eee;">{commit}</td></tr>')
        
        config_html_lines.append('</table></div>')
    
    # Environment details
    if env:
        config_html_lines.append('<div style="margin-top: 15px;"><h4 style="color: #555; margin-bottom: 10px;">Environment:</h4>')
        config_html_lines.append('<table style="width: 100%; border-collapse: collapse; font-size: 0.9em;">')
        
        host = env.get('host', {})
        if host.get('cpu'):
            config_html_lines.append(f'<tr><td style="padding: 5px; border-bottom: 1px solid #eee; width: 200px;"><strong>CPU:</strong></td><td style="padding: 5px; border-bottom: 1px solid #eee;">{host.get("cpu")}</td></tr>')
        if host.get('memory'):
            config_html_lines.append(f'<tr><td style="padding: 5px; border-bottom: 1px solid #eee;"><strong>Memory:</strong></td><td style="padding: 5px; border-bottom: 1px solid #eee;">{host.get("memory")}</td></tr>')
        if host.get('os'):
            config_html_lines.append(f'<tr><td style="padding: 5px; border-bottom: 1px solid #eee;"><strong>OS:</strong></td><td style="padding: 5px; border-bottom: 1px solid #eee;">{host.get("os")}</td></tr>')
        if host.get('kernel'):
            config_html_lines.append(f'<tr><td style="padding: 5px; border-bottom: 1px solid #eee;"><strong>Kernel:</strong></td><td style="padding: 5px; border-bottom: 1px solid #eee;">{host.get("kernel")}</td></tr>')
        
        run = env.get('run', {})
        if run:
            run_host = run.get('host', {})
            if run_host and run_host.get('name'):
                config_html_lines.append(f'<tr><td style="padding: 5px; border-bottom: 1px solid #eee;"><strong>Run Host:</strong></td><td style="padding: 5px; border-bottom: 1px solid #eee;">{run_host.get("name")}</td></tr>')
        
        config_html_lines.append('</table></div>')
    
    config_html_lines.append('</div>')

config_html_lines.append('</div>')
config_html = '\n'.join(config_html_lines)

# Update overall layout
fig.update_layout(
    title_text="Quarkus 3 Native Performance Metrics",
    height=600 * num_plots,
    width=1400,
    showlegend=True,
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1
    )
)

# Write HTML with configuration info appended (standalone, no internet required)
html_content = fig.to_html(full_html=True, include_plotlyjs=True)
# Insert config HTML before closing body tag
html_content = html_content.replace('</body>', f'{config_html}</body>')

with open('report.html', 'w') as f:
    f.write(html_content)

print(f"\nCombined report saved as report.html")
print(f"Metrics plotted: {', '.join([m[0] for m in available_metrics])}")
print(f"Configurations plotted: {', '.join(configurations)}")

# Print configuration and environment information
print("\n" + "="*80)
print("CONFIGURATION AND ENVIRONMENT INFORMATION")
print("="*80)

for config_name in config_names:
    # Strip prefix if it was applied
    display_name = config_name
    if len(config_names) > 1:
        common_prefix = os.path.commonprefix(config_names)
        common_prefix = common_prefix.rstrip('-_. ')
        if common_prefix:
            display_name = config_name[len(common_prefix):].lstrip('-_. ')
    
    print(f"\n{'─'*80}")
    print(f"Configuration: {display_name} (from {config_name})")
    print(f"{'─'*80}")
    
    config = all_configs.get(config_name, {})
    env = all_envs.get(config_name, {})
    
    # Print key configuration details
    if config:
        print("\nKey Configuration:")
        
        # JVM info
        jvm = config.get('jvm', {})
        if jvm:
            print(f"  JVM Version: {jvm.get('version', 'N/A')}")
            print(f"  JVM Memory: {jvm.get('memory', 'N/A')}")
            graalvm = jvm.get('graalvm', {})
            if graalvm and graalvm.get('version'):
                print(f"  GraalVM Version: {graalvm.get('version', 'N/A')}")
        
        # Framework versions
        quarkus = config.get('quarkus', {})
        if quarkus and quarkus.get('version'):
            print(f"  Quarkus Version: {quarkus.get('version', 'N/A')}")
        
        springboot3 = config.get('springboot3', {})
        if springboot3 and springboot3.get('version'):
            print(f"  Spring Boot 3 Version: {springboot3.get('version', 'N/A')}")
        
        springboot4 = config.get('springboot4', {})
        if springboot4 and springboot4.get('version'):
            print(f"  Spring Boot 4 Version: {springboot4.get('version', 'N/A')}")
        
        # Iterations
        num_iterations = config.get('num_iterations')
        if num_iterations:
            print(f"  Iterations: {num_iterations}")
        
        # Resources
        resources = config.get('resources', {})
        if resources:
            cpu = resources.get('cpu', {})
            if cpu:
                print(f"  App CPUs: {cpu.get('app', 'N/A')}")
            app_cpus = resources.get('app_cpus')
            if app_cpus:
                print(f"  Number of App CPUs: {app_cpus}")
        
        # Repository info
        repo = config.get('repo', {})
        if repo:
            print(f"  Scenario: {repo.get('scenarioName', repo.get('scenario', 'N/A'))}")
            print(f"  Branch: {repo.get('branch', 'N/A')}")
            print(f"  Commit: {repo.get('short_commit', repo.get('commit', 'N/A')[:7])}")
    
    # Print environment details
    if env:
        print("\nEnvironment:")
        
        host = env.get('host', {})
        if host:
            print(f"  CPU: {host.get('cpu', 'N/A')}")
            print(f"  Memory: {host.get('memory', 'N/A')}")
            print(f"  OS: {host.get('os', 'N/A')}")
            print(f"  Kernel: {host.get('kernel', 'N/A')}")
        
        run = env.get('run', {})
        if run:
            run_host = run.get('host', {})
            if run_host:
                print(f"  Run Host: {run_host.get('name', 'N/A')}")

print("\n" + "="*80)
