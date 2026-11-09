# Aloita tästä — RF Spectrum Lab

Tämä on valmis, itsenäinen Python-projekti, jolla voidaan esitellä signaalinkäsittelyn, NumPyn, SciPyn, Streamlitin ja testauksen osaamista. Ohjelma käyttää oletusarvoisesti simuloituja radiotaajuussignaaleja, eli erillistä radiovastaanotinta ei tarvita.

## Käyttöönotto Windowsilla

1. Pura ZIP-tiedosto ja avaa sen sisältämä `rf-spectrum-lab`-kansio.
2. Varmista, että koneellasi on Python 3.11 tai uudempi (mieluiten Python 3.11 tai 3.12). Pythonin lataus: https://www.python.org/downloads/
3. Kaksoisklikkaa `setup_windows.bat`. Asennus tekee oman virtuaaliympäristön ja asentaa tarvittavat kirjastot. Tämä vaihe tarvitsee internetyhteyden.
4. Kaksoisklikkaa `run_windows.bat`.
5. Selain avautuu yleensä osoitteessa `http://localhost:8501`.

Jos Windows ei löydä Pythonin `py`-komentoa, asenna Python uudelleen ja varmista, että Python Launcher on valittu asennuksessa.

## Ohjelman testaaminen

- Vasemman reunan **Beacon A** ja **Beacon B** ovat simuloituja jatkuvia taajuuspiikkejä.
- **Sweeper C** on taajuutta muuttava purske, jonka pitäisi näkyä waterfall-kuvaajassa vinona viivana.
- Kasvata **Noise RMS** -arvoa tai muuta **Minimum above-floor power** -arvoa: näet, miten havainnot muuttuvat.
- Voit tallentaa raportin CSV- tai JSON-muotoon ja ladata simuloidun IQ-datan `.npy`-tiedostona.

## Testit ja komentorivi

Avaa PowerShell projektikansiossa ja suorita:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m rf_analyzer.cli --output outputs\demo
```

Komentoriviversio tallentaa `outputs/demo`-kansioon spektrikuvan, datan, havainnot ja raportin.

Kattavat tekniset ohjeet ja toteutuksen kuvaus ovat englanninkielisessä `README.md`-tiedostossa.
