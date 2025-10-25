# glpi_agent/task/inventory/generic/ssh.py

from glpi_agent.task.inventory.module import InventoryModule
from glpi_agent.tools import can_run, can_read, get_all_lines


class SSH(InventoryModule):
    """Generic SSH inventory module."""
    
    @staticmethod
    def category():
        return "os"
    
    def is_enabled(self, **params):
        return can_run('ssh-keyscan')
    
    def do_inventory(self, **params):
        inventory = params.get('inventory')
        
        port = None
        command = "ssh-keyscan"
        
        if can_read('/etc/ssh/sshd_config'):
            for line in get_all_lines(file='/etc/ssh/sshd_config'):
                import re
                match = re.match(r'^Port\s+(\d+)', line)
                if match:
                    port = match.group(1)
                    break
        
        if port:
            command += f" -p {port}"
        

        command += ' -T 1 127.0.0.1'
        
        lines = get_all_lines(command=command, **params)
        
        # Extract ssh keys: lines starting with non-# and containing 'ssh'
        ssh_keys = []
        for line in lines:
            if line.startswith('#'):
                continue
            import re
            match = re.match(r'^\S+\s(ssh.*)', line)
            if match:
                ssh_keys.append(match.group(1))
        
        ssh_keys.sort()
        
        if ssh_keys:
            inventory.set_operating_system({
                'SSH_KEY': ssh_keys[0]
            })