""" MultiQC module to parse output from HOPS postprocessing script """

from __future__ import print_function
from collections import OrderedDict
from itertools import chain
import logging
import json

from multiqc.plots import heatmap
from multiqc.utils import config
from multiqc.modules.base_module import BaseMultiqcModule

log = logging.getLogger(__name__)

class MultiqcModule(BaseMultiqcModule):
    def __init__(self):
        # Initialise the parent object
        super(MultiqcModule, self).__init__(name='My Module', anchor='mymod',
        href="https://www.https://github.com/rhuebler/HOPS/",
        info=" Ancient DNA characteristics screening tool of metagenomic aligner MALT.")

        # Find and load any HOPS post-processing JSONs
        self.hops_data = dict()

        for f in self.find_log_files('hops',filehandles=True):
            try:
                self.parseJSON(f)
            except KeyError:
                logging.warning("Error loading file {}".format(f['fn']))

        self.hops_data = self.ignore_samples(self.hops_data)

        if len(self.hops_data) == 0:
            raise UserWarning

        log.info("Found {} samples".format(len(self.hops_data)))

        #self.hops_heatmap(self.hops_data)

    def parseJSON(self, f):
        """ Parse the JSON output from HOPS and save the summary statistics """

        try:
            parsed_json = json.load(f['f'])
            # Check for Keys existing
        except JSONDecodeError as e:
            log.debug("Could not parse HOPS JSON: '{}'".format(f['fn']))
            log.debug(e)
            return None
        
        for s in parsed_json: 
            s_name = self.clean_s_name(s, f['root'])
            if s_name in self.hops_data: 
                log.debug("Duplicate sample name found! Overwriting: {}".format(s_name))
            self.add_data_source(f, s_name=s_name)
            self.hops_data[s_name] = {}
            for t in parsed_json[s]:
                self.hops_data[s_name][t] = parsed_json[s][t][0]
    
    def hops_heatmap(self, hops_data):
        """ Heatmap showing all statuses for every sample """
        heatmap_numbers = {
            'none': 1,
            'edit_only': 2,
            'damage_only': 3,
            'edit_and_damage': 4
        }

        pconfig = {
            'id': 'hops-heatmap',
            'title': 'HOPS: Potential Candidates',
            'xTitle': 'Node',
            'yTitle': 'Sample',
            'min': 0,
            'max': 1,
            'square': False,
            'colstops': [
                [1, '#ffffff'],
                [2, '#ffeda0'],
                [3, '#feb24c'],
                [4, '#f03b20'],
            ],
            'decimalPlaces': 1,
            'legend': True,
            'datalabels': False
        }

        # Heatmaps expect data in the structure of a list of lists. Then, a 
        # list of sample names for the x-axis, and optionally for the y-axis 
        # (defaults to the same as the x-axis).
        # https://multiqc.info/docs/#heatmaps

        self.add_section (
            name = 'HOPS: Potential Candidates',
            anchor = 'hops_heatmap',
            description = '''
            HOPS heatmap indicating different levels of possible candidates for
            downstream aDNA analysis.
            ''',
            helptext = '''
            HOPS assigns a category based on how many ancient DNA 
            characteristics a given node (i.e. taxon) in a sample has. This goes
            from grey (no characteristics detected), yellow (small edit distance
            from reference), orange (has typical aDNA damage pattern), to
            red (both small edit distance and damage pattern). A red category
            will typically indicates a good candidate for further investigation
            for ownstream analysis
            ''',
            ## TODO
            plot = heatmap.plot(self.hops_data, xcats = None,ycats = None, pconfig = pconfig)
        )
