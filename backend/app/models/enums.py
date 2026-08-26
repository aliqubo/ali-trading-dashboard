"""Enumerations.

All ENUM types defined in DATABASE_DESIGN.md, declared once as Python string
enums and reused by the models. Values match the design document verbatim.

Structure only — no logic.
"""

from __future__ import annotations

import enum

from sqlalchemy.dialects.postgresql import ENUM as _PgEnum


def pg_enum(enum_cls: type[enum.Enum], *, name: str) -> _PgEnum:
    """Build a PostgreSQL ENUM that stores the enum *values* (lowercase).

    By default SQLAlchemy persists enum *member names*; DATABASE_DESIGN.md
    specifies lowercase values (e.g. 'active', not 'ACTIVE'), so we force the
    stored representation to use ``.value`` via ``values_callable``.
    """
    return _PgEnum(
        enum_cls,
        name=name,
        values_callable=lambda ec: [member.value for member in ec],
    )


class UserStatus(str, enum.Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    PENDING = "pending"
    DELETED = "deleted"


class MarketType(str, enum.Enum):
    STOCKS = "stocks"
    FOREX = "forex"
    CRYPTO = "crypto"
    COMMODITIES = "commodities"
    INDICES = "indices"
    FUTURES = "futures"


class ProviderType(str, enum.Enum):
    REST = "rest"
    WEBSOCKET = "websocket"
    HYBRID = "hybrid"


class TickSide(str, enum.Enum):
    BUY = "buy"
    SELL = "sell"
    UNKNOWN = "unknown"


class OrderSide(str, enum.Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, enum.Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class TimeInForce(str, enum.Enum):
    GTC = "gtc"
    IOC = "ioc"
    FOK = "fok"
    DAY = "day"


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    OPEN = "open"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class Liquidity(str, enum.Enum):
    MAKER = "maker"
    TAKER = "taker"
    UNKNOWN = "unknown"


class PositionSide(str, enum.Enum):
    LONG = "long"
    SHORT = "short"


class PositionStatus(str, enum.Enum):
    OPEN = "open"
    CLOSED = "closed"


class PositionEventType(str, enum.Enum):
    OPEN = "open"
    INCREASE = "increase"
    DECREASE = "decrease"
    CLOSE = "close"
    MARK = "mark"


class TradeStatus(str, enum.Enum):
    OPEN = "open"
    CLOSED = "closed"


class Emotion(str, enum.Enum):
    CALM = "calm"
    CONFIDENT = "confident"
    FEARFUL = "fearful"
    GREEDY = "greedy"
    FRUSTRATED = "frustrated"
    NEUTRAL = "neutral"


class TradeNoteType(str, enum.Enum):
    OBSERVATION = "observation"
    CORRECTION = "correction"
    IDEA = "idea"
    GENERAL = "general"


class StrategyType(str, enum.Enum):
    MANUAL = "manual"
    AUTOMATED = "automated"
    HYBRID = "hybrid"


class StrategyStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class ParamValueType(str, enum.Enum):
    """Strategy parameter value type (includes json)."""

    INT = "int"
    FLOAT = "float"
    STRING = "string"
    BOOL = "bool"
    JSON = "json"


class IndicatorParamValueType(str, enum.Enum):
    """Indicator parameter value type (no json)."""

    INT = "int"
    FLOAT = "float"
    STRING = "string"
    BOOL = "bool"


class IndicatorCategory(str, enum.Enum):
    TREND = "trend"
    MOMENTUM = "momentum"
    VOLATILITY = "volatility"
    VOLUME = "volume"
    OTHER = "other"


class AlertType(str, enum.Enum):
    PRICE = "price"
    INDICATOR = "indicator"
    VOLUME = "volume"
    NEWS = "news"
    CUSTOM = "custom"


class AlertStatus(str, enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    TRIGGERED = "triggered"
    EXPIRED = "expired"


class AlertOperator(str, enum.Enum):
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    EQ = "eq"
    CROSSES_ABOVE = "crosses_above"
    CROSSES_BELOW = "crosses_below"


class LogicOperator(str, enum.Enum):
    AND = "and"
    OR = "or"


class NotificationCategory(str, enum.Enum):
    ALERT = "alert"
    ORDER = "order"
    SYSTEM = "system"
    AI = "ai"
    NEWS = "news"
    RISK = "risk"


class NotificationChannel(str, enum.Enum):
    IN_APP = "in_app"
    EMAIL = "email"
    PUSH = "push"
    SMS = "sms"
    WEBHOOK = "webhook"


class NotificationPriority(str, enum.Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class Sentiment(str, enum.Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class EventImpact(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RiskLevel(str, enum.Enum):
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"
    CUSTOM = "custom"


class RiskRuleType(str, enum.Enum):
    POSITION_LIMIT = "position_limit"
    LOSS_LIMIT = "loss_limit"
    EXPOSURE_LIMIT = "exposure_limit"
    LEVERAGE_LIMIT = "leverage_limit"
    CUSTOM = "custom"


class RiskComparisonOperator(str, enum.Enum):
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    EQ = "eq"


class RiskAction(str, enum.Enum):
    BLOCK = "block"
    WARN = "warn"
    NOTIFY = "notify"


class RiskOutcome(str, enum.Enum):
    PASSED = "passed"
    WARNED = "warned"
    BLOCKED = "blocked"


class AnalysisType(str, enum.Enum):
    TECHNICAL = "technical"
    SENTIMENT = "sentiment"
    PATTERN = "pattern"
    PORTFOLIO = "portfolio"
    FORECAST = "forecast"


class AnalysisStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class SignalType(str, enum.Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    CLOSE = "close"


class SignalStrength(str, enum.Enum):
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"


class SignalStatus(str, enum.Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    HIT_TARGET = "hit_target"
    HIT_STOP = "hit_stop"
    CANCELLED = "cancelled"


class PromptStatus(str, enum.Enum):
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"


class AuditStatus(str, enum.Enum):
    SUCCESS = "success"
    FAILURE = "failure"


class LogLevel(str, enum.Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class SettingScope(str, enum.Enum):
    GLOBAL = "global"
    USER = "user"
    SYSTEM = "system"


class SettingValueType(str, enum.Enum):
    STRING = "string"
    INT = "int"
    FLOAT = "float"
    BOOL = "bool"
    JSON = "json"


class FeatureFlagEnvironment(str, enum.Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    ALL = "all"
