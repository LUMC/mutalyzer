#!/usr/bin/python

"""
Mutalyzer webservices.

@requires: soaplib.wsgi_soap.SimpleWSGISoapApp
@requires: soaplib.service.soapmethod
@requires: soaplib.serializers.primitive.String
@requires: soaplib.serializers.primitive.Integer
@requires: soaplib.serializers.primitive.Array
@requires: soaplib.serializers.primitive.Fault

@requires: Modules.Web
@requires: Modules.Db
@requires: Modules.Output
@requires: Modules.Config
@requires: Modules.Parser
@requires: Modules.Mapper

@requires: Modules.Serializers.SoapMessage
@requires: Modules.Serializers.Mapping
@requires: Modules.Serializers.Transcript
"""
# Public classes:
#     - MutalyzerService ; Mutalyzer webservices.

# Patch lxml.etree.cleanup_namespaces to not do anything:
# soaplib calls this function, but it removes namespaces we need (see
# wsgi_soap.py in the soaplib library).
# Current versions of soaplib don't have this bug.
# https://github.com/soaplib/soaplib
# https://github.com/arskom/rpclib (forked soaplib)
import lxml.etree; lxml.etree.cleanup_namespaces = lambda _: None

# todo: If we use Array(String) in a Soap method signature, soaplib generates
# the following type declaration for it:
#
#   <xs:complexType name="stringArray">
#     <xs:sequence>
#       <xs:element minOccurs="0" maxOccurs="unbounded"
#          type="tns:string" name="string" />
#     </xs:sequence>
#   </xs:complexType>
#
# However, tns:string does not exist. This should be:
#
#   <xs:complexType name="stringArray">
#     <xs:sequence>
#       <xs:element minOccurs="0" maxOccurs="unbounded"
#          type="xs:string" name="string" />
#     </xs:sequence>
#   </xs:complexType>
#
# This affects the wsdl tool, Mono's Web Service Proxy Generator. If we fix
# it, the webservice functions correctly with a Mono client.

from soaplib.wsgi_soap import SimpleWSGISoapApp
from soaplib.service import soapmethod
from soaplib.serializers.primitive import String, Integer, Array, Fault

# Unfortunately, Mutalyzer assumes a working directory at some points, but
# it is not there if we use Apache/mod_wsgi
# todo: instead of this patch we should fix Mutalyzer
import os
os.chdir(os.path.split(os.path.dirname(__file__))[0])

# Same goes for the Python module path
# todo: instead of this patch we should fix Mutalyzer
import sys
sys.path.append(os.path.dirname(__file__))

import Mutalyzer
from Modules import Web
from Modules import Db
from Modules import Output
from Modules import Config
from Modules import Parser
from Modules import Mapper
from Modules import Retriever
from Modules.Serializers import SoapMessage, Mapping, Transcript, \
                                MutalyzerOutput

