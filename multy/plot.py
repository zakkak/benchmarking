import argparse
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


EXPECTED_FILES = [
    "metrics_all_Q.tsv",
    "metrics_all_Q_CRT.tsv",
]


def config_name_from_file(tsv_path: Path) -> str:
    name = tsv_path.stem
    if name.startswith("metrics_all_"):
        name = name[len("metrics_all_"):]
    return name


def read_metrics_all_tsv(tsv_path: Path) -> pd.DataFrame:
    """Read metrics_all_*.tsv with expected columns: app, ttfr_ms, rss_mb."""
    df = pd.read_csv(
        tsv_path,
        sep="\t",
        header=None,
        names=["app", "ttfr_ms", "rss_mb"],
        usecols=[0, 1, 2],
    )

    df["ttfr_ms"] = pd.to_numeric(df["ttfr_ms"], errors="coerce")
    df["rss_mb"] = pd.to_numeric(df["rss_mb"], errors="coerce")
    df = df.dropna(subset=["app", "ttfr_ms", "rss_mb"])
    df["configuration"] = config_name_from_file(tsv_path)
    return df


def load_all_metrics(matrix_folder: Path) -> pd.DataFrame:
    all_data = []

    for file_name in EXPECTED_FILES:
        file_path = matrix_folder / file_name

        if not file_path.exists():
            print(f"Warning: missing {file_name}")
            continue

        if file_path.stat().st_size == 0:
            print(f"Warning: empty {file_name}")
            continue

        try:
            df = read_metrics_all_tsv(file_path)
        except Exception as exc:
            print(f"Warning: failed reading {file_name}: {exc}")
            continue

        if df.empty:
            print(f"Warning: no valid rows in {file_name}")
            continue

        all_data.append(df)
        print(f"Loaded {len(df)} rows from {file_name}")

    if not all_data:
        raise ValueError("No usable metrics data found")

    return pd.concat(all_data, ignore_index=True)


def build_plot(combined_df: pd.DataFrame, matrix_folder_name: str) -> go.Figure:
    apps = sorted(combined_df["app"].unique())
    configurations = list(dict.fromkeys(combined_df["configuration"].tolist()))

    colors = [
        "#4E79A7",
        "#F28E2B",
        "#E15759",
        "#76B7B2",
        "#59A14F",
        "#EDC948",
    ]
    color_map = {cfg: colors[i % len(colors)] for i, cfg in enumerate(configurations)}

    metrics = [
        ("ttfr_ms", "TTFR (ms)", "TTFR Distribution"),
        ("rss_mb", "RSS (MB)", "RSS Distribution"),
    ]

    fig = make_subplots(
        rows=len(apps),
        cols=len(metrics),
        subplot_titles=[title for _ in apps for _, _, title in metrics],
        vertical_spacing=0.16,
        horizontal_spacing=0.1,
        specs=[[{"type": "violin"} for _ in metrics] for _ in apps],
        row_titles=apps,
    )

    for app_idx, app_name in enumerate(apps, start=1):
        app_data = combined_df[combined_df["app"] == app_name]

        for metric_idx, (metric_col, metric_label, _) in enumerate(metrics, start=1):
            for config in configurations:
                series = app_data[app_data["configuration"] == config][metric_col]
                if series.empty:
                    continue

                fig.add_trace(
                    go.Violin(
                        y=series,
                        name=config,
                        x0=config,
                        legendgroup=config,
                        showlegend=(app_idx == 1 and metric_idx == 1),
                        width=0.8,
                        jitter=0.5,
                        marker=dict(size=10, opacity=0.65),
                        box_visible=True,
                        meanline_visible=True,
                        fillcolor=color_map[config],
                        line_color="#1F2937",
                        opacity=0.75,
                    ),
                    row=app_idx,
                    col=metric_idx,
                )

            fig.update_xaxes(title_text="Configuration", tickangle=25, row=app_idx, col=metric_idx)
            fig.update_yaxes(title_text=metric_label, row=app_idx, col=metric_idx)

    fig.update_layout(
        title_text=f"Runtime Metrics Comparison ({matrix_folder_name})",
        height=max(500, 500 * len(apps)),
        width=980,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    return fig


def print_summary(combined_df: pd.DataFrame) -> None:
    print("\n" + "=" * 80)
    print("SUMMARY STATISTICS")
    print("=" * 80)

    for app_name in sorted(combined_df["app"].unique()):
        app_data = combined_df[combined_df["app"] == app_name]
        print(f"\n{app_name}:")
        print("-" * 80)

        for config in app_data["configuration"].unique():
            cfg_data = app_data[app_data["configuration"] == config]
            print(f"\n  {config}:")
            print(f"    TTFR: {cfg_data['ttfr_ms'].mean():.2f} ms (±{cfg_data['ttfr_ms'].std():.2f})")
            print(f"    RSS: {cfg_data['rss_mb'].mean():.2f} MB (±{cfg_data['rss_mb'].std():.2f})")
            print(f"    Samples: {len(cfg_data)}")

    print("\n" + "=" * 80)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Plot runtime metrics from metrics_all_Q.tsv and metrics_all_Q_CRT.tsv.",
    )
    parser.add_argument("matrix_folder", help="Path to a matrix_results_* folder")
    parser.add_argument("--output", default="report.html", help="Output HTML report file")
    args = parser.parse_args()

    matrix_folder = Path(args.matrix_folder)
    if not matrix_folder.exists() or not matrix_folder.is_dir():
        print(f"Error: folder does not exist or is not a directory: {matrix_folder}")
        return 1

    try:
        combined_df = load_all_metrics(matrix_folder)
    except ValueError as exc:
        print(f"Error: {exc}")
        return 1

    print(f"\nTotal measurements: {len(combined_df)}")
    print(f"Configurations: {', '.join(combined_df['configuration'].unique())}")
    print(f"Apps: {', '.join(sorted(combined_df['app'].unique()))}")

    fig = build_plot(combined_df, matrix_folder.name)
    fig.write_html(args.output, include_plotlyjs=True)
    print(f"\nReport saved as {args.output}")

    print_summary(combined_df)
    return 0


if __name__ == "__main__":
    sys.exit(main())
