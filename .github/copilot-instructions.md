<!-- rtk-instructions v2 -->
# RTK — Token-Optimized CLI

**rtk** is a CLI proxy that filters and compresses command outputs, cutting 60-90% of bash output.

## Rule

Prefix external programs with `rtk`:

```bash
# Instead of:              Use:
git status                 rtk git status
git log -10                rtk git log -10
cargo test                 rtk cargo test
docker ps                  rtk docker ps
kubectl get pods           rtk kubectl get pods
```

Do not prefix shell builtins or keywords — `test`, `[`, `read`, `cd`, `echo`,
`export`, `eval`, `source`, `printf`. Commands such as `test`, `read`, and
`env` also have RTK subcommands with different meanings; invoke the native
command directly when you need it.

## Meta commands (use directly)

```bash
rtk gain              # Token savings dashboard
rtk gain --history    # Per-command savings history
rtk discover          # Find missed rtk opportunities
rtk bypass <cmd>      # Run raw (no filtering) but track usage
```
<!-- /rtk-instructions -->
