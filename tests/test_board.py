"""Tests for the Sokoban rules, levels, solutions and savegame."""
import hashlib
import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from game.board import DOWN, LEFT, RIGHT, UP, Board, LevelFormatError  # noqa: E402
from game.level import LevelPack  # noqa: E402
from game.savegame import SaveGame  # noqa: E402

ROOM = [
    "#######",
    "#     #",
    "# $$ .#",
    "#@ b .#",
    "#######",
]


class BoardRules(unittest.TestCase):
    def setUp(self):
        self.b = Board.from_rows(ROOM)

    def test_parse(self):
        self.assertEqual(self.b.player, (1, 3))
        self.assertEqual(self.b.boxes, {(2, 2), (3, 2)})
        self.assertEqual(self.b.goals, {(5, 2), (5, 3)})
        self.assertEqual(self.b.furniture[(3, 3)], "bureau")

    def test_cannot_walk_through_wall(self):
        res = self.b.move(LEFT)
        self.assertFalse(res.moved)
        self.assertEqual(res.blocked_by, "wall")
        self.assertEqual(self.b.player, (1, 3))
        self.assertEqual(self.b.moves, 0)

    def test_cannot_walk_through_furniture(self):
        self.b.move(RIGHT)
        res = self.b.move(RIGHT)
        self.assertFalse(res.moved)
        self.assertEqual(res.blocked_by, "furniture")

    def test_push_box(self):
        self.b.move(UP)                      # (1,2)
        res = self.b.move(RIGHT)             # push (2,2) into (3,2)? blocked by box
        self.assertFalse(res.moved)
        self.assertEqual(res.blocked_by, "box")  # two boxes cannot be pushed

    def test_push_single_box_and_counters(self):
        self.b.move(UP)
        self.b.move(UP)                      # (1,1)
        self.b.move(RIGHT)
        self.b.move(RIGHT)                   # (3,1)
        res = self.b.move(DOWN)              # push (3,2) -> (3,3) is furniture
        self.assertFalse(res.moved)
        self.b.move(RIGHT)                   # (4,1)
        self.b.move(DOWN)                    # (4,2)
        res = self.b.move(LEFT)              # push (3,2) -> (2,2) occupied
        self.assertFalse(res.moved)
        self.assertEqual(self.b.moves, 6)
        self.assertEqual(self.b.pushes, 0)

    def test_box_not_through_wall(self):
        b = Board.from_rows(["#####", "#@$.#", "#####"])
        b.move(RIGHT)
        self.assertTrue(b.is_solved)
        res = b.move(RIGHT)                  # box against wall
        self.assertFalse(res.moved)
        self.assertEqual(b.boxes, {(3, 1)})

    def test_no_pull(self):
        b = Board.from_rows(["######", "# @$.#", "######"])
        b.move(LEFT)
        self.assertEqual(b.boxes, {(3, 1)})  # box stays behind

    def test_undo(self):
        b = Board.from_rows(["######", "#@$ .#", "######"])
        b.move(RIGHT)
        b.move(RIGHT)
        self.assertEqual((b.moves, b.pushes), (2, 2))
        b.undo()
        self.assertEqual(b.boxes, {(3, 1)})
        self.assertEqual(b.player, (2, 1))
        self.assertEqual((b.moves, b.pushes), (1, 1))
        b.undo()
        self.assertEqual(b.boxes, {(2, 1)})
        self.assertEqual(b.player, (1, 1))
        self.assertIsNone(b.undo())

    def test_restart(self):
        b = Board.from_rows(["######", "#@$ .#", "######"])
        b.move(RIGHT)
        b.reset()
        self.assertEqual(b.boxes, {(2, 1)})
        self.assertEqual(b.player, (1, 1))
        self.assertEqual((b.moves, b.pushes), (0, 0))
        self.assertEqual(b.history, [])

    def test_completion(self):
        b = Board.from_rows(["######", "#@$ .#", "######"])
        self.assertFalse(b.move(RIGHT).solved)
        res = b.move(RIGHT)
        self.assertTrue(res.solved)
        self.assertTrue(res.box_on_goal)

    def test_deadlock_detection(self):
        b = Board.from_rows(["#####", "#  .#", "# $ #", "#@  #", "#####"])
        self.assertTrue(b.is_dead_box((1, 1)))
        self.assertFalse(b.is_dead_box((3, 1)))   # goal
        self.assertFalse(b.is_dead_box((2, 2)))

    def test_bad_levels(self):
        with self.assertRaises(LevelFormatError):
            Board.from_rows(["####", "#$.#", "####"])          # no player
        with self.assertRaises(LevelFormatError):
            Board.from_rows(["#####", "#@$$.#", "#####"])      # boxes != goals
        with self.assertRaises(LevelFormatError):
            Board.from_rows(["####", "#@X#", "####"])          # unknown char


