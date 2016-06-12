#!/usr/bin/env python
"""
Run the Mutalyzer namechecker on a variant description.

Usage:
  {command} description [verbosity]

  description: Variant description to check.
  verbosity: If 'verbose', also output full original and variant sequences.

The namechecker results are retrieved from the Mutalyzer SOAP web service and
printed to standard output.
"""


from __future__ import unicode_literals

from mutalyzer.util import monkey_patch_suds; monkey_patch_suds()

import sys
from suds.client import Client

from mutalyzer.util import format_usage


WSDL_LOCATION = 'http://127.0.0.1:8081/?wsdl'


def main(description, verbosity=None):
    """
    Run the Mutalyzer namechecker and print results to standard output.
    """
    service = Client(WSDL_LOCATION, cache=None).service
    result = service.runMutalyzer(description)

    print 'Reference id: %s' % result.referenceId
    print 'Source id: %s' % result.sourceId
    if 'sourceAccession' in result:
        print 'Source accession number: %s' % result.sourceAccession
    if 'sourceVersion' in result:
        print 'Source version: %s' % result.sourceVersion
    print 'Molecule type: %s\n' % result.molecule

    if result.rawVariants:
        for v in result.rawVariants.RawVariant:
            print 'Raw variant: %s' % v.description
            print '%s\n' % v.visualisation

    if verbosity == 'verbose':
        print 'Original:\n%s\n' % result.original
        print 'Mutated:\n%s\n' % result.mutated
        print 'origMRNA:\n%s\n' % result.origMRNA
        print 'mutatedMRNA:\n%s\n' % result.mutatedMRNA
        print 'origCDS:\n%s\n' % result.origCDS
        print 'newCDS:\n%s\n' % result.newCDS
        print 'origProtein:\n%s\n' % result.origProtein
        print 'newProtein:\n%s\n' % result.newProtein
        print 'altProtein:\n%s\n' % result.altProtein

    print 'Errors: %s' % result.errors
    print 'Warnings: %s' % result.warnings
    print 'Summary: %s\n' % result.summary

    if result.messages:
        for m in result.messages.SoapMessage:
            print 'Error %s: %s\n' % (m.errorcode, m.message)

    if 'chromDescription' in result:
        print 'Chromosomal description: %s' % result.chromDescription
    print 'Genomic description: %s' % result.genomicDescription

    if result.transcriptDescriptions:
        print 'Affected transcripts:'
        print '\n'.join(result.transcriptDescriptions.string)
    if result.proteinDescriptions:
        print 'Affected proteins:'
        print '\n'.join(result.proteinDescriptions.string)

    if 'exons' in result:
        print '\nExon table for selected transcript:'
        print '\t'.join(['Number', 'Start (g.)', 'Stop (g.)', 'Start (c.)', 'Stop (c.)'])
        for i, exon in enumerate(result.exons.ExonInfo, start=1):
            print '\t'.join([str(i), str(exon.gStart), str(exon.gStop), exon.cStart, exon.cStop])


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print format_usage()
        sys.exit(1)
    main(*sys.argv[1:])
