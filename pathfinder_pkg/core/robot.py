"""
Base robot class for the PathfinderBot platform.

This module provides the base Robot class that serves as a foundation for
robot functionality, including hardware access and resource management.
"""

from pathfinder_pkg.utils.logging import get_logger

logger = get_logger(__name__)


class Robot:
    """
    Base class for the PathfinderBot robot.

    This class manages robot-wide resources and provides access to
    hardware components such as motors, servos, camera, and sensors.

    Attributes:
        name (str): The name of the robot.
        initialized (bool): Whether the robot has been initialized.
    """

    def __init__(self, name="PathfinderBot"):
        """
        Initialize the robot with a name.

        Args:
            name (str, optional): The name of the robot. Defaults to "PathfinderBot".
        """
        self.name = name
        self.initialized = False
        self._components = {}
        logger.info(f"Robot '{self.name}' created")

    def initialize(self):
        """
        Initialize the robot's hardware components.

        This method should be called before using the robot.
        It ensures that all hardware components are properly set up.

        Returns:
            bool: True if initialization was successful, False otherwise.
        """
        if self.initialized:
            logger.warning(f"Robot '{self.name}' already initialized")
            return True

        try:
            logger.info(f"Initializing robot '{self.name}'...")
            # Hardware initialization code will go here
            self.initialized = True
            logger.info(f"Robot '{self.name}' initialization completed successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize robot '{self.name}': {e}")
            return False

    def shutdown(self):
        """
        Shut down the robot and release resources.

        This method should be called when the robot is no longer needed
        to ensure that all hardware components are properly released.
        """
        if not self.initialized:
            logger.warning(f"Robot '{self.name}' not initialized, nothing to shut down")
            return

        try:
            logger.info(f"Shutting down robot '{self.name}'...")
            # Hardware shutdown code will go here
            self.initialized = False
            logger.info(f"Robot '{self.name}' shut down successfully")
        except Exception as e:
            logger.error(f"Error during robot '{self.name}' shutdown: {e}")

    def add_component(self, component_name, component):
        """
        Add a component to the robot.

        Args:
            component_name (str): The name of the component.
            component: The component object.
        """
        self._components[component_name] = component
        logger.debug(f"Added component '{component_name}' to robot '{self.name}'")

    def get_component(self, component_name):
        """
        Get a component by name.

        Args:
            component_name (str): The name of the component.

        Returns:
            The component object, or None if not found.
        """
        return self._components.get(component_name)

    def list_components(self):
        """
        List all components.

        Returns:
            list: A list of component names.
        """
        return list(self._components.keys())


# Create a singleton instance for use throughout the package
robot = Robot()