class MutalyzerService(SimpleWSGISoapApp) :
    """
    Mutalyzer webservices.

    These methods are made public via a SOAP interface.

    Private methods:
      - __checkBuild(L, D, build) ; Check if the build is supported.
      - __checkChrom(L, D, chrom) ; Check if the chromosome is in our
                                    database.
      - __checkPos(L, pos)        ; Check if the position is valid.

    Public methods:
      - getTranscripts(build, chrom,  pos); Get all transcripts that overlap
        with a chromosomal position.
      - getTranscriptsRange(build, chrom, pos1, pos2, method) ; Get all
        transcripts that overlap with a range on a chromosome.
      - getGeneName(build, accno)    ; Find the gene name associated with a
        transcript.
      - mappingInfo(LOVD_ver, build, accNo, variant) ; Convert a transcript
        coordinate to a chromosomal one, or vice versa.
      - transcriptInfo(LOVD_ver, build, accNo) ; Find transcription start and
        end, and CDS end (in I{c.} notation) for a given transcript.
      - cTogConversion(self, build, variant) ; Convert I{c.} to I{g.}
      - gTocConversion(self, build,  variant) ; Convert I{g.} to I{c.}

    """

    def __checkBuild(self, L, build, config) :
        """
        Check if the build is supported (hg18 or hg19).


        Returns:
            - Nothing (but raises an EARG exception).

        @arg L: an output object for logging
        @type L: object
        @arg build: The human genome build name that needs to be checked
        @type build: string
        @arg config: configuration object of the Db module
        @type config: object
        """

        if not build in config.dbNames :
            L.addMessage(__file__, 4, "EARG", "EARG %s" % build)
            raise Fault("EARG",
                        "The build argument (%s) was not a valid " \
                        "build name." % build)
        #if
    #__checkBuild

    def __checkChrom(self, L, D, chrom) :
        """
        Check if the chromosome is in our database.

        Returns:
            - Nothing (but raises an EARG exception).

        @arg L: An output object for logging
        @type L: object
        @arg D: A handle to the database.
        @type D: object
        @arg chrom: The name of the chromosome
        @type chrom: string
        """

        if not D.isChrom(chrom) :
            L.addMessage(__file__, 4, "EARG", "EARG %s" % chrom)
            raise Fault("EARG",
                        "The chrom argument (%s) was not a valid " \
                        "chromosome name." % chrom)
        #if
    #__checkChrom

    def __checkPos(self, L, pos) :
        """
        Check if the position is valid.

        Returns:
            - Nothing (but raises an ERANGE exception).

        @arg L: An output object for logging
        @type L: object
        @arg pos: The position
        @type pos: integer
        """

        if pos < 1 :
            L.addMessage(__file__, 4, "ERANGE", "ERANGE %i" % pos)
            raise Fault("ERANGE",
                        "The pos argument (%i) is out of range." % pos)
        #if
    #__checkPos

    def __checkVariant(self, L, variant) :
        """
        Check if a variant is provided.

        Returns:
            - Nothing (but raises an EARG exception).

        @arg L: An output object for logging
        @type L: object
        @arg variant: The variant
        @type variant: string
        """

        if not variant :
            L.addMessage(__file__, 4, "EARG", "EARG no variant")
            raise Fault("EARG", "The variant argument is not provided.")
        #if
    #__checkVariant

    @soapmethod(String, String, Integer, _returns = Array(String))
    def getTranscripts(self, build, chrom, pos) :
        """
        Get all the transcripts that overlap with a chromosomal position.

        On error an exception is raised:
          - detail       ; Human readable description of the error.
          - faultstring: ; A code to indicate the type of error.
              - EARG   ; The argument was not valid.
              - ERANGE ; An invalid range was given.

        @arg build: The human genome build (hg19 or hg18)
        @type build: string
        @arg chrom: A chromosome encoded as "chr1", ..., "chrY"
        @type chrom: string
        @arg pos: A position on the chromosome
        @type pos: integer

        @return: A list of transcripts
        @rtype: list
        """

        C = Config.Config()
        L = Output.Output(__file__, C.Output)

        L.addMessage(__file__, -1, "INFO",
                     "Received request getTranscripts(%s %s %s)" % (build,
                     chrom, pos))

        self.__checkBuild(L, build, C.Db)
        D = Db.Mapping(build, C.Db)

        self.__checkChrom(L, D, chrom)
        self.__checkPos(L, pos)

        ret = D.get_Transcripts(chrom, pos, pos, True)

        #filter out the accNo
        ret = [r[0] for r in ret]


        L.addMessage(__file__, -1, "INFO",
                     "Finished processing getTranscripts(%s %s %s)" % (build,
                     chrom, pos))

        del D, L, C
        return [ret]
    #getTranscripts

    @soapmethod(String, String, _returns = Array(String))
    def getTranscriptsByGeneName(self, build, name) :
        """
            blabla
        """

        C = Config.Config()
        L = Output.Output(__file__, C.Output)

        L.addMessage(__file__, -1, "INFO",
                     "Received request getTranscriptsByGene(%s %s)" % (build,
                     name))

        self.__checkBuild(L, build, C.Db)
        D = Db.Mapping(build, C.Db)

        ret = D.get_TranscriptsByGeneName(name)

        L.addMessage(__file__, -1, "INFO",
                     "Finished processing getTranscriptsByGene(%s %s)" % (
                     build, name))
        return [ret]
    #getTranscriptsByGene

    @soapmethod(String, String, Integer, Integer, Integer,
        _returns = Array(String))
    def getTranscriptsRange(self, build, chrom, pos1, pos2, method) :
        """
        Get all the transcripts that overlap with a range on a chromosome.

        @arg build: The human genome build (hg19 or hg18)
        @type build: string
        @arg chrom: A chromosome encoded as "chr1", ..., "chrY"
        @type chrom: string
        @arg pos1: The first postion of the range
        @type pos1: integer
        @arg pos2: The last postion of the range
        @type pos2: integer
        @arg method: The method of determining overlap:
            - 0 ; Return only the transcripts that completely fall in the range
                  [pos1, pos2].
            - 1 ; Return all hit transcripts

        @return: A list of transcripts
        @rtype: list
        """

        C = Config.Config()
        L = Output.Output(__file__, C.Output)

        L.addMessage(__file__, -1, "INFO",
            "Received request getTranscriptsRange(%s %s %s %s %s)" % (build,
            chrom, pos1, pos2, method))

        D = Db.Mapping(build, C.Db)
        self.__checkBuild(L, build, C.Db)

        ret = D.get_Transcripts(chrom, pos1, pos2, method)

        #filter out the accNo
        ret = [r[0] for r in ret]

        L.addMessage(__file__, -1, "INFO",
            "Finished processing getTranscriptsRange(%s %s %s %s %s)" % (
            build, chrom, pos1, pos2, method))

        del D, L, C
        return [ret]
    #getTranscriptsRange

    @soapmethod(String, String, _returns = String)
    def getGeneName(self, build, accno) :
        """
        Find the gene name associated with a transcript.

        @arg build: The human genome build (hg19 or hg18)
        @type build: string
        @arg accno: The identifier of a transcript
        @type accno: string

        @return: The name of the associated gene
        @rtype: string
        """

        C = Config.Config()
        L = Output.Output(__file__, C.Output)

        L.addMessage(__file__, -1, "INFO",
                     "Received request getGeneName(%s %s)" % (build, accno))

        D = Db.Mapping(build, C.Db)
        self.__checkBuild(L, build, C.Db)

        ret = D.get_GeneName(accno.split('.')[0])

        L.addMessage(__file__, -1, "INFO",
                     "Finished processing getGeneName(%s %s)" % (build, accno))

        del D, L, C
        return ret
    #getGeneName


    @soapmethod(String, String, String, String, _returns = Mapping)
    def mappingInfo(self, LOVD_ver, build, accNo, variant) :
        """
        Search for an NM number in the MySQL database, if the version
        number matches, get the start and end positions in a variant and
        translate these positions to I{g.} notation if the variant is in I{c.}
        notation and vice versa.

          - If no end position is present, the start position is assumed to be
            the end position.
          - If the version number is not found in the database, an error message
            is generated and a suggestion for an other version is given.
          - If the reference sequence is not found at all, an error is returned.
          - If no variant is present, an error is returned.
          - If the variant is not accepted by the nomenclature parser, a parse
            error will be printed.

        @arg LOVD_ver: The LOVD version
        @type LOVD_ver: string
        @arg build: The human genome build (hg19 or hg18)
        @type build: string
        @arg accNo: The NM accession number and version
        @type accNo: string
        @arg variant: The variant
        @type variant: string

        @return: complex object:
          - start_main   ; The main coordinate of the start position
                           in I{c.} (non-star) notation.
          - start_offset ; The offset coordinate of the start position
                           in I{c.} notation (intronic position).
          - end_main     ; The main coordinate of the end position in
                           I{c.} (non-star) notation.
          - end_offset   ; The offset coordinate of the end position in
                           I{c.} notation (intronic position).
          - start_g      ; The I{g.} notation of the start position.
          - end_g        ; The I{g.} notation of the end position.
          - type         ; The mutation type.
        @rtype: object
        """

        C = Config.Config()
        L = Output.Output(__file__, C.Output)

        L.addMessage(__file__, -1, "INFO",
                     "Reveived request mappingInfo(%s %s %s %s)" % (
                        LOVD_ver, build, accNo, variant))

        conv = Mapper.Converter(build, C, L)
        result = conv.mainMapping(accNo, variant)

        L.addMessage(__file__, -1, "INFO",
                     "Finished processing mappingInfo(%s %s %s %s)" % (
                        LOVD_ver, build, accNo, variant))

        del L, C
        return result
    #mappingInfo

    @soapmethod(String, String, String, _returns = Transcript)
    def transcriptInfo(self, LOVD_ver, build, accNo) :
        """
        Search for an NM number in the MySQL database, if the version
        number matches, the transcription start and end and CDS end
        in I{c.} notation is returned.

        @arg LOVD_ver: The LOVD version
        @type LOVD_ver: string
        @arg build: The human genome build (hg19 or hg18)
        @type build: string
        @arg accNo: The NM accession number and version
        @type accNo: string

        @return: complex object:
          - trans_start  ; Transcription start in I{c.} notation.
          - trans_stop   ; Transcription stop in I{c.} notation.
          - CDS_stop     ; CDS stop in I{c.} notation.
        @rtype: object
        """

        C = Config.Config()
        O = Output.Output(__file__, C.Output)

        O.addMessage(__file__, -1, "INFO",
                     "Received request transcriptInfo(%s %s %s)" % (LOVD_ver,
                     build, accNo))

        converter = Mapper.Converter(build, C, O)
        T = converter.mainTranscript(accNo)

        O.addMessage(__file__, -1, "INFO",
                     "Finished processing transcriptInfo(%s %s %s)" % (
                     LOVD_ver, build, accNo))
        return T
    #transcriptInfo

    @soapmethod(String, String, _returns = String)
    def chromAccession(self, build, name) :
        """
        Get the accession number of a chromosome, given a name.

        @arg build: The human genome build (hg19 or hg18)
        @type build: string
        @arg name: The name of a chromosome (e.g. chr1)
        @type name: string

        @return: The accession number of a chromosome
        @rtype: string
        """
        C = Config.Config() # Read the configuration file.
        D = Db.Mapping(build, C.Db)
        L = Output.Output(__file__, C.Output)

        L.addMessage(__file__, -1, "INFO",
                     "Received request chromAccession(%s %s)" % (build, name))

        self.__checkBuild(L, build, C.Db)
        self.__checkChrom(L, D, name)

        result = D.chromAcc(name)

        L.addMessage(__file__, -1, "INFO",
                     "Finished processing chromAccession(%s %s)" % (build,
                     name))

        del D,L,C
        return result
    #chromAccession

    @soapmethod(String, String, _returns = String)
    def chromosomeName(self, build, accNo) :
        """
        Get the name of a chromosome, given a chromosome accession number.

        @arg build: The human genome build (hg19 or hg18)
        @type build: string
        @arg accNo: The accession number of a chromosome (NC_...)
        @type accNo: string

        @return: The name of a chromosome
        @rtype: string
        """
        C = Config.Config() # Read the configuration file.
        D = Db.Mapping(build, C.Db)
        L = Output.Output(__file__, C.Output)

        L.addMessage(__file__, -1, "INFO",
                     "Received request chromName(%s %s)" % (build, accNo))

        self.__checkBuild(L, build, C.Db)
