import unittest
from pathlib import Path

from game.lantern_room import LanternRoom
from game.map_loader import load_map

ROOT = Path(__file__).resolve().parents[1]


class LateStageTest(unittest.TestCase):
    def test_every_late_room_requires_an_e_only_progress_condition(self):
        from game.app import STAGES
        for stage in range(6, 10):
            with self.subTest(stage=stage):
                room = LanternRoom(load_map(STAGES[stage]))
                # Walking can load plates, but cannot ignite beacons or dock the orb.
                self.assertTrue(room.beacons or (room.exit_socket is not None
                                                 and room.exit_socket is not room.initial_socket))
                for tick in range(160):
                    room.step(1 / 60, 1 if tick % 160 < 80 else -1, jump=tick % 31 == 0)
                    self.assertFalse(room.complete)
                    self.assertIs(room.socket, room.initial_socket)
                    self.assertFalse(room.lit_beacons)

    def start(self, stage, filename):
        self.room = LanternRoom(load_map(ROOT / f'maps/stage_{stage:02d}' / filename))
        self.mirror = stage == 7

    def act(self, frames=45, direction=0, *, jump=False, interact=False):
        for tick in range(frames):
            self.room.step(1 / 60, direction, jump and tick == 0, interact and tick == 0)
            self.assertIsNone(self.room.death_elapsed, 'Solution entered a death state')

    def go(self, x, *, jump=False):
        if self.mirror:
            x = 264 - x
        direction = 1 if x > self.room.x else -1
        for tick in range(380):
            if self.room.complete or (abs(self.room.x - x) < 1.18 and (tick or not jump)):
                return
            self.act(1, direction, jump=jump and tick == 0)
        self.fail(f'Blocked at {self.room.x, self.room.y} trying to reach {x}')

    def foundry_return(self):
        self.go(190)
        self.go(212, jump=True)
        self.act()
        self.go(236)
        self.go(216)
        self.go(194, jump=True)
        self.act()
        self.go(178, jump=True)
        self.act()
        self.act(interact=True)
        self.assertEqual(self.room.lit_beacons, {'Return beacon'})
        self.go(143, jump=True)
        self.act()
        self.go(119, jump=True)
        self.act()
        if self.mirror:
            self.go(91)
            self.go(60, jump=True)
            self.act()
        self.go(35)
        self.assertEqual(len(self.room.collected), 2)
        self.assertFalse(self.room.exit_ready)
        if self.mirror:
            self.go(57)
            self.go(76, jump=True)
            self.act()
            self.go(95)
            self.assertEqual(len(self.room.collected), 3)
            self.go(64)
            self.act(65)
            return
        self.go(3)
        self.act(10)
        self.go(20)
        self.act(65)

    def finish_foundry(self):
        self.go(58)
        self.act(interact=True)
        self.go(28)
        self.act(interact=True)
        self.go(19)
        self.assertTrue(self.room.complete)

    def test_stage6_full_input_replay_requires_unloading_after_return(self):
        self.start(6, 'stage6_pressure_foundry.tmj')
        self.go(75)
        self.act()
        self.assertIn('Weight treadle', self.room.pressed_plates)
        self.go(25)
        self.act(interact=True)
        self.go(58)
        self.act(interact=True)
        self.go(70)
        self.go(105, jump=True)
        self.act()
        self.go(120)
        self.go(149, jump=True)
        self.act()
        self.foundry_return()
        self.go(105)
        self.act()
        self.assertFalse(self.room.pressed_plates)
        self.finish_foundry()

    def test_stage8_crate_services_sump_then_powers_exit(self):
        from test_counterweight import CounterweightTest
        driver = CounterweightTest()
        driver.room = LanternRoom(load_map(ROOT / 'maps/stage_08/stage8_freight_interlock.tmj'))
        driver.send_crate()
        driver.descend_with_lamp()
        driver.go(79)
        driver.go(54, jump=True)
        driver.act(50)
        driver.go(27)
        self.assertEqual(driver.room.collected, {0, 1})
        driver.go(29)
        driver.go(48, jump=True)
        driver.act(40)
        driver.go(70, jump=True)
        driver.act(40)
        driver.go(95)
        driver.act(45)
        driver.push_lit_crate()
        self.assertIn('Weight treadle', driver.room.pressed_plates)
        driver.go(188, jump=True)
        driver.act(35)
        driver.act(interact=True)
        self.assertTrue(driver.room.carrying_lantern)
        driver.go(212, jump=True)
        driver.act(35)
        driver.go(241)
        self.assertFalse(driver.room.complete)
        driver.act(interact=True)
        driver.act(45)
        driver.go(229)
        self.assertTrue(driver.room.complete)
        self.room = driver.room

    def test_stage9_load_interlock_then_solve_both_floods(self):
        from test_flooded_reservoir import FloodedReservoirTest
        driver = FloodedReservoirTest()
        driver.room = LanternRoom(load_map(ROOT / 'maps/stage_09/stage9_reservoir_interlock.tmj'))
        driver.west, driver.east = driver.room.floods
        original_reach = driver.reach_pump

        def load_interlock():
            original_reach()
            driver.go(109)
            driver.use()
            driver.go(91)
            driver.go(60, jump=True)
            driver.act(40)
            driver.go(104)
            driver.go(136, jump=True)
            driver.act(40)
            driver.go(130)
            driver.use()
            driver.go(125)
            driver.go(146, jump=True)
            driver.act(40)
            driver.use()
            driver.go(100)
            driver.act(35)
            driver.go(153)
            driver.act(40)
            self.assertIn('Weight treadle', driver.room.pressed_plates)
            driver.go(145)
            driver.go(165, jump=True)
            driver.act(35)
            driver.use()
            driver.go(145)
            driver.act(35)
            driver.go(130)
            driver.use()
            driver.go(119)
            self.assertIs(driver.room.socket, driver.room.data.object_named('Pump cradle'))

        original_go = driver.go

        def go_around_load(x, *, jump=False):
            if driver.room.y == 160 and driver.room.x < 146 and x > 182:
                original_go(145)
                original_go(182, jump=True)
                driver.act(35)
            elif driver.room.y == 160 and driver.room.x > 190 and x < 145:
                original_go(190)
                original_go(146, jump=True)
                driver.act(35)
            original_go(x, jump=jump)

        load_interlock()
        driver.go = go_around_load
        driver.go(151)
        driver.use()
        driver.go(130)
        driver.use()
        driver.go(219)
        self.assertEqual(driver.room.collected, {1})
        driver.go(130)
        driver.use()
        driver.go(109)
        driver.use()
        driver.go(130)
        driver.use()
        driver.go(103)
        driver.use()
        driver.go(61)
        driver.go(40, jump=True)
        driver.act(40)
        driver.go(32)
        self.assertEqual(driver.room.collected, {0, 1})
        driver.go(41)
        driver.go(64, jump=True)
        driver.act(40)
        driver.go(103)
        driver.use()
        driver.go(130)
        driver.use()
        driver.go(151)
        driver.use()
        driver.go(130)
        driver.use()
        driver.go(216)
        driver.go(233, jump=True)
        driver.act(40)
        driver.go(213, jump=True)
        driver.act(40)
        driver.go(218)
        driver.go(244, jump=True)
        driver.act(40)
        driver.go(253)
        driver.use()
        driver.go(241)
        self.assertTrue(driver.room.complete)
        self.assertIn('Weight treadle', driver.room.pressed_plates)
        self.room = driver.room

    def test_stage7_full_input_replay_requires_loading_after_return(self):
        self.start(7, 'stage7_reverse_foundry.tmj')
        self.go(105)
        self.act()
        self.assertFalse(self.room.pressed_plates)
        self.go(25)
        self.act(interact=True)
        self.go(58)
        self.act(interact=True)
        self.go(94)
        self.go(116, jump=True)
        self.act()
        self.go(149, jump=True)
        self.act()
        self.foundry_return()
        self.go(92)
        self.go(127, jump=True)
        self.act()
        self.go(94)
        self.act()
        self.assertIn('Weight treadle', self.room.pressed_plates)
        self.go(59, jump=True)
        self.act()
        self.finish_foundry()
