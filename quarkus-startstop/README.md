# Quarkus StartStop Native Tests Plotting

Generates performance comparison plots for Quarkus Native tests from the StartStop test suite.

## Usage

```bash
python plot.py <folder1> [folder2] ...
```

**Example:**
```bash
python plot.py \
  data/20260429-oracle-graal-13416/target3-33-1-jdk25-defaults \
  data/20260429-oracle-graal-13416/target3-33-1-jdk25-complete-reflection
```

## Features

- Auto-discovers `*Native` test directories under `archived-logs/io.quarkus.ts.startstop.StartStopTest/`
- Reads `measurements.csv` from each test
- Generates violin plots organized by test (rows) and metric (columns)
- Strips common prefixes from configuration names
- Outputs `report.html` with interactive plots and console summary statistics

## Metrics

- **Build Time (ms)**: Native image build time
- **Time to First Request (ms)**: Time to first successful HTTP request
- **Started In (ms)**: Application startup time
- **RSS (kB)**: Memory usage

## Data Structure

```
<folder>/
└── archived-logs/
    └── io.quarkus.ts.startstop.StartStopTest/
        ├── fullMicroProfileNative/
        │   └── measurements.csv
        └── jakartaRESTMinimalNative/
            └── measurements.csv
```

## Requirements

```bash
pip install pandas plotly
```