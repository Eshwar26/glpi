import os
import glob
import importlib.util
import logging

# Constants (extracted from SNMPv2-MIB)
SYS_OR_ID = '.1.3.6.1.2.1.1.9.1.2'

available_mib_support = None


class MibSupportManager:
    def __init__(self, device=None, sysobjectid=None, logger=None, **params):
        if not device:
            return

        self.logger = logger or getattr(device, 'logger', None) or logging.getLogger(__name__)
        sysorid = device.walk(SYS_OR_ID)
        self._SUPPORT = {}

        global available_mib_support
        if not available_mib_support:
            preload(**params)

        sysorid_mib_support = {}

        for mib_support in available_mib_support:
            mibname = mib_support.get('name')
            module_name = mib_support.get('module')
            if not (mibname and module_name):
                continue

            # sysObjectID match
            if mib_support.get('sysobjectid') and sysobjectid:
                if mib_support['sysobjectid'].search(sysobjectid):
                    self.logger.debug(f"sysobjectID match: {mibname} MIB support enabled")
                    module = mib_support['module_ref']
                    self._SUPPORT[module] = module(device=device, mibsupport=mibname)
                    continue

            # Private OID match
            private_oid = mib_support.get('privateoid')
            if private_oid:
                if device.get(private_oid) is not None:
                    self.logger.debug(f"PrivateOID match: {mibname} MIB support enabled")
                    module = mib_support['module_ref']
                    self._SUPPORT[module] = module(device=device)
                    continue

            # sysORID mapping
            miboid = mib_support.get('oid')
            if miboid:
                sysorid_mib_support[miboid] = mib_support

        # Match sysORIDs
        for mibindex, miboid in sorted(sysorid.items()):
            supported = sysorid_mib_support.get(miboid)
            if not supported:
                continue
            mibname = supported.get('name')
            module = supported.get('module_ref')
            self.logger.debug(f"sysorid: {mibname} MIB support enabled")
            self._SUPPORT[module] = module(device=device, mibsupport=mibname)

        # Sort modules by priority
        supported = sorted(
            filter(None, self._SUPPORT.values()),
            key=lambda m: m.priority()
        )
        self._SUPPORT = supported

    def get_method(self, method_name):
        if not method_name:
            return None
        for mibsupport in self._SUPPORT:
            if not mibsupport:
                continue
            value = getattr(mibsupport, method_name, lambda: None)()
            if value is not None:
                return value
        return None

    def run(self):
        for mibsupport in self._SUPPORT:
            if mibsupport:
                mibsupport.run()


def preload(**params):
    """Dynamically load MIB support submodules."""
    global available_mib_support
    if available_mib_support:
        return

    logger = params.get('logger', logging.getLogger(__name__))

    # Locate submodules relative to this file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    submodules_path = os.path.join(current_dir)
    available_mib_support = []

    for file_path in glob.glob(os.path.join(submodules_path, "*.py")):
        filename = os.path.basename(file_path)
        if filename == os.path.basename(__file__):
            continue

        module_name = f"{__name__}.{filename[:-3]}"
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception as e:
            logger.debug(f"{module_name} import error: {e}")
            continue

        # Initialize module via configure()
        if hasattr(module, "configure"):
            module.configure(
                logger=params.get('logger'),
                config=params.get('config')
            )

        supported_mibs = getattr(module, "mibSupport", None)
        if supported_mibs and isinstance(supported_mibs, list):
            for mib_support in supported_mibs:
                mib_support["module"] = module_name
                mib_support["module_ref"] = getattr(module, module.__name__.split('.')[-1], None)
                available_mib_support.append(mib_support)

    if not available_mib_support:
        raise RuntimeError("No MIB support module loaded")
