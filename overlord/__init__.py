"""
Overlord - Autopoiesis PM/Eng Multi-Agent System.

A self-developing Multi-Agent System that converts high-level product plans
into tracked, testable work across GitHub Projects, Issues, and Repositories.
"""

__version__ = "0.1.0"
__author__ = "Overlord Team"
__license__ = "MIT"

from overlord.config import get_settings

__all__ = ["get_settings", "__version__"]
