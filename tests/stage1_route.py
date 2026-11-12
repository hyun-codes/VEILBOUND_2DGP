"""키 입력만으로 Stage 1의 세 다리와 높이 차를 넘는다."""


def stage1_commands(game):
    player, world = game.player, game.scene.world
    if game.player_at_exit():
        if world == "shadow" and not game.pending_switches:
            return [("d", False), ("shift_left", True), ("shift_left", False)]
        return []

    commands = [] if "d" in game.keys else [("d", True)]
    if not game.pending_switches and (
            (100 <= player.x < 120 and world == "real")
            or (280 <= player.x < 320 and world == "shadow")
            or (448 <= player.x < 480 and player.grounded and world == "real")):
        commands.extend((("shift_left", True), ("shift_left", False)))
    if 424 <= player.x < 440 and player.y == 183 and player.grounded and "space" not in game.keys:
        commands.append(("space", True))
    elif "space" in game.keys and player.y <= 167:
        commands.append(("space", False))
    return commands
