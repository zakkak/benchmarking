#!/bin/bash

set -ou pipefail

#
# @author: karm@ibm.com
# AI aided: (cores pinning, awk->markdown formatting)
#

JAVA_HOME_17="$HOME/.sdkman/candidates/java/17.0.18-tem/"
GRAALVM_21="$HOME/.sdkman/candidates/java/23.1.9.r21-mandrel/"
GRAALVM_25="$HOME/.sdkman/candidates/java/25.0.2.r25-mandrel/"

DIR_VANILLA="/home/karm/workspaceRH/quarkus_vanilla"
DIR_PATCHED="/home/karm/workspaceRH/quarkus"

DIR_APP1="$HOME/code/plotting/dev-null/quarkus-mp-orm-dbs-awt"
DIR_APP2="$HOME/code/quarkus-quickstarts/validation-quickstart"
DIR_APP3="$HOME/code/quarkus-quickstarts/hibernate-orm-quickstart"

# --- Optimal spread by Google Gemini + Intel manual
CPU_SET_NATIVE="4-7"       # P-Cores for Quarkus Application
CPU_SET_ECORES="11-15"     # E-Cores for Databases
CPU_SET_PROBE="8-10"       # Dedicated cores for readiness probes

XML_PAYLOAD="/tmp/10-employee-profiles-test.xml"
RUN_COUNT=${RUN_COUNT:-10}

ORIGINAL_PATH=$PATH
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
RESULTS_DIR="$(pwd)/matrix_results_$TIMESTAMP"
mkdir -p "$RESULTS_DIR"

DRY_RUN=false
TARGET_GRAALVM="25"
EXTRA_NATIVE_ARGS=""

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --dry-run)
            echo "Executing in DRY-RUN mode. Quarkus builds skipped. Patched Q run MOCKED."
            DRY_RUN=true
            shift
            ;;
        --graalvm)
            TARGET_GRAALVM="$2"
            shift 2
            ;;
        --additional-build-args)
            EXTRA_NATIVE_ARGS="$2"
            shift 2
            ;;
        *)
            echo "unknown parameter: $1"
            exit 1
            ;;
    esac
done

if [ "$TARGET_GRAALVM" = "21" ]; then
    ACTIVE_GRAALVM=$GRAALVM_21
elif [ "$TARGET_GRAALVM" = "25" ]; then
    ACTIVE_GRAALVM=$GRAALVM_25
else
    echo "Mandrel version: $TARGET_GRAALVM ? 21 or 25."
    exit 1
fi

if [ ! -f "$XML_PAYLOAD" ]; then
    echo "ERROR: Payload file $XML_PAYLOAD not found."
    exit 1
fi

wait_port_free() {
    local port=$1
    for j in {1..50}; do
        if ! bash -c "</dev/tcp/127.0.0.1/$port" 2>/dev/null; then
            return 0
        fi
        sleep 0.1
    done
    echo "WARNING: Port $port still bound."
}

start_dbs_app1() {
    echo "[INFO] Starting App 1 DBs (Postgres & MariaDB) on E-Cores..."

    taskset -c "$CPU_SET_ECORES" podman run -it -d --rm=true \
        --name quarkus_test_db -p 5432:5432 \
        -e POSTGRES_USER=quarkus -e POSTGRES_PASSWORD=quarkus -e POSTGRES_DB=db1 \
        quay.io/debezium/postgres:15 -c max_prepared_transactions=100 >/dev/null

    taskset -c "$CPU_SET_ECORES" podman run -it -d --rm=true \
        --name mariadb -p 49157:3306 \
        --env MARIADB_USER=quarkus --env MARIADB_PASSWORD=quarkus \
        --env MARIADB_ROOT_PASSWORD=quarkus --env MARIADB_DATABASE=db2 \
        docker.io/library/mariadb:11.0 >/dev/null

    local pg_up=false
    for i in {1..30}; do
        if nc -z 127.0.0.1 5432 2>/dev/null; then pg_up=true; break; fi
        sleep 1
    done

    local maria_up=false
    for i in {1..30}; do
        if nc -z 127.0.0.1 49157 2>/dev/null; then maria_up=true; break; fi
        sleep 1
    done

    if [ "$pg_up" = false ] || [ "$maria_up" = false ]; then
        echo "[ERROR] App 1 Databases failed to bind. Bailing out."
        stop_dbs
        exit 1
    fi
    sleep 3
}

