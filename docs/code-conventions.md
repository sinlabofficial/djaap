# djaapp Code Conventions

Code convention dan aturan `Do / Don't` untuk starterkit djaapp. Dokumen ini
melengkapi `AGENTS.md`, `CONTEXT.md`, `CONTRIBUTING.md`, App Map, dan ADR.

Jika aturan berbeda, gunakan urutan source of truth berikut:

1. security dan data-safety rules;
2. `CONTEXT.md` dan `AGENTS.md`;
3. App Map serta ADR;
4. dokumen ini;
5. kebiasaan lokal pada file yang berdekatan.

## 1. Prinsip utama

### Do

- Pilih perubahan terkecil yang menyelesaikan outcome.
- Pertahankan boundary yang sudah ada sebelum membuat abstraksi baru.
- Gunakan nama yang menjelaskan business intent.
- Tulis test untuk behavior eksternal dan failure path.
- Jadikan source code, configuration, dan test sebagai source of truth.
- Dokumentasikan keputusan yang sulit dibalik di ADR.

### Don't

- Jangan menambah layer generic sebelum ada kebutuhan nyata.
- Jangan memindahkan business behavior ke framework adapter.
- Jangan mengubah kontrak publik hanya untuk memudahkan satu caller.
- Jangan menyebut perubahan selesai hanya karena command berhasil dijalankan;
  baca output dan simpan evidence.
- Jangan menghapus perubahan user lain atau merapikan file yang tidak terkait.

## 2. Python dan tooling

Project memakai Python 3.14, type hints, Ruff, pytest, dan Mypy.

### Do

- Ikuti PEP 8 dan batas 88 kolom.
- Gunakan type hint pada public function, service, selector, dan data contract.
- Gunakan `pathlib.Path` untuk path filesystem.
- Gunakan `collections.abc` untuk `Mapping`, `Sequence`, dan tipe collection
  pada public interface.
- Gunakan `str | None`, `list[str]`, dan syntax modern yang sesuai versi Python.
- Jalankan formatter/linter yang sudah dikonfigurasi repository.
- Gunakan exception yang spesifik dan message yang membantu operator.

```python
from collections.abc import Mapping
from typing import Any


def normalize_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {str(key): value for key, value in payload.items()}
```

### Don't

- Jangan menambahkan `# type: ignore` tanpa alasan dan test.
- Jangan memakai `Any` sebagai pengganti desain contract.
- Jangan menangkap `Exception` lalu mengabaikannya.
- Jangan membuat global mutable state untuk business data.
- Jangan menambahkan dependency baru bila standard library atau dependency
  yang sudah ada cukup.
- Jangan menulis code generator atau script sekali pakai ke source tree tanpa
  kebutuhan maintenance.

## 3. Naming dan struktur file

### Naming

| Artefak | Convention | Contoh |
| --- | --- | --- |
| Domain App | snake_case | `billing`, `order_fulfillment` |
| model | singular PascalCase | `Invoice`, `PaymentAttempt` |
| selector | noun + verb | `invoice_get`, `invoice_list` |
| service | noun + command | `invoice_submit`, `payment_capture` |
| task | verb + object | `send_invoice`, `reconcile_payment` |
| permission | `resource:action` | `invoices:view` |
| event | `domain.action` | `invoice.approved` |
| test | behavior yang diverifikasi | `test_submit_is_idempotent` |
| template | snake_case | `invoice_detail.html` |

### Struktur Domain App

```text
backend/apps/<domain>/
├── AGENTS.md
├── apps.py
├── models.py
├── selectors.py
├── services.py
├── forms.py
├── views.py
├── urls.py
├── tasks.py
├── webhooks.py
├── contracts.py
├── migrations/
└── tests/
```

Tambahkan file hanya saat ada behavior yang membutuhkannya. Tidak semua app
harus memiliki API, task, webhook, atau realtime adapter.

## 4. Arsitektur aplikasi

`djaapp` adalah single-organization full-stack webapp. Tidak ada tenancy
Workspace sebagai boundary default.

### Boundary utama