class Levels(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack = LevelPack(os.path.join(ROOT, "levels", "levels.json"))
        with open(os.path.join(ROOT, "tools", "solutions.json"), encoding="utf-8") as f:
            cls.solutions = json.load(f)

    def test_100_levels_in_25_departments_of_4(self):
        self.assertEqual(len(self.pack.levels), 100)
        self.assertEqual([d.id for d in self.pack.departments], list(range(1, 26)))
        for dept in self.pack.departments:
            self.assertEqual([lv.id for lv in dept.levels],
                             [f"{dept.id}-{n}" for n in range(1, 5)], dept.name)
        ids = [lv.id for lv in self.pack.levels]
        self.assertEqual(len(ids), len(set(ids)))
        maps = [tuple(lv.rows) for lv in self.pack.levels]
        self.assertEqual(len(maps), len(set(maps)), "dubbele plattegrond")

    def test_original_20_levels_unchanged(self):
        # Fingerprint of departments 1-5 as released in version 1.0. Save games
        # store progress per level id, so these must never change.
        with open(os.path.join(ROOT, "levels", "levels.json"), encoding="utf-8") as f:
            data = json.load(f)
        blob = json.dumps(data["departments"][:5], sort_keys=True, ensure_ascii=False).encode()
        self.assertEqual(hashlib.sha256(blob).hexdigest(),
                         "f3bb183d63cd2c2852406a9f6781b9debe6237cd299ddcd880313b431d668227")

    def test_levels_fit_screen(self):
        for lv in self.pack.levels:
            b = lv.make_board()
            self.assertLessEqual(b.width * 32, 780, lv.id)
            self.assertLessEqual(b.height * 32, 516, lv.id)

    def test_every_level_is_solvable(self):
        for lv in self.pack.levels:
            with self.subTest(level=lv.id):
                b = lv.make_board()
                self.assertFalse(b.is_solved)
                self.assertTrue(b.apply_solution(self.solutions[lv.id]))

    def test_undo_whole_solution_restores_start(self):
        for lv in self.pack.levels:
            b = lv.make_board()
            b.apply_solution(self.solutions[lv.id])
            while b.undo():
                pass
            self.assertEqual(b.boxes, b.start_boxes, lv.id)
            self.assertEqual(b.player, b.start_player, lv.id)
            self.assertEqual((b.moves, b.pushes), (0, 0))


class SaveGames(unittest.TestCase):
    def test_roundtrip_and_best(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "save.json")
            s = SaveGame(path)
            self.assertTrue(s.record("1-1", 20, 5))
            self.assertFalse(s.record("1-1", 25, 5))
            self.assertTrue(s.record("1-1", 18, 7))
            s.last_level = "1-2"
            s.settings["sfx_volume"] = 0.3
            s.save()
            s2 = SaveGame(path)
            self.assertEqual(s2.best("1-1"), {"moves": 18, "pushes": 7})
            self.assertEqual(s2.last_level, "1-2")
            self.assertAlmostEqual(s2.settings["sfx_volume"], 0.3)

    def test_corrupt_save_is_recovered(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "save.json")
            with open(path, "w") as f:
                f.write("{dit is geen json")
            s = SaveGame(path)
            self.assertEqual(s.completed, {})
            self.assertIsNotNone(s.load_error)
            self.assertTrue(s.save())

    def test_unlocking(self):
        pack = LevelPack(os.path.join(ROOT, "levels", "levels.json"))
        with tempfile.TemporaryDirectory() as d:
            s = SaveGame(os.path.join(d, "save.json"))
            self.assertTrue(pack.is_unlocked(pack.levels[0], s))
            self.assertFalse(pack.is_unlocked(pack.levels[1], s))
            s.record(pack.levels[0].id, 10, 2)
            self.assertTrue(pack.is_unlocked(pack.levels[1], s))
            self.assertEqual(pack.continue_level(s), pack.levels[1])

    def test_secret_unlock_all_and_relock(self):
        """The secret mode opens everything; switching it off keeps progress and
        only opens the first level whose predecessors are all completed."""
        pack = LevelPack(os.path.join(ROOT, "levels", "levels.json"))
        L = pack.levels
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "save.json")
            s = SaveGame(path)
            for lv in L[:11]:
                s.record(lv.id, 10, 2)
            self.assertTrue(s.toggle_unlock_all())
            self.assertTrue(all(pack.is_unlocked(lv, s) for lv in L))
            self.assertTrue(SaveGame(path).unlock_all)          # remembered
            s.record(L[40].id, 99, 9)                            # solved while unlocked
            self.assertFalse(s.toggle_unlock_all())
            s = SaveGame(path)
            self.assertFalse(s.unlock_all)
            open_ids = [lv.id for lv in L if pack.is_unlocked(lv, s)]
            self.assertEqual(open_ids, [lv.id for lv in L[:12]] + [L[40].id])
            self.assertFalse(pack.is_unlocked(L[41], s))         # no skipping ahead
            self.assertEqual(pack.continue_level(s), L[11])
            self.assertEqual(len(s.completed), 12)

    def test_version_1_save_keeps_progress(self):
        """A save from the 20-level version opens level 21 and keeps all records."""
        pack = LevelPack(os.path.join(ROOT, "levels", "levels.json"))
        old_ids = [lv.id for lv in pack.levels[:20]]
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "savegame.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"version": 1, "last_level": "5-4",
                           "completed": {i: {"moves": 50, "pushes": 9} for i in old_ids},
                           "settings": {"sound": False}}, f)
            s = SaveGame(path)
            self.assertIsNone(s.load_error)
            self.assertFalse(s.upgrade(pack.legacy_map()))   # nothing to rename
            self.assertEqual(set(s.completed), set(old_ids))
            self.assertEqual(s.best("3-4"), {"moves": 50, "pushes": 9})
            self.assertFalse(s.settings["sound"])
            nxt = pack.levels[20]
            self.assertEqual(nxt.id, "6-1")
            self.assertTrue(pack.is_unlocked(nxt, s))
            self.assertFalse(pack.is_unlocked(pack.levels[21], s))
            self.assertEqual(pack.continue_level(s), nxt)
            self.assertEqual(SaveGame(path).loaded_version, 2)

    def test_save_from_16_level_departments_is_upgraded(self):
        """Progress on 6-1..10-16 (16 per department) moves to the new ids."""
        pack = LevelPack(os.path.join(ROOT, "levels", "levels.json"))
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "savegame.json")
            completed = {"5-4": {"moves": 1, "pushes": 1},
                         "6-1": {"moves": 2, "pushes": 2},     # level 21 -> 6-1
                         "6-5": {"moves": 3, "pushes": 3},     # level 25 -> 7-1
                         "7-1": {"moves": 4, "pushes": 4},     # level 37 -> 10-1
                         "10-16": {"moves": 5, "pushes": 5}}   # level 100 -> 25-4
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"version": 1, "last_level": "7-2", "completed": completed}, f)
            s = SaveGame(path)
            self.assertTrue(s.upgrade(pack.legacy_map()))
            self.assertEqual(s.completed, {
                "5-4": {"moves": 1, "pushes": 1}, "6-1": {"moves": 2, "pushes": 2},
                "7-1": {"moves": 3, "pushes": 3}, "10-1": {"moves": 4, "pushes": 4},
                "25-4": {"moves": 5, "pushes": 5}})
            self.assertEqual(s.last_level, "10-2")
            self.assertEqual(pack.by_id("10-1").name, "Formulier A1")
            # the upgraded file is version 2 and is never renamed again
            s2 = SaveGame(path)
            self.assertEqual(s2.loaded_version, 2)
            self.assertFalse(s2.upgrade(pack.legacy_map()))
            self.assertEqual(s2.completed, s.completed)


if __name__ == "__main__":
    unittest.main()
