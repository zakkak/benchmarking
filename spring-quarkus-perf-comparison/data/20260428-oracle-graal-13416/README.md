Data generated with command

```
export ITERATIONS=50; ./run-benchmarks.sh --drop-fs-caches --graalvm-version 25.0.2.r25-graalce --host LOCAL --java-version 25.0.2-tem --runtimes quarkus3-native --quarkus-version 3.33.1 --output-dir ../../20260428-defaults --tests measure-time-to-first-request,measure-rss,run-load-test --wait-time 1 --iterations $ITERATIONS; ./run-benchmarks.sh --drop-fs-caches --graalvm-version 25.0.2.r25-graalce --host LOCAL --java-version 25.0.2-tem --runtimes quarkus3-native --quarkus-version 3.33.1 --output-dir
../../20260428-complete-reflection --tests measure-time-to-first-request,measure-rss,run-load-test --wait-time 1 --iterations $ITERATIONS --native-quarkus-build-options -Dquarkus.native.additional-build-args-append=--future-defaults=complete-reflection-types
```

To evaluate the impact of `--future-defaults=complete-reflection-types` for https://github.com/oracle/graal/issues/13416
