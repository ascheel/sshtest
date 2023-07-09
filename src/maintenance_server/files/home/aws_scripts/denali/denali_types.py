""" denali_types.py: Some data types used throughout denali.  """


class OutputTarget(object):
    """ OutputTarget encapsulates the information needed for denali to determine
        how to format output. These are:

            1) The output type (e.g. 'csv_screen', 'csv_file', etc.)
            2) The output filename if any.
            3) A flag specifying that the file would be opened in append
               (instead of write) mode.
    """
    def __init__(self, type=None, filename='', append=False):
        """ Initialize this object with defaults. """
        self.type = type
        self.filename = filename
        self.append = append

    def __repr__(self):
        """ Returns a string representation of this object. """
        return 'OutputTarget(type={0}, filename={1}, append={2}'.format(
            self.type, self.filename, self.append)

    def __eq__(self, other):
        """ Return true if this object is equivalent to 'other'. """
        return (self.type == other.type
                and self.filename == other.filename
                and self.append == other.append)
