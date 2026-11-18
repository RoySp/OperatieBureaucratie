"""Generate levels/levels.json from office floor plans.

Every template below is drawn in the *solved* state ('*' = archived box).
A reverse search pulls the boxes away from the archive to find the hardest
starting position, and the resulting solution is replayed on the real game
rules to prove each level is solvable. Solutions are written to
tools/solutions.json and are used by the test-suite.

Usage:  python tools/make_levels.py
"""
from __future__ import annotations

import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from game.board import Board  # noqa: E402
from tools.solver import board_to_rows, hardest_start  # noqa: E402

DEPARTMENTS = [
    {
        "id": 1,
        "name": "Burgerzaken",
        "motto": "Trek een nummertje en neem plaats.",
        "levels": [
            ("Uw eerste aanvraag", "Breng het dossier naar het archief. Eén formulier, één loket.", 60, [
                "###########",
                "#p   #   k#",
                "#         #",
                "#  @    * #",
                "#         #",
                "#bc     bc#",
                "###########",
            ]),
            ("Paspoort verlopen", "Twee aanvragen, twee archiefplekken. Neem een nummertje.", 60, [
                "############",
                "#a   #    p#",
                "#    #     #",
                "#  *   @   #",
                "#    #   * #",
                "#bc  #   bc#",
                "############",
            ]),
            ("Verhuizing doorgeven", "Uw nieuwe adres is bij ons bekend. Uw dossiers nog niet.", 60, [
                "#############",
                "#k    #    p#",
                "#  *  #     #",
                "#  *     @  #",
                "#     #     #",
                "#bc   ##  ###",
                "#          a#",
                "#############",
            ]),
            ("Rijbewijs ophalen", "Vergeet uw pasfoto niet. Of uw dossiers.", 60, [
                "#############",
                "#p   ###   a#",
                "#           #",
                "#  ***  @   #",
                "#           #",
                "###  #b#  ###",
                "#k         r#",
                "#############",
            ]),
        ],
    },
    {
        "id": 2,
        "name": "Vergunningen",
        "motto": "Voor het aanvragen van een vergunning is een vergunning vereist.",
        "levels": [
            ("Dakkapel aanvragen", "Welstandscommissie vergadert. Archiveer intussen alles.", 60, [
                "##############",
                "#bc  #      p#",
                "#    #  #    #",
                "#  @    #  * #",
                "###  ###   * #",
                "#      *  #  #",
                "#k   #       #",
                "##############",
            ]),
            ("Kapvergunning", "Voor één boom. In drievoud.", 60, [
                "##############",
                "#   p   p    #",
                "#  ###  ###  #",
                "#  *  @    * #",
                "#  ###  ###  #",
                "#   p   *   k#",
                "##############",
            ]),
            ("Evenementenvergunning", "Het feest is al geweest. De vergunning nog niet.", 60, [
                "#############",
                "#k  #   #  r#",
                "#           #",
                "#   # @ #   #",
                "## ##   ## ##",
                "#  *  #  *  #",
                "#  * pbc    #",
                "#############",
            ]),
            ("Bezwaarschrift", "Uw bezwaar is ontvankelijk. Helaas.", 60, [
                "##############",
                "#a #     #  a#",
                "#  #     #   #",
                "#     @   ** #",
                "#  #     #** #",
                "#bc#  ####  ##",
                "#        p   #",
                "##############",
            ]),
        ],
    },
    {
        "id": 3,
        "name": "Belastingdienst",
        "motto": "Leuker kunnen we het niet maken. Smaller wel.",
        "levels": [
            ("Blauwe envelop", "Er is post voor u. Het moet naar het archief.", 80, [
                "############",
                "#a  ##  ##k#",
                "#          #",
                "## #### # ##",
                "#     #  **#",
                "# ## @   **#",
                "#    #  ####",
                "############",
            ]),
            ("Voorlopige aanslag", "Definitief wordt het pas na archivering.", 80, [
                "###########",
                "###  #  ###",
                "#         #",
                "# ## ### ##",
                "#     ** #",
                "## # #**##",
                "#   @    #",
                "##########",
            ]),
            ("Naheffing", "U had dit dossier eerder moeten verplaatsen.", 80, [
                "############",
                "#   ##     #",
                "# *    ### #",
                "#  #*#  *  #",
                "## #  @ #  #",
                "#  #### #  #",
                "#    *     #",
                "############",
            ]),
            ("Box 3", "Een ingewikkelde regeling. Net als dit kantoor.", 80, [
                "#############",
                "#k  #   #   #",
                "# #   #   # #",
                "#   # * #   #",
                "## ##   ## ##",
                "#  * @ *  * #",
                "###  # * ####",
                "#############",
            ]),
        ],
    },
    {
        "id": 4,
        "name": "Ministerie van Algemene Zaken",
        "motto": "Alle zaken zijn hier algemeen. Behalve de uwe.",
        "levels": [
            ("Ministerraad", "Vrijdagmiddag. Iedereen wil naar huis. U ook.", 120, [
                "#################",
                "#bc   #    #  p #",
                "#     #    #    #",
                "#  #     @    # #",
                "#  ####  ###  # #",
                "#             # #",
                "###  #####  *** #",
                "#k        #  ** #",
                "#################",
            ]),
            ("Persconferentie", "Geen vragen meer, alleen nog dossiers.", 120, [
                "################",
                "#p    #   #   a#",
                "#  ##   #   #  #",
                "#   #  ###  #  #",
                "## ### @  ###  #",
                "#        #     #",
                "#  ****  #  #  #",
                "#   *    #   bc#",
                "################",
            ]),
            ("Coalitieakkoord", "Iedereen moet een stukje opschuiven.", 120, [
                "#################",
                "#k   #     #   r#",
                "#    #  #  #    #",
                "## ###  #  ## ###",
                "#     @         #",
                "#  #  ###### #  #",
                "#  # ***       ##",
                "#  # ***  #     #",
                "#################",
            ]),
            ("Torentje", "Het mooiste kantoor van het land. Ook het volste.", 120, [
                "################",
                "#a  #  ##  #  a#",
                "#      ##      #",
                "#  #        #  #",
                "### ##  @ ## ###",
                "#              #",
                "# ##  ****  ## #",
                "#  #  #**#  #  #",
                "################",
            ]),
        ],
    },
    {
        "id": 5,
        "name": "Het Archief",
        "motto": "Wat hier binnenkomt, komt er nooit meer uit.",
        "levels": [
            ("Kelderverdieping", "Het licht doet het niet. De dossiers wel.", 150, [
                "##########",
                "###   ####",
                "#   #   ##",
                "# # ## ###",
                "#   @    #",
                "## # ** ##",
                "##   ** ##",
                "###  * ###",
                "##########",
            ]),
            ("Stoffige stellingkasten", "Sinds 1987 niet meer afgestoft.", 200, [
                "############",
                "#    #     #",
                "# ** # ### #",
                "#  # @     #",
                "## #  ## # #",
                "#  ** #    #",
                "#     #  ###",
                "############",
            ]),
            ("Microfiche", "Kleine letters, grote gevolgen.", 200, [
                "##############",
                "#     #      #",
                "# *** # #### #",
                "# *** @      #",
                "#     # ## # #",
                "###  ##    # #",
                "#        #   #",
                "##############",
            ]),
            ("De Laatste Stempel", "Rond de procedure af. Daarna mag u naar huis.", 150, [
                "#############",
                "#  #     #  #",
                "#     #     #",
                "## # ### # ##",
                "#     @     #",
                "# ##*****## #",
                "#   **  #   #",
                "#############",
            ]),
        ],
    },
]


