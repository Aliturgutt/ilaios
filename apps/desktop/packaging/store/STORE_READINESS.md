# ILAIOS Desktop — Microsoft Store Readiness

This file prepares the repository-owned Store listing material that can be completed before Microsoft account / Partner Center publisher connection. It deliberately does **not** claim signing, certification, publication, or Microsoft OAuth completion.

## Product identity

- Product name: **ILAIOS Desktop**
- Publisher display name: **ILAIOS**
- Platform: Windows Desktop, x64
- UI languages implemented by the Desktop client: **English (en-US)** and **Türkçe (tr-TR)**
- Package identity / publisher subject: **EXTERNAL — use the exact Partner Center-assigned values only**
- Production signing certificate: **EXTERNAL — never invent or commit certificate material**

## English listing copy

### Short description

A governed Windows control-plane client for ILAIOS goals, workflows, execution visibility, evidence, approvals, artifacts, and usage state.

### Description

ILAIOS Desktop provides a Windows interface to the authenticated ILAIOS control plane. From one application, users can submit goals, inspect governed workflow state, view authoritative execution events and worker leases when exposed by the backend, review evidence and approvals, save verified artifacts, and inspect available usage information.

The Desktop client is intentionally truth-preserving: when the control plane does not expose an authoritative value, the interface reports it as unavailable instead of generating synthetic progress, workers, costs, logs, or artifacts. English and Turkish interfaces are supported, and the selected language is retained locally.

Availability of individual runtime projections depends on the connected ILAIOS backend and the user’s authenticated permissions.

## Turkish listing copy

### Kısa açıklama

ILAIOS hedefleri, iş akışları, yürütme görünürlüğü, kanıtlar, onaylar, çıktılar ve kullanım durumu için yönetilen Windows istemcisi.

### Açıklama

ILAIOS Desktop, kimliği doğrulanmış ILAIOS kontrol düzlemi için Windows arayüzüdür. Kullanıcılar tek uygulamadan hedef gönderebilir, yönetilen iş akışı durumunu inceleyebilir, arka uç tarafından sunulduğunda yetkili yürütme olaylarını ve çalışan kiralamalarını görebilir, kanıt ve onayları inceleyebilir, doğrulanmış çıktıları kaydedebilir ve mevcut kullanım bilgilerini görüntüleyebilir.

Desktop istemcisi gerçeği koruyacak şekilde tasarlanmıştır: kontrol düzlemi yetkili bir değer sunmuyorsa arayüz sahte ilerleme, çalışan, maliyet, günlük veya çıktı üretmek yerine bilgiyi kullanılamıyor olarak gösterir. İngilizce ve Türkçe arayüz desteklenir ve seçilen dil yerel olarak hatırlanır.

Tek tek çalışma zamanı projeksiyonlarının kullanılabilirliği bağlı ILAIOS arka ucuna ve kullanıcının kimliği doğrulanmış yetkilerine bağlıdır.

## Store assets and screenshots

Repository package generation already derives Store/MSIX logo assets from the canonical ILAIOS application-icon master. Final Store screenshots must be captured from the exact signed/release-candidate Windows build, not from mockups.

Required final screenshot set after exact-final Windows QA:

1. Home / Active Workflow — wide layout, authoritative empty or real state.
2. Goals — one-prompt entry surface.
3. Workflows / Control Center.
4. Evidence or Artifacts — only real authoritative records if available.
5. Turkish UI — one representative wide screen.

Do not populate fake runtime data solely for screenshots.

## External fields intentionally blocked until Microsoft connection

The following are not repository-owned facts and must remain unresolved until Microsoft / Partner Center provides or confirms them:

- Partner Center package Identity Name.
- Publisher subject / certificate identity.
- Production signing secrets.
- Store submission ID and certification result.

Privacy-policy and support URLs must be copied only from verified live ILAIOS production pages. They are intentionally not guessed in this file.

## Pre-submission technical gates

A release candidate is eligible for Store submission only when all of the following are true on one exact master SHA:

- Flutter analyze: PASS.
- Flutter tests: PASS.
- Required CI Gate: PASS.
- Desktop Windows Gate: PASS.
- MSIX Packaging: PASS.
- MSIX unpack/manifest inspection: PASS.
- Exact-master Windows launch: PASS.
- English/Turkish UI and 100%/125%/150% scaling QA: PASS.
- Existing Google session regression: PASS where Google is configured.
- No fabricated runtime telemetry.

Microsoft OAuth is independent of the Desktop release-readiness checks above and is not required to be represented as complete until it has its own configuration and evidence.