| Layer | Tanggung jawab | Boleh melakukan |
| --- | --- | --- |
| `core` | user, role, permission, organization settings | identity dan RBAC global |
| Domain App | business model dan workflow | business read/write |
| `dashboard` | session UI adapter | render, form binding, routing |
| `api` | optional external adapter | serialize dan expose API |
| `platform_runtime` | task, webhook, realtime, operational log | generic infrastructure |

### Do

- Domain App memiliki model, navigation, permission, selector, service, dan
  template sendiri.
- Cross-domain dependency harus tercatat di `docs/architecture/app-map.md`.
- Setiap cross-domain workflow memiliki satu Workflow Owner.
- Gunakan public selector untuk membaca Domain App lain.
- Gunakan public service untuk menulis ke Domain App lain.
- Perbarui architecture import test jika dependency publik berubah.

### Don't

- Jangan import model, view, form, admin, task, atau helper private app lain.
- Jangan membuat `utils.py` sebagai tempat business rule lintas domain.
- Jangan membuat Dashboard query langsung ke model Domain App bila public
  selector tersedia.
- Jangan membuat Platform Runtime mengetahui business model atau business
  state Domain App.
- Jangan memperlakukan `models.py`, `signals.py`, `observability.py`,
  `redaction.py`, atau `consumers.py` Platform Runtime sebagai public API
  tanpa keputusan kontrak baru.

## 5. Models dan database

### Do

- Model menyimpan state dan invariant data yang memang dimiliki app.
- Beri `unique`/`UniqueConstraint` untuk idempotency dan deduplication.
- Tambahkan index untuk query operasional yang terbukti sering digunakan.
- Gunakan soft delete untuk model yang mengikuti safe-delete policy.
- Buat migration melalui Django dan baca hasil migration.
- Gunakan `select_for_update()` untuk state transition yang bersaing.
- Gunakan `transaction.atomic()` untuk perubahan yang harus atomik.

```python
class Invoice(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"

    status = models.CharField(max_length=20, choices=Status)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["customer_id", "external_id"],
                name="invoice_customer_external_id_unique",
            )
        ]
```

### Don't

- Jangan hard-delete model business tanpa product decision.
- Jangan menyimpan raw credential, webhook body, access token, atau unrestricted
  task result.
- Jangan memakai database increment sebagai pengganti idempotency event.
- Jangan mengubah data di migration dengan side effect eksternal.
- Jangan menjalankan network call di dalam transaction terbuka tanpa alasan
  yang terdokumentasi.
- Jangan membuat field generik seperti `data = JSONField()` untuk menghindari
  pemodelan domain yang sudah jelas.

## 6. Selectors

Untuk pembagian tanggung jawab validation antara forms, serializers, services,
models, webhook, dan task, gunakan
[`docs/guides/data-validation.md`](guides/data-validation.md).

Selector adalah read boundary. Selector boleh mengembalikan QuerySet untuk
pagination, atau DTO sederhana untuk read model.

### Do

```python
from django.db.models import QuerySet

from .models import Invoice


def invoice_list(*, status: str = "") -> QuerySet[Invoice]:
    queryset = Invoice.objects.order_by("-created")
    if status:
        queryset = queryset.filter(status=status)
    return queryset


def invoice_get(*, invoice_id) -> Invoice | None:
    return Invoice.objects.filter(id=invoice_id).first()
```

- Beri nama selector berdasarkan intent read.
- Filter input yang valid di form atau selector boundary.
- Gunakan `select_related`/`prefetch_related` jika query shape memang perlu.
- Kembalikan `None` untuk get yang tidak menemukan object bila itu contract-nya.
- Tambahkan test untuk empty, filtered, unauthorized, dan deleted state.

### Don't

- Jangan melakukan mutation di selector.
- Jangan memanggil task, email, webhook, atau external API dari selector.
- Jangan menyembunyikan permission mutation di query yang tidak terdokumentasi.
- Jangan membuat selector mengembalikan raw credential atau private metadata.

## 7. Services dan transaction

Service adalah write boundary dan pemilik business command.

### Do

```python
from django.db import transaction


@transaction.atomic
def invoice_submit(*, invoice_id, actor):
    invoice = Invoice.objects.select_for_update().get(id=invoice_id)
    if invoice.status != Invoice.Status.DRAFT:
        raise ValueError("Only draft invoices can be submitted")

    invoice.status = Invoice.Status.SUBMITTED
    invoice.save(update_fields=["status", "updated"])
    transaction.on_commit(
        lambda: enqueue_invoice_processing(str(invoice.id))
    )
    return invoice
```

