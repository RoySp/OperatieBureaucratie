# Operatie Bureaucratie

*De weg naar het juiste loket.*
**"Waar iedere stap eerst moet worden goedgekeurd."**

Een retro Sokoban-puzzelspel (Python 3 + Pygame) in de stijl van een begin-jaren-90
DOS-spel. U bent ambtenaar bij de volledig verzonnen **Rijksdienst voor
Dossierverplaatsing (RDV)** en moet alle dossierdozen naar de juiste archiefplekken duwen.

## Spelen

**Kant-en-klaar:** start `dist\OperatieBureaucratie.exe`. Er hoeft niets te worden
geïnstalleerd (geen Python, geen Pygame, geen internet).

**Vanuit de broncode:**

```bat
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe main.py
```

### Besturing

| Toets | Actie |
|---|---|
| Pijltjestoetsen / WASD | Lopen en dossiers duwen |
| Z (of Backspace) | Eén stap ongedaan maken |
| R | Level opnieuw beginnen |
| ESC (of P) | Pauzemenu |
| M | Wachtmuziek aan/uit |
| F11 | Volledig scherm aan/uit |
| Enter / Spatie | Menu-keuze bevestigen (muis werkt ook) |

### Spelregels

Duw alle dossiers naar de gele archiefplekken. U kunt maar één doos tegelijk duwen,
nooit trekken, en dozen gaan niet door muren, meubilair of andere dozen heen. Zetten
en duwen worden geteld; uw beste resultaat per dossier wordt bewaard.
Een doos in een hoek die niet op een archiefplek staat, zit klem. Het spel waarschuwt
dan met **KLEM!** (gebruik Z of R).

## Inhoud

* **20 levels** in 5 afdelingen: Burgerzaken, Vergunningen, Belastingdienst,
  Ministerie van Algemene Zaken en Het Archief, met oplopende moeilijkheid
  (1 tot 7 dossiers, tot 45 duwbewegingen in de optimale oplossing).
* Hoofdmenu, verder spelen, level selecteren met voorbeeldweergave, opties
  (geluid aan/uit, effect- en muziekvolume, volledig scherm), credits, pauzemenu,
  overwinningsbeschikking met stempel, eindscherm.
* Voortgang wordt automatisch opgeslagen in
  `%APPDATA%\OperatieBureaucratie\savegame.json`. Een beschadigd savebestand wordt
  hernoemd naar `.beschadigd` en het spel start gewoon opnieuw.
* Onverwachte fouten worden gelogd in `%APPDATA%\OperatieBureaucratie\foutrapport.txt`.

## Projectstructuur

```text
main.py                  startpunt
game/
  board.py               spelregels (los van pygame, volledig getest)
  level.py               levels laden uit levels/levels.json, ontgrendelen
  player.py              animatie van ambtenaar en dozen
  engine.py              hoofdlus, scènebeheer, schermschudden, foutafhandeling
  menu.py                laadscherm, hoofdmenu, opties, credits, levelselectie
  play.py                speelscherm, pauze, overwinning, eindscherm
  ui.py                  lettertypen, sprites, DOS/Windows 3.1-vensters
  settings.py            constanten, kleuren en alle humoristische teksten
  savegame.py            voortgang en instellingen (JSON in AppData)
  sound.py               geluidseffecten en muziek
  resources.py           paden voor broncode én PyInstaller-EXE
assets/                  sprites, achtergrond, geluid, lettertype, icoon
levels/levels.json       alle levels
tools/
  generate_assets.py     tekent alle pixelart en synthetiseert alle 8-bit geluiden
  make_levels.py         genereert levels uit plattegronden + bewijst oplosbaarheid
  solver.py              Sokoban-solver / omgekeerde zoekgenerator
  smoke_test.py          speelt headless alle 20 levels uit via de echte schermen
tests/test_board.py      unittests (regels, undo, herstart, levels, savegame)
build.bat                bouwt dist\OperatieBureaucratie.exe
OperatieBureaucratie.spec PyInstaller-configuratie
```

## Nieuwe levels toevoegen

Voeg een level toe aan `levels/levels.json` binnen een afdeling:

```json
{ "id": "6-1", "name": "Mijn level", "note": "Korte omschrijving.",
  "map": ["#######",
          "#@ $ .#",
          "#######"] }
```

Tekens: `#` muur, spatie vloer, `.` archiefplek, `$` dossier, `*` dossier op
archiefplek, `@` ambtenaar, `+` ambtenaar op archiefplek. Meubilair (gedraagt zich
als muur): `b` bureau, `c` computer, `p` plant, `k` koffieautomaat, `r` printer,
`a` archiefkast. Het aantal dossiers moet gelijk zijn aan het aantal archiefplekken.

Wilt u zeker weten dat een level oplosbaar is? Teken de plattegrond in opgeloste
toestand in `tools/make_levels.py`; dat script zoekt de moeilijkste startpositie en
controleert de oplossing met de echte spelregels.

## Testen

```bat
.venv\Scripts\python.exe -m unittest discover -s tests -v
.venv\Scripts\python.exe tools\smoke_test.py
```

De unittests controleren onder meer: niet door muren lopen, dozen niet door muren of
over elkaar, niet trekken, undo, herstart, levelvoltooiing, savegame opslaan/laden en
dat **elk level oplosbaar is** (een opgeslagen oplossing wordt afgespeeld met de echte
regels). De smoke test speelt alle 20 levels uit via het echte speelscherm.

## EXE bouwen

Op Windows 10/11 met Python 3.10+:

```bat
build.bat
```

Dit maakt een virtuele omgeving, installeert Pygame en PyInstaller, draait de tests en
bouwt `dist\OperatieBureaucratie.exe` (één bestand, ±15 MB, met alle assets erin).
Het equivalent zonder spec-bestand:

```bat
pyinstaller --noconfirm --clean --onefile --windowed --name OperatieBureaucratie ^
  --icon assets\icon.ico --add-data "assets;assets" --add-data "levels;levels" main.py
```

Een Windows-EXE moet op Windows worden gebouwd.

## Licentie en verantwoording

Alle pixelart, geluiden en muziek zijn origineel en worden door
`tools/generate_assets.py` gegenereerd. Lettertype: FreeSans Bold (GNU FreeFont,
meegeleverd met Pygame). De RDV is fictief; het spel gebruikt geen officiële
overheidslogo's of huisstijl. Elke gelijkenis met bestaande loketten berust op toeval.
