# konica_mib_support.py
# Converted from Perl (GLPI::Agent::SNMP::MibSupport::Konica)

from glpi_agent.tools import (
    get_canonical_string,
    get_canonical_mac_address,
    get_regexp_oid_match,
    hex2char,
)
class SNMPBase:
    def __init__(self, device=None):
        self.device = device

    def get(self, oid):
        """Method to get SNMP value for an OID"""
        # Implement SNMP GET logic here
        return None

    def walk(self, oid):
        """Method to walk SNMP OID tree"""
        # Implement SNMP WALK logic here
        return {}

ENTERPRISES = ".1.3.6.1.4.1"
KONICA = f"{ENTERPRISES}.18334"

# Konica MIB constants
KONICA_SYSOBJECT_ID = f"{KONICA}.1.1.1.2"
KONICA_MODEL = f"{KONICA}.1.1.1.1.6.2.1.0"
KONICA_PRINTER_COUNTERS = f"{KONICA}.1.1.1.5.7.2"

KONICA_TOTAL = f"{KONICA_PRINTER_COUNTERS}.1.1.0"
KONICA_RECTO_VERSO = f"{KONICA_PRINTER_COUNTERS}.1.3.0"
KONICA_BLACK_COPY = f"{KONICA_PRINTER_COUNTERS}.2.1.5.1.1"
KONICA_BLACK_PRINT = f"{KONICA_PRINTER_COUNTERS}.2.1.5.1.2"
KONICA_COLOR_COPY = f"{KONICA_PRINTER_COUNTERS}.2.1.5.2.1"
KONICA_COLOR_PRINT = f"{KONICA_PRINTER_COUNTERS}.2.1.5.2.2"
KONICA_SCANS = f"{KONICA_PRINTER_COUNTERS}.3.1.5.1"

KONICA_FIRMWARE = f"{KONICA}.1.1.1.5.5.1.1"
KONICA_FIRMWARE_NAME = f"{KONICA_FIRMWARE}.2"
KONICA_FIRMWARE_VERSION = f"{KONICA_FIRMWARE}.3"

MIB_SUPPORT = [
    {
        "name": "konica-printer",
        "sysobjectid": get_regexp_oid_match(KONICA_SYSOBJECT_ID),
    }
]


class KonicaMibSupport(SNMPBase):
    """
    Python equivalent of GLPI::Agent::SNMP::MibSupport::Konica
    Provides SNMP-based printer inventory enhancement for Konica devices.
    """

    def get_model(self):
        """Extract printer model name and remove 'KONICA MINOLTA' prefix."""
        raw_model = self.get(KONICA_MODEL)
        if not raw_model:
            return None
        model = get_canonical_string(hex2char(raw_model))
        if not model:
            return None
        return model.replace("KONICA MINOLTA ", "", 1).strip()

    def run(self):
        """Collect and process device data such as page counters and firmware."""
        device = self.device
        if not device:
            return

        # Map SNMP counters to GLPI attributes
        mapping = {
            "PRINTCOLOR": KONICA_COLOR_PRINT,
            "PRINTBLACK": KONICA_BLACK_PRINT,
            "RECTOVERSO": KONICA_RECTO_VERSO,
            "COPYCOLOR": KONICA_COLOR_COPY,
            "COPYBLACK": KONICA_BLACK_COPY,
            "SCANNED": KONICA_SCANS,
            "TOTAL": KONICA_TOTAL,
        }

        for counter, oid in mapping.items():
            count = self.get(oid)
            if count is not None:
                device.setdefault("PAGECOUNTERS", {})[counter] = count

        pc = device.get("PAGECOUNTERS", {})

        # Derived totals
        if pc.get("PRINTCOLOR") or pc.get("PRINTBLACK"):
            pc["PRINTTOTAL"] = (pc.get("PRINTBLACK", 0) + pc.get("PRINTCOLOR", 0))

        if pc.get("COPYCOLOR") or pc.get("COPYBLACK"):
            pc["COPYTOTAL"] = (pc.get("COPYBLACK", 0) + pc.get("COPYCOLOR", 0))

        # Firmware information
        firmware_name = self.walk(KONICA_FIRMWARE_NAME)
        firmware_version = self.walk(KONICA_FIRMWARE_VERSION)

        if firmware_name and firmware_version:
            for key, name_val in firmware_name.items():
                name = get_canonical_string(hex2char(name_val))
                if not name:
                    continue

                version = get_canonical_string(hex2char(firmware_version.get(key, "")))
                if not version or version in ("-", "Registered"):
                    continue

                name = name.replace(" version", "", 1).strip()
                firmware = {
                    "NAME": f"Konica {name}",
                    "DESCRIPTION": f"Printer {name}",
                    "TYPE": "printer",
                    "VERSION": version,
                    "MANUFACTURER": "Konica",
                }
                device.add_firmware(firmware)package GLPI::Agent::SNMP::MibSupport::Konica;

