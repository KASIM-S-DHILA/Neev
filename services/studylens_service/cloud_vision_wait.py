"""A scheduling signal with no model/runtime dependencies."""


class Deferred(Exception):
    def __init__(self, seconds, stage="Waiting for Groq quota"):
        self.seconds = max(1, min(86400, seconds))
        self.stage = stage
