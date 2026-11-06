"""등록한 스테이지만 로드한다. 출구 문자열을 임의의 파일 경로로 해석하지 않는다."""

from game.map_loader import load_map


class StageManager:
    def __init__(self, paths):
        self.paths = dict(paths)

    def next_map(self, current):
        destination = current.object_named("Exit").properties.get("destination")
        if destination not in self.paths:
            return None
        return load_map(self.paths[destination])
