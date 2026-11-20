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

* **100 levels** in 25 afdelingen van elk 4 levels, met oplopende moeilijkheid:
  * 1-1 t/m 5-4 (de 20 originele levels): Burgerzaken, Vergunningen, Belastingdienst,
    Ministerie van Algemene Zaken en Het Archief.
  * 6-1 t/m 25-4 (80 nieuwe levels): van Bezwaar en Beroep, via Dienst
    Formulierbeheer, Directie Stempelzaken en Bureau Wachtrijen, tot het Ministerie van
    Ministeries en afdeling 25, *Het Juiste Loket*.
* De levelselectie is scrollbaar: pijltjes, links/rechts per afdeling, PgUp/PgDn per 10,
  Home/End, muiswiel of de schuifbalk.
* Geheime machtiging: toets in de levelselectie
  **↑ ↑ ↓ ↓ ← → ← → B A** om alle levels vrij te geven. Nog een keer de code en de
  niet-afgeronde levels gaan weer op slot. Je voortgang wordt nooit aangepast: open
  blijven dan alle opgeloste levels plus het eerste level waarvan alle vorige levels
  zijn afgerond. Levels die je met de code hebt opgelost, blijven opgelost. De stand
  van de machtiging wordt in de savegame bewaard (`unlock_all`).
* Bestaande voortgang blijft behouden: voortgang wordt per level-ID bewaard en de
  eerste 20 levels zijn ongewijzigd (een test bewaakt dat). Voortgang uit de korte
  tussenversie met 16 levels per afdeling (6-1 t/m 10-16) wordt bij de eerste start
  automatisch omgezet naar de nieuwe nummers (savegame-versie 2).
* Hoofdmenu, verder spelen, level selecteren met voorbeeldweergave, opties
  (geluid aan/uit, effect- en muziekvolume, volledig scherm), credits, pauzemenu,
  overwinningsbeschikking met stempel, eindscherm.
* Voortgang wordt automatisch opgeslagen in
  `%APPDATA%\OperatieBureaucratie\savegame.json`. Een beschadigd savebestand wordt
  hernoemd naar `.beschadigd` en het spel start gewoon opnieuw.
* **Discord Rich Presence**: vrienden zien in Discord dat u *Operatie Bureaucratie*
  speelt, welk dossier, en of u loopt, duwt, nadenkt, pauzeert of in het menu zit
  (zie hieronder). Uit te zetten via Opties > Discord-status.
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
  discord_rpc.py         Discord Rich Presence (lokale IPC-verbinding)
discord/logo.png         afbeelding om te uploaden als Discord-asset "logo"
assets/                  sprites, achtergrond, geluid, lettertype, icoon
levels/levels.json       alle levels
tools/
  generate_assets.py     tekent alle pixelart en synthetiseert alle 8-bit geluiden
  make_levels.py         genereert levels 1-1 t/m 5-4 uit getekende plattegronden
  make_extra_levels.py   genereert levels 6-1 t/m 25-4 (willekeurige kantoren)
  roomgen.py             bouwt willekeurige kantoorplattegronden
  solver.py              Sokoban-solver / omgekeerde zoekgenerator
  smoke_test.py          speelt headless alle 100 levels uit via de echte schermen
tests/test_board.py      unittests (regels, undo, herstart, levels, savegame)
tests/test_discord.py    unittests Discord-koppeling (tegen een nep-Discord)
build.bat                bouwt dist\OperatieBureaucratie.exe
OperatieBureaucratie.spec PyInstaller-configuratie
```

## Discord Rich Presence instellen

Discord toont de status alleen voor een geregistreerde "applicatie". Die maakt u
eenmalig zelf aan (gratis):

1. Ga naar <https://discord.com/developers/applications> en klik **New Application**.
   Noem hem `Operatie Bureaucratie`: die naam verschijnt als "Speelt Operatie Bureaucratie".
2. Kopieer op de pagina **General Information** de **Application ID**.
3. Ga naar **Rich Presence > Art Assets**, upload `discord/logo.png` en geef het de
   naam `logo`.
4. Zet de ID in `game/settings.py`: `DISCORD_CLIENT_ID = "123456789012345678"` en
   bouw de EXE opnieuw met `build.bat`.

Daarna ziet uw profiel er tijdens het spelen zo uit:

```text
Speelt Operatie Bureaucratie
Dossier 3-4: Box 3
Duwt een dossier (2/5 gearchiveerd)
00:42 verstreken
```

| Situatie | Status |
|---|---|
| Lopen (afgelopen 1,6 s een stap gezet) | Loopt door de gang |
| Duwen (afgelopen 2,5 s een doos geduwd) | Duwt een dossier |
| Stilstaan | Denkt na... |
| Pauzemenu | Koffiepauze |
| Level gehaald | Dossier goedgekeurd! |
| Hoofdmenu / levelselectie / opties / credits | In het hoofdmenu + wat u doet |

Discord staat een statuswijziging maximaal eens per 4 seconden toe, dus de status loopt
soms een paar seconden achter. Draait Discord niet, dan merkt het spel daar niets van;
start u Discord later, dan verbindt het spel vanzelf (binnen 15 seconden). Er wordt geen
extra Python-pakket gebruikt: het spel praat rechtstreeks met de lokale Discord-app.

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
regels), dat de eerste 20 levels ongewijzigd zijn en dat een savegame van versie 1.0
zijn voortgang houdt. De smoke test speelt alle 100 levels uit via het echte speelscherm
en test het scrollen in de levelselectie.

### Hoe de 80 nieuwe levels zijn gemaakt

`tools/make_extra_levels.py` bouwt honderden willekeurige kantoorplattegronden uit
blokken van 3x3, zet er archiefplekken in en zoekt dan achterwaarts (dozen wegtrekken
van de archiefplekken) naar de moeilijkste startpositie. Alleen plattegronden waarvan
die zoektocht volledig is afgerond worden gebruikt; het aantal duwen is dan exact het
minimum en de opgeslagen oplossing bewijst dat het level oplosbaar is. Alle bruikbare
plattegronden worden op moeilijkheid gesorteerd; daaruit worden er 80 gelijkmatig
gekozen en per 4 over de afdelingen 6 t/m 25 verdeeld. Een overzicht staat in
`tools/levels_report_extra.txt`.

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
