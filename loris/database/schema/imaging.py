"""imaging tables
"""

import datajoint as dj

from . import subjects, anatomy, equipment
from ..attributes import trueboo, tarfolder
from .base import COMMENTS, NEURAL_RECORDING


schema = dj.schema('imaging')


@schema
class TwoPhotonRecording(dj.Manual):
    definition = f"""
    {NEURAL_RECORDING}
    -> [nullable] anatomy.NeuronSection
    -> [nullable] anatomy.BrainLocation
    sequence_no = 1 : int unsigned # number of sequences in recording
    plane_no = 1 : smallint unsigned # number of z-planes in recording
    channel_no = 1 : smallint unsigned # number of channels in recording
    voltage_input = 0 : <truebool> # whether voltage input was recorded
    voltage_output = 0 : <truebool> # whether voltage output was recorded
    linescan = 0 : <truebool> # whether linescan was captured or not
    manual_start_time = null : float # manual start time of recording, if offset
    manual_end_time = null : float # manual end time of recording, if offset
    """
