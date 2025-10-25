# glpi_agent/task/inventory/generic/printers.py

import platform

from glpi_agent.task.inventory.module import InventoryModule
from glpi_agent.tools import remote as remote_tools


class Printers(InventoryModule):
    """Generic Printers inventory module."""
    
    @staticmethod
    def category():
        return "printer"
    
    def is_enabled(self, **params):
        # we use system profiler on MacOS
        if platform.system() == 'Darwin':
            return False
        
        # we use WMI on Windows
        if platform.system() == 'Windows':
            return False
        
        logger = params.get('logger')
        remote = params.get('remote')
        
        # Printers inventory only supported remotely with Net::CUPS equivalent
        if remote:
            if not hasattr(remote_tools, 'mode') or not remote_tools.mode('perl'):
                if logger:
                    logger.debug(
                        "printers inventory not supported remotely without perl mode enabled"
                    )
                return False
            
            if not hasattr(remote_tools, 'remote_perl_module') or not remote_tools.remote_perl_module('Net::CUPS'):
                if logger:
                    logger.debug(
                        "printers inventory not supported remotely without Net::CUPS Perl module on remote"
                    )
                return False
            
            if not remote_tools.remote_perl_module('Net::CUPS', "0.60"):
                if logger:
                    logger.debug(
                        "Net::CUPS Perl remote module too old (required at least: 0.60), unable to retrieve printers"
                    )
                return False
            
            return True
        
        # Check for pycups module (Python equivalent of Net::CUPS)
        try:
            import cups
            # Check if version is sufficient (pycups doesn't have __version__ in older versions)
            return True
        except ImportError:
            if logger:
                logger.debug(
                    "cups Python module not available, unable to retrieve printers"
                )
            return False
    
    def do_inventory(self, **params):
        inventory = params.get('inventory')
        remote = inventory.get_remote()
        
        # We should handle remote case
        if remote:
            if hasattr(remote_tools, 'remote_get_printers'):
                for printer in remote_tools.remote_get_printers():
                    inventory.add_entry(
                        section='PRINTERS',
                        entry=printer
                    )
            return
        
        try:
            import cups
        except ImportError:
            return
        
        conn = cups.Connection()
        printers = conn.getPrinters()
        
        for printer_name, printer_attrs in printers.items():
            uri = printer_attrs.get('device-uri', '')
            
            # Parse options from URI
            opts_str = ''
            if '?' in uri:
                opts_str = uri.split('?', 1)[1]
            
            opts = opts_str.split('&') if opts_str else []
            
            printer_entry = {
                'NAME': printer_name,
                'PORT': uri,
                'DESCRIPTION': printer_attrs.get('printer-info', ''),
                'DRIVER': printer_attrs.get('printer-make-and-model', ''),
            }
            
            # Extract serial from options
            serial = None
            for opt in opts:
                if opt.startswith('serial='):
                    serial = opt.split('=', 1)[1]
                    break
            
            if not serial:
                for opt in opts:
                    if opt.startswith('uuid='):
                        serial = opt.split('=', 1)[1]
                        break
            
            if serial:
                printer_entry['SERIAL'] = serial
            
            inventory.add_entry(
                section='PRINTERS',
                entry=printer_entry
            )