# SCZB TRYOUT

Aplikasi ujian kenaikan level karyawan SCZB (Indonesia/Mandarin).

## Jalankan di komputer (Windows)
1. Install Python 3.11 atau lebih baru.
2. Buka terminal di folder proyek.
3. Jalankan:
   `py -m venv .venv`
   `.venv\\Scripts\\activate`
   `pip install -r requirements.txt`
4. Buat akun admin dengan PowerShell:
   `$env:ADMIN_USER="admin"; $env:ADMIN_PASSWORD="GantiPasswordKuat"`
   `python app.py`
5. Buka http://127.0.0.1:5000

## Deploy ke Render
1. Upload folder proyek ini ke repository GitHub.
2. Di Render pilih **New > Blueprint**, lalu hubungkan repository.
3. Render membaca `render.yaml` dan membuat web service + PostgreSQL.
4. Isi `ADMIN_USER` dan `ADMIN_PASSWORD` saat Render meminta environment variables.
5. Deploy. URL akan berbentuk `https://sczb-tryout.onrender.com`.

Catatan:
- Ganti nama service `sczb-tryout` di render.yaml jika subdomain tersebut sudah dipakai.
- Database free/paid dan kebijakan Render dapat berubah; cek biaya dan masa penyimpanan sebelum produksi.
- Buat backup database secara berkala.
- Ini adalah fondasi awal. Sebelum ujian resmi, tambahkan fitur penguncian percobaan, autosave jawaban, audit log, dan pengujian keamanan.
