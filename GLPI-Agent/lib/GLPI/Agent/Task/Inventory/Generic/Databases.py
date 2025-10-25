# glpi_agent/task/inventory/generic/databases.py

import platform

from glpi_agent.task.inventory.module import InventoryModule


class Databases(InventoryModule):
    """Generic Databases inventory module."""
    
    @staticmethod
    def category():
        return "database"
    
    def is_enabled(self, **params):
        # Database inventory can be done remotely by using appropriate credentials
        return not params.get('remote')
    
    def do_inventory(self, **params):
        pass
    
    @staticmethod
    def _credentials(hashref, usage):
        """Extract credentials for database access."""
        credentials = []
        params = hashref.pop('params', None)
        logger = hashref.get('logger')
        
        if params:
            for param in params:
                url = param.get('_glpi_url')
                if not url:
                    continue
                
                if not (param.get('params_id') and param.get('_glpi_client')):
                    continue
                
                if not (param.get('category') and param['category'] == "database"):
                    continue
                
                if not (param.get('use') and usage in param['use']):
                    continue
                
                try:
                    from glpi_agent.protocol.get_params import GetParams
                except ImportError:
                    if logger:
                        logger.error(f"Can't request credentials on {url}")
                    break
                
                inventory = hashref.get('inventory')
                device_id = inventory.get_device_id() if inventory else None
                
                getparams = GetParams(
                    deviceid=device_id,
                    params_id=param['params_id'],
                    use=usage
                )
                
                answer = param['_glpi_client'].send(
                    url=url,
                    message=getparams
                )
                
                if answer:
                    status = answer.get('status')
                    creds = answer.get('credentials')
                    
                    if status == 'ok' and creds:
                        if creds:
                            credentials.extend(creds)
                        else:
                            if logger:
                                logger.debug(f"No credential returned for credentials id {param['params_id']}")
                    elif status == 'error':
                        message = answer.get('message') or 'no error given'
                        if logger:
                            logger.debug(f"Credential request error: {message}")
                    else:
                        if logger:
                            logger.error("Database credential request not supported by server")
                else:
                    if logger:
                        logger.error(f"Got no credentials with credentials id {param['params_id']}")
        
        inventory = hashref.get('inventory')
        if inventory:
            inv_credentials = inventory.credentials()
            if isinstance(inv_credentials, list):
                filtered_creds = [
                    cred for cred in inv_credentials
                    if (not cred.get('category') or cred['category'] == "database")
                    and (not cred.get('use') or usage in cred['use'].lower())
                ]
                credentials.extend(filtered_creds)
        
        # When no credential is provided, leave module tries its default database access
        if not credentials:
            credentials.append({})
        
        hashref['credentials'] = credentials
    
    @staticmethod
    def trying_credentials(logger, credential):
        """Log credential attempt."""
        if not logger or not credential:
            return
        
        if credential.get('type'):
            params_id = credential.get('params_id')
            debugid = f" id {params_id}" if params_id else ""
            logger.debug2(f"Trying {credential['type']} credential type{debugid}")
        else:
            logger.debug2("Trying default credential")