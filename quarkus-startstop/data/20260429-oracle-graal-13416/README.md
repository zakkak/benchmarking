Data generated with command

```
mvn clean verify -Pnative -Dquarkus.native.container-runtime=podman -DexcludeTags=bomtests,generator,special-chars,codequarkus -Dquarkus.version=3.33.1 -Dstart-stop.skip.log-check -Dstart-stop.iterations=30 -Dstart-stop.command.prefix='taskset -c 5-8' -Dstart-stop.cold-start -Dstart-stop.skip.threshold-check

mv testsuite/target/ target3-33-1-jdk25-defaults

mvn clean verify -Pnative -Dquarkus.native.container-runtime=podman -DexcludeTags=bomtests,generator,special-chars,codequarkus -Dquarkus.version=3.33.1 -Dstart-stop.skip.log-check -Dstart-stop.iterations=30 -Dstart-stop.command.prefix='taskset -c 5-8' -Dstart-stop.cold-start -Dstart-stop.skip.threshold-check -Dquarkus.native.additional-build-args-append=--future-defaults=complete-reflection-types

mv testsuite/target/ target3-33-1-jdk25-complete-reflection
```

To evaluate the impact of `--future-defaults=complete-reflection-types` for https://github.com/oracle/graal/issues/13416
