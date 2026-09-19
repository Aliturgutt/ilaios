# Desktop 7-Page Canonical Reference Manifest

Task scope: DESKTOP only.

Canonical repository: `Aliturgutt/ilaios`
Base branch: `master`
Base exact HEAD: `3c6170f7fbc5af99d5c64860b2119f6749df6f63`
Migration branch: `desktop/7-page-canonical-migration-20260907`

The user-supplied ZIP `Desktop_7_Page_References_FIXED(1).zip` is the only canonical visual reference set for this migration. Previous Desktop reference images, previous visual baselines, previous logo presentation, and the previous 10-screen visual design are not visual authorities for this task.

Canonical page mapping and verified source-file hashes:

| Page | File | Resolution | SHA-256 |
| --- | --- | --- | --- |
| Ana Sayfa | `01_Ana_Sayfa.png` | 1536×1024 | `700b60c8199719cffc854adc21188a5c3b84d2ff707f74ea170acad138020d93` |
| İş Akışları | `02_Is_Akislari.png` | 1536×1024 | `94cc35b8329d2f4eec701434c35df935a08dfc1088612604d3803391aad6c3d7` |
| Ajanlar | `03_Ajanlar.png` | 1536×1024 | `32e7e90b91a07bbe250ce02898099af23b7267b82d7e347584e6b0668d5d20b2` |
| Çıktılar | `04_Ciktilar.png` | 1536×1024 | `22646276dbb0dd3ff0cd328a02f3a64708922b6d90b8bbe4cd60e2572ca649a1` |
| Onaylar | `05_Onaylar.png` | 1536×1024 | `342c8c91e2b326c6560ae03625860ac2c3e68703e97b786b3119f9edda33c07d` |
| Kanıtlar | `06_Kanitlar.png` | 1536×1024 | `3e5ba7c9ced5452b17212ae6e2a80e974c09bfc348a54f4548e0c8aa73c7bdc8` |
| Ayarlar | `07_Ayarlar.png` | 1536×1024 | `db1996bc13b1423175289f0e01c5f43cf88c5693d8b76ee45d9be967fa536bde` |
| Visual spec | `DESKTOP_VISUAL_SPEC.docx` | — | `cb843af26432f933ccd4a32c73db0974134e489d4811a90f25c85c589c045b3f` |

ZIP SHA-256: `6a34896230fc032923c56107ac4db066cd3e3b1dbaeea2d38bfd7e52abf2eb6c`

## Repository binary verification

At PR #1407 exact head `c6881cea1b0f182fd51a015006e3159894bbbef1`, all eight files under `docs/platform/desktop/Desktop_7_Page_References/` were verified byte-identical to the user-supplied fixed ZIP by matching both byte size and Git blob SHA-1 calculated from the local canonical bytes.

| File | Bytes | Git blob SHA-1 |
| --- | ---: | --- |
| `01_Ana_Sayfa.png` | 987565 | `7ccc313df587955fe9c297d841b3a7ecde1b3edb` |
| `02_Is_Akislari.png` | 836024 | `5871bcb5d0d8519da0875d5ecba33f486d12f129` |
| `03_Ajanlar.png` | 1342622 | `4dd19ecee85e083a387ce23b0881afb4dc9c07a7` |
| `04_Ciktilar.png` | 802932 | `3f87be23b12955045ce7ab52187c2470dbbdffef` |
| `05_Onaylar.png` | 833220 | `425293ecfb1ae29333bb6214c411d7a388140eab` |
| `06_Kanitlar.png` | 799771 | `c767f5015e86c47b2476ce42bff65c128d390a60` |
| `07_Ayarlar.png` | 709355 | `c8c18b38b5922e458c8e8382b842f86fdd8f5baf` |
| `DESKTOP_VISUAL_SPEC.docx` | 14433 | `190382b7857f4a051e4338d47cff37143e993fbc` |

This closes the reference-presence blocker. It does not constitute visual implementation acceptance.

## Measured common shell geometry

Measurements below are taken directly from the 1536×1024 canonical PNGs before implementation. One-pixel separator/anti-alias boundaries are recorded explicitly rather than rounded into old Desktop constants.

- Canonical viewport: `1536×1024`.
- Sidebar visual region: `x=0..218`; main vertical separator is approximately `x=219..220`.
- Main/header region begins immediately after the sidebar separator.
- Header visual height: approximately `68 px`; horizontal separator occupies the following boundary row.
- Canonical main content begins below that header; page-specific content must not reuse the old 72 px topbar assumption.
- Sidebar contains exactly seven top-level items: Ana Sayfa, İş Akışları, Ajanlar, Çıktılar, Onaylar, Kanıtlar, Ayarlar.
- No secondary-navigation menu is present in any canonical reference.
- The light horizontal ILAIOS lockup shown in the new references is the logo-presentation authority. Previous Desktop logo sizing/placement is superseded.

Page-specific measurement is recorded immediately before each page implementation and must be compared against the corresponding canonical PNG. Do not copy screenshot telemetry or demo counts into runtime state.

Runtime/business truth remains repo/runtime-authoritative. Screenshot values must never be copied as live runtime truth.

Required implementation order: reference measurement → in-place Flutter implementation → real render → screenshot → overlay/diff → correction → re-render. Screenshot/CI success alone is not visual acceptance.