#        self.__checkChrom(L, D, name)

        result = D.chromName(accNo)

        L.addMessage(__file__, -1, "INFO",
                     "Finished processing chromName(%s %s)" % (build,
                     accNo))

        del D,L,C
        return result
    #chromosomeName

    @soapmethod(String, String, _returns = String)
    def getchromName(self, build, acc) :
        """
        Get the chromosome name, given a transcript identifier (NM number).

        @arg build: The human genome build (hg19 or hg18)
        @type build: string
        @arg acc: The NM accession number (version NOT included)
        @type acc: string

        @return: The name of a chromosome
        @rtype: string
        """
        C = Config.Config() # Read the configuration file.
        D = Db.Mapping(build, C.Db)
        L = Output.Output(__file__, C.Output)

        L.addMessage(__file__, -1, "INFO",
                     "Received request getchromName(%s %s)" % (build, acc))

        self.__checkBuild(L, build, C.Db)
#        self.__checkChrom(L, D, name)

        result = D.get_chromName(acc)

        L.addMessage(__file__, -1, "INFO",
                     "Finished processing getchromName(%s %s)" % (build,
                     acc))

        del D,L,C
        return result
    #chromosomeName

    @soapmethod(String, String, _returns = Array(String))
    def numberConversion(self, build, variant) :
        """
        Converts I{c.} to I{g.} notation or vice versa


        @arg build: The human genome build (hg19 or hg18)
        @type build: string
        @arg variant: The variant in either I{c.} or I{g.} notation, full HGVS
        notation, including NM_ or NC_ accession number
        @type variant: string

        @return: The variant in either I{g.} or I{c.} notation
        @rtype: string
        """

        C = Config.Config() # Read the configuration file.
        D = Db.Mapping(build, C.Db)
        O = Output.Output(__file__, C.Output)
        O.addMessage(__file__, -1, "INFO",
                     "Received request cTogConversion(%s %s)" % (
                     build, variant))
        converter = Mapper.Converter(build, C, O)
        variant = converter.correctChrVariant(variant)

        if "c." in variant :
            result = [converter.c2chrom(variant)]
        elif "g." in variant :
            result = converter.chrom2c(variant, "list")
        else:
            result = [""]

        O.addMessage(__file__, -1, "INFO",
                     "Finished processing cTogConversion(%s %s)" % (
                     build, variant))
        return result
    #numberConversion

    @soapmethod(String, _returns = String)
    def checkSyntax(self, variant):
        """
        Checks the syntax of a variant.

        @arg variant: the variant to check
        @type variant: string

        @return: message
        @rtype: string
        """
        C = Config.Config() # Read the configuration file.
        L = Output.Output(__file__, C.Output)
        L.addMessage(__file__, -1, "INFO",
                     "Received request checkSyntax(%s)" % (variant))

        self.__checkVariant(L, variant)

        P = Parser.Nomenclatureparser(L)
        parsetree = P.parse(variant)
        del C, P
        if not parsetree :
            result = "This variant does not have the right syntax. "\
                     "Please try again."
        #if
        else :
            result = "The syntax of this variant is OK!"

        L.addMessage(__file__, -1, "INFO",
                     "Finished processing checkSyntax(%s)" % (variant))

        del L
        return result
    #checkSyntax

    @soapmethod(String, _returns = MutalyzerOutput)
    def runMutalyzer(self, variant) :
        C = Config.Config() # Read the configuration file.
        L = Output.Output(__file__, C.Output)
        L.addMessage(__file__, -1, "INFO",
                     "Received request runMutalyzer(%s)" % (variant))
        Mutalyzer.process(variant, C, L)
        M = MutalyzerOutput()

        M.original = L.getIndexedOutput("original", 0)
        M.mutated = L.getIndexedOutput("mutated", 0)

        M.origMRNA = L.getIndexedOutput("origMRNA", 0)
        M.mutatedMRNA = L.getIndexedOutput("mutatedMRNA", 0)

        M.origCDS = L.getIndexedOutput("origCDS", 0)
        M.newCDS = L.getIndexedOutput("newCDS", 0)

        M.origProtein = L.getIndexedOutput("oldprotein", 0)
        M.newProtein = L.getIndexedOutput("newprotein", 0)
        M.altProtein = L.getIndexedOutput("altProtein", 0)

        M.errors, M.warnings, M.summary = L.Summary()

        L.addMessage(__file__, -1, "INFO",
                     "Finished processing runMutalyzer(%s)" % (variant))
        return M
    #runMutalyzer

    @soapmethod(String, String, _returns = String)
    def getGeneAndTranscipt(self, genomicReference, transcriptReference) :
        C = Config.Config()
        O = Output.Output(__file__, C.Output)
        D = Db.Cache(C.Db)

        O.addMessage(__file__, -1, "INFO",
            "Received request getGeneAndTranscipt(%s, %s)" % (genomicReference,
            transcriptReference))
        retriever = Retriever.GenBankRetriever(C.Retriever, O, D)
        record = retriever.loadrecord(genomicReference)

        ret = None
        for i in record.geneList :
            for j in i.transcriptList :
                if j.transcriptID == transcriptReference :
                    ret = "%s_v%s" % (i.name, j.name)

        O.addMessage(__file__, -1, "INFO",
            "Finished processing getGeneAndTranscipt(%s, %s)" % (
            genomicReference, transcriptReference))
        return ret
    #getGeneAndTranscipt
#MutalyzerService

# WSGI application for use with e.g. Apache/mod_wsgi
application = MutalyzerService()

# We can also use the built-in webserver by executing this file directly
if __name__ == '__main__':
    from wsgiref.simple_server import make_server
    print 'Listening to http://localhost:8080/'
    print 'WDSL file is at http://localhost:8080/?wsdl'
    make_server('localhost', 8080, application).serve_forever()
