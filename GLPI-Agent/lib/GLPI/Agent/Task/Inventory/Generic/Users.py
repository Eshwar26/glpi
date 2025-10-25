# glpi_agent/task/inventory/generic/users.py

import platform

from glpi_agent.task.inventory.module import InventoryModule
from glpi_agent.tools import can_run, can_read, get_all_lines


class Users(InventoryModule):
    """Generic Users inventory module."""
    
    @staticmethod
    def other_categories():
        return ['local_user', 'local_group']
    
    @staticmethod
    def category():
        return "user"
    
    def is_enabled(self, **params):
        # Not working under win32
        if platform.system() == 'Windows':
            return False
        
        return (can_run('who') or 
                can_run('last') or 
                can_read('/etc/passwd'))
    
    def do_inventory(self, **params):
        inventory = params.get('inventory')
        logger = params.get('logger')
        no_category = params.get('no_category', {})
        
        users = {}
        
        if not no_category.get('local_user'):
            for user in self._get_local_users(logger=logger):
                # record user -> primary group relationship
                gid = user.pop('gid', None)
                if gid:
                    if gid not in users:
                        users[gid] = []
                    users[gid].append(user['LOGIN'])
                
                inventory.add_entry(
                    section='LOCAL_USERS',
                    entry=user
                )
        
        if not no_category.get('local_group'):
            for group in self._get_local_groups(logger=logger):
                # add users having this group as primary group, if any
                gid = group['ID']
                if gid in users:
                    if 'MEMBER' not in group:
                        group['MEMBER'] = []
                    group['MEMBER'].extend(users[gid])
                
                inventory.add_entry(
                    section='LOCAL_GROUPS',
                    entry=group
                )
        
        for user in self._get_logged_users(logger=logger):
            inventory.add_entry(
                section='USERS',
                entry=user
            )
        
        last = self._get_last_user(logger=logger)
        if last:
            inventory.set_hardware(last)
    
    def _get_local_users(self, **params):
        params.setdefault('file', '/etc/passwd')
        
        lines = get_all_lines(**params)
        if not lines:
            return []
        
        users = []
        
        for line in lines:
            if line.startswith('#'):
                continue
            if line.startswith(('+', '-')):  # old format for external inclusion, see #2460
                continue
            
            parts = line.split(':')
            if len(parts) < 7:
                continue
            
            login, _, uid, gid, gecos, home, shell = parts[:7]
            
            users.append({
                'LOGIN': login,
                'ID': uid,
                'gid': gid,
                'NAME': gecos,
                'HOME': home,
                'SHELL': shell
            })
        
        return users
    
    def _get_local_groups(self, **params):
        params.setdefault('file', '/etc/group')
        
        lines = get_all_lines(**params)
        if not lines:
            return []
        
        groups = []
        
        for line in lines:
            if line.startswith('#'):
                continue
            
            parts = line.split(':')
            if len(parts) < 4:
                continue
            
            name, _, gid, members = parts[:4]
            
            # prevent warning for malformed group file (#2384)
            if not members:
                continue
            
            member_list = members.split(',') if members else []
            
            groups.append({
                'ID': gid,
                'NAME': name,
                'MEMBER': member_list,
            })
        
        return groups
    
    def _get_logged_users(self, **params):
        params.setdefault('command', 'who')
        
        lines = get_all_lines(**params)
        if not lines:
            return []
        
        users = []
        seen = set()
        
        for line in lines:
            import re
            match = re.match(r'^(\S+)', line)
            if not match:
                continue
            
            username = match.group(1)
            if username in seen:
                continue
            
            seen.add(username)
            users.append({'LOGIN': username})
        
        return users
    
    def _get_last_user(self, **params):
        params.setdefault('command', 'last -w')
        
        lastuser = None
        lastlogged = None
        
        lines = get_all_lines(**params)
        if not lines:
            params['command'] = 'last'
            lines = get_all_lines(**params)
            if not lines:
                return None
        
        for last in lines:
            if last.startswith(('reboot', 'shutdown')):
                continue
            
            last_parts = last.split()
            if not last_parts:
                continue
            
            lastuser = last_parts.pop(0)
            if not lastuser:
                continue
            
            # Found time on column starting as week day
            import re
            while len(last_parts) > 3 and not re.match(r'^(mon|tue|wed|thu|fri|sat|sun)', last_parts[0], re.IGNORECASE):
                last_parts.pop(0)
            
            lastlogged = ' '.join(last_parts[0:4]) if len(last_parts) > 3 else None
            break
        
        if not lastuser:
            return None
        
        return {
            'LASTLOGGEDUSER': lastuser,
            'DATELASTLOGGEDUSER': lastlogged
        }