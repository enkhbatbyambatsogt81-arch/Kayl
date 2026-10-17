from .pushup import PushupAnalyzer
from .squat import SquatAnalyzer

ANALYZERS = {"squat": SquatAnalyzer, "pushup": PushupAnalyzer}


def create_analyzer(name, level="normal", common=None):
    """level: шалгуурын түвшин ("easy" / "normal" / "strict"), config.LEVELS-ийг үз."""
    from ..config import exercise_config
    analyzer = ANALYZERS[name](exercise_config(name, level), common)
    analyzer.level = level
    return analyzer
