# Issue Tracker

Repository ini menggunakan issue tracker lokal berbasis Markdown.

## Konvensi

- Satu feature menggunakan satu folder: `.scratch/<feature-slug>/`.
- Spec disimpan di `.scratch/<feature-slug>/spec.md`.
- Ticket implementasi disimpan sebagai file terpisah di
  `.scratch/<feature-slug>/issues/<NN>-<slug>.md`.
- Nomor ticket dimulai dari `01`.
- Status triage ditulis pada baris `Status:` di bagian awal issue.
- Komentar dan riwayat diskusi ditambahkan di bawah heading `## Comments`.

## Wayfinding

- Peta keputusan disimpan di `.scratch/<effort>/map.md`.
- Ticket keputusan disimpan di `.scratch/<effort>/issues/`.
- Dependency ticket ditulis pada baris `Blocked by: NN, NN`.
- Ticket dapat dikerjakan ketika semua blocker berstatus `resolved`.

## Saat skill menerbitkan issue

Buat file Markdown baru di bawah `.scratch/<feature-slug>/` dan buat foldernya
jika belum ada.
