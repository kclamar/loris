"""imaging tables
"""

import datajoint as dj

from loris.database.schema import (
    subjects, anatomy, equipment, recordings, core
)
from loris.database.attributes import truebool, attachplaceholder, tags
from loris.database.attributes import lookupname
from loris.database.schema.base import (
    COMMENTS, NEURAL_RECORDING, ManualLookup,
    FilesMixin, DataMixin, ExtensionMixin
)


schema = dj.Schema('imaging')


@schema
class OpticalIndicator(ManualLookup, dj.Manual):
    primary_comment = 'indicator - e.g. GCaMP6f'


@schema
class TwoPhotonRecording(dj.Manual):
    definition = f"""
    {NEURAL_RECORDING}
    -> [nullable] anatomy.NeuronSection
    -> [nullable] anatomy.BrainArea
    -> [nullable] OpticalIndicator
    voltage_input = 0 : <truebool> # whether voltage input was recorded
    voltage_output = 0 : <truebool> # whether voltage output was recorded
    linescan = 0 : <truebool> # whether linescan was captured or not
    manual_start_time = null : float # manual start time of recording, if offset
    manual_end_time = null : float # manual end time of recording, if offset
    """

    class Files(FilesMixin, dj.Part):
        master_name = "TwoPhotonRecording"

    class Data(DataMixin, dj.Part):
        master_name = "TwoPhotonRecording"

    class Extensions(ExtensionMixin, dj.Part):
        master_name = "TwoPhotonRecording"


@schema
class RawTwoPhotonData(dj.AutoImported):
    definition = """
    -> TwoPhotonRecording
    ---
    rate : float # in Hz
    timestamps : blob@datastore # in seconds
    movie : blob@datastore
    imaging_offset = null : float #offset of image acquisition in s
    vout_data = null : blob@datastore
    absolute_time_vout = null : float #offset of voltage output in s
    vin_data = null : blob@datastore
    absolute_time_vin = null : float #offset of voltage input in s
    field_of_view = null : blob # width, height and depth of image in micrometers
    pmt_gain = null : float # photomultiplier gain
    scan_line_rate = null : float # lines imaged per second
    dimension = null : blob # number of pixels on x, y, and z axes
    location = null : longblob #x, y, and z position of microscope
    laser_power = null : float # pockels
    laser_wavelength = null : float # in nm
    dwell_time = null : float # in s
    microns_per_pixel = null : blob # x, y, z um/px
    """

    class Data(DataMixin, dj.Part):
        master_name = "RawTwoPhotonData"

    class Files(FilesMixin, dj.Part):
        master_name = "RawTwoPhotonData"


@schema
class MotionCorrectedData(dj.AutoComputed):
    definition = """
    -> RawTwoPhotonData
    ---
    rate : float # in Hz
    timestamps : blob@datastore # in seconds
    movie : blob@datastore
    """

    class Data(DataMixin, dj.Part):
        master_name = "MotionCorrectedData"

    class Files(FilesMixin, dj.Part):
        master_name = "MotionCorrectedData"


@schema
class ExtractedData(dj.AutoComputed):
    definition = """
    -> MotionCorrectedData
    ---
    """

    class Data(DataMixin, dj.Part):
        master_name = "ExtractedData"

    class Files(FilesMixin, dj.Part):
        master_name = "ExtractedData"

    class Roi(dj.Part):
        definition = """
        -> ExtractedData
        cell_id : int
        ---
        label = null : varchar(51) # label for Roi
        mask : blob@datastore # array of roi mask (boolean or weighted)
        rate : float # in Hz
        timestamps : blob@datastore # in seconds
        signal : blob@datastore
        metadata = null : blob@datastore # additional data to describe mask
        """
