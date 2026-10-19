# 5D3 Live AF r21 review

Base: reticulatedpines/magiclantern_simplified ed3e7c0dfacfdeaf3349dee73edf9e3621217462.

These commits were reconstructed on 2026-10-19 from the final preserved source. They are not represented as the original development history. The original upstream commits remain ancestors.

The implementation targets the historical localized 5D3 1.2.3 r9 core ABI (`VIDAF_LEGACY_R9`). It is experimental and is not asserted to work with an arbitrary upstream core. The original r9 localized core's exact modified source is still missing; this module branch does not close that gap.

The module observes Canon's AF frame in LiveView and requests one native focus operation after the frame settles. It is not a replacement for Canon's focusing algorithm. Recording/RAW behavior remains experimental and requires real-camera validation.

## Reproduce the distributed module

Use xPack ARM GCC 12.2.1-1.1. From this repository root in PowerShell:

```powershell
& ./tools/reproduce_af_r21.ps1 -ArmBin 'D:/toolchains/xpack-arm-none-eabi-gcc-12.2.1-1.1/bin'
```

The script uses explicitly frozen historical metadata in doc/repro, including its historical build date. That generated header is reproduction input, not the normal Makefile's metadata generator.

Expected output SHA-256:
`81e00fcd8c430e5c9f6a2dc006a091bd86508f1a7346bcb8bcf2dd2f49f57e09`

Verified on 2026-10-19: the four module files compiled against the unmodified ed3e7c0 upstream include/src headers produce exactly this SHA-256. No localized core headers were required. This verifies module correspondence, not camera safety or reproduction of the historical whole package.
