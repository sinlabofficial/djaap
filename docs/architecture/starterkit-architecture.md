# Arsitektur djaapp Starterkit

Status: reference baseline | Updated: 2026-08-12

Dokumen ini menjelaskan model mental, boundary, aliran request, dan keputusan
arsitektur djaapp. Detail perintah ada di
[`docs/toolchain-and-commands.md`](../toolchain-and-commands.md), sedangkan
prosedur produksi ada di
[`docs/platform-runtime-deployment.md`](../platform-runtime-deployment.md) dan
[`docs/operations-runbook-and-observability.md`](../operations-runbook-and-observability.md).

## Ringkasan arsitektur

djaapp adalah Django full-stack webapp untuk **satu organisasi per deployment**.
Dashboard internal adalah antarmuka utama: Django Templates merender halaman,
HTMX melakukan interaksi server-backed, Alpine.js menangani state lokal, dan
TailwindCSS menyediakan token serta style.

```text
Browser / mobile client / integration
          |
          +--> /dashboard/  -- session auth --> dashboard
          |                                      |
          |                                      +--> core selectors/services
          |                                      +--> Domain App public interfaces
          |
          +--> /api/        -- JWT (optional) -> api adapter
          |                                      |
          |                                      +--> core / Domain App public interfaces
          |
          +--> /webhooks/   -- signature ------> platform_runtime
                                                 |
                 +-------------------------------+----------------+
                 |                               |                |
              tasks                         webhooks         realtime
                 |                               |                |
                 +---------- Runtime Logs ------+----------------+
```

API dan realtime adalah adapter opsional. Dashboard HTTP/HTMX tetap menjadi
sumber state authoritative; realtime hanya memberi notifikasi agar client
mengambil ulang state.

## Boundary aplikasi

| Aplikasi | Kepemilikan | Interface publik |
| --- | --- | --- |
| `core` | User, Role, Permission, UserRole, OrganizationSettings, identity/RBAC | model, selector, service |
| `dashboard` | UI internal session-authenticated | views, forms, selectors, service calls |
| `platform_runtime` | task, webhook, realtime, Runtime Log | `tasks`, `webhooks`, `realtime`, `maintenance` |
| `api` | REST/JWT untuk client eksternal | serializer, viewset, adapter |
| `example` | replaceable Domain App reference | selector, service, form, template miliknya |

Aturan dependency bersifat default-deny. App boleh memakai interface publik yang
tercatat di App Map, tetapi tidak boleh mengimpor model, view, form, admin,
private helper, atau signal wiring milik app lain. Cross-domain workflow punya
satu Workflow Owner.

### `core`: identitas dan kebijakan global

`User` menggunakan email sebagai canonical username dan mendukung phone serta
employee ID sebagai identitas login melalui authentication backend. Role
memiliki kumpulan Permission dalam bentuk `resource:action`; UserRole
menghubungkan user dan role. Permission user adalah union dari role aktif, dan
superuser melewati pemeriksaan RBAC.

Model core menggunakan safe delete. Query normal menyembunyikan record yang
terhapus, sementara manager khusus tersedia untuk kebutuhan pemulihan atau
audit. `OrganizationSettings` adalah singleton identitas organisasi, bukan
tenant registry.

### `dashboard`: presentation boundary

View dashboard harus tipis. View menerima request, memeriksa authentication dan
permission, memanggil selector untuk reads atau service untuk writes, lalu
merender template. Template tidak boleh memuat business logic atau mengakses
model lintas Domain App.

Dashboard memiliki dua shell presentasi: shell dashboard sebagai default dan
Mobile Presentation Mode sebagai opsi. Resolusi mode:

```text
forced role policy -> user preference -> organization default
```

Mode presentasi tidak mengubah route, permission, service, atau authoritative
state domain.

### `platform_runtime`: infrastructure boundary

Platform Runtime menyediakan kontrak generik, bukan domain bisnis:

- Background Task harus kecil, retry-aware, memiliki timeout, dan idempotent.
- `enqueue_after_commit()` menjadwalkan task setelah transaksi berhasil commit.
- Webhook diverifikasi, direduplikasi, disimpan dalam bentuk aman, lalu
  diserahkan ke task.
- Realtime event dipublish setelah commit dan difilter berdasarkan permission.
- Runtime Log mencatat lifecycle task, webhook, dan realtime secara terpisah
  dari Audit Log.
- Redaction diterapkan pada metadata operasional, payload webhook, dan payload
  realtime.

Tidak ada worker provider, broker, scheduler, Redis, atau Channels yang wajib
di baseline. Production harus memilih dan memasang adapter eksternal ketika
capability terkait diaktifkan.

## Pola data dan transaksi

Gunakan alur berikut untuk setiap perubahan bisnis:

```text
request -> form/serializer validation -> service -> transaction.atomic()
                                      -> authoritative write
                                      -> transaction.on_commit(task/realtime)
                                      -> response / redirect / HTMX fragment
```

Selector hanya membaca. Service menjadi lokasi validasi invariants yang perlu
transaksi, perubahan model, audit, dan orkestrasi public service. Side effect
tidak boleh dijalankan sebelum commit karena transaksi dapat dibatalkan.

Idempotency wajib untuk operasi side-effecting. Gunakan state transition yang
aman atau idempotency key stabil. Webhook memakai dedupe key dari provider dan
event identifier/payload hash. Replay webhook selalu eksplisit dan menghasilkan
jejak audit.

## Authentication, authorization, dan audit

Dashboard memakai Django session authentication. REST adapter, jika diaktifkan,
menggunakan JWT. Authentication dan authorization bukan tanggung jawab
template; endpoint tetap harus menegakkan decorator/permission check.

RBAC terdiri dari:

1. resource dan action permission;
2. role yang memiliki permission;
3. active UserRole assignment;
4. pemeriksaan `user_has_permission()` atau public equivalent.

`Audit Log` menjawab "siapa mengubah data apa". `Runtime Log` menjawab "task,
webhook, atau realtime event berada di lifecycle mana". Keduanya memiliki
retention dan kebutuhan akses berbeda. Jangan memasukkan credential, secret,
raw request body, atau payload sensitif ke salah satu log.

## Request lifecycle

### Dashboard request

1. Django routing mencocokkan URL dashboard.
2. Authentication middleware mengisi `request.user`.
3. Decorator memeriksa login, staff, dan permission yang diperlukan.
4. View memanggil selector untuk data atau form untuk input.
5. Write memanggil service transactional.
6. View mengembalikan full page atau HTMX partial/redirect.
7. Audit atau runtime evidence dicatat tanpa mengekspos data sensitif.

### API request

API adalah adapter, bukan domain baru. Serializer memvalidasi bentuk request,
kemudian viewset memanggil public selector/service yang sama dengan dashboard.
Perbedaan client tidak boleh menghasilkan aturan bisnis atau authorization yang
berbeda.

### Webhook request

1. Provider dicari di registry.
2. Signature HMAC diverifikasi.
3. JSON object divalidasi dan direduksi menjadi safe payload.
4. Dedupe key mencegah event yang sama diproses dua kali.
5. Event disimpan dan task di-enqueue setelah commit.
6. Handler Domain App mengubah authoritative state secara idempotent.
7. Runtime Log mencatat received, verified, enqueued, processed, atau failed.

## Deployment shape

Development Compose menjalankan PostgreSQL 16, web Django, dan Tailwind watch.
Production Compose hanya merepresentasikan web process dan menggunakan
PostgreSQL eksternal. Worker, scheduler, ASGI/realtime, TLS, backup, alerting,
dan incident response adalah responsibility deployment platform.

Urutan release production:

```text
check-deploy
  -> backup checkpoint
  -> prod-build
  -> deploy-migrate
  -> start web and enabled process roles
  -> health/capability smoke checks
  -> monitoring stabilization window
```

`deploy-migrate` dijalankan sekali dari immutable image sebelum web process
scaled. Startup web bersifat serve-only agar beberapa instance tidak berlomba
melakukan mutation release.

## Batasan yang disengaja

Starterkit ini tidak menyediakan:

- shared SaaS tenancy atau Workspace/multi-workspace;
- DataSource, Dataset, Artifact, connector, refresh, atau scheduler domain;
- AgentRun, AgentStep, ToolCall, PydanticAI, queue agent, atau agent runtime;
- provider worker/broker tertentu;
- observability SaaS, managed backup, TLS ingress, atau alert delivery.

Batasan ini menjaga baseline tetap installable dan backend-neutral. Capability
baru ditambahkan sebagai Domain App atau adapter eksplisit setelah outcome
produk dan responsibility deployment ditentukan.

## Cara memperluas tanpa merusak boundary

Sebelum membuat Domain App baru:

1. baca `CONTEXT.md`, `docs/architecture/app-map.md`, dan ADR terkait;
2. tetapkan ownership model, navigation, permission, selector, service, dan
   Workflow Owner;
3. buat `backend/apps/<domain>/AGENTS.md` dari template;
4. implementasikan vertical slice dengan test public seam;
5. tambahkan architecture import-boundary test bila exception diperlukan;
6. update App Map, glossary, reference docs, dan release evidence;
7. jalankan `just verify`.

Jangan memindahkan business logic ke view/template hanya karena flow dimulai
dari dashboard, dan jangan menambahkan dependency eksternal jika boundary yang
ada sudah cukup.
