"""Tests for the Sokoban rules, levels, solutions and savegame."""
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

    def test_at_least_20_levels_in_5_departments(self):
        self.assertGreaterEqual(len(self.pack.levels), 20)
        self.assertEqual(len(self.pack.departments), 5)

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


if __name__ == "__main__":
    unittest.main()