- Validasi permission dan invariant sebelum mutation.
- Gunakan state transition yang eksplisit.
- Gunakan unique event/idempotency key bila command dapat diulang.
- Pisahkan perubahan database dari side effect eksternal.
- Kembalikan result yang stabil dan berguna bagi caller.
- Test success, invalid state, unauthorized, duplicate, rollback, dan
  concurrent path yang relevan.

### Don't

- Jangan menaruh business mutation di view, form `clean()`, model property,
  selector, atau template.
- Jangan menggunakan `get_or_create` tanpa memahami duplicate/concurrency
  semantics.
- Jangan mengirim email, memanggil provider, atau enqueue task sebelum commit.
- Jangan increment counter pada retry tanpa event key yang unik.

## 8. Views, forms, dan routes

### Views

### Do

- Gunakan view sebagai adapter tipis.
- Ambil input dari request, validasi form, panggil selector/service, render
  template, dan set response/HTMX header.
- Gunakan decorator auth dan permission yang konsisten.
- Bedakan full-page response dan HTMX partial response.
- Gunakan `Http404` atau response yang eksplisit untuk resource tidak ditemukan.

### Don't

- Jangan menulis query panjang dan business branching di view.
- Jangan menerima mutation hanya karena user sudah login.
- Jangan membocorkan exception internal atau credential pada response.
- Jangan membuat view mengimpor private helper Domain App lain.

### Forms

### Do

- Gunakan form untuk parsing dan input validation.
- Validasi field-level dan cross-field input yang memang merupakan input rule.
- Set widget class secara konsisten melalui helper yang ada.
- Re-render form dengan error yang dapat dipahami.

### Don't

- Jangan melakukan side effect di `clean()`.
- Jangan menggunakan form sebagai pengganti service.
- Jangan memberi user field yang tidak boleh dimutasi.

## 9. Dashboard frontend

Stack dashboard adalah Django Templates, HTMX, Alpine.js, dan TailwindCSS.

### Do

- Gunakan server-rendered HTML sebagai default.
- Gunakan HTMX untuk request server dan partial update.
- Gunakan Alpine.js hanya untuk local UI state.
- Beri stable `id`, `data-testid`, dan accessible label pada interactive region.
- Sediakan loading, empty, error, dan success state.
- Pertahankan query filter saat pagination dan refresh.
- Pastikan partial HTMX tidak mengembalikan application shell kedua.
- Escape output default Django; render safe HTML hanya setelah review keamanan.

### Don't

- Jangan mengubah dashboard menjadi SPA.
- Jangan menulis `fetch`/XHR manual jika HTMX sudah memenuhi kebutuhan.
- Jangan menyimpan business state authoritative di browser.
- Jangan menampilkan `safe_payload`, `safe_metadata`, credential, atau raw error
  detail ke HTML.
- Jangan mengandalkan warna saja untuk status atau error.

### Template style

```django
{% if page_obj.object_list %}
  {% for item in page_obj %}
    <article data-testid="item-{{ item.id }}">
      <h2>{{ item.name }}</h2>
    </article>
  {% endfor %}
{% else %}
  <p>No items found.</p>
{% endif %}
```

## 10. REST API

REST adalah adapter optional untuk external client, bukan primary dashboard
interface.

### Do

- Gunakan JWT/session contract yang sudah ada.
- Gunakan serializer untuk representation dan validation API.
- Panggil public selector/service dari API view.
- Terapkan permission, pagination, throttling, dan safe error response.
- Version atau document breaking contract.

### Don't

- Jangan membuat business logic berbeda antara Dashboard dan API.
- Jangan mengekspos model internal secara otomatis.
- Jangan mengembalikan raw exception, secret, atau unrestricted task result.
- Jangan menambah API endpoint bila hanya dashboard internal yang membutuhkan
  behavior tersebut.

## 11. Background Tasks, Webhooks, dan Realtime

Platform Runtime bersifat backend-neutral. Celery, Django-Q2, Redis, dan
Channels tetap optional.

### Background task Do

