#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Linux Storages MegacliWithSmartctl - Python Implementation

Provides inventory of megaraid controllers using megacli and smartctl
"""

import os
import re
from typing import Any, Dict

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_first_match, get_all_lines, Glob
from GLPI.Agent.Tools.Linux import get_info_from_smartctl


class MegacliWithSmartctl(InventoryModule):
    """LSI Megaraid inventory using megacli and smartctl."""
    
    RE = re.compile(r'^([^:]+?)\s*:\s*(.*\S)')
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_run('megacli') and can_run('smartctl')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        
        count = get_first_match(
            command='megacli -adpCount',
            pattern=r'Controller Count: (\d+)'
        )
        if not count:
            return
        
        for adp in range(int(count)):
            adpinfo = MegacliWithSmartctl._get_adp_pci_info(adp=adp)
            block = MegacliWithSmartctl._adp_info_to_block(adpinfo)
            pdlist = MegacliWithSmartctl._get_pdlist(adp=adp)
            ldinfo = MegacliWithSmartctl._get_ldinfo(adp=adp)
            
            for disk_id, pd in pdlist.items():
                # JBOD and Non-RAID are processed by the parent module, skip
                diskgroup = pd.get('__diskgroup')
                firmware_state = pd.get('Firmware state', '')
                
                if 'JBOD' in firmware_state.upper():
                    continue
                
                if diskgroup is not None and diskgroup in ldinfo:
                    ld = ldinfo[diskgroup]
                    if (ld.get('Number Of Drives') == '1' and
                        ld.get('Name') and
                        re.search(r'Non\s*\-*RAID', ld['Name'], re.IGNORECASE)):
                        continue
                
                storage = get_info_from_smartctl(
                    device=f'/dev/{block}',
                    extra=f'-d megaraid,{disk_id}'
                )
                
                if inventory:
                    inventory.add_entry(
                        section='STORAGES',
                        entry=storage
                    )
    
    @staticmethod
    def _get_pdlist(**params) -> Dict[str, Dict[str, str]]:
        """Get physical drive list from megacli."""
        adp = params.get('adp')
        if adp is not None:
            params['command'] = f'megacli -pdlist -a{adp} -NoLog'
        
        pdlist = {}
        src = {}
        
        for line in get_all_lines(**params):
            match = MegacliWithSmartctl.RE.match(line)
            if not match:
                continue
            
            key, val = match.groups()
            
            if key == 'Enclosure Device ID':
                if 'Device Id' in src:
                    pdlist[src['Device Id']] = src
                src = {}
            elif key == "Drive's position":
                position_match = re.search(r'DiskGroup: (\d+), Span: (\d+), Arm: (\d+)', val)
                if position_match:
                    src['__diskgroup'], src['__span'], src['__arm'] = position_match.groups()
            
            src[key] = val
        
        if 'Device Id' in src:
            pdlist[src['Device Id']] = src
        
        return pdlist
    
    @staticmethod
    def _get_ldinfo(**params) -> Dict[int, Dict[str, str]]:
        """Get logical drive info from megacli."""
        adp = params.get('adp')
        if adp is not None:
            params['command'] = f'megacli -ldinfo -lAll -a{adp} -NoLog'
        
        ldinfo = {}
        n = -1
        
        for line in get_all_lines(**params):
            match = MegacliWithSmartctl.RE.match(line)
            if not match:
                continue
            
            key, val = match.groups()
            
            if key == 'Virtual Drive':
                vd_match = re.match(r'^\s*(\d+)', val)
                if vd_match:
                    n = int(vd_match.group(1))
            
            if n not in ldinfo:
                ldinfo[n] = {}
            ldinfo[n][key] = val
        
        return ldinfo
    
    @staticmethod
    def _get_adp_pci_info(**params) -> Dict[str, str]:
        """Get adapter PCI info from megacli."""
        adp = params.get('adp')
        if adp is not None:
            params['command'] = f'megacli -AdpGetPciInfo -a{adp} -NoLog'
        
        adpinfo = {}
        for line in get_all_lines(**params):
            match = MegacliWithSmartctl.RE.match(line)
            if match:
                adpinfo[match.group(1)] = match.group(2)
        
        return adpinfo
    
    @staticmethod
    def _adp_info_to_block(adpinfo: Dict[str, str]) -> str:
        """Convert adapter PCI info to block device name."""
        pciid = '0000:{:02s}:{:02s}.{:01s}'.format(
            adpinfo.get('Bus Number', '00'),
            adpinfo.get('Device Number', '00'),
            adpinfo.get('Function Number', '0')
        )
        
        blocks = Glob(f'/sys/bus/pci/devices/{pciid}/host*/target*/*/block/*')

    # return first block device name
        if blocks:
            return os.path.basename(blocks[0])
        return ''
