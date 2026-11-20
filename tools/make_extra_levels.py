"""Add the procedurally generated departments 6-10 (levels 21-100).

Departments 1-5 in levels/levels.json are copied unchanged (so existing save
games keep their progress). For every new level many random office floor plans
are tried (tools/roomgen.py); only candidates whose reverse search finished
completely are kept, so the push count is the exact optimum and the stored
solution proves the level is solvable. All usable candidates are sorted by
difficulty and 80 are picked evenly; each department gets the next 16.

Usage:
    python tools/make_extra_levels.py            # generate (cached) + write levels
    python tools/make_extra_levels.py --more 100 # 100 extra deep candidates

Candidates are cached in build/level_candidates.json, so re-running is cheap.
"""
from __future__ import annotations

import json
import os
import sys
import time
from multiprocessing import Pool

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from game.board import Board  # noqa: E402
from tools.roomgen import candidate, seal  # noqa: E402

LEVELS_PATH = os.path.join(ROOT, "levels", "levels.json")
SOLUTIONS_PATH = os.path.join(ROOT, "tools", "solutions.json")
CACHE_PATH = os.path.join(ROOT, "build", "level_candidates.json")
REPORT_PATH = os.path.join(ROOT, "tools", "levels_report_extra.txt")
MAX_STATES = 500_000
PER_DEPT = 16
MIN_DIFFICULTY = 33          # level 5-3 needs 45 pushes; 6-1 may start a bit gentler
# Extra candidates from the room types that most often give deep puzzles.
EXTRA_GROUP = 11
DEEP_CONFIGS = [(4, 3, 4, False), (5, 3, 4, True), (5, 4, 5, True), (5, 3, 4, False)]

