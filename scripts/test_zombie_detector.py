import os
import sys
import unittest
from types import SimpleNamespace


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "p_game"))

from battle.engine import Engine
from battle.map import Map
from battle.unit import Unit
import network_bridge


class ZombieDetectorTest(unittest.TestCase):
    def test_confirmed_dead_unit_coming_back_is_marked_zombie(self):
        engine = Engine("stest1", "braindead", "braindead", 0)
        engine.game_map = Map(10, 10)

        unit = Unit(hp=10, team="R", type="P", position=(1, 1))
        unit.unit_id = 7
        engine.units = [unit]
        engine.game_map.map[unit.position] = unit

        unit.current_hp = 0
        unit.is_alive = False
        for _ in range(engine.DEATH_CONFIRM_TICKS):
            engine.update_units(1 / 60)

        self.assertIn(unit.unit_id, engine._dead_unit_ids)

        unit.current_hp = 5
        unit.is_alive = True
        unit.state = "idle"
        engine.update_units(1 / 60)

        self.assertTrue(unit.is_zombie)
        self.assertEqual(engine.zombie_count, 1)
        self.assertEqual(engine.zombie_events[-1]["unit_id"], unit.unit_id)
        self.assertEqual(engine.zombie_events[-1]["hp"], 5)
        self.assertEqual(engine.zombie_events[-1]["source"], "engine")

    def test_network_resurrection_is_marked_at_activation_time(self):
        engine = Engine("stest1", "braindead", "braindead", 0)
        engine.game_map = Map(10, 10)

        unit = Unit(hp=10, team="B", type="C", position=(2, 2))
        unit.unit_id = 8
        unit.current_hp = 0
        unit.is_alive = False
        unit.state = "dead"
        engine.units = [unit]

        engine.confirm_unit_dead(unit, source="network")
        slot = SimpleNamespace(alive=1, hp=6, hp_max=10, x=3.0, y=4.0)

        self.assertTrue(network_bridge._activate_remote_unit(engine, unit, slot))

        self.assertTrue(unit.is_alive)
        self.assertTrue(unit.is_zombie)
        self.assertEqual(engine.zombie_count, 1)
        self.assertEqual(engine.zombie_events[-1]["source"], "network_resurrected")
        self.assertIn(unit, engine.game_map.map.values())


if __name__ == "__main__":
    unittest.main()
