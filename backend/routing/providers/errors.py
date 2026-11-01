class ProviderError(Exception):
    """A provider could not supply usable data."""


class ProviderConfigurationError(ProviderError):
    """The selected provider mode is missing required configuration."""
