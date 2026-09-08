from enum import Enum

# ============================================================
# USER STATUS
# ============================================================
class UserStatus(str, Enum):
    FREE = "free"
    PREMIUM = "premium"
    EXPIRED = "expired"

# ============================================================
# SUBSCRIPTION STATUS
# ============================================================
class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    INCOMPLETE = "incomplete"
    EXPIRED = "expired"

# ============================================================
# GENDER
# ============================================================
class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    NON_BINARY = "non_binary"
    OTHER = "other"
    PREFER_NOT_TO_SAY = "prefer_not_to_say"

# ============================================================
# MATCH STATUS
# ============================================================
class MatchStatus(str, Enum):
    PENDING = "pending"
    MATCHED = "matched"
    REJECTED = "rejected"
    BLOCKED = "blocked"
    EXPIRED = "expired"

# ============================================================
# MESSAGE TYPE
# ============================================================
class MessageType(str, Enum):
    TEXT = "text"
    PHOTO = "photo"
    VIDEO = "video"
    AUDIO = "audio"
    SYSTEM = "system"
    LOCATION = "location"

# ============================================================
# NOTIFICATION TYPE
# ============================================================
class NotificationType(str, Enum):
    NEW_MATCH = "new_match"
    NEW_MESSAGE = "new_message"
    SUBSCRIPTION_EXPIRY = "subscription_expiry"
    PAYMENT_SUCCESS = "payment_success"
    PAYMENT_FAILED = "payment_failed"
    PROFILE_VIEW = "profile_view"
    NEW_SWIPE = "new_swipe"
    ACCOUNT_VERIFIED = "account_verified"
    PROMOTIONAL = "promotional"

# ============================================================
# REPORT REASON
# ============================================================
class ReportReason(str, Enum):
    SPAM = "spam"
    INAPPROPRIATE = "inappropriate"
    HARASSMENT = "harassment"
    FAKE_PROFILE = "fake_profile"
    UNDERAGE = "underage"
    OFFENSIVE = "offensive"
    OTHER = "other"

# ============================================================
# SWIPE DIRECTION
# ============================================================
class SwipeDirection(str, Enum):
    LIKE = "like"
    PASS = "pass"

# ============================================================
# PAYMENT STATUS
# ============================================================
class PaymentStatus(str, Enum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"

# ============================================================
# PAYMENT METHOD
# ============================================================
class PaymentMethod(str, Enum):
    CHAPA = "chapa"
    TELEBIRR = "telebirr"
    CBE_BIRR = "cbe_birr"
    AMOLE = "amole"
    HELLO_CASH = "hello_cash"
    CARD = "card"
    PAYPAL = "paypal"