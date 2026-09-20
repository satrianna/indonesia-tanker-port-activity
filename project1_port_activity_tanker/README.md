# Port Activity Snapshot — Analisis Tren Tanker

Dashboard interaktif (Streamlit) untuk menganalisis tren aktivitas kapal tanker
di pelabuhan-pelabuhan Indonesia: port calls, volume import/export, peringkat
pelabuhan, perbandingan antar pelabuhan, pola musiman, dan komposisi jenis kapal.

## Struktur folder

```
project1_port_activity_tanker/
├── app.py
├── requirements.txt
├── indonesia_shipment.csv.gz
├── .streamlit/config.toml
└── README.md
```

> File data sengaja ditaruh sejajar dengan `app.py` (bukan di dalam subfolder
> `data/`) karena fitur upload file lewat browser di GitHub sering tidak
> mempertahankan struktur subfolder, yang menyebabkan error `FileNotFoundError`
> saat aplikasi dijalankan di Streamlit Cloud.

## Jalankan di lokal

```bash
pip install -r requirements.txt
streamlit run app.py
```

Buka `http://localhost:8501` di browser.

## Deploy ke Streamlit Community Cloud (gratis)

1. Buat repository baru di GitHub, lalu upload **seluruh isi folder ini**
   (termasuk `indonesia_shipment.csv.gz` dan folder `.streamlit/`) langsung
   ke root repo — struktur folder harus sama persis seperti di atas. Jika
   meng-upload lewat browser, gunakan **drag-and-drop folder** langsung dari
   File Explorer/Finder ke halaman GitHub, bukan tombol "choose your files"
   (tombol itu sering gagal mempertahankan subfolder seperti `.streamlit/`).
2. Buka https://share.streamlit.io/ dan login dengan akun GitHub Anda.
3. Klik **"New app"** → pilih repository dan branch yang tadi dibuat.
4. Isi **"Main file path"** dengan `app.py`.
5. Klik **Deploy**. Tunggu beberapa menit sampai proses build selesai.
6. Aplikasi akan online di URL seperti
   `https://<nama-app>-<username>.streamlit.app`.

## Mengganti data

Jika ingin memakai data terbaru, cukup ganti file
`indonesia_shipment.csv.gz` (di root folder) dengan file CSV (boleh
terkompresi .gz atau tidak, tinggal sesuaikan `pd.read_csv(...)` di `app.py`)
yang memiliki kolom yang sama persis (date, portname, portcalls_tanker,
import_tanker, export_tanker, dst).
