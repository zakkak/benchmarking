Numbers obtained using `89b0bf875919e61717f1950b13bac23f11bd9f21` sha of
this repository (optimized script version)

## System Configuration

**Hardware:**
- CPU: AMD Ryzen 9 7950X 16-Core Processor
- Cores: 16 cores (1 thread per core, 16 online)
- Memory: 61 GiB

**Software:**
- OS: Fedora Linux 43 (Workstation Edition)
- Kernel: 6.19.13-200.fc43.x86_64
- GraalVM: Mandrel 25.0.2.r25

## Tested Apps

1. `mp-orm-dbs-awt` - Multi-DB with AWT/PDF
   - Repository: https://github.com/Karm/dev-null
   - SHA: `7815e9ee7aedbf301527c7cfa7629f0249cd47a5`

2. `validation-quickstart` - Bean validation
   - Repository: https://github.com/quarkusio/quarkus-quickstarts
   - SHA: `ffde221187d66696d963e2d18ee5e543f2121723`

3. `hibernate-orm-quickstart` - JPA/Hibernate
   - Repository: https://github.com/quarkusio/quarkus-quickstarts
   - SHA: `ffde221187d66696d963e2d18ee5e543f2121723`

## Reproducer

```bash
sudo ./bmark-setup start

# Run benchmarks 15 times without building quarkus (optimized script, reverse order)
RUN_COUNT=15 taskset -c 8-10 bash ./run_matrix7_runtime.sh --dry-run

sudo ./bmark-setup stop
```

## Notes

These were run in reverse order:

``` diff
diff --git a/multy/run_matrix7_runtime.sh b/multy/run_matrix7_runtime.sh
index e1e4dda..f45666a 100644
--- a/multy/run_matrix7_runtime.sh
+++ b/multy/run_matrix7_runtime.sh
@@ -385,8 +385,8 @@ if [ -n "$EXTRA_NATIVE_ARGS" ]; then
 fi
 
 if [ "$DRY_RUN" = "true" ]; then
-    run_matrix_job "$DIR_VANILLA" "Q" false "$MAVEN_ARG_DEFAULT"
     run_matrix_job "$DIR_VANILLA" "Q_CRT" false "$MAVEN_ARG_CRT"
+    run_matrix_job "$DIR_VANILLA" "Q" false "$MAVEN_ARG_DEFAULT"
     echo "[INFO] DRY RUN: Mocking Q_Patched metrics using Q Vanilla metrics..."
     cp "$RESULTS_DIR/metrics_Q.tsv" "$RESULTS_DIR/metrics_Q_Patched.tsv"
 else
 
```
