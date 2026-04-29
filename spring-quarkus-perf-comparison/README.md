# Quarkus Performance Metrics Plotter

Generates interactive HTML reports with violin plots comparing Quarkus 3 Native performance metrics across multiple configurations.

## Data Generation

Metrics JSON files are generated using [spring-quarkus-perf-comparison](https://github.com/quarkusio/spring-quarkus-perf-comparison).

**Example:**
```bash
export ITERATIONS=10
export COMMON="--drop-fs-caches --graalvm-version 25.0.2.r25-graalce --host LOCAL --java-version 25.0.2-tem --runtimes quarkus3-native --quarkus-version 3.33.1 --tests measure-time-to-first-request,measure-rss,run-load-test --wait-time 1 --iterations $ITERATIONS"

./run-benchmarks.sh $COMMON --output-dir ../../20260429-defaults

./run-benchmarks.sh $COMMON --output-dir ../../20260429-complete-reflection \
  --native-quarkus-build-options -Dquarkus.native.additional-build-args-append=--future-defaults=complete-reflection-types
```

## Usage

```bash
python plot.py <folder1> [folder2] [folder3] ...
```

**Example:**
```bash
python plot.py 20260429-defaults 20260429-complete-reflection
```

## Input Structure

Each folder must contain: `<folder>/target-host/metrics.json`

Expected JSON structure:
```json
{
  "results": {
    "quarkus3-native": {
      "startup": { "timings": [...] },
      "rss": { "startup": [...], "firstRequest": [...] },
      "load": { "throughput": [...], "rss": [...] }
    }
  },
  "config": { "units": {...}, ... },
  "env": { "host": {...}, ... }
}
```

## Output

- **`report.html`**: Standalone HTML file with:
  - Violin plots for available metrics (TTFR, RSS startup, RSS first request, load throughput, load RSS)
  - Configuration and environment details
  - No internet required (includes Plotly.js)

## Metrics Plotted

- **TTFR**: Time to First Request
- **RSS Startup**: Memory at startup
- **RSS First Request**: Memory after first request
- **Load Throughput**: Requests per second under load
- **Load RSS**: Memory under load

## Features

- Automatic common prefix stripping from configuration names
- Dynamic subplot generation based on available metrics
- Pastel color palette for configurations
- Box plots and mean lines in violin plots
- Configuration/environment metadata display

## Dependencies

- pandas
- plotly
- Python 3.x