# (blocks wide, blocks high, boxes, tight) configurations used to generate candidates per department
DEPARTMENTS = [
    {
        "id": 6, "name": "Bezwaar en Beroep",
        "motto": "U kunt binnen zes weken bezwaar maken tegen dit motto.",
        "configs": [(4, 2, 3, False), (4, 3, 3, False), (4, 3, 4, False)],
        "levels": [
            ("Bezwaarschrift", "Uw bezwaar is ontvangen. Het bezwaar tegen uw bezwaar ook."),
            ("Termijn verstreken", "U bent te laat. Gelukkig zijn wij dat ook."),
            ("Hoorzitting", "U wordt gehoord. Luisteren is een aparte procedure."),
            ("Pro forma", "Alles is voorlopig. Behalve deze dossiers."),
            ("Ingebrekestelling", "Wij stellen onszelf in gebreke. Daarna gaan we lunchen."),
            ("Gegrond verklaard", "U krijgt gelijk. Het dossier nog niet."),
            ("Ongegrond verklaard", "U krijgt ongelijk, maar wel netjes geordend."),
            ("Niet-ontvankelijk", "Uw dossier is niet ontvangen. Het staat in de gang."),
            ("Herziening", "We kijken er nog één keer naar. En daarna nog eens."),
            ("Voorlopige voorziening", "Tijdelijk geregeld, voor onbepaalde tijd."),
            ("Commissie van Advies", "De commissie adviseert een commissie op te richten."),
            ("Dwangsom", "Elke dag te laat kost geld. Wij rekenen in stempels."),
            ("Beroep in tweede aanleg", "De eerste aanleg was ook al zwaar."),
            ("Raad van Advies", "Een raad die adviseert over raad. Of andersom."),
            ("Wraking", "De ambtenaar is partijdig: houdt van rechte stapels."),
            ("Onherroepelijk", "Na dit dossier is er geen weg terug. Behalve de Z-toets."),
        ],
    },
    {
        "id": 7, "name": "Dienst Formulierbeheer",
        "motto": "Voor elk formulier bestaat een formulier.",
        "configs": [(4, 3, 4, False), (4, 3, 4, True), (5, 3, 4, False)],
        "levels": [
            ("Formulier A1", "Het begint simpel. Dat zeggen ze altijd."),
            ("Doorhalen wat niet van toepassing is", "Alles is van toepassing."),
            ("In blokletters", "SCHRIJF DUIDELIJK. DUW ZORGVULDIG."),
            ("Bijlage 3 van 7", "Bijlagen 1, 2 en 4 tot en met 7 volgen later."),
            ("Handtekening hier", "En hier. En hier. Paraferen op elke pagina."),
            ("Doorslag in drievoud", "Wit voor ons, geel voor u, roze voor niemand."),
            ("Toelichting op de toelichting", "Zie pagina 14 van de toelichting."),
            ("Het kopje 'Overig'", "Hier past werkelijk alles in. Behalve dit."),
            ("Verplicht veld", "Dit veld mag niet leeg blijven. Deze archiefplek ook niet."),
            ("Digitaal invullen, op papier inleveren", "Modernisering in uitvoering."),
            ("Formulier 12C", "Formulier 12B is gevonden. Nu 12C nog."),
            ("Paginanummering", "Pagina 3 van 2."),
            ("Kladversie", "Dit is een concept. Het blijft een concept."),
            ("Nietmachine", "Alles moet aan elkaar vast. Behalve de nietjes."),
            ("Ontvangstbevestiging", "Wij bevestigen dat wij dit bevestigen."),
            ("Het Moederformulier", "Het formulier waar alle formulieren uit voortkomen."),
        ],
    },
    {
        "id": 8, "name": "Directie Stempelzaken",
        "motto": "Zonder stempel bestaat het niet.",
        "configs": [(4, 3, 5, True), (5, 3, 4, True), (5, 3, 5, True)],
        "levels": [
            ("Eerste stempel", "Inkt erop, stempel erop, dossier weg."),
            ("Natte inkt", "Niet aanraken. Wel duwen."),
            ("Datumstempel", "De datum is altijd gisteren."),
            ("Gezien", "Gezien is niet hetzelfde als goedgekeurd."),
            ("Voor akkoord", "Akkoord gaat pas na akkoord."),
            ("Stempelkussen leeg", "Inkt is besteld. Levertijd: zes tot acht weken."),
            ("Scheef gestempeld", "Ongeldig. Opnieuw beginnen. Grapje. Of niet."),
            ("Kopie conform origineel", "Het origineel is zoek. De kopie is conform."),
            ("Stempelcarrousel", "Draai, kies, stempel. Herhaal."),
            ("Spoedstempel", "Spoed betekent: na de lunch."),
            ("Geheim", "U heeft dit level nooit gezien."),
            ("Gewaarmerkt", "Echt waar. Met een waarmerk."),
            ("Dubbel gestempeld", "Twee keer goedgekeurd is één keer afgekeurd."),
            ("Het Stempelarchief", "Elke stempel heeft een eigen dossier."),
            ("Stempelkamer B", "Stempelkamer A wordt sinds 2009 gerenoveerd."),
            ("De Gouden Stempel", "Slechts drie ambtenaren hebben hem ooit vastgehouden."),
        ],
    },
    {
        "id": 9, "name": "Bureau Wachtrijen",
        "motto": "Uw wachttijd bedraagt: onbekend.",
        "configs": [(5, 3, 5, True), (5, 4, 5, True), (4, 3, 5, True)],
        "levels": [
            ("Nummertje 1", "U bent de eerste. Toch moet u wachten."),
            ("Nummertje 412", "Nu aan de beurt: nummer 17."),
            ("Wachtkamer", "Met tijdschriften uit 1994."),
            ("Pauzescherm", "Wij zijn even weg. Terug om: ooit."),
            ("Spreekuur", "Alleen op dinsdag van 9:00 tot 9:05."),
            ("Terugbelverzoek", "U wordt teruggebeld. Wanneer staat nog niet vast."),
            ("Muziek in de wacht", "U hoort deze melodie nog dagen."),
            ("Wachtrij voor de wachtrij", "Eerst een nummertje voor het nummertje."),
            ("Verkeerde balie", "Deze balie gaat over de andere balie."),
            ("Afspraak verzet", "Uw afspraak is verzet naar de vorige afspraak."),
            ("Loket gesloten", "Het bordje hangt er al sinds de vorige reorganisatie."),
            ("Zelfbedieningszuil", "Het scherm reageert niet. Dat is de bedoeling."),
            ("Rij 7, stoel 3", "U zit goed. Uw dossiers niet."),
            ("De lange gang", "Aan het eind is een deur. Daarachter een gang."),
            ("Bijna aan de beurt", "Nog maar drie wachtenden. Met elk zeven dossiers."),
            ("Nummertje 999", "Het display springt terug naar 000."),
        ],
    },
    {
        "id": 10, "name": "Ministerie van Ministeries",
        "motto": "Het hoogste loket. Alleen bereikbaar via een loket.",
        "configs": [(5, 3, 5, True), (5, 4, 5, True), (5, 3, 6, True), (5, 4, 6, True)],
        "levels": [
            ("Ambtelijk vooroverleg", "Overleg over het overleg."),
            ("Kamerbrief", "De Kamer is geïnformeerd. De dossiers nog niet."),
            ("Coalitieakkoord", "Iedereen is het eens over de datum van de volgende vergadering."),
            ("Nota van Wijziging", "Alles blijft anders."),
            ("Interdepartementaal", "Elk ministerie duwt een dossier naar het andere."),
            ("Begroting", "Er is geld voor dozen. Niet voor kasten."),
            ("Motie aangenomen", "Uitvoering volgt. Of niet."),
            ("Reorganisatie", "Alles verhuist. Behalve de koffieautomaat."),
            ("Staatssecretaris", "Niet aanwezig. De secretaris ook niet."),
            ("Ministerraad", "Vrijdag. Na afloop: persconferentie over dozen."),
            ("Parlementaire enquête", "Onder ede: waar staat dossier 47?"),
            ("Regeerakkoord", "Vierhonderd pagina's. Allemaal in deze kamer."),
            ("Archiefwet", "Wat hier staat, staat hier voor altijd."),
            ("Kabinetsformatie", "Duurt langer dan dit level. Hopelijk."),
            ("De Hoogste Ambtenaar", "Tekent alles. Als het te vinden is."),
            ("Het Juiste Loket", "U heeft het gevonden. Archiveer dit, en de procedure is voltooid."),
        ],
    },
]


