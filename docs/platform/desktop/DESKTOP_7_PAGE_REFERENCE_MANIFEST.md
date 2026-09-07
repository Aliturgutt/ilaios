# Desktop 7-Page Canonical Reference Manifest

Task scope: DESKTOP only.

Canonical repository: `Aliturgutt/ilaios`
Base branch: `master`
Base exact HEAD: `3c6170f7fbc5af99d5c64860b2119f6749df6f63`
Migration branch: `desktop/7-page-canonical-migration-20260907`

The user-supplied ZIP `Desktop_7_Page_References_FIXED(1).zip` is the only canonical visual reference set for this migration. Previous Desktop reference images, previous visual baselines, and the previous 10-screen visual design are not visual authorities for this task.

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

Runtime/business truth remains repo/runtime-authoritative. Screenshot values must never be copied as live runtime truth.

Required implementation order: reference measurement → in-place Flutter implementation → real render → screenshot → overlay/diff → correction → re-render. Screenshot/CI success alone is not visual acceptance.

Binary reference files are not represented by this manifest; their repository presence and byte-identical hashes must be verified before visual acceptance can be claimed.
