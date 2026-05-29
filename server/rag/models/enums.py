from enum import Enum


class SafetyLabel(str, Enum):
    SAFE = "safe"
    ADVERSARIAL = "adversarial"
    HERETICAL_REWRITE = "heretical_rewrite"
    POLICY_VIOLATION = "policy_violation"


class Intent(str, Enum):
    SCRIPTURE_LOOKUP = "scripture_lookup"
    THEOLOGICAL_Q = "theological_q"
    CONTENT_GENERATION = "content_generation"
    IMAGE_REQUEST = "image_request"
    SMALLTALK = "smalltalk"
    UNSAFE = "unsafe"


class Denomination(str, Enum):
    CATHOLIC = "catholic"
    PROTESTANT = "protestant"
    ORTHODOX = "orthodox"
    NONE = "none"
    SHARED = "shared"


class Verified(str, Enum):
    FULL = "full"
    PARTIAL = "partial"
    NONE = "none"


CitationsVerified = Verified