- Gunakan `platform_task`.
- Buat task kecil dan focused.
- Gunakan state-based write atau idempotency key.
- Retry hanya exception transient.
- Beri timeout pada task yang memiliki batas waktu yang jelas.
- Gunakan `enqueue_after_commit` untuk task setelah database commit.
- Baca ulang authoritative state di dalam task.
- Log lifecycle secara aman dan monitor failure/timeout/retry.

### Background task Don't

- Jangan menyimpan raw args atau unrestricted return value ke Runtime Log.
- Jangan retry validation error, permission error, atau permanent provider error.
- Jangan menggabungkan orchestration, business mutation, dan network fan-out
  ke satu task besar.
- Jangan menganggap ImmediateBackend sebagai production worker.

### Webhook Do

- Gunakan endpoint generik `POST /webhooks/<provider>/` dan verifikasi
  signature dari raw request body sebelum parsing business data.
- Untuk kontrak bawaan, gunakan header `X-Webhook-Signature` dengan format
  `sha256=<HMAC-SHA256>`.
- Daftarkan provider dan handler melalui
  `apps.platform_runtime.webhooks.register_webhook_provider` dari wiring
  startup Domain App; registration harus terjadi di setiap web dan worker
  process.
- Dedupe berdasarkan provider + external event ID atau payload hash.
- Simpan payload hash/reference dan safe redacted payload saja.
- Acknowledge dengan `202 Accepted` setelah event diterima dan di-handoff
  sesuai contract; proses business handler dilakukan asynchronous.
- Buat handler idempotent dan replayable.
- Beri permission khusus untuk replay dan Audit Log setiap replay.

### Webhook Don't

- Jangan menyimpan raw request body, provider secret, signature, atau token.
- Jangan menganggap request provider aman hanya karena format JSON valid.
- Jangan menjalankan workflow bisnis besar langsung di HTTP request.
- Jangan replay event tanpa validasi status dan permission.
- Jangan menganggap semua provider memakai HMAC-SHA256; buat adapter/verifier
  khusus bila provider memiliki signature scheme yang berbeda.

### Realtime Do

- Publish setelah commit.
- Kirim notification minimal dengan permission dan correlation ID.
- Perlakukan HTTP/HTMX sebagai authoritative fallback.
- Re-check permission pada subscription/delivery.
- Gunakan shared channel layer di production.

### Realtime Don't

- Jangan memakai WebSocket sebagai source of truth.
- Jangan mengirim seluruh object atau secret pada payload.
- Jangan membuat Channels/Redis dependency wajib baseline.
- Jangan menganggap in-memory channel layer aman untuk multi-process production.

## 12. Security, RBAC, audit, dan data safety

### Do

- Default deny untuk permission.
- Bedakan read permission dari mutate/replay/admin permission.
- Gunakan superuser bypass hanya pada contract RBAC yang sudah ada.
- Audit perubahan business/access data.
- Simpan Runtime Log terpisah dari Audit Log.
- Redact secret berdasarkan key pattern sebelum storage dan logging.
- Terapkan retention pada operational data.
- Uji unauthorized response, bukan hanya happy path.

### Don't

- Jangan menurunkan RBAC agar UI lebih mudah.
- Jangan memasukkan password, API key, cookie, token, raw payload, atau
  credential ke log, exception, HTML, API, atau test snapshot.
- Jangan menghapus Audit Log saat cleanup Runtime Log.
- Jangan memakai correlation ID sebagai authorization.
- Jangan menganggap hidden form field sebagai security control.

## 13. Testing convention

Gunakan TDD vertical slice: satu failing test, implementasi minimal, refactor.

### Test naming

Gunakan nama yang menyatakan behavior:

```python
def test_duplicate_webhook_does_not_run_handler_twice():
    ...


def test_staff_without_runtime_permission_cannot_view_logs(client):
    ...
```

### Do

- Test public behavior, bukan private implementation detail.
- Gunakan database marker bila test menyentuh database.
- Test transaction rollback dan `on_commit` untuk side effect penting.
- Test idempotency dengan memanggil command dua kali.
- Test redaction di storage, logger, response, dan HTML sesuai seam.
- Gunakan factory/helper kecil yang tidak menyembunyikan assertion.
- Pertahankan coverage minimal repository 80%.