start_dbs_app3() {
    echo "INFO: Starting App 3 DB (Postgres 'quarkus_test') on E-Cores..."

    taskset -c "$CPU_SET_ECORES" podman run -it -d --rm=true \
        --name quarkus_test -p 5432:5432 \
        -e POSTGRES_USER=quarkus_test -e POSTGRES_PASSWORD=quarkus_test -e POSTGRES_DB=quarkus_test \
        quay.io/debezium/postgres:15 >/dev/null

    local pg_up=false
    for i in {1..30}; do
        if nc -z 127.0.0.1 5432 2>/dev/null; then pg_up=true; break; fi
        sleep 1
    done

    if [ "$pg_up" = false ]; then
        echo "ERROR: App 3 Database failed to bind. Bailing out."
        stop_dbs
        exit 1
    fi
    sleep 3
}

stop_dbs() {
    echo "INFO: Stopping all known Databases..."
    podman rm -f quarkus_test_db mariadb quarkus_test >/dev/null 2>&1
    wait_port_free 5432
    wait_port_free 49157
}

run_matrix_job() {
    local quarkus_dir=$1
    local job_label=$2
    local do_quarkus_build=$3
    local extra_maven_args=$4

    echo "======================================================================"
    echo "RUNNING: $job_label | GraalVM $TARGET_GRAALVM"
    echo "======================================================================"

    export JAVA_HOME=$JAVA_HOME_17
    export GRAALVM_HOME=$ACTIVE_GRAALVM
    export PATH=${JAVA_HOME}/bin:${GRAALVM_HOME}/bin:${ORIGINAL_PATH}

    local metrics_tsv="$RESULTS_DIR/metrics_${job_label}.tsv"
    > "$metrics_tsv"
    local metrics_all_tsv="$RESULTS_DIR/metrics_all_${job_label}.tsv"
    > "$metrics_all_tsv"

    # rebuild Quarkus
    if [ "$do_quarkus_build" = true ]; then
        echo "INFO: Rebuilding Quarkus in $quarkus_dir (-Dquickly)..."
        cd "$quarkus_dir" || exit 1
        local q_build_log="$RESULTS_DIR/quarkus_build_${job_label}.log"
        if ! time ./mvnw clean install -Dquickly > "$q_build_log" 2>&1; then
            echo "ERROR: Quarkus build failed."
            tail -n 50 "$q_build_log"
            exit 1
        fi
    fi

    # iterate over  apps
    for APP_ID in "mp-orm-dbs-awt" "validation-quickstart" "hibernate-orm-quickstart"; do
        echo ""
        echo "   --- Processing Application: $APP_ID ---"

        local app_dir=""
        local target_dir=""
        local app_run_args=""

        case $APP_ID in
            "mp-orm-dbs-awt")
                app_dir="$DIR_APP1"
                target_dir="app/target"
                app_run_args="-Dquarkus.profile=dev"
                ;;
            "validation-quickstart")
                app_dir="$DIR_APP2"
                target_dir="target"
                app_run_args=""
                ;;
            "hibernate-orm-quickstart")
                app_dir="$DIR_APP3"
                target_dir="target"
                app_run_args=""
                ;;
        esac

        cd "$app_dir" || exit 1

        # purge targets
        if [ "$APP_ID" = "mp-orm-dbs-awt" ]; then
            rm -rf target app/target auxiliary-ext/runtime/target auxiliary-ext/deployment/target
        else
            rm -rf target
        fi

        echo "INFO Building native-image for $APP_ID..."
        local app_build_log="$RESULTS_DIR/app_build_${job_label}_${APP_ID}.log"

