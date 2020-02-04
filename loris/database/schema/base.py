"""Base classes for tables
"""

COMMENTS = 'comments = null : varchar(4000)'
DESCRIPTION = 'description = null : varchar(4000) # (detailed) description'
PRIMARY_NAME = '{name} : varchar(127) # {comment}'
NEURAL_RECORDING = f"""
    -> subjects.FlySubject
    recording_id : smallint # integer id number
    ---
    -> recordings.RecordingType
    recording_ext = null : varchar(63) # file extension name of recording file used for post-processing
    recording_file = null : attach@attachstore # file of recording, if available
    recording_time = CURRENT_TIMESTAMP : timestamp # time of recording
    recording_temperature = null : float # recording temperature in Celsius
    -> recordings.RecordingSolution
    was_completed = 0 : <truebool> # was the recording completed as intended
    use_recording = 0 : <truebool> # should the recording be used for further analysis
    {COMMENTS}
    -> recordings.ProtocolType
    protocol_ext = null : varchar(63) # file extension name of protocol file used for post-processing
    protocol_file = null : attach@attachstore # file of protocol, if available
    protocol_data = null : blob@attachstore # data of protocol, if available
    """


class ManualLookup:

    primary_comment = "short name identifier"

    @property
    def definition(self):
        return f"""
        {PRIMARY_NAME.format(name=self.table_name, comment=self.primary_comment)}
        ---
        {COMMENTS}
        """
