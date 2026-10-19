# Simplified Chinese localization review

Upstream base: ed3e7c0dfacfdeaf3349dee73edf9e3621217462 (2025-06-20).

This branch preserves original upstream history and reconstructs the final locally saved modifications as a logical commit series dated 2026-10-19. It is not a recovery of the original chronological development commits.

The first five commits cover all 49 substantive changed/new files in the preserved modern working copy, with upstream files retained in place. No unchanged upstream source tree is copied into a nested source/ directory. Unmodified upstream files omitted by the earlier export filters are retained from the base, not deleted.

The source is the final working copy, including later shared memory and AF changes. It is not proven to recreate every historical camera ZIP byte-for-byte. Original 5D3 r9 core modifications are still missing. The standalone AF branch has the smaller feature diff and reproduces the r21 module against unchanged upstream headers.

Support tools are a separate commit. Their historical external inputs/layout requirements are documented. This cleanup does not imply fresh full-camera builds, upstream compatibility, or new real-camera test evidence.

Use `git log --reverse ed3e7c0..HEAD` and `git diff ed3e7c0..HEAD`. Upstream copyrights and licenses are preserved.