#            -Dquarkus.version=999-SNAPSHOT -Dquarkus.platform.version=999-SNAPSHOT \
        if ! ./mvnw clean package -Dnative -DskipTests \
            $extra_maven_args > "$app_build_log" 2>&1; then
            echo "ERROR: native build failed for $APP_ID!"
            tail -n 50 "$app_build_log"
            exit 1
        fi

        local runner_file=$(find "$target_dir" -type f -name "*-runner" | head -n 1)
        local stats_file=$(find "$target_dir" -type f -name "*-build-output-stats.json" | head -n 1)

        if [ ! -f "$runner_file" ] || [ -z "$stats_file" ]; then
            echo "ERROR executable or stats file not found for $APP_ID!"
            exit 1
        fi

        # extract build metrics by Google Gemini
        local size_bytes=$(stat -c%s "$runner_file")
        local size_mb=$(awk -v bytes="$size_bytes" 'BEGIN {printf "%.2f", bytes / 1048576}')
        local resources=$(jq -r '.image_details.image_heap.resources.count // 0' "$stats_file")
        local types=$(jq -r '.analysis_results.types.total // 0' "$stats_file")
        local methods=$(jq -r '.analysis_results.methods.total // 0' "$stats_file")
        local classes=$(jq -r '.analysis_results.classes.total // 0' "$stats_file")
        local fields=$(jq -r '.analysis_results.fields.total // 0' "$stats_file")

        # handle DB lifecycle
        stop_dbs
        if [ "$APP_ID" = "mp-orm-dbs-awt" ]; then start_dbs_app1; fi
        if [ "$APP_ID" = "hibernate-orm-quickstart" ]; then start_dbs_app3; fi

        # run and measure application
        local ttfr_cold_ns=-1
        local min_ttfr_ns=-1
        local min_rss_mb=-1
        local out_payload="$RESULTS_DIR/response_${job_label}_${APP_ID}.out"
        local app_log="$RESULTS_DIR/app_run_${job_label}_${APP_ID}.log"

        echo "INFO Running $RUN_COUNT start cycles..."

        sleep 10

        for (( i=1; i<=RUN_COUNT; i++ )); do
            sudo ~/bin/bmark-setup drop-caches

            local ttfr_ns=-1
            local timeout_sec=60
            local deadline_sec=$((SECONDS + timeout_sec))
            local http_code=000
            local response_valid=false
            local -a probe_cmd=()

            # Build the full probe command once per cycle (outside the retry while-loop).

            # Precompute request metadata once per app to keep retry loop lean.
            local probe_expected_http=""

            if [ "$APP_ID" = "mp-orm-dbs-awt" ]; then
                probe_cmd=(taskset -c "$CPU_SET_PROBE" curl -s -o "$out_payload" -w "%{http_code}" -X POST \
                    -H "Content-Type: application/xml" -d @"$XML_PAYLOAD" "http://127.0.0.1:8080/perfMeshup")
                probe_expected_http="200"
            elif [ "$APP_ID" = "validation-quickstart" ]; then
                probe_cmd=(taskset -c "$CPU_SET_PROBE" curl -s -o "$out_payload" -w "%{http_code}" -X POST \
                    -H "Content-Type: application/json" -d '{"title": "some book", "author": "me", "pages":5}' "http://127.0.0.1:8080/books/service-method-validation")
                probe_expected_http="200"
            elif [ "$APP_ID" = "hibernate-orm-quickstart" ]; then
                probe_cmd=(taskset -c "$CPU_SET_PROBE" curl -s -o "$out_payload" -w "%{http_code}" -X POST \
                    -H "Content-Type: application/json" -d "{\"name\" : \"Pear${i}\"}" "http://127.0.0.1:8080/fruits")
                probe_expected_http="201"
            fi

            local start_time_ns=$(date +%s%N)

            taskset -c "$CPU_SET_NATIVE" "$runner_file" $app_run_args > "$app_log" 2>&1 &
            APP_PID=$!

            while true; do
                # Execute prebuilt probe command to avoid per-iteration command construction.
                http_code=$("${probe_cmd[@]}")

                if [ "$http_code" = "$probe_expected_http" ]; then
                    break;
                fi

                if (( SECONDS > deadline_sec )); then
                    echo "ERROR Timeout waiting for response on cycle $i."
                    cat "$app_log"
                    break
                fi
            done

            if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
                local end_time_ns=$(date +%s%N)
                ttfr_ns=$(( end_time_ns - start_time_ns ))

                # Validate payload once, outside the retry loop to avoid extra probe overhead.
                if [ "$APP_ID" = "mp-orm-dbs-awt" ]; then
                    if [ -s "$out_payload" ] && file "$out_payload" | grep -qi "pdf document"; then
                        response_valid=true
                    fi
                elif [ "$APP_ID" = "validation-quickstart" ]; then
                    if grep -qi '"success":true' "$out_payload"; then
                        response_valid=true
                    fi
                elif [ "$APP_ID" = "hibernate-orm-quickstart" ]; then
                    if grep -qi "\"name\":\"Pear${i}\"" "$out_payload"; then
                        response_valid=true
                    fi
                fi

                if [ "$response_valid" = false ]; then
                    echo "ERROR: Post-success payload validation failed on cycle $i (status=$http_code)."
                    ttfr_ns=-1
                fi
            fi

            local ttfr_ms=-1
            if [ "$ttfr_ns" -gt 0 ]; then
                ttfr_ms=$(( ttfr_ns / 1000000 ))
            fi
            echo I=$i TTFR=$ttfr_ms

            sleep 10 # wait for RSS stabilization
            local rss_kb=$(ps -p $APP_PID -o rss= | tr -d ' ')
            if [ -z "$rss_kb" ]; then rss_kb=0; fi
            local rss_mb=$(awk -v r="$rss_kb" 'BEGIN {printf "%.2f", r / 1024}')

            # update minimums, we take the best
            if [ "$ttfr_ns" -gt 0 ]; then
                if [ "$i" -eq 1 ]; then ttfr_cold_ns=$ttfr_ns; fi
                if [ "$min_ttfr_ns" -eq -1 ] || [ "$ttfr_ns" -lt "$min_ttfr_ns" ]; then min_ttfr_ns=$ttfr_ns; fi
            fi

            if [ $(awk -v r="$rss_kb" 'BEGIN {print (r > 0 ? 1 : 0)}') -eq 1 ]; then
                min_rss_mb=$(awk -v curr="$rss_mb" -v min="$min_rss_mb" 'BEGIN { if (min == -1 || curr < min) printf "%.2f", curr; else printf "%.2f", min }')
            fi

            kill -9 $APP_PID 2>/dev/null
            wait $APP_PID 2>/dev/null
            wait_port_free 8080

            # Append to TSV: APP | TTFR | RSS
            echo -e "${APP_ID}\t${ttfr_ms}\t${rss_mb}" >> "$metrics_all_tsv"

        done

        local ttfr_cold_ms=-1
        local min_ttfr_ms=-1
        if [ "$ttfr_cold_ns" -gt 0 ]; then ttfr_cold_ms=$(( ttfr_cold_ns / 1000000 )); fi
        if [ "$min_ttfr_ns" -gt 0 ]; then min_ttfr_ms=$(( min_ttfr_ns / 1000000 )); fi

        stop_dbs
        # Google Gemini formatter
        echo "[INFO] BEST METRICS ($APP_ID) -> TTFR: ${min_ttfr_ms} ms | RSS: ${min_rss_mb} MB"
        # Append to TSV: APP | Size | Resources | Types | Methods | Classes | Fields | TTFR_Cold | TTFR | RSS
        echo -e "${APP_ID}\t${size_mb}\t${resources}\t${types}\t${methods}\t${classes}\t${fields}\t${ttfr_cold_ms}\t${min_ttfr_ms}\t${min_rss_mb}" >> "$metrics_tsv"
    done
}


