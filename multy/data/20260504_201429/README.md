Numbers obtained using `bfe6aa706683c51483733a6e81f73469424cc76b` sha of
this repository

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

# Run benchmarks 30 times without building quarkus
RUN_COUNT=30 ./run_matrix7_runtime.sh --dry-run

sudo ./bmark-setup stop
```
