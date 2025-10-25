#!/usr/bin/env python3
"""
GLPI Agent Inventory Module - Python Implementation

Base class for all inventory task modules. Defines the interface and
dependency configuration for inventory collection modules.
"""

from abc import ABC
from typing import List, Dict, Any, Optional


class InventoryModule(ABC):
    """
    Base class for inventory task modules.
    
    This abstract class defines the interface that all inventory modules
    must implement, as well as module dependency configuration.
    
    Class Attributes:
        runAfter: List of modules that must run before this one (hard dependency)
        runAfterIfEnabled: List of modules that should run before if enabled (soft dependency)
        runMeIfTheseChecksFailed: List of modules that disable this one if enabled
    """
    
    # Module dependency configuration
    # These are class-level attributes that should be overridden in subclasses
    runAfter: List[str] = []
    runAfterIfEnabled: List[str] = []
    runMeIfTheseChecksFailed: List[str] = []
    
    @staticmethod
    def category() -> str:
        """
        Get the inventory category for this module.
        
        Returns:
            Category name (e.g., 'hardware', 'software', 'network')
            Empty string by default (override in subclasses)
        """
        return ""
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """
        Check if module should be enabled for local inventory.
        
        Args:
            **params: Module parameters including:
                - datadir: Resources folder path
                - logger: Agent logger instance
                - registry: Registry option passed by server
                - scan_homedirs: scan-homedirs configuration parameter
                - scan_profiles: scan-profiles configuration parameter
                - remote: Remote execution context (if any)
                
        Returns:
            True if module should run, False otherwise
            Default implementation returns False (override in subclasses)
        """
        return False
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """
        Perform inventory collection and update inventory object.
        
        Args:
            **params: Inventory parameters including:
                - inventory: Inventory object to populate
                - no_category: Dict of disabled categories
                - datadir: Resources folder path
                - logger: Agent logger instance
                - registry: Registry option passed by server
                - params: Additional parameters from server
                - scan_homedirs: scan-homedirs configuration parameter
                - scan_profiles: scan-profiles configuration parameter
                - assetname_support: assetname-support configuration parameter
                
        Returns:
            None - Updates inventory object in place
            Default implementation does nothing (override in subclasses)
        """
        pass


# Example concrete implementation for reference
class ExampleInventoryModule(InventoryModule):
    """
    Example inventory module showing proper implementation pattern.
    """
    
    # Override dependency configuration
    runAfter = []  # No hard dependencies
    runAfterIfEnabled = ['GLPI::Agent::Task::Inventory::Generic::Dmidecode']
    runMeIfTheseChecksFailed = []
    
    @staticmethod
    def category() -> str:
        """This module belongs to the 'hardware' category."""
        return "hardware"
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """
        Check if example module is enabled.
        
        This example checks if we're on Linux and have required tools.
        """
        logger = params.get('logger')
        
        # Example: Check OS type
        import platform
        if platform.system() != 'Linux':
            if logger:
                logger.debug2("Example module: Not on Linux")
            return False
        
        # Example: Check for required command
        try:
            from glpi_agent.tools import can_run
            if not can_run('lspci'):
                if logger:
                    logger.debug2("Example module: lspci not available")
                return False
        except ImportError:
            pass
        
        return True
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """
        Perform example inventory collection.
        
        This example shows how to properly add data to inventory.
        """
        inventory = params.get('inventory')
        logger = params.get('logger')
        no_category = params.get('no_category', {})
        
        # Check if our category is disabled
        if no_category.get('hardware'):
            if logger:
                logger.debug("Example module: hardware category disabled")
            return
        
        if logger:
            logger.debug("Example module: Collecting hardware information")
        
        # Example: Add hardware information to inventory
        if inventory:
            # This is how you'd add data to the inventory object
            # The actual method calls depend on the Inventory class implementation
            pass


# Module configuration helper functions
def get_module_dependencies(module_class: type) -> Dict[str, List[str]]:
    """
    Get dependency configuration for a module.
    
    Args:
        module_class: Module class to inspect
        
    Returns:
        Dictionary with dependency lists
    """
    return {
        'runAfter': getattr(module_class, 'runAfter', []),
        'runAfterIfEnabled': getattr(module_class, 'runAfterIfEnabled', []),
        'runMeIfTheseChecksFailed': getattr(module_class, 'runMeIfTheseChecksFailed', [])
    }


def has_category(module_class: type) -> bool:
    """
    Check if module defines a category.
    
    Args:
        module_class: Module class to check
        
    Returns:
        True if module has a non-empty category
    """
    if hasattr(module_class, 'category'):
        category = module_class.category()
        return bool(category)
    return False


def check_dependencies_met(module_class: type, 
                          enabled_modules: List[str]) -> tuple[bool, str]:
    """
    Check if module dependencies are met.
    
    Args:
        module_class: Module class to check
        enabled_modules: List of enabled module names
        
    Returns:
        Tuple of (dependencies_met, reason)
    """
    deps = get_module_dependencies(module_class)
    
    # Check hard dependencies (runAfter)
    for required in deps['runAfter']:
        if required not in enabled_modules:
            return False, f"Required module {required} not enabled"
    
    # Check exclusion list (runMeIfTheseChecksFailed)
    for blocker in deps['runMeIfTheseChecksFailed']:
        if blocker in enabled_modules:
            return False, f"Blocked by enabled module {blocker}"
    
    return True, "All dependencies met"


if __name__ == "__main__":
    # Example usage and testing
    print("=== GLPI Inventory Module Base Class ===\n")
    
    # Test base class
    print("Base class category:", InventoryModule.category())
    print("Base class isEnabled:", InventoryModule.isEnabled())
    
    # Test example module
    print("\n=== Example Module ===")
    print("Category:", ExampleInventoryModule.category())
    print("Dependencies:", get_module_dependencies(ExampleInventoryModule))
    print("Has category:", has_category(ExampleInventoryModule))
    
    # Test dependency checking
    enabled = [
        'GLPI::Agent::Task::Inventory::Generic::Dmidecode',
        'GLPI::Agent::Task::Inventory::Generic::CPU'
    ]
    met, reason = check_dependencies_met(ExampleInventoryModule, enabled)
    print(f"Dependencies met: {met} ({reason})")
    
    # Test with mock parameters
    print("\n=== Testing with mock parameters ===")
    
    class MockLogger:
        def debug(self, msg): print(f"[DEBUG] {msg}")
        def debug2(self, msg): print(f"[DEBUG2] {msg}")
    
    is_enabled = ExampleInventoryModule.isEnabled(
        logger=MockLogger(),
        datadir="/usr/share/glpi-agent"
    )
    print(f"Example module enabled: {is_enabled}")