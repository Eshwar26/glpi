#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Generic Databases PostgreSQL - Python Implementation
"""

import os
import re
import tempfile
from typing import Any, List, Optional

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_first_line, get_all_lines, get_canonical_size, empty
from GLPI.Agent.Inventory.DatabaseService import DatabaseService


class PostgreSQL(InventoryModule):
    """PostgreSQL database inventory module."""
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_run('psql')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        
        # Try to retrieve credentials
        from GLPI.Agent.Task.Inventory.Generic.Databases import get_credentials
        credentials = get_credentials(params, "postgresql")
        params['credentials'] = credentials
        
        dbservices = PostgreSQL._get_database_service(**params)
        
        for dbs in dbservices:
            if inventory:
                inventory.add_entry(
                    section='DATABASES_SERVICES',
                    entry=dbs.entry()
                )
    
    @staticmethod
    def _get_database_service(**params) -> List[DatabaseService]:
        """Get PostgreSQL database service information."""
        credentials = params.pop('credentials', None)
        if not credentials or not isinstance(credentials, list):
            return []
        
        dbs_list = []
        
        # Cleanup PG environment
        if 'PGPASSFILE' in os.environ:
            del os.environ['PGPASSFILE']
        
        for credential in credentials:
            from GLPI.Agent.Task.Inventory.Generic.Databases import trying_credentials
            trying_credentials(params.get('logger'), credential)
            
            passfile = PostgreSQL._psql_pgpass_file(credential)
            if passfile:
                os.environ['PGPASSFILE'] = passfile.name
            
            if 'sudo' in params:
                del params['sudo']
            
            options = ""
            if not empty(credential.get('host')):
                options += f' -h "{credential["host"]}"'
            if credential.get('port') and re.match(r'^\d+$', str(credential['port'])):
                options += f' -p {credential["port"]}'
            if not empty(credential.get('login')):
                options += f' -U "{credential["login"]}"'
            
            params['options'] = options
            
            if not options:
                id_result = get_first_line(command='id -u')
                if id_result and id_result == '0':
                    params['sudo'] = 'su postgres -c "%s"'
                elif can_run('sudo'):
                    sudo_result = get_first_line(command='sudo -nu postgres echo true')
                    if sudo_result and sudo_result == 'true':
                        params['sudo'] = 'sudo -nu postgres %s'
            
            name, manufacturer = 'PostgreSQL', 'PostgreSQL'
            version = PostgreSQL._run_sql(
                sql='SHOW server_version',
                **params
            )
            if not version:
                continue
            
            dbs_size = 0
            lastboot_raw = PostgreSQL._run_sql(
                sql='SELECT pg_postmaster_start_time()',
                **params
            )
            lastboot = PostgreSQL._date(lastboot_raw)
            
            dbs = DatabaseService(
                type='postgresql',
                name=name,
                version=version,
                manufacturer=manufacturer,
                port=credential.get('port', 5432),
                is_active=True,
                last_boot_date=lastboot,
            )
            
            dbinfos = PostgreSQL._run_sql(
                sql='SELECT datname,oid FROM pg_database',
                array=True,
                **params
            )
            
            for dbinfo in dbinfos:
                parts = dbinfo.split(',')
                if len(parts) < 2:
                    continue
                db, oid = parts[0], parts[1]
                
                size_str = PostgreSQL._run_sql(
                    sql=f"SELECT pg_size_pretty(pg_database_size('{db}'))",
                    **params
                )
                size = None
                if size_str:
                    size = get_canonical_size(size_str, 1024)
                    if size:
                        dbs_size += size
                
                # Find creation date
                created_raw = PostgreSQL._run_sql(
                    sql=f"SELECT (pg_stat_file('base/{oid}/PG_VERSION')).modification FROM pg_database",
                    **params
                )
                created = PostgreSQL._date(created_raw)
                
                # Find update date
                updated_raw = PostgreSQL._run_sql(
                    sql=f"SELECT (pg_stat_file('base/{oid}')).modification FROM pg_database",
                    **params
                )
                updated = PostgreSQL._date(updated_raw)
                
                dbs.add_database(
                    name=db,
                    size=size,
                    is_active=True,
                    creation_date=created,
                    update_date=updated,
                )
            
            if dbs_size:
                dbs.size(dbs_size)
            
            dbs_list.append(dbs)
            
            # Cleanup PG environment
            if 'PGPASSFILE' in os.environ:
                del os.environ['PGPASSFILE']
        
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
        """Execute SQL command via psql."""
        sql = params.pop('sql', None)
        if not sql:
            return None
        
        array = params.pop('array', False)
        options = params.pop('options', '')
        command = f'psql{options}'
        command += f' -Anqtw -F, -c "{sql}" connect_timeout=30'
        
        if not options:
            sudo = params.pop('sudo', None)
            if sudo and sudo.startswith('su '):
                command = command.replace('"', '\\"')
            if sudo:
                command = sudo % command
        
        # Support for unittests
        if params.get('file'):
            sql_clean = re.sub(r'\s+', '-', sql)
            sql_clean = re.sub(r'[^-_0-9A-Za-z]', '', sql_clean)
            sql_clean = re.sub(r'[-][-]+', '-', sql_clean)
            file_path = f"{params['file']}-{sql_clean.lower()}"
            if not params.get('istest'):
                print(f"\nGenerating {file_path} for new PostgreSQL test case...", file=sys.stderr)
                os.system(f"{command} >{file_path}")
            params['file'] = file_path
        else:
            params['command'] = command
        
        if array:
            lines = get_all_lines(**params)
            return [line.strip() for line in lines] if lines else []
        else:
            result = get_first_line(**params)
            if result is None:
                return None
            return result.strip()
    
    @staticmethod
    def _psql_pgpass_file(credential: dict) -> Optional[tempfile._TemporaryFileWrapper]:
        """Create temporary pgpass file."""
        if not credential.get('type'):
            return None
        
        if credential['type'] == 'login_password' and credential.get('password'):
            fh = tempfile.NamedTemporaryFile(
                mode='w',
                prefix='pgpass-',
                suffix='.conf',
                delete=False
            )
            os.chmod(fh.name, 0o600)
            
            pgpass_line = ':'.join([
                credential.get('host', '*'),
                str(credential.get('port', '*')),
                '*',
                credential.get('login', '*'),
                credential['password']
            ])
            fh.write(pgpass_line + '\n')
            fh.close()
            
            # Return file object for caller to manage deletion
            return fh
        
        return None
