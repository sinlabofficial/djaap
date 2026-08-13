# Domain Docs

Repository ini menggunakan layout **single-context**.

## Dokumen domain

- Baca `CONTEXT.md` di root sebelum melakukan eksplorasi substansial.
- Baca ADR yang relevan di `docs/adr/` sebelum mengubah area yang tercakup
  oleh keputusan arsitektur.
- Gunakan istilah domain sesuai glossary di `CONTEXT.md`.
- Jika istilah baru diperlukan dan belum ada di glossary, tandai sebagai gap
  domain dan selaraskan melalui proses domain modeling.

## Struktur

```text
/
├── CONTEXT.md
├── docs/
│   ├── agents/
│   └── adr/
└── backend/
```

Dokumen ini adalah panduan konsumen untuk skill engineering; keputusan domain
tetap bersumber dari `CONTEXT.md` dan ADR.
