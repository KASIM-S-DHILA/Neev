class Cancelled(Exception):
    pass


class Interrupted(Exception):
    pass


class PermanentFailure(Exception):
    pass


class ExtractionFailure(PermanentFailure):
    pass
