"""Global constants: screen, colours, timing and the humorous texts."""
from __future__ import annotations

SCREEN_W, SCREEN_H = 800, 600
FPS = 60
TILE = 32
TITLE = "Operatie Bureaucratie"
SUBTITLE = "Waar iedere stap eerst moet worden goedgekeurd."
ORGANISATION = "Rijksdienst voor Dossierverplaatsing"
ORG_SHORT = "RDV"
VERSION = "1.0"

# Discord Rich Presence: the "Application ID" of your app on
# https://discord.com/developers/applications (leave empty to disable).
DISCORD_CLIENT_ID = "1572647721783791666"
DISCORD_LARGE_IMAGE = "logo"     # asset key uploaded under Rich Presence > Art Assets
DISCORD_WALK_WINDOW = 1600       # ms after the last step that still counts as walking
DISCORD_PUSH_WINDOW = 2500       # ms after the last push that still counts as pushing

HUD_H = 40
STATUS_H = 28
PLAY_RECT = (0, HUD_H, SCREEN_W, SCREEN_H - HUD_H - STATUS_H)

# Timing (milliseconds)
MOVE_TIME = 110          # tween duration for one step
KEY_REPEAT_DELAY = 170   # hold a key this long before auto-repeat starts
KEY_REPEAT_RATE = 115

# Palette (DOS / Windows 3.1 inspired, in government blues)
BLACK = (8, 10, 20)
NAVY = (14, 30, 72)
RIJKSBLAUW = (24, 50, 112)
BLUE = (48, 98, 178)
LIGHT_BLUE = (130, 178, 232)
PALE_BLUE = (214, 228, 246)
WHITE = (244, 244, 240)
GREY = (196, 198, 206)
MID_GREY = (138, 142, 156)
DARK_GREY = (72, 74, 92)
YELLOW = (250, 214, 90)
RED = (210, 50, 50)
GREEN = (70, 180, 80)
CYAN = (90, 220, 230)

# ----------------------------------------------------------------- texts
MSG_WALL = [
    "U heeft een verkeerde stap gezet.",
    "Dit is geen loket. Dit is een muur.",
    "Doorgang geweigerd. Meld u bij de receptie.",
]
MSG_FURNITURE = [
    "Dit meubilair is eigendom van de Rijksoverheid.",
    "Niet aankomen. Inventarisnummer 4471-B.",
    "Dit bureau is gereserveerd via het boekingssysteem.",
]
MSG_BLOCKED_BOX = [
    "Deze aanvraag kan niet worden verplaatst.",
    "Er ligt al een dossier in behandeling.",
    "Formulier 12B ontbreekt.",
]
MSG_GOAL = [
    "Dossier gearchiveerd. Keurig.",
    "Dit dossier is bij het juiste loket.",
    "Afgestempeld en opgeborgen.",
]
MSG_DEADLOCK = [
    "Dit dossier zit klem. Overweeg Z (bezwaar).",
    "Procedure vastgelopen. Druk op Z of R.",
]
MSG_UNDO = [
    "Uw bezwaar is gegrond. Stap teruggedraaid.",
    "De vorige beslissing is herroepen.",
]
MSG_RESTART = [
    "Uw aanvraag wordt doorgeschoven naar een andere afdeling.",
    "Alles opnieuw. Graag in drievoud.",
]
MSG_IDLE = [
    "Uw aanvraag is in behandeling.",
    "Dit dossier moet naar het juiste loket.",
    "Een moment geduld alstublieft...",
    "De koffieautomaat is tijdelijk buiten gebruik.",
    "Vergeet niet uw uren te schrijven.",
    "De lift is defect. Dossiers gaan via de trap.",
    "Er is taart in de kantine. Eerst archiveren.",
    "Reorganisatie aangekondigd. Niets verandert.",
]
WIN_LINES = [
    "Gefeliciteerd! Uw dossier is gearchiveerd.",
    "De procedure is succesvol afgerond.",
    "Uw aanvraag is goedgekeurd en bijgezet.",
]
LOADING_LINES = [
    "Een moment geduld alstublieft...",
    "Formulieren worden gesorteerd...",
    "Stempelkussens worden bijgevuld...",
    "Koffie wordt gezet...",
    "Uw aanvraag is in behandeling...",
]