use strict;
use warnings;

use parent 'GLPI::Agent::SNMP::MibSupportTemplate';

use GLPI::Agent::Tools;
use GLPI::Agent::Tools::SNMP;

use constant    enterprises => '.1.3.6.1.4.1' ;

use constant    konica  => enterprises . '.18334';

use constant    konicaSysobjectID   => konica . '.1.1.1.2' ;

use constant    konicaModel => konica . '.1.1.1.1.6.2.1.0';

use constant    konicaPrinterCounters   => konica . '.1.1.1.5.7.2' ;

use constant    konicaTotal         => konicaPrinterCounters . '.1.1.0' ;
use constant    konicaRectoVerso    => konicaPrinterCounters . '.1.3.0' ;
use constant    konicaBlackCopy     => konicaPrinterCounters . '.2.1.5.1.1' ;
use constant    konicaBlackPrint    => konicaPrinterCounters . '.2.1.5.1.2' ;
use constant    konicaColorCopy     => konicaPrinterCounters . '.2.1.5.2.1' ;
use constant    konicaColorPrint    => konicaPrinterCounters . '.2.1.5.2.2' ;
use constant    konicaScans         => konicaPrinterCounters . '.3.1.5.1' ;

use constant    konicaFirmware  => konica . '.1.1.1.5.5.1.1';
use constant    konicaFirmwareName      => konicaFirmware . '.2';
use constant    konicaFirmwareVersion   => konicaFirmware . '.3';

our $mibSupport = [
    {
        name        => "konica-printer",
        sysobjectid => getRegexpOidMatch(konicaSysobjectID)
    }
];

sub getModel {
    my ($self) = @_;

    my $model = getCanonicalString(hex2char($self->get(konicaModel)))
        or return;

    # Strip manufacturer
    $model =~ s/^KONICA MINOLTA\s+//i;

    return $model;
}

sub run {
    my ($self) = @_;

    my $device = $self->device
        or return;

    my %mapping = (
        PRINTCOLOR  => konicaColorPrint,
        PRINTBLACK  => konicaBlackPrint,
        RECTOVERSO  => konicaRectoVerso,
        COPYCOLOR   => konicaColorCopy,
        COPYBLACK   => konicaBlackCopy,
        SCANNED     => konicaScans,
        TOTAL       => konicaTotal,
    );

    foreach my $counter (sort keys(%mapping)) {
        my $count = $self->get($mapping{$counter})
            or next;
        $device->{PAGECOUNTERS}->{$counter} = $count;
    }

    # Set PRINTTOTAL if print found and no dedicated counter is defined
    if ($device->{PAGECOUNTERS}->{PRINTCOLOR} || $device->{PAGECOUNTERS}->{PRINTBLACK}) {
        $device->{PAGECOUNTERS}->{PRINTTOTAL} = ($device->{PAGECOUNTERS}->{PRINTBLACK} // 0) + ($device->{PAGECOUNTERS}->{PRINTCOLOR} // 0);
    }

    # Set COPYTOTAL if copy found and no dedicated counter is defined
    if ($device->{PAGECOUNTERS}->{COPYCOLOR} || $device->{PAGECOUNTERS}->{COPYBLACK}) {
        $device->{PAGECOUNTERS}->{COPYTOTAL} = ($device->{PAGECOUNTERS}->{COPYBLACK} // 0) + ($device->{PAGECOUNTERS}->{COPYCOLOR} // 0);
    }

    my $firmwareName    = $self->walk(konicaFirmwareName);
    my $firmwareVersion = $self->walk(konicaFirmwareVersion);
    if ($firmwareName && $firmwareVersion) {
        foreach my $key (keys(%{$firmwareName})) {
            my $name = getCanonicalString(hex2char($firmwareName->{$key}))
                or next;
            my $version = getCanonicalString(hex2char($firmwareVersion->{$key}))
                or next;
            next if $version eq '-' || $version eq "Registered";

            # Strip version string at the end of name
            $name =~ s/\s+version$//i;

            my $firmware = {
                NAME            => "Konica $name",
                DESCRIPTION     => "Printer $name",
                TYPE            => "printer",
                VERSION         => $version,
                MANUFACTURER    => "Konica"
            };
            $device->addFirmware($firmware);
        }
    }
}

1;

__END__

=head1 NAME

GLPI::Agent::SNMP::MibSupport::Konica - Inventory module for Konica Printers

=head1 DESCRIPTION

The module enhances Konica printers devices support.