def build():
    out_departments = []
    solutions = {}
    total_start = time.time()
    for dept in DEPARTMENTS:
        levels = []
        for n, (name, note, max_depth, template) in enumerate(dept["levels"], start=1):
            level_id = f"{dept['id']}-{n}"
            t0 = time.time()
            board = Board.from_rows(template)
            result = hardest_start(board, board.start_player, max_states=700_000, max_depth=max_depth)
            if result is None:
                raise SystemExit(f"{level_id}: geen startpositie gevonden")
            rows = board_to_rows(board, result["boxes"], result["player"])
            check = Board.from_rows(rows)
            if not check.apply_solution(result["solution"]):
                raise SystemExit(f"{level_id}: oplossing klopt niet!")
            print(f"{level_id:5} {name:28} boxes={len(board.goals)} pushes={result['depth']:3} "
                  f"moves={len(result['solution']):4} states={result['states']:7} "
                  f"({time.time() - t0:.1f}s)")
            for r in rows:
                print("      " + r)
            levels.append({"id": level_id, "name": name, "note": note, "map": rows})
            solutions[level_id] = result["solution"]
        out_departments.append({
            "id": dept["id"], "name": dept["name"], "motto": dept["motto"], "levels": levels,
        })
    with open(os.path.join(ROOT, "levels", "levels.json"), "w", encoding="utf-8") as f:
        json.dump({"version": 1, "departments": out_departments}, f, indent=2, ensure_ascii=False)
    with open(os.path.join(ROOT, "tools", "solutions.json"), "w", encoding="utf-8") as f:
        json.dump(solutions, f, indent=2)
    print(f"Klaar in {time.time() - total_start:.1f}s")


if __name__ == "__main__":
    build()