MAVEN_ARG_DEFAULT=""
if [ -n "$EXTRA_NATIVE_ARGS" ]; then
    MAVEN_ARG_DEFAULT="-Dquarkus.native.additional-build-args=${EXTRA_NATIVE_ARGS}"
fi

MAVEN_ARG_CRT="-Dquarkus.native.additional-build-args=--future-defaults=complete-reflection-types"
if [ -n "$EXTRA_NATIVE_ARGS" ]; then
    MAVEN_ARG_CRT="-Dquarkus.native.additional-build-args=${EXTRA_NATIVE_ARGS},--future-defaults=complete-reflection-types"
fi

if [ "$DRY_RUN" = "true" ]; then
    run_matrix_job "$DIR_VANILLA" "Q" false "$MAVEN_ARG_DEFAULT"
    run_matrix_job "$DIR_VANILLA" "Q_CRT" false "$MAVEN_ARG_CRT"
    echo "[INFO] DRY RUN: Mocking Q_Patched metrics using Q Vanilla metrics..."
    cp "$RESULTS_DIR/metrics_Q.tsv" "$RESULTS_DIR/metrics_Q_Patched.tsv"
else
    run_matrix_job "$DIR_VANILLA" "Q" true "$MAVEN_ARG_DEFAULT"
    run_matrix_job "$DIR_VANILLA" "Q_CRT" false "$MAVEN_ARG_CRT"
    run_matrix_job "$DIR_PATCHED" "Q_Patched" true "$MAVEN_ARG_DEFAULT"
fi

echo ""
echo "======================================================================"
echo "FINAL SUMMARY (MARKDOWN)"
echo "======================================================================"

