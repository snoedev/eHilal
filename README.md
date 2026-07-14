# eHilal (Streamlit)

Aplikasi kiraan hilal (Imkanur Rukyah MABIMS) menggunakan `Streamlit` + `Skyfield`.

Antara muka menyediakan tema terang dan gelap, susun atur responsif, jadual perbandingan lokasi,
serta graf altitud dan azimut yang mengikut tema pilihan pengguna.

## Keperluan

- Python 3.10+ (disyorkan)
- Internet (sekali sahaja) untuk download ephemeris jika fail `.bsp` tiada

## Setup Local (guna venv)

### Windows (PowerShell)

```powershell
cd c:\laragon\www\eHilal
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### macOS / Linux (bash/zsh)

```bash
cd /path/to/eHilal
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Jalankan App

```bash
streamlit run app.py
```

Kemudian buka URL yang keluar di terminal (kebiasaannya `http://localhost:8501`).

## Nota ephemeris (`.bsp`)

App guna ephemeris melalui `Skyfield`:

- Jika `de440.bsp` ada dalam folder projek, ia akan digunakan.
- Jika tiada, `Skyfield` akan cuba download automatik.

## Penting untuk upload ke GitHub

`de440.bsp` (sekitar 120MB) melebihi had fail GitHub (100MB).  
Disyorkan:

1. Jangan commit fail `.bsp` besar.
2. Tambah ke `.gitignore`:

```gitignore
*.bsp
.venv/
__pycache__/
```

3. Biar pengguna download ephemeris semasa run pertama.
