import os
from typing import Dict, Any, List, Optional, Tuple

from ..base_task import BaseTask
from ..http.fusion_client import FusionClient
from ..storage import Storage
from .deploy.datastore import Datastore
from .deploy.file import File
from .deploy.job import Job
from .deploy.action_processor import ActionProcessor
from .deploy.maintenance import Maintenance
from ..event import Event
from .deploy.version import VERSION


class DeployTask(BaseTask):
    def __init__(self, **params):
        super().__init__(**params)
        self.client = None
        self._software_inventory_required = False
    
    def isEnabled(self) -> bool:
        """Check if deploy task is enabled for this target"""
        if not self.target.isType('server'):
            self.logger.debug("Deploy task only compatible with server target")
            return False
        return True
    
    def _validateAnswer(self, answer: Any) -> Tuple[bool, str]:
        """Validate server response format"""
        if answer is None:
            return False, "No answer from server."
        
        if not isinstance(answer, dict):
            return False, "Bad answer from server. Not a hash reference."
        
        if 'associatedFiles' not in answer:
            return False, "missing associatedFiles key"
        
        if not isinstance(answer['associatedFiles'], dict):
            return False, "associatedFiles should be a hash"
        
        # Validate associated files structure
        for k, file_data in answer['associatedFiles'].items():
            required_keys = ['mirrors', 'multiparts', 'name', 'p2p-retention-duration', 'p2p', 'uncompress']
            for key in required_keys:
                if key not in file_data:
                    return False, f"Missing key `{key}` in associatedFiles"
        
        # Validate jobs structure
        if 'jobs' not in answer:
            return False, "missing jobs key"
        
        if not isinstance(answer['jobs'], list):
            return False, "jobs should be an array"
        
        for job in answer['jobs']:
            required_keys = ['uuid', 'associatedFiles', 'actions', 'checks']
            for key in required_keys:
                if key not in job:
                    return False, f"Missing key `{key}` in jobs"
            
            if not isinstance(job['actions'], list):
                return False, "jobs/actions must be an array"
        
        return True, ""
    
    def processRemote(self, remote_url: str) -> int:
        """Process deployment jobs from remote server"""
        if not remote_url:
            self.logger.debug("No remote URL provided for processing")
            return 0
        
        # Get storage folder and create datastore
        folder = self.target.getStorage().getDirectory()
        datastore = Datastore(
            config=self.config,
            path=folder,
            logger=self.logger
        )
        datastore.cleanUp()
        
        job_list = []
        files = {}
        
        # Request jobs from server
        answer = self.client.send(
            url=remote_url,
            args={
                'action': 'getJobs',
                'machineid': self.deviceid,
                'version': VERSION
            }
        )
        
        if isinstance(answer, dict) and not answer:
            self.logger.debug("Nothing to do")
            return 0
        
        # Validate server response
        valid, msg = self._validateAnswer(answer)
        if not valid:
            self.logger.debug(f"bad JSON: {msg}")
            return 0
        
        # Create file objects for associated files
        for sha512, file_data in answer['associatedFiles'].items():
            files[sha512] = File(
                client=self.client,
                sha512=sha512,
                data=file_data,
                datastore=datastore,
                prolog=self.target.getMaxDelay(),
                logger=self.logger
            )
        
        # Create job objects
        for job_data in answer['jobs']:
            associated_files = []
            
            if job_data.get('associatedFiles'):
                for uuid in job_data['associatedFiles']:
                    if uuid not in files:
                        self.logger.error(f"unknown file: '{uuid}'. Not found in JSON answer!")
                        continue
                    associated_files.append(files[uuid])
                
                if len(associated_files) != len(job_data['associatedFiles']):
                    self.logger.error("Bad job definition in JSON answer!")
                    continue
            
            job = Job(
                remoteUrl=remote_url,
                client=self.client,
                machineid=self.deviceid,
                data=job_data,
                associatedFiles=associated_files,
                logger=self.logger
            )
            
            job_list.append(job)
            self.logger.debug2(f"Deploy job {job_data['uuid']} in the list")
        
        # Process each job
        for job in job_list:
            if not self._process_job(job, datastore):
                continue  # Skip to next job on failure
        
        self.logger.debug2("All deploy jobs processed")
        datastore.cleanUp()
        
        return 1 if job_list else 0
    
    def _process_job(self, job: Job, datastore: Datastore) -> bool:
        """Process a single deployment job"""
        self.logger.debug2(f"Processing job {job.uuid} from the list")
        
        # RECEIVED - Initial checking
        job.currentStep('checking')
        job.setStatus(msg='starting')
        self.logger.debug2(f"Checking job {job.uuid}...")
        
        # CHECKING - Run job-level checks
        if job.skip_on_check_failure():
            return False
        
        job.setStatus(status='ok', msg='all checks are ok')
        
        # USER INTERACTION - Before job
        if job.next_on_usercheck(type='before'):
            return False
        
        # DOWNLOADING - Download required files
        self.logger.debug2(f"Downloading for job {job.uuid}...")
        job.currentStep('downloading')
        job.setStatus(msg='downloading files')
        
        retry = 5
        workdir = datastore.createWorkDir(job.uuid)
        if not workdir:
            job.setStatus(status='ko', msg='failed to create work directory')
            return False
        
        # Download each associated file
        for file in job.associatedFiles:
            if not self._download_file(job, file, workdir, retry):
                return False  # Download failed, skip job
        
        job.setStatus(status='ok', msg='success')
        
        # USER INTERACTION - After download
        if job.next_on_usercheck(type='after_download'):
            return False
        
        # PREPARE - Prepare work directory
        self.logger.debug2(f"Preparation for job {job.uuid}...")
        job.currentStep('prepare')
        
        if not workdir.prepare():
            job.next_on_usercheck(type='after_failure')
            job.setStatus(status='ko', msg='failed to prepare work dir')
            return False
        
        job.setStatus(status='ok', msg='success')
        
        # Check if software inventory is required
        if job.requiresSoftwaresInventory():
            self._software_inventory_required = True
        
        # PROCESSING - Execute job actions
        if not self._process_actions(job, workdir):
            return False
        
        # USER INTERACTION - Final
        job.next_on_usercheck(type='after')
        
        self.logger.debug2(f"Finished job {job.uuid}...")
        
        # Clean up private files when job completes successfully
        for file in job.associatedFiles:
            file.cleanup_private()
        
        job.currentStep('end')
        job.setStatus(status='ok', msg='job successfully completed')
        
        return True
    
    def _download_file(self, job: Job, file: File, workdir, max_retry: int) -> bool:
        """Download a single file with retry logic"""
        retry = max_retry
        
        while True:
            # Check if file already exists
            if file.filePartsExists():
                job.setStatus(
                    file=file,
                    status='ok',
                    msg=f'{file.name} already downloaded'
                )
                file.resetPartFilePaths()
                workdir.addFile(file)
                return True
            
            # Attempt download
            job.setStatus(
                file=file,
                msg=f'fetching {file.name}'
            )
            
            try:
                file.download()
                file.resetPartFilePaths()
                
                if file.filePartsExists():
                    job.setStatus(
                        file=file,
                        status='ok',
                        msg=f'{file.name} downloaded'
                    )
                    workdir.addFile(file)
                    return True
            except Exception as e:
                self.logger.error(f"Download error for {file.name}: {e}")
            
            # Retry logic
            if retry > 0:
                retry -= 1
                job.setStatus(
                    file=file,
                    msg=f'retrying {file.name}'
                )
                continue
            else:
                # Give up after max retries
                job.next_on_usercheck(type='after_download_failure')
                job.setStatus(
                    file=file,
                    status='ko',
                    msg=f'{file.name} download failed'
                )
                return False
    
    def _process_actions(self, job: Job, workdir) -> bool:
        """Process all actions in a job"""
        self.logger.debug2(f"Processing for job {job.uuid}...")
        
        action_processor = ActionProcessor(
            logger=self.logger,
            workdir=workdir.path()
        )
        
        action_num = 0
        action_processor.starting()
        
        try:
            while True:
                action = job.getNextToProcess()
                if not action:
                    break
                
                # Extract action name and parameters
                if isinstance(action, dict) and len(action) == 1:
                    action_name, params = next(iter(action.items()))
                else:
                    self.logger.error(f"Invalid action format: {action}")
                    continue
                
                # Check action-level checks
                if (params and isinstance(params.get('checks'), list)):
                    self.logger.debug2(f"Processing action check for job {job.uuid}...")
                    job.currentStep('checking')
                    
                    if job.skip_on_check_failure(
                        checks=params['checks'],
                        level='action'
                    ):
                        continue
                
                job.currentStep('processing')
                
                # Execute action
                try:
                    ret = action_processor.process(action_name, params)
                except Exception as e:
                    ret = {
                        'status': False,
                        'msg': [str(e)]
                    }
                
                if not ret:
                    ret = {'status': False, 'msg': []}
                if 'msg' not in ret:
                    ret['msg'] = []
                
                name = params.get('name', f"action #{action_num + 1}")
                
                # Handle log line limits
                log_line_limit = params.get('logLineLimit', 10)
                if log_line_limit == 0 and ret.get('status'):
                    ret['msg'] = []
                elif log_line_limit > 0:
                    log_line_limit += 7  # Add header lines for cmd
                
                # Log action messages
                for i, line in enumerate(ret['msg']):
                    if not line:
                        continue
                    job.setStatus(
                        msg=f"{name}: {line}",
                        actionnum=action_num
                    )
                    if log_line_limit > 0:
                        log_line_limit -= 1
                        if log_line_limit <= 0:
                            break
                
                # Handle action failure
                if not ret.get('status'):
                    job.next_on_usercheck(type='after_failure')
                    job.setStatus(
                        status='ko',
                        actionnum=action_num,
                        msg=f"{name}, processing failure"
                    )
                    action_processor.failure()
                    return False
                
                job.setStatus(
                    status='ok',
                    actionnum=action_num,
                    msg=f"{name}, processing success"
                )
                
                action_num += 1
        
        finally:
            action_processor.done()
        
        return not action_processor.failed()
    
    def run(self) -> bool:
        """Main task execution method"""
        # Set locale for consistent command output
        os.environ['LC_ALL'] = 'C'
        os.environ['LANG'] = 'C'
        
        # Handle maintenance events
        event = self.resetEvent()
        if event:
            name = event.name()
            if name and event.maintenance():
                next_event = None
                target_id = self.target.id()
                self.logger.debug(f"Deploy task {name} event for {target_id} target")
                
                maintenance = Maintenance(
                    target=self.target,
                    config=self.config,
                    logger=self.logger
                )
                
                if maintenance.doMaintenance():
                    next_event = self.newEvent()
                    self.logger.debug(
                        f"Planning another {name} event for {target_id} target in {event.delay()}s"
                    )
                else:
                    self.logger.debug(f"No need to plan another {name} event for {target_id} target")
                
                self.resetEvent(next_event)
                return True
        
        # Initialize HTTP client
        self.client = FusionClient(
            logger=self.logger,
            config=self.config
        )
        
        # Get configuration from server
        global_remote_config = self.client.send(
            url=self.target.getUrl(),
            args={
                'action': 'getConfig',
                'machineid': self.deviceid,
                'task': {'Deploy': VERSION}
            }
        )
        
        target_id = self.target.id()
        
        if not global_remote_config:
            self.logger.info(f"Deploy task not supported by {target_id}")
            return False
        
        if not global_remote_config.get('schedule'):
            self.logger.info(f"No job schedule returned by {target_id}")
            return False
        
        if not isinstance(global_remote_config['schedule'], list):
            self.logger.info(f"Malformed schedule returned by {target_id}")
            return False
        
        if not global_remote_config['schedule']:
            self.logger.info("No Deploy job enabled or Deploy support disabled server side.")
            return False
        
        # Process scheduled deploy jobs
        run_jobs = 0
        for job_config in global_remote_config['schedule']:
            if job_config.get('task') == 'Deploy':
                run_jobs += self.processRemote(job_config['remote'])
        
        if not run_jobs:
            self.logger.info("No Deploy job found in server jobs list.")
            return False
        
        # Schedule maintenance event
        self.resetEvent(self.newEvent())
        
        # Schedule software inventory if required
        if self._software_inventory_required:
            self.addEvent(Event(
                name="software inventory",
                task="inventory",
                partial="yes",
                target=self.target.id(),
                delay=0
            ))
        
        return True
    
    def newEvent(self) -> Event:
        """Create new maintenance event"""
        return Event(
            name="storage maintenance",
            task="deploy",
            maintenance="yes",
            target=self.target.id(),
            delay=120
        )