"""수업의 레이어별 객체 관리에 안전한 추가·제거를 적용한다."""

from collections import defaultdict


class GameWorld:
    def __init__(self):
        self._layers = defaultdict(list)
        self._walking = False
        self._pending = []
        self._removed = set()
        self._cleared = False

    def add_object(self, obj, depth=0):
        if not isinstance(depth, int):
            raise TypeError("depth must be an integer")
        registered = any(obj is other for layer in self._layers.values() for other in layer)
        queued = any(op == "add" and obj is other for op, other, _ in self._pending)
        if registered or queued:
            raise ValueError("Object is already registered")
        self._change("add", obj, depth)

    def remove_object(self, obj):
        # 중복 사망·정리 요청은 안전하게 무시한다.
        if self._walking:
            self._removed.add(id(obj))
        self._change("remove", obj, 0)

    def clear(self):
        if self._walking:
            self._cleared = True
        self._change("clear", None, 0)

    def _change(self, operation, obj, depth):
        if self._walking:
            self._pending.append((operation, obj, depth))
        else:
            self._apply(operation, obj, depth)

    def _apply(self, operation, obj, depth):
        if operation == "add":
            self._layers[depth].append(obj)
        elif operation == "remove":
            for layer in self._layers.values():
                layer[:] = [other for other in layer if other is not obj]
        else:
            self._layers.clear()

    def _visit(self, callback):
        if self._walking:
            raise RuntimeError("GameWorld traversal cannot be nested")
        self._walking = True
        snapshot = [obj for depth in sorted(self._layers) for obj in self._layers[depth]]
        try:
            for obj in snapshot:
                if self._cleared:
                    break
                if id(obj) not in self._removed:
                    callback(obj)
        finally:
            self._walking = False
            pending, self._pending = self._pending, []
            for operation, obj, depth in pending:
                self._apply(operation, obj, depth)
            self._removed.clear()
            self._cleared = False

    def update(self, dt):
        self._visit(lambda obj: obj.update(dt))

    def render(self, renderer, camera):
        self._visit(lambda obj: obj.draw(renderer, camera))