# The 80 levels above are published in departments of 4 levels, like the
# original 20: afdeling 6 t/m 25. Every 4 departments follow one theme above.
LEVELS_PER_OFFICE = 4
OFFICES = [
    (6, "Bezwaar en Beroep", "U kunt binnen zes weken bezwaar maken tegen dit motto."),
    (7, "Hoorcommissie", "Wij horen u. Of wij luisteren is een andere procedure."),
    (8, "Juridische Zaken", "Alles is juridisch correct. Niets is duidelijk."),
    (9, "Hoger Beroep", "Hoe hoger het beroep, hoe langer de trap."),
    (10, "Dienst Formulierbeheer", "Voor elk formulier bestaat een formulier."),
    (11, "Afdeling Bijlagen", "Zie bijlage. Bijlage volgt."),
    (12, "Bureau Handtekeningen", "Paraaf hier, hier en hier."),
    (13, "Afdeling Concepten", "Alles is een concept. Ook deze afdeling."),
    (14, "Directie Stempelzaken", "Zonder stempel bestaat het niet."),
    (15, "Inktvoorziening", "De inkt is op. De aanvraag voor nieuwe inkt ook."),
    (16, "Afdeling Waarmerken", "Echt is pas echt als het gewaarmerkt is."),
    (17, "Het Stempelarchief", "Elke stempel heeft een eigen dossier."),
    (18, "Bureau Wachtrijen", "Uw wachttijd bedraagt: onbekend."),
    (19, "Klantcontactcentrum", "Uw vraag is belangrijk voor ons. Blijft u aan de lijn."),
    (20, "Balie Afspraken", "Afspraken maken kan alleen op afspraak."),
    (21, "De Wachtkamer", "Neem een tijdschrift. Ze zijn van 1994."),
    (22, "Ministerie van Ministeries", "Het hoogste loket. Alleen bereikbaar via een loket."),
    (23, "Beleidsdirectie", "Wij maken beleid over het maken van beleid."),
    (24, "De Ministerraad", "Op vrijdag besloten, op maandag herzien."),
    (25, "Het Juiste Loket", "Het einde van de procedure. Bijna."),
]


def legacy_id(i: int) -> str:
    """ID that new level number i (0..79) had in the 16-levels-per-department build."""
    return f"{6 + i // 16}-{i % 16 + 1}"


def acceptable(c) -> bool:
    if c is None or not c["complete"]:
        return False
    allowed_on_goal = 0 if c["boxes"] <= 4 else 1
    w, h = c["size"]
    return c["on_goal"] <= allowed_on_goal and w <= 24 and h <= 16


def load_cache():
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_cache(cache):
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    tmp = CACHE_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cache, f)
    os.replace(tmp, CACHE_PATH)