### Don't

- Jangan hanya test status code tanpa memverifikasi state atau response body.
- Jangan menonaktifkan permission check dalam test untuk memudahkan setup.
- Jangan mock semua hal sampai behavior nyata tidak diuji.
- Jangan membuat test bergantung pada urutan test lain.
- Jangan menerima warning baru tanpa alasan dan dokumentasi.

### Required test matrix

| Area | Minimum test |
| --- | --- |
| Model | invariant, constraint, safe delete/retention |
| Selector | empty, filter, pagination, visibility |
| Service | success, invalid state, permission, rollback, duplicate |
| Task | immediate backend, retry, timeout, idempotency, failure |
| Webhook | signature, JSON validation, dedupe, handoff, replay |
| Realtime | post-commit, permission, expiry, HTTP fallback |
| Dashboard | auth, RBAC, HTMX partial, redaction, empty state |
| Architecture | App Map and import boundary |
| Config | optional dependencies absent, production guard |

## 14. Documentation dan dependency

### Do

- Update docs saat public contract, config, route, permission, atau workflow
  berubah.
- Update App Map untuk dependency lintas Domain App.
- Tambahkan atau update `backend/apps/<domain>/AGENTS.md` untuk Domain App baru.
- Gunakan ADR untuk keputusan arsitektur yang sulit dibalik.
- Pin/update lockfile bila dependency memang disetujui.
- Dokumentasikan environment variable dan process role.

### Don't

- Jangan membuat dokumentasi yang bertentangan dengan configuration.
- Jangan mengedit `uv.lock` secara manual.
- Jangan menambah dependency framework untuk mengisi gap yang bisa ditangani
  Django/HTMX.
- Jangan mendokumentasikan optional service sebagai baseline wajib.
- Jangan menyimpan secret contoh yang tampak seperti credential production.

## 15. Verification command

Gunakan focused command selama development:

```bash
./.venv/bin/pytest backend/tests/test_<area>.py -q
./.venv/bin/ruff check backend/
```

Gunakan full gate sebelum menyatakan selesai:

```bash
./.venv/bin/pytest backend/tests -q
./.venv/bin/ruff check backend/
./.venv/bin/python backend/manage.py check
./.venv/bin/python backend/manage.py makemigrations --check --dry-run
PYTHONPATH=backend ./.venv/bin/mypy backend/ --config-file /dev/null \
  --ignore-missing-imports --follow-imports=skip
just verify
```

Jika `just verify` gagal karena environment/dependency resolution, jalankan
fallback `.venv`, baca output, dan laporkan gap secara eksplisit.

## 16. Code review checklist

### Standards

- [ ] naming dan struktur file konsisten;
- [ ] selector/service/view boundary benar;
- [ ] Domain App import boundary explicit;
- [ ] tidak ada abstraction/speculative generality yang tidak perlu;
- [ ] lint/typecheck/test convention terpenuhi;
- [ ] diff tetap kecil dan fokus.

### Spec

- [ ] semua acceptance criteria terbukti;
- [ ] non-goal tidak ikut terimplementasi;
- [ ] RBAC dan auth path benar;
- [ ] idempotency, transaction, retry, timeout, dan rollback benar;
- [ ] redaction, retention, audit, dan runtime log benar;
- [ ] optional adapter dan fallback benar;
- [ ] documentation/configuration sinkron.

### Handoff

- [ ] changed files dicatat;
- [ ] command dan output verification dicatat;
- [ ] warning atau environment gap dicatat;
- [ ] migration/deployment impact dicatat;
- [ ] follow-up issue hanya dibuat bila ada outcome yang jelas.

## 17. Definition of Done

Sebuah perubahan dianggap selesai bila:

1. behavior yang diminta tersedia melalui boundary yang tepat;
2. test regression dan failure path lulus;
3. RBAC, redaction, audit, retention, dan safe fallback sudah diverifikasi;
4. Domain App tidak mengambil alih ownership app lain;
5. tidak ada dependency atau abstraction speculative;
6. lint, typecheck, Django check, migration check, dan full suite lulus;
7. dokumentasi dan configuration sesuai dengan implementation;
8. remaining risk ditulis, bukan disembunyikan.
