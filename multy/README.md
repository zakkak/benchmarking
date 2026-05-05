# Quarkus Multi-Config Benchmark

Benchmark suite comparing Quarkus native image performance across configurations.

## Components

- `run_matrix7_runtime.sh` - Orchestrates builds, runs, and measurements
- `plot.py` - Generates interactive violin plots from results

## Quick Start

```bash
# Run benchmarks 30 times (default: 10 cycles, GraalVM 25) without building quarkus
RUN_COUNT=30 ./run_matrix7_runtime.sh --dry-run

# Generate plots
python plot.py --output report.html matrix_results_YYYYMMDD_HHMMSS/
```

## Prerequisites

**System:**
- Linux with `taskset`, `podman`, `nc`, `jq`
- JDK 17, GraalVM/Mandrel 21 or 25

**Python:**
```bash
pip install pandas plotly
```

## Configurations

- **Q** - Vanilla Quarkus
- **Q_CRT** - With `--future-defaults=complete-reflection-types`
- **Q_Patched** - Custom Quarkus build

## Tested Apps

1. `mp-orm-dbs-awt` - Multi-DB with AWT/PDF
   - Repository: https://github.com/Karm/dev-null

2. `validation-quickstart` - Bean validation
   - Repository: https://github.com/quarkusio/quarkus-quickstarts

3. `hibernate-orm-quickstart` - JPA/Hibernate
   - Repository: https://github.com/quarkusio/quarkus-quickstarts

## Output

Results in `matrix_results_YYYYMMDD_HHMMSS/`:

**Metrics:**
- `metrics_*.tsv` - Best run summary
- `metrics_all_*.tsv` - All measurements
- `final_markdown_summary.md` - Comparison table
- `report.html` - Interactive plots (via plot.py)

**Logs:**
- `quarkus_build_*.log`
- `app_build_*.log`
- `app_run_*.log`

## Key Metrics

- **TTFR** - Time to first response (startup + first request)
- **RSS** - Memory footprint
- **Size** - Native executable size
- **Resources/Types/Methods/Classes/Fields** - Reachability analysis

## Configuration

Edit paths in script:
```bash
JAVA_HOME_17="/path/to/jdk17"
GRAALVM_25="/path/to/mandrel25"
DIR_VANILLA="/path/to/quarkus_vanilla"
DIR_PATCHED="/path/to/quarkus_patched"
```

### CPU Pinning

Make sure to update CPU Pinning to match your processor, defaults are:
- 4-7: Native app
- 11-15: Databases
- 8-10: HTTP probes
