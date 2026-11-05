import unittest

from game.game_world import GameWorld


class Actor:
    def __init__(self, name, log, action=None):
        self.name, self.log, self.action = name, log, action

    def update(self, dt):
        self.log.append(self.name)
        if self.action:
            self.action()

    def draw(self, renderer, camera):
        self.log.append(self.name)


class GameWorldTests(unittest.TestCase):
    def test_self_removal_does_not_skip_next_actor(self):
        world, log = GameWorld(), []
        a = Actor("a", log)
        b = Actor("b", log)
        a.action = lambda: world.remove_object(a)
        world.add_object(a)
        world.add_object(b)
        world.update(1 / 60)
        self.assertEqual(log, ["a", "b"])
        log.clear()
        world.update(1 / 60)
        self.assertEqual(log, ["b"])

    def test_removed_actor_does_not_act_and_spawn_waits_until_next_tick(self):
        world, log = GameWorld(), []
        b, child = Actor("b", log), Actor("child", log)
        a = Actor("a", log)

        def action():
            world.remove_object(b)
            world.add_object(child)
            a.action = None

        a.action = action
        world.add_object(a)
        world.add_object(b)
        world.update(1 / 60)
        self.assertEqual(log, ["a"])
        log.clear()
        world.update(1 / 60)
        self.assertEqual(log, ["a", "child"])

    def test_clear_during_update_and_layer_order(self):
        world, log = GameWorld(), []
        a = Actor("a", log, world.clear)
        world.add_object(Actor("late", log), 10)
        world.add_object(a, 0)
        world.update(1 / 60)
        self.assertEqual(log, ["a"])
        log.clear()
        world.render(None, None)
        self.assertEqual(log, [])

    def test_duplicate_registration_is_rejected_and_worlds_are_isolated(self):
        first, second, log = GameWorld(), GameWorld(), []
        actor = Actor("a", log)
        first.add_object(actor)
        with self.assertRaises(ValueError):
            first.add_object(actor)
        second.update(1 / 60)
        self.assertEqual(log, [])
        first.remove_object(actor)
        first.remove_object(actor)

    def test_render_order_is_depth_then_insertion(self):
        world, log = GameWorld(), []
        world.add_object(Actor("front", log), 3)
        world.add_object(Actor("back1", log), -1)
        world.add_object(Actor("back2", log), -1)
        world.render(None, None)
        self.assertEqual(log, ["back1", "back2", "front"])
