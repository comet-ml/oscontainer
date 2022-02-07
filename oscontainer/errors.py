class OSContainerError(Exception):
    """General container data processing error"""

    def __init__(self, *args, **kwargs):
        super(OSContainerError, self).__init__(*args, **kwargs)
