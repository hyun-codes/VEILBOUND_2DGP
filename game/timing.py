"""고정 물리 스텝과 과부하 제한. 렌더링 프레임 수에 의존하지 않는다."""

import math


class FixedStepper:
    def __init__(self, hz=60, max_steps=5):
        if hz <= 0 or max_steps < 1:
            raise ValueError("hz and max_steps must be positive")
        self.dt = 1.0 / hz
        self.max_steps = max_steps
        self.accumulator = 0.0
        self.dropped_seconds = 0.0

    def reset(self):
        self.accumulator = 0.0

    def advance(self, elapsed, update):
        if not math.isfinite(elapsed) or elapsed < 0:
            raise ValueError("elapsed must be finite and non-negative")
        self.accumulator += elapsed
        count = 0
        while self.accumulator + 1e-12 >= self.dt and count < self.max_steps:
            update(self.dt)
            self.accumulator = max(0.0, self.accumulator - self.dt)
            count += 1
        if self.accumulator + 1e-12 >= self.dt:
            dropped = math.floor((self.accumulator + 1e-12) / self.dt) * self.dt
            self.accumulator = max(0.0, self.accumulator - dropped)
            self.dropped_seconds += dropped
        return count
