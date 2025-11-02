#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Generic Databases MSSQL - Python Implementation
"""

import os
import platform
import re
from typing import Any, List, Optional

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_first_line, get_all_lines, get_canonical_size
from GLPI.Agent.Inventory.DatabaseService import DatabaseService


class MSSQL(InventoryModule):
    """Microsoft SQL Server database inventory module."""
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_run('sqlcmd') or can_run('/opt/mssql-tools/bin/sqlcmd')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        
        # Try to retrieve credentials
        from GLPI.Agent.Task.Inventory.Generic.Databases import get_credentials
        credentials = get_credentials(params, "mssql")
        params['credentials'] = credentials
        
        dbservices = MSSQL._get_database_service(**params)
        
        for dbs in dbservices:
            if inventory:
                inventory.add_entry(
                    section='DATABASES_SERVICES',
                    entry=dbs.entry()
                )
    
    @staticmethod
    def _get_database_service(**params) -> List[DatabaseService]:
        """Get MSSQL database service information."""
        credentials = params.pop('credentials', None)
        if not credentials or not isinstance(credentials, list):
            return []
        
        # Handle default credentials case
        if len(credentials) == 1 and not credentials[0]:
            # On Windows, we can discover instance names in registry
            if platform.system() == 'Windows':
                from GLPI.Agent.Tools.Win32 import get_registry_key
                instances = get_registry_key(
                    path='HKEY_LOCAL_MACHINE/SOFTWARE/Microsoft/Microsoft SQL Server/Instance Names/SQL'
                )
                if instances:
                    for key in instances.keys():
                        # Only consider valuename keys
                        match = re.match(r'^/(.+)$', key)
                        if not match:
                            continue
                        instance = match.group(1)
                        # Default credentials will still match MSSQLSERVER instance
                        if instance == 'MSSQLSERVER':
                            continue
                        credentials.append({
                            'type': '_discovered_instance',
                            'instance': instance,
                        })
            # Add SQLExpress default credential when trying default credential
            credentials.append({
                'type': 'login_password',
                'socket': 'localhost\\SQLExpress',
            })
        
        dbs_list = []
        
        # Support sqlcmd on linux with standard full path for command from mssql-tools package
        if 'sqlcmd' not in params:
            params['sqlcmd'] = '/opt/mssql-tools/bin/sqlcmd' if not can_run('sqlcmd') else 'sqlcmd'
        
        for credential in credentials:
            from GLPI.Agent.Task.Inventory.Generic.Databases import trying_credentials
            trying_credentials(params.get('logger'), credential)
            
            params['options'] = MSSQL._mssql_options(credential) or '-l 5'
            
            productversion = MSSQL._run_sql(
                sql="SELECT SERVERPROPERTY('productversion')",
                **params
            )
            if not productversion:
                continue
            
            name = MSSQL._run_sql(
                sql='SELECT @@servicename',
                **params
            )
            if not name:
                continue
            
            version = MSSQL._run_sql(
                sql='SELECT @@version',
                **params
            )
            if not version:
                continue
            
            match = re.match(
                r'^\s*(Microsoft)\s+SQL\s+Server\s+\d+',
                version,
                re.IGNORECASE | re.VERBOSE
            )
            if not match:
                continue
            manufacturer = match.group(1)
            
            dbs_size = 0
            starttime = MSSQL._run_sql(
                sql='SELECT sqlserver_start_time FROM sys.dm_os_sys_info',
                **params
            )
            if starttime:
                starttime = re.sub(r'\..*$', '', starttime)
            
            dbs = DatabaseService(
                type='mssql',
                name=name,
                version=productversion,
                manufacturer=manufacturer,
                port=credential.get('port', 1433),
                is_active=True,
                last_boot_date=starttime,
            )
            
            db_list = MSSQL._run_sql(
                sql='SELECT name,create_date,state FROM sys.databases',
                array=True,
                **params
            )
            
            for db in db_list:
                match = re.match(r'^(\S+);([^.]*)\.\d+;(\d+)$', db)
                if not match:
                    continue
                db_name, db_create, state = match.groups()
                
                size_output = MSSQL._run_sql(
                    sql=f'USE [{db_name}] ; EXEC sp_spaceused',
                    array=True,
                    **params
                )
                size = None
                if size_output:
                    size_line = size_output[0] if isinstance(size_output, list) else size_output
                    size_match = re.search(rf'^{re.escape(db_name)};([0-9.]+\s*\S+);', size_line)
                    if size_match:
                        size = get_canonical_size(size_match.group(1), 1024)
                        if size:
                            dbs_size += size
                
                # Find update date
                updated_output = MSSQL._run_sql(
                    sql=f'USE [{db_name}] ; SELECT TOP(1) modify_date FROM sys.objects ORDER BY modify_date DESC',
                    array=True,
                    **params
                )
                updated = None
                if updated_output:
                    updated_line = updated_output[0] if isinstance(updated_output, list) else updated_output
                    updated_match = re.match(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', updated_line)
                    if updated_match:
                        updated = updated_match.group(1)
                
                dbs.add_database(
                    name=db_name,
                    size=int(size) if size else None,
                    is_active=(int(state) == 0),
                    creation_date=db_create,
                    update_date=updated,
                )
            
            dbs.size(int(dbs_size))
            
            dbs_list.append(dbs)
        
        return dbs_list
    
    @staticmethod
    def _run_sql(**params) -> Optional[Any]:
        """Execute SQL command via sqlcmd."""
        sql = params.pop('sql', None)
        if not sql:
            return None
        
        array = params.pop('array', False)
        command = params.get('sqlcmd', 'sqlcmd')
        if params.get('options'):
            command += f" {params['options']}"
        command += f' -X1 -t 30 -K ReadOnly -r1 -W -h -1 -s ";" -Q "{sql}"'
        
        # Support for unittests
        if params.get('file'):
            sql_clean = re.sub(r'\s+', '-', sql)
            sql_clean = re.sub(r'[^-_0-9A-Za-z]', '', sql_clean)
            sql_clean = re.sub(r'[-][-]+', '-', sql_clean)
            file_path = f"{params['file']}-{sql_clean.lower()}"
            if not params.get('istest'):
                import sys
                print(f"\nGenerating {file_path} for new MSSQL test case...", file=sys.stderr)
                os.system(f"{command} >{file_path}")
            params['file'] = file_path
        else:
            params['command'] = command
        
        if array:
            lines = get_all_lines(**params)
            return [line.rstrip('\r\n') for line in lines] if lines else []
        else:
            result = get_first_line(**params)
            if result:
                return result.rstrip('\r\n')
            return None
    
    @staticmethod
    def _mssql_options(credential: dict) -> Optional[str]:
        """Build sqlcmd options from credential."""
        if not credential.get('type'):
            return None
        
        options = '-l 5'
        if credential['type'] == 'login_password':
            if credential.get('host'):
                options = '-l 30'
                options += f" -S {credential['host']}"
                if credential.get('port'):
                    options += f",{credential['port']}"
            if credential.get('login'):
                options += f" -U {credential['login']}"
            if not credential.get('host') and credential.get('socket'):
                options += f" -S {credential['socket']}"
            if credential.get('password'):
                password = credential['password'].replace('"', '\\"')
                options += f' -P "{password}"'
        elif credential['type'] == '_discovered_instance' and credential.get('instance'):
            options += f" -S .\\{credential['instance']}"
        
        return options
