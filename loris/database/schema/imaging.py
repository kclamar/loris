"""imaging tables
"""

import datajoint as dj

from loris.database.schema import subjects, anatomy, equipment, recordings
from loris.database.attributes import truebool
from loris.database.schema.base import COMMENTS, NEURAL_RECORDING, ManualLookup


schema = dj.schema('imaging')


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
    sequence_no = 1 : int unsigned # number of sequences in recording
    plane_no = 1 : smallint unsigned # number of z-planes in recording
    channel_no = 1 : smallint unsigned # number of channels in recording
    voltage_input = 0 : <truebool> # whether voltage input was recorded
    voltage_output = 0 : <truebool> # whether voltage output was recorded
    linescan = 0 : <truebool> # whether linescan was captured or not
    manual_start_time = null : float # manual start time of recording, if offset
    manual_end_time = null : float # manual end time of recording, if offset
    """


@schema
class RawTwoPhotonData(dj.AutoImported):
    definition = f"""
    -> TwoPhotonRecording
    ---
    rate : float # in Hz
    raw_timestamps : blob@datastore # in seconds
    raw_movie : blob@datastore
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
    twophoton_metadata = null : blob # metadata relating to the whole movie
    frames_metadata = null : blob@datastore # metadata associated to each frame
    {COMMENTS}
    """
