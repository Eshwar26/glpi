#!/usr/bin/env python3
"""
GLPI Agent Task Inventory Generic Databases MongoDB - Python Implementation
"""

import json
import os
import re
import tempfile
import time
from typing import Any, List, Optional

from GLPI.Agent.Task.Inventory.Module import InventoryModule
from GLPI.Agent.Tools import can_run, get_all_lines, get_last_line, get_canonical_size
from GLPI.Agent.Inventory.DatabaseService import DatabaseService


class MongoDB(InventoryModule):
    """MongoDB database inventory module."""
    
    @staticmethod
    def isEnabled(**params: Any) -> bool:
        """Check if module should be enabled."""
        return can_run('mongo') or can_run('mongosh')
    
    @staticmethod
    def doInventory(**params: Any) -> None:
        """Perform inventory collection."""
        inventory = params.get('inventory')
        
        # Try to retrieve credentials
        from GLPI.Agent.Task.Inventory.Generic.Databases import get_credentials
        credentials = get_credentials(params, "mongodb")
        params['credentials'] = credentials
        
        dbservices = MongoDB._get_database_service(**params)
        
        for dbs in dbservices:
            if inventory:
                inventory.add_entry(
                    section='DATABASES_SERVICES',
                    entry=dbs.entry()
                )
    
    @staticmethod
    def _get_database_service(**params) -> List[DatabaseService]:
        """Get MongoDB database service information."""
        credentials = params.pop('credentials', None)
        if not credentials or not isinstance(credentials, list):
            return []
        
        dbs_list = []
        logger = params.get('logger')
        
        # Needed for tests
        if 'mongosh' not in params:
            params['mongosh'] = can_run('mongosh')
        
        for credential in credentials:
            from GLPI.Agent.Task.Inventory.Generic.Databases import trying_credentials
            trying_credentials(logger, credential)
            
            rcfile = MongoDB._mongo_rc_file(credential)
            if rcfile:
                params['rcfile'] = rcfile.name
            
            # Keep port as we need it to set --port option
            if credential.get('port'):
                params['port'] = credential['port']
            
            name, manufacturer = 'MongoDB', 'MongoDB'
            version = MongoDB._run_js(
                sql='db.version()',
                script="try { print(db.version()) } catch(e) { print('ERR('+e.codeName+'): <'+e.errmsg+'>') }",
                **params
            )
            if not version:
                continue
            
            if not re.match(r'^\d', version):
                if logger:
                    logger.error(f"Connection failure on {MongoDB._connect_url(credential)}, {version}")
                continue
            
            dbs_size = 0
            lastbootmilli = MongoDB._run_js(
                sql='ISODate().getTime()-db.serverStatus().uptimeMillis',
                script=(
                    "t = ISODate().getTime();"
                    "try { s = db.serverStatus({ repl: 0,  metrics: 0, locks: 0 }) } "
                    "catch(e) { s = e } "
                    "if (s.ok) { print(t-s.uptimeMillis) } "
                    "else { print('ERR:('+s.codeName+'): '+s.errmsg) }"
                ),
                **params
            )
            if not lastbootmilli:
                continue
            
            lastboot = None
            if not re.match(r'^\d+$', lastbootmilli):
                if logger:
                    logger.error(f"Failed to get last mongodb boot time, {lastbootmilli}")
            else:
                lastboot = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(int(lastbootmilli) // 1000))
            
            dbs = DatabaseService(
                type='mongodb',
                name=name,
                version=version,
                manufacturer=manufacturer,
                port=credential.get('port', 27017),
                is_active=True,
                last_boot_date=lastboot,
            )
            
            databases_output = MongoDB._run_js(
                sql='db.adminCommand( { listDatabases: 1 } ).databases',
                script=(
                    "try { l = db.adminCommand( { listDatabases: 1 } ) } "
                    "catch(e) { l = e } "
                    f"if (l.ok) {{ print({'EJSON.stringify' if params.get('mongosh') else 'tojson'}(l.databases)) }} "
                    "else { print('ERR('+l.codeName+'): '+l.errmsg) }"
                ),
                array=True,
                **params
            )
            if not databases_output:
                continue
            
            databases_str = ''.join(databases_output)
            databases = []
            
            if databases_str.startswith('ERR'):
                if logger:
                    logger.error(f"Failed to get database list, {databases_str}")
            else:
                # Cleanup any "Implicit session header"
                databases_str = re.sub(r'^Implicit\s+session:\s+session\s+\{[^}]+\}\s*', '', databases_str, flags=re.VERBOSE)
                try:
                    parsed = json.loads(databases_str)
                    databases = [db for db in parsed if isinstance(db, dict)]
                except json.JSONDecodeError as e:
                    if logger:
                        error_msg = f"Can't decode database list: {databases_str}"
                        if databases_str.startswith('['):
                            error_msg += f"\n{e}"
                        logger.error(error_msg)
            
            for dbinfo in databases:
                db = dbinfo.get('name')
                if not db:
                    continue
                size_val = dbinfo.get('sizeOnDisk')
                if not size_val:
                    continue
                
                size = None
                if size_val:
                    dbs_size += size_val
                    size = get_canonical_size(f"{size_val} bytes", 1024)
                
                ping = MongoDB._run_js(
                    sql=f"db.getSiblingDB('{db}').runCommand({{'ping': 1}}).ok",
                    script=f"try {{ print(db.getSiblingDB('{db}').runCommand({{'ping': 1}}).ok) }} catch(e) {{ print('ERR('+e.codeName+'): '+e.errmsg) }}",
                    **params
                )
                status = False
                if not ping or not re.match(r'^\d+$', ping):
                    if logger:
                        logger.error(f"Failed to get {db} database status, {ping or 'request failure'}")
                else:
                    status = bool(int(ping))
                
                dbs.add_database(
                    name=db,
                    size=size,
                    is_active=status,
                )
            
            dbs.size(get_canonical_size(f"{dbs_size} bytes", 1024))
            
            dbs_list.append(dbs)
            
            # Always forget rcfile and port
            if 'rcfile' in params:
                del params['rcfile']
            if 'port' in params:
                del params['port']
        
        return dbs_list
    
    @staticmethod
    def _run_js(**params) -> Optional[Any]:
        """Execute JavaScript command via mongo/mongosh."""
        sql = params.pop('sql', None)
        script = params.pop('script', None)
        if not sql or not script:
            return None
        
        array = params.pop('array', False)
        rcfile = params.pop('rcfile', None)
        
        command = 'mongo'
        if params.get('mongosh'):
            command += 'sh'
        command += ' --quiet'
        if rcfile:
            command += f' --nodb --norc {rcfile}'
        
        # Create temporary JavaScript file
        fh = tempfile.NamedTemporaryFile(
            mode='w',
            prefix='mongocmd-',
            suffix='.js',
            delete=False
        )
        
        # Mongosh must be instructed to output JSON like mongo does before
        logger = params.get('logger')
        if logger:
            logger.debug(f"Requesting: {sql}")
        fh.write(script)
        fh.close()
        command += f' {fh.name}'
        
        # Support for unittests
        if params.get('file'):
            sql_clean = re.sub(r'[ .]+', '-', sql)
            sql_clean = re.sub(r'[^-_0-9A-Za-z]', '', sql_clean)
            sql_clean = re.sub(r'[-][-]+', '-', sql_clean)
            file_path = f"{params['file']}-{sql_clean.lower()}"
            if not params.get('istest'):
                import sys
                print(f"\nGenerating {file_path} for new MongoDB test case...", file=sys.stderr)
                os.system(f"{command} >{file_path}")
            params['file'] = file_path
        else:
            params['command'] = command
        
        try:
            if array:
                lines = get_all_lines(**params)
                # Filter out MongoDB startup messages
                return [
                    line.strip() for line in lines
                    if not re.match(r'^(loading file|connecting to|MongoDB server version):', line)
                ] if lines else []
            else:
                return get_last_line(**params)
        finally:
            # Cleanup temp file
            try:
                os.unlink(fh.name)
            except OSError:
                pass
    
    @staticmethod
    def _connect_url(credential: dict) -> str:
        """Build MongoDB connection URL."""
        if credential.get('socket'):
            return credential['socket']
        
        conn = credential.get('host', 'localhost')
        conn += f":{credential.get('port', 27017)}"
        
        # Always default to connect on "admin" database
        conn += '/admin'
        
        return conn
    
    @staticmethod
    def _mongo_rc_file(credential: dict) -> Optional[tempfile._TemporaryFileWrapper]:
        """Create temporary MongoDB RC file."""
        if not credential.get('type'):
            return None
        
        if credential['type'] == 'login_password':
            fh = tempfile.NamedTemporaryFile(
                mode='w',
                prefix='mongorc-',
                suffix='.js',
                delete=False
            )
            
            conn = MongoDB._connect_url(credential)
            if credential.get('login'):
                conn += f"','{credential['login']}"
                if credential.get('password'):
                    password = credential['password'].replace("'", "\\'")
                    conn += f"','{password}"
            
            fh.write(f"try {{ db = connect('{conn}') }}\n")
            fh.write("catch(e) { print('ERR('+e.codeName+'): '+e.errmsg); exit(1) }\n")
            fh.close()
            
            return fh
        
        return None
