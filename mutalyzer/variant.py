"""
"""

from extractor import extractor

from mutalyzer import models

weights = {
    "subst": extractor.WEIGHT_SUBSTITUTION,
    "del": extractor.WEIGHT_DELETION,
    "ins": extractor.WEIGHT_INSERTION,
    "dup": extractor.WEIGHT_INSERTION,
    "inv": extractor.WEIGHT_INVERSION,
    "delins": extractor.WEIGHT_DELETION_INSERTION
}

class HGVSList(list):
    """
    Container for a list of sequences or variants.
    """
    def __str__(self):
        if len(self) > 1:
            return "[{}]".format(';'.join(map(str, self)))
        return str(self[0])
    #__str__

    def weight(self):
        weight = sum(map(lambda x: x.weight(), self))

        if len(self) > 1:
            return weight + (len(self) + 1) * extractor.WEIGHT_SEPARATOR
        return weight
    #weight
#HGVSList

class Allele(HGVSList):
    pass

class ISeqList(HGVSList):
    pass

class ISeq(object):
    """
    Container for an inserted sequence.
    """
    def __init__(self, sequence="", start=0, end=0, reverse=False,
            weight_position=1):
        """
        :arg sequence: Literal inserted sequence.
        :type sequence: str
        :arg start: Start position for a transposed sequence.
        :type start: int
        :arg end: End position for a transposed sequence.
        :type end: int
        :arg reverse: Inverted transposed sequence.
        :type reverse: bool
        """
        self.sequence = sequence
        self.start = start
        self.end = end
        self.reverse = reverse
        self.weight_position = weight_position

        self.type = "trans"
        if self.sequence:
            self.type = "ins"
    #__init__

    def __str__(self):
        if self.type == "ins":
            return self.sequence

        inverted = "inv" if self.reverse else ""
        return "{}_{}{}".format(self.start, self.end, inverted)
    #__str__

    def __nonzero__(self):
         return bool(self.sequence)

    def weight(self):
        if self.type == "ins":
            return len(self.sequence) * extractor.WEIGHT_BASE

        inverse_weight = weights["inv"] if self.reverse else 0
        return (self.weight_position * 2 + extractor.WEIGHT_SEPARATOR +
            inverse_weight)
    #weight
#ISeq

class DNAVar(models.DNAVar):
    """
    Container for a DNA variant.
    """
    def __init__(self, start=0, start_offset=0, end=0, end_offset=0,
            sample_start=0, sample_start_offset=0, sample_end=0,
            sample_end_offset=0, type="none", deleted=ISeqList([ISeq()]),
            inserted=ISeqList([ISeq()]), shift=0, weight_position=1):
        """
        Initialise the class with the appropriate values.

        :arg start: Start position.
        :type start: int
        :arg start_offset:
        :type start_offset: int
        :arg end: End position.
        :type end: int
        :arg end_offset:
        :type end_offset: int
        :arg sample_start: Start position.
        :type sample_start: int
        :arg sample_start_offset:
        :type sample_start_offset: int
        :arg sample_end: End position.
        :type sample_end: int
        :arg sample_end_offset:
        :type sample_end_offset: int
        :arg type: Variant type.
        :type type: str
        :arg deleted: Deleted part of the reference sequence.
        :type deleted: str
        :arg inserted: Inserted part.
        :type inserted: object
        :arg shift: Amount of freedom.
        :type shift: int
        """
        # TODO: Will this container be used for all variants, or only genomic?
        #       start_offset and end_offset may be never used.
        self.start = start
        self.start_offset = start_offset
        self.end = end
        self.end_offset = end_offset
        self.sample_start = sample_start
        self.sample_start_offset = sample_start_offset
        self.sample_end = sample_end
        self.sample_end_offset = sample_end_offset
        self.type = type
        self.deleted = deleted
        self.inserted = inserted
        self.weight_position = weight_position
        self.shift = shift
    #__init__

    def __str__(self):
        """
        Give the HGVS description of the raw variant stored in this class.

        :returns: The HGVS description of the raw variant stored in this class.
        :rtype: str
        """
        if self.type == "unknown":
            return "?"
        if self.type == "none":
            return "="

        description = "{}".format(self.start)

        if self.start != self.end:
            description += "_{}".format(self.end)

        if self.type != "subst":
            description += "{}".format(self.type)

            if self.type in ("ins", "delins"):
                return description + "{}".format(self.inserted)
            return description
        #if

        return description + "{}>{}".format(self.deleted, self.inserted)
    #__str__

    def weight(self):
        if self.type == "unknown":
            return -1
        if self.type == "none":
            return 0

        weight = self.weight_position
        if self.start != self.end:
            weight += self.weight_position + extractor.WEIGHT_SEPARATOR

        return weight + weights[self.type] + self.inserted.weight()
    #weight
#DNAVar

class ProteinVar(models.ProteinVar):
    """
    Container for a protein variant.
    """
    def __init__(self, start=0, end=0, sample_start=0, sample_end=0,
            type="none", deleted=ISeqList([ISeq()]),
            inserted=ISeqList([ISeq()]), shift=0, term=0):
        """
        Initialise the class with the appropriate values.

        :arg start: Start position.
        :type start: int
        :arg end: End position.
        :type end: int
        :arg sample_start: Start position.
        :type sample_start: int
        :arg sample_end: End position.
        :type sample_end: int
        :arg type: Variant type.
        :type type: str
        :arg deleted: Deleted part of the reference sequence.
        :type deleted: str
        :arg inserted: Inserted part.
        :type inserted: object
        :arg shift: Amount of freedom.
        :type shift: int
        :arg term:
        :type term:
        """
        self.start = start
        self.end = end
        self.sample_start = sample_start
        self.sample_end = sample_end
        self.type = type
        self.deleted = deleted
        self.inserted = inserted
        self.shift = shift
        self.term = term
    #__init__

    def __str__(self):
        """
        Give the HGVS description of the raw variant stored in this class.

        Note that this function relies on the absence of values to make the
        correct description. Also see the comment in the class definition.

        :returns: The HGVS description of the raw variant stored in this class.
        :rtype: str
        """
        if self.type == "unknown":
            return "?"
        if self.type == "none":
            return "="

        description = ""
        if not self.deleted:
            if self.type == "ext":
                description += '*'
            else:
                description += "{}".format(seq3(self.start_aa))
        #if
        else:
            description += "{}".format(seq3(self.deleted))
        description += "{}".format(self.start)
        if self.end:
            description += "_{}{}".format(seq3(self.end_aa), self.end)
        if self.type not in ["subst", "stop", "ext", "fs"]: # fs is not a type
            description += self.type
        if self.inserted:
            description += "{}".format(seq3(self.inserted))

        if self.type == "stop":
            return description + '*'
        if self.term:
            return description + "fs*{}".format(self.term)
        return description
    #__str__
#ProteinVar
