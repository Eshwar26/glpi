from pathlib import Path
from typing import Optional

from ....logger import Logger
from ....storage import Storage
from .datastore import Datastore


class Maintenance:
    def __init__(self, **params):
        if not params.get('target'):
            raise ValueError('no target parameter')
        if not params.get('config'):
            raise ValueError('no config parameter')
        
        self.logger = params.get('logger') or Logger()
        self.config = params['config']
        self.target = params['target']
    
    def doMaintenance(self) -> int:
        """
        Cleanup the deploy datastore associated with the target.
        
        Returns:
            int: Number of remaining file parts (0 if fully cleaned)
        """
        # Get storage directory from target
        storage = self.target.getStorage()
        if not storage:
            return 0
        
        folder = storage.getDirectory()
        if not folder:
            return 0
        
        # Deploy data is stored in 'deploy' subdirectory
        deploy_folder = str(Path(folder) / 'deploy')
        
        if not Path(deploy_folder).is_dir():
            return 0
        
        # Create datastore instance for cleanup
        datastore = Datastore(
            config=self.config,
            path=deploy_folder,
            logger=self.logger
        )
        
        # Perform cleanup and return remaining file count
        return datastore.cleanUp()