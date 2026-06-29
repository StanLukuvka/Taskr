from app.errors.base import TaskrError


class HermesConfigurationError(TaskrError):
    status_code = 500
    detail = "Hermes is not configured"


class HermesIntegrationError(TaskrError):
    status_code = 502
    detail = "Hermes integration failed"


class StripeConfigurationError(TaskrError):
    status_code = 500
    detail = "Stripe is not configured for test mode"


class StripeIntegrationError(TaskrError):
    status_code = 502
    detail = "Stripe integration failed"
