"""Local state for the Pro editor preview."""
from dataclasses import dataclass

TRIAL_EXPORTS = 3
WEEK_SECONDS = 7 * 24 * 60 * 60


@dataclass
class ProPreview:
    captures: int = 0
    exports: int = 0
    last_offer: int = 0

    @property
    def remaining(self) -> int:
        return max(0, TRIAL_EXPORTS - self.exports)

    def record_capture(self, now: int, *, can_show: bool) -> bool:
        self.captures += 1
        if (
            can_show
            and self.captures in (100, 200)
            and (not self.last_offer or now - self.last_offer >= WEEK_SECONDS)
        ):
            self.last_offer = now
            return True
        return False
