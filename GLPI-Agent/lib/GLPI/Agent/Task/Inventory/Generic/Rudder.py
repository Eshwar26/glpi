# glpi_agent/task/inventory/generic/rudder.py

import platform
import os

from glpi_agent.task.inventory.module import InventoryModule
from glpi_agent.tools import can_read, get_first_line, get_all_lines, has_folder, has_file, Glob


class Rudder(InventoryModule):
    """Generic Rudder inventory module."""
    
    @staticmethod
    def category():
        return "rudder"
    
    def is_enabled(self, **params):
        return can_read(self.get_uuid_file())
    
    @staticmethod
    def get_uuid_file():
        if platform.system() == 'Windows':
            return 'C:\\Program Files\\Rudder\\etc\\uuid.hive'
        else:
            return '/opt/rudder/etc/uuid.hive'
    
    def do_inventory(self, **params):
        inventory = params.get('inventory')
        logger = params.get('logger')
        
        uuid_hive = self.get_uuid_file()
        
        # Get Rudder UUID
        uuid = get_first_line(logger=logger, file=uuid_hive)
        
        # Get all agents running on that machine
        agents = self._manage_agent(logger=logger)
        
        # Get machine hostname
        if platform.system() == 'Linux':
            command = 'hostname --fqdn'
        else:
            command = 'hostname'
        hostname = get_first_line(logger=logger, command=command)
        
        # Get server roles
        server_roles = self._list_server_roles()
        
        # Get agent capabilities
        agent_capabilities = self._list_agent_capabilities()
        
        rudder = {
            'HOSTNAME': hostname,
            'UUID': uuid,
            'AGENT': agents,
            'SERVER_ROLES': {'SERVER_ROLE': server_roles},
            'AGENT_CAPABILITIES': {'AGENT_CAPABILITY': agent_capabilities},
        }
        
        inventory.add_entry(section='RUDDER', entry=rudder)
    
    def _list_server_roles(self):
        if platform.system() == 'Windows':
            server_roles_dir = 'C:\\Program Files\\Rudder\\etc\\server-roles.d'
        else:
            server_roles_dir = '/opt/rudder/etc/server-roles.d'
        
        server_roles = []
        
        if has_folder(server_roles_dir):
            # List each file in the server-roles directory, each file name is a role
            for file in Glob(f"{server_roles_dir}/*"):
                server_roles.append(file)
        
        return server_roles
    
    def _list_agent_capabilities(self):
        if platform.system() == 'Windows':
            capabilities_file = 'C:\\Program Files\\Rudder\\etc\\agent-capabilities'
        else:
            capabilities_file = '/opt/rudder/etc/agent-capabilities'
        
        capabilities = []
        
        # List agent capabilities, one per line in the file
        for row in get_all_lines(capabilities_file):
            row = row.strip()
            capabilities.append(row)
        
        return capabilities
    
    def _manage_agent(self, **params):
        logger = params.get('logger')
        agents = []
        
        # Potential agent directory candidates
        agent_candidates = {
            '/var/rudder/cfengine-community': 'cfengine-community',
            '/var/rudder/cfengine-nova': 'cfengine-nova',
            'C:/Program Files/Cfengine': 'cfengine-nova',
        }
        
        for candidate, agent_type in agent_candidates.items():
            # Verify if the candidate is installed and configured
            if not has_file(f"{candidate}/policy_server.dat"):
                continue
            
            # Get a list of useful file paths to key Rudder components
            agent_name = agent_type
            server_hostname_file = f"{candidate}/policy_server.dat"
            uuid_file = f"{candidate}/rudder-server-uuid.txt"
            cfengine_key_file = f"{candidate}/ppkeys/localhost.pub"
            
            # get policy server hostname
            server_hostname = get_first_line(logger=logger, file=server_hostname_file)
            if server_hostname:
                server_hostname = server_hostname.strip()
            
            # Get the policy server UUID
            #
            # The default file is no longer /var/rudder/tmp/uuid.txt since the
            # change in http://www.rudder-project.org/redmine/issues/2443.
            # We gracefully fallback to the old default if the new file cannot
            # be found.
            if has_file(uuid_file):
                server_uuid = get_first_line(logger=logger, file=uuid_file)
            else:
                server_uuid = get_first_line(logger=logger, file="/var/rudder/tmp/uuid.txt")
            
            if server_uuid:
                server_uuid = server_uuid.strip()
            
            # get CFengine public key
            cfengine_key = get_all_lines(file=cfengine_key_file)
            
            # get owner name
            owner = get_first_line(logger=logger, command='whoami')
            
            # build agent from datas
            agent = {
                'AGENT_NAME': agent_name,
                'POLICY_SERVER_HOSTNAME': server_hostname,
                'CFENGINE_KEY': cfengine_key,
                'OWNER': owner,
                'POLICY_SERVER_UUID': server_uuid,
            }
            
            agents.append(agent)
        
        return agents