def generate(per_dept: int, extra: int):
    cache = load_cache()
    jobs = []
    groups = [(d["id"], d["configs"], per_dept) for d in DEPARTMENTS]
    groups.append((EXTRA_GROUP, DEEP_CONFIGS, extra))
    for gid, configs, count in groups:
        for i in range(count):
            seed = gid * 100_000 + i
            if str(seed) in cache:
                continue
            bw, bh, k, tight = configs[i % len(configs)]
            jobs.append((seed, bw, bh, k, MAX_STATES, tight))
    if not jobs:
        return cache
    print(f"{len(jobs)} kandidaten genereren...", flush=True)
    t0 = time.time()
    with Pool(max(1, (os.cpu_count() or 2) - 1), maxtasksperchild=4) as pool:
        for n, (job, res) in enumerate(zip(jobs, pool.imap(candidate, jobs)), start=1):
            cache[str(job[0])] = res
            if n % 10 == 0 or n == len(jobs):
                save_cache(cache)
                good = sum(1 for c in cache.values() if acceptable(c))
                print(f"  {n}/{len(jobs)}  bruikbaar: {good}  ({time.time() - t0:.0f}s)", flush=True)
    save_cache(cache)
    return cache


def difficulty(c) -> int:
    """Optimal pushes, plus a little extra per box to keep track of."""
    return c["depth"] + 2 * (c["boxes"] - 3)


def pick(pool, count):
    """Spread `count` picks evenly over the pool (easy -> hard), always the hardest last."""
    pool = sorted(pool, key=lambda c: (difficulty(c), c["seed"]))
    if len(pool) < count:
        raise SystemExit(f"te weinig kandidaten ({len(pool)}/{count}); draai met --more")
    idx = sorted({round(i * (len(pool) - 1) / (count - 1)) for i in range(count)})
    spare = [i for i in range(len(pool)) if i not in idx]
    while len(idx) < count:            # rounding collisions: fill from the hard end
        idx.append(spare.pop())
    return [pool[i] for i in sorted(idx)]


def build(per_dept: int, extra: int):
    with open(LEVELS_PATH, encoding="utf-8") as f:
        data = json.load(f)
    original = [d for d in data["departments"] if d["id"] <= 5]
    if len(original) != 5 or sum(len(d["levels"]) for d in original) != 20:
        raise SystemExit("verwacht 5 originele afdelingen met 20 levels")
    with open(SOLUTIONS_PATH, encoding="utf-8") as f:
        solutions = {k: v for k, v in json.load(f).items() if int(k.split("-")[0]) <= 5}

    cache = generate(per_dept, extra)
    # One global pool, sorted by difficulty and cut into departments, so every
    # department is harder than the one before it.
    pool, seen_maps = [], set()
    for c in sorted((c for c in cache.values() if acceptable(c)), key=lambda c: c["seed"]):
        key = tuple(c["rows"])
        if key not in seen_maps and difficulty(c) >= MIN_DIFFICULTY:
            seen_maps.add(key)
            pool.append(c)
    chosen_all = pick(pool, PER_DEPT * len(DEPARTMENTS))
    print(f"Pool: {len(pool)} bruikbare kandidaten (moeilijkheid >= {MIN_DIFFICULTY})")
    names = [nn for dept in DEPARTMENTS for nn in dept["levels"]]
    assert len(names) == len(chosen_all) == len(OFFICES) * LEVELS_PER_OFFICE
    out = list(original)
    report = []
    for o, (office_id, office_name, motto) in enumerate(OFFICES):
        levels = []
        for n in range(1, LEVELS_PER_OFFICE + 1):
            i = o * LEVELS_PER_OFFICE + n - 1
            c, (name, note) = chosen_all[i], names[i]
            level_id = f"{office_id}-{n}"
            c["rows"] = seal(c["rows"])
            board = Board.from_rows(c["rows"])
            if not board.apply_solution(c["solution"]):
                raise SystemExit(f"{level_id}: oplossing klopt niet!")
            levels.append({"id": level_id, "name": name, "note": note, "map": c["rows"],
                           "legacy_id": legacy_id(i)})
            solutions[level_id] = c["solution"]
            report.append(f"{level_id:6} {name:40} dossiers={c['boxes']} duwen={c['depth']:3} "
                          f"zetten={len(c['solution']):4} grootte={c['size'][0]}x{c['size'][1]} "
                          f"seed={c['seed']}")
            report.extend("       " + r for r in c["rows"])
        out.append({"id": office_id, "name": office_name, "motto": motto, "levels": levels})

    data["departments"] = out
    with open(LEVELS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    with open(SOLUTIONS_PATH, "w", encoding="utf-8") as f:
        json.dump(solutions, f, indent=2)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(report) + "\n")
    print("\n".join(line for line in report if not line.startswith("       ")))
    print(f"Geschreven: {sum(len(d['levels']) for d in out)} levels")


if __name__ == "__main__":
    per, extra = 70, 280
    if "--more" in sys.argv:
        extra += int(sys.argv[sys.argv.index("--more") + 1])
    build(per, extra)