# Markdown summary by Google Gemini
generate_markdown_summary() {
    local tsv_q="$RESULTS_DIR/metrics_Q.tsv"
    local tsv_crt="$RESULTS_DIR/metrics_Q_CRT.tsv"
    local tsv_patched="$RESULTS_DIR/metrics_Q_Patched.tsv"

    echo "## GraalVM $TARGET_GRAALVM: comparison"
    echo "Hardware: E-Cores (DB), P-Cores (Native image) | Cycles: $RUN_COUNT"
    if [ "$DRY_RUN" = "true" ]; then
        echo "**Note:** This was a DRY RUN. Q_Patched metrics are mocked from Vanilla Q."
    fi
    if [ -n "$EXTRA_NATIVE_ARGS" ]; then
        echo "**Additional Native Args:** \`$EXTRA_NATIVE_ARGS\`"
    fi
    echo ""

    if [[ -s "$tsv_q" && -s "$tsv_crt" && -s "$tsv_patched" ]]; then
        awk -F'\t' '
        function pct(diff, base) {
            if (base == 0) return 0;
            return (diff / base) * 100;
        }
        function fmt_float(name, q, crt, p) {
            d_crt = crt - q; d_p = p - q;
            printf "| **%s** | %.2f | %.2f | %.2f | %+.2f (%+.0f%%) | %+.2f (%+.0f%%) |\n", name, q, crt, p, d_crt, pct(d_crt, q), d_p, pct(d_p, q)
        }
        function fmt_int(name, q, crt, p) {
            d_crt = crt - q; d_p = p - q;
            printf "| **%s** | %d | %d | %d | %+d (%+.0f%%) | %+d (%+.0f%%) |\n", name, q, crt, p, d_crt, pct(d_crt, q), d_p, pct(d_p, q)
        }

        BEGIN {
            app_list[1] = "mp-orm-dbs-awt"
            app_list[2] = "validation-quickstart"
            app_list[3] = "hibernate-orm-quickstart"
        }

        FILENAME==ARGV[1] { q_sz[$1]=$2; q_rs[$1]=$3; q_ty[$1]=$4; q_mt[$1]=$5; q_cl[$1]=$6; q_fd[$1]=$7; q_ttfrc[$1]=$8; q_ttfr[$1]=$9; q_rss[$1]=$10; next }
        FILENAME==ARGV[2] { crt_sz[$1]=$2; crt_rs[$1]=$3; crt_ty[$1]=$4; crt_mt[$1]=$5; crt_cl[$1]=$6; crt_fd[$1]=$7; crt_ttfrc[$1]=$8; crt_ttfr[$1]=$9; crt_rss[$1]=$10; next }
        FILENAME==ARGV[3] { p_sz[$1]=$2; p_rs[$1]=$3; p_ty[$1]=$4; p_mt[$1]=$5; p_cl[$1]=$6; p_fd[$1]=$7; p_ttfrc[$1]=$8; p_ttfr[$1]=$9; p_rss[$1]=$10; next }

        END {
            for (i=1; i<=3; i++) {
                app = app_list[i]
                if (app in q_sz) {
                    printf "### App: `%s`\n", app
                    printf "| Metric | Q (Vanilla) | Q CRT | Q Patched | Δ (Q CRT - Q) | Δ (Q Patched - Q) |\n"
                    printf "|---|---|---|---|---|---|\n"
                    fmt_float("Size (MB)", q_sz[app], crt_sz[app], p_sz[app]);
                    fmt_int("TTFR cold (ms)", q_ttfrc[app], crt_ttfrc[app], p_ttfrc[app]);
                    fmt_int("TTFR (ms)", q_ttfr[app], crt_ttfr[app], p_ttfr[app]);
                    fmt_float("RSS (MB)", q_rss[app], crt_rss[app], p_rss[app]);
                    fmt_int("Resources", q_rs[app], crt_rs[app], p_rs[app]);
                    fmt_int("Types", q_ty[app], crt_ty[app], p_ty[app]);
                    fmt_int("Methods", q_mt[app], crt_mt[app], p_mt[app]);
                    fmt_int("Classes", q_cl[app], crt_cl[app], p_cl[app]);
                    fmt_int("Fields", q_fd[app], crt_fd[app], p_fd[app]);
                    printf "\n"
                }
            }
        }
        ' "$tsv_q" "$tsv_crt" "$tsv_patched"
    else
        echo "| Error | Metrics files missing or empty | N/A | N/A | N/A | N/A | N/A |"
    fi
}

{
    echo "# Quarkus Matrix Run Summary"
    echo "Run Date/Time: $TIMESTAMP"
    echo ""
    generate_markdown_summary
} | tee "$RESULTS_DIR/final_markdown_summary.md"

echo "======================================================================"
echo "[SUCCESS] Markdown summary generated at: $RESULTS_DIR/final_markdown_summary.md"
echo "======================================================================"
