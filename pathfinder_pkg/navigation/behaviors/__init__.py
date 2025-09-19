"""
Navigation behaviors module for PathfinderBot.

This module provides higher-level navigation behaviors that combine path planning,
obstacle avoidance, and motion control to achieve complex tasks such as waypoint
navigation, following a target, and exploring an environment.
"""

from pathfinder_pkg.navigation.behaviors.navigator import NavigationController
from pathfinder_pkg.navigation.behaviors.navigator import NavigationBehavior

__all__ = ["NavigationController", "NavigationBehavior"]
