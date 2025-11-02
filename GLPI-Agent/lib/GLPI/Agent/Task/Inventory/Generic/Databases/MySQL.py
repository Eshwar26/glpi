#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Generic Databases MySQL - Python Implementation
"""

import os
import re
import tempfile
from typing import Any, List, Optional

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_all_lines, get_canonical_size
from GLPI.Agent.Inventory.DatabaseService import DatabaseService


class MySQL(InventoryModule):
    """MySQL/MariaDB database inventory module."""
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_run('mysql')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        
        # Try to retrieve credentials
        from GLPI.Agent.Task.Inventory.Generic.Databases import get_credentials
        credentials = get_credentials(params, "mysql")
        params['credentials'] = credentials
        
        dbservices = MySQL._get_database_service(**params)
        
        for dbs in dbservices:
            if inventory:
                inventory.add_entry(
                    section='DATABASES_SERVICES',
                    entry=dbs.entry()
                )
    
    @staticmethod
    def _get_database_service(**params) -> List[DatabaseService]:
        """Get MySQL database service information."""
        credentials = params.pop('credentials', None)
        if not credentials or not isinstance(credentials, list):
            return []
        
        dbs_list = []
        
        for credential in credentials:
            from GLPI.Agent.Task.Inventory.Generic.Databases import trying_credentials
            trying_credentials(params.get('logger'), credential)
            
            # Be sure to forget previous credential option between loops
            if 'extra' in params:
                del params['extra']
            
            extra_file = MySQL._mysql_options_file(credential)
            if extra_file:
                params['extra'] = f" --defaults-extra-file={extra_file.name}"
            
            name, manufacturer = 'MySQL', 'Oracle'
            version = MySQL._run_sql(
                sql="SHOW VARIABLES LIKE 'version'",
                **params
            )
            if not version:
                continue
            
            version = re.sub(r'^version\s*', '', version)
            if re.search(r'mariadb', version, re.IGNORECASE):
                name, manufacturer = 'MariaDB', 'MariaDB'
                version = re.sub(r'-mariadb', '', version, flags=re.IGNORECASE)
            
            dbs_size = 0
            lastboot = MySQL._date(MySQL._run_sql(
                sql="SELECT DATE_SUB(now(), INTERVAL variable_value SECOND) from information_schema.global_status where variable_name='Uptime'",
                **params
            ))
            if not lastboot:
                lastboot = MySQL._date(MySQL._run_sql(
                    sql="SELECT DATE_SUB(now(), INTERVAL variable_value SECOND) from performance_schema.global_status where variable_name='Uptime'",
                    **params
                ))
            
            dbs = DatabaseService(
                type='mysql',
                name=name,
                version=version,
                manufacturer=manufacturer,
                port=credential.get('port', 3306),
                is_active=True,
                last_boot_date=lastboot,
            )
            
            databases = MySQL._run_sql(
                sql='SHOW DATABASES',
                array=True,
                **params
            )
            
            for db in databases:
                size_str = MySQL._run_sql(
                    sql=f"SELECT sum(data_length+index_length) FROM information_schema.TABLES WHERE table_schema = '{db}'",
                    **params
                )
                size = None
                if size_str and re.match(r'^\d+$', size_str):
                    dbs_size += int(size_str)
                    size = get_canonical_size(f"{size_str} bytes", 1024)
                
                # Find creation date
                created = MySQL._date(MySQL._run_sql(
                    sql=f"SELECT MIN(create_time) FROM information_schema.TABLES WHERE table_schema = '{db}'",
                    **params
                ))
                
                # Find update date
                updated = MySQL._date(MySQL._run_sql(
                    sql=f"SELECT MAX(update_time) FROM information_schema.TABLES WHERE table_schema = '{db}'",
                    **params
                ))
                
                dbs.add_database(
                    name=db,
                    size=size,
                    is_active=True,
                    creation_date=created,
                    update_date=updated,
                )
            
            dbs.size(get_canonical_size(f"{dbs_size} bytes", 1024))
            
            dbs_list.append(dbs)
        
        return dbs_list
    
    @staticmethod
    def _date(date: Optional[str]) -> Optional[str]:
        """Parse date string."""
        if not date:
            return None
        match = re.match(r'^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', date)
        return match.group(1) if match else None
    
    @staticmethod
    def _run_sql(**params) -> Optional[Any]:
        """Execute SQL command via mysql."""
        sql = params.pop('sql', None)
        if not sql:
            return None
        
        array = params.pop('array', False)
        command = 'mysql'
        if params.get('extra'):
            command += params['extra']
        command += f' -q -sN -e "{sql}"'
        
        # Support for unittests
        if params.get('file'):
            sql_clean = re.sub(r'\s+', '-', sql)
            sql_clean = re.sub(r'[^-_0-9A-Za-z]', '', sql_clean)
            sql_clean = re.sub(r'[-][-]+', '-', sql_clean)
            file_path = f"{params['file']}-{sql_clean.lower()}"
            if not params.get('istest'):
                import sys
                print(f"\nGenerating {file_path} for new MySQL test case...", file=sys.stderr)
                os.system(f"{command} >{file_path}")
            params['file'] = file_path
        else:
            params['command'] = command
        
        if array:
            lines = get_all_lines(**params)
            return [line.strip() for line in lines] if lines else []
        else:
            result = get_all_lines(**params)
            if result:
                # Get first line
                result = result[0] if isinstance(result, list) else result
                return result.strip() if result else None
            return None
    
    @staticmethod
    def _mysql_options_file(credential: dict) -> Optional[tempfile._TemporaryFileWrapper]:
        """Create temporary MySQL options file."""
        if not credential.get('type'):
            return None
        
        if credential['type'] == 'login_password':
            fh = tempfile.NamedTemporaryFile(
                mode='w',
                prefix='my-',
                suffix='.cnf',
                delete=False
            )
            
            fh.write('[client]\n')
            if credential.get('host'):
                fh.write(f"host = {credential['host']}\n")
            if credential.get('port'):
                fh.write(f"port = {credential['port']}\n")
            if credential.get('login'):
                fh.write(f"user = {credential['login']}\n")
            if credential.get('socket'):
                fh.write(f"socket = {credential['socket']}\n")
            if credential.get('password'):
                password = credential['password']
                if re.search(r'[#\'"]', password):
                    password = password.replace('"', '\\"')
                    password = f'"{password}"'
                fh.write(f"password = {password}\n")
            fh.write('connect-timeout = 30\n')
            fh.close()
            
            return fh
        
        return None
