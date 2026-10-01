"""Tap timing uses input-event timestamps, independent of display/render latency."""
EMERGENCY_TAPS = 5
EMERGENCY_WINDOW = 0.500


class TapGesture:
    def __init__(self):
        self.taps = []

    def clear(self):
        self.taps.clear()

    def tap(self, pressed_at, released_at):
        if released_at < pressed_at or released_at - pressed_at > EMERGENCY_WINDOW:
            self.clear()
            return None
        self.taps = [(p, r) for p, r in self.taps
                     if released_at - p <= EMERGENCY_WINDOW + 1e-9]
        self.taps.append((pressed_at, released_at))
        if len(self.taps) >= EMERGENCY_TAPS:
            self.clear()
            return 'emergency'
        return None

    def flush(self, now):
        if not self.taps or now - self.taps[0][0] <= EMERGENCY_WINDOW:
            return None
        count = len(self.taps)
        self.clear()
        return 'single' if count == 1 else 'double' if count == 2 else None
