"""
GLPI Agent Task Inventory MacOS AntiVirus Module

This is a stub module that serves as a parent for specific antivirus
detection modules in the AntiVirus subdirectory.
"""


class AntiVirus:
    """MacOS AntiVirus inventory module (stub)."""
    
    @staticmethod
    def category():
        """Return the category for this inventory module."""
        return "antivirus"
    
    def is_enabled(self, **params):
        """
        Check if this module can run on the current system.
        
        Returns:
            bool: Always True for macOS systems.
        """
        return True
    
    def do_inventory(self, **params):
        """
        Perform the antivirus inventory.
        
        This is a stub method. Actual antivirus detection is performed
        by specific modules in the AntiVirus subdirectory (Cortex, CrowdStrike,
        Defender, SentinelOne).
        
        Args:
            **params: Keyword arguments including:
                - inventory: The inventory object to add entries to
                - logger: Optional logger object for logging
        """
        pass

