"Exception classes"


class ClakError(Exception):
    "Argument error"

    rc = 99
    advice = None
    message = None


    def __init__(self, message=None, advice=None):
        self.message = message
        self.advice = advice
        super().__init__(message)


# User errors
# ==============================

class ClakUserError(ClakError):
    "User error"

    rc = 1
    advice = None

class ClakParseError(ClakUserError):
    "Raised when there is a parse issue"

    rc = 2

class ClakExitError(ClakUserError):
    "Raised when there is a exit"

    rc = 4


# Application errors
# ==============================
class ClakAppError(ClakError):
    "Application error"

    rc = 30

class ClakNotImplementedError(ClakAppError):
    "Raised when a method is not implemented"

    rc = 31

class ClakBugError(ClakAppError):
    "Raised when a bug is found"

    rc = 32