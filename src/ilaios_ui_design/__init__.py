"""ILAIOS-native UI design intent resolution."""

from .models import UIDesignSpec
from .resolver import UIDesignError, resolve_ui_design

__all__ = ["UIDesignError", "UIDesignSpec", "resolve_ui_design"]
