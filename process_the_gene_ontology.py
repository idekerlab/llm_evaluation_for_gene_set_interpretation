#! /usr/bin/env python

import os
import sys
import argparse
import requests
import gzip
import traceback
import pandas as pd
import mygene
import ddot
from ddot import Ontology


NAMESPACE = 'namespace: '
NAMESPACE_OFFSET = len(NAMESPACE)
ID = 'id: '
ID_OFFSET = len(ID)
ALT_ID = 'alt_id: '
ALT_ID_OFFSET = len(ALT_ID)
IS_OBSOLETE = 'is_obsolete: '
IS_OBSOLETE_OFFSET = len(IS_OBSOLETE)

GO_BASIC_OBO = 'go-basic.obo'

GO_BASIC_FILTERED_OBO = 'go-basic-filtered.obo'

GOA_HUMAN_GAF = 'goa_human.gaf.gz'


class Formatter(argparse.ArgumentDefaultsHelpFormatter,
                argparse.RawDescriptionHelpFormatter):
    pass


def _parse_arguments(desc, args):
    """
    Parses command line arguments
    :param desc:
    :param args:
    :return:
    """
    parser = argparse.ArgumentParser(description=desc,
                                     formatter_class=Formatter)
    parser.add_argument('outdir',
                        help='Directory to write GO hierarchy')
    parser.add_argument('--keep_obsolete', action='store_true',
                        help='If set, keeps obsolete GO terms')
    parser.add_argument('--namespace', default='',
                        choices=['cellular_component', 'biological_process',
                                 'molecular_function', ''],
                        help='Keeps only GO terms in namespace '
                             'specified. If set to empty'
                             'string all are kept')
    parser.add_argument('--server', default='public.ndexbio.org',
                        help='Server where hierarchy resides')
    parser.add_argument('--user',
                        help='NDEx username, if set uploads GO hierarchies to NDEx')
    parser.add_argument('--password',
                        help='NDEx password, if set uploads GO hierarchies to NDEx')
    parser.add_argument('--prefix',
                        help='Prefix name to give to GO hierarchy uploaded to NDEx')
    parser.add_argument('--gobasic', default='http://purl.obolibrary.org/obo/go/go-basic.obo',
                        help='URL to go-basic.obo file')
    parser.add_argument('--goahuman', default='http://geneontology.org/gene-associations/goa_human.gaf.gz',
                        help='URL to goa_human.gaf.gz file')
    return parser.parse_args(args)


def filter_termlist(term_list=None, go_ids_to_skip=None,
                    keep_obsolete=False,
                    namespace=None):
    """

    :param term_list:
    :return:
    """
    skip_term = False
    go_ids = set()
    for entry in term_list:
        if entry.startswith(ID):
            go_ids.add(entry[ID_OFFSET:].strip())
        elif entry.startswith(ALT_ID):
            go_ids.add(entry[ALT_ID_OFFSET:].strip())
        elif keep_obsolete is False and entry.startswith(IS_OBSOLETE):
            if 'true' in entry:
                skip_term = True
        elif namespace is not None and namespace != '' and entry.startswith(NAMESPACE):
            if namespace not in entry:
                skip_term = True

    if skip_term is True:
        go_ids_to_skip.update(go_ids)
    return skip_term


def convert_symbol(x):
    x = x['symbol']
    if len(x) == 1:
        return x[0]
    else:
        return x.tolist()


def convert_entrezgene(x):
    x = x['entrezgene'].astype(int).astype(str)
    if len(x) == 1:
        return x[0]
    else:
        return x.tolist()


def download_go_basic(gobasic=None, outputdir=None):
    """
    Downloads go-basic.obo from Gene Ontology site specified by
    **gobasic** URL passed in to file under **outputdir**

    :param gourl: URL to Gene Ontology go-basic.obo file
    :type gourl: str
    :param outputdir: Directory to write obo file to
    :return: Path to downloaded go-basic.obo file
    :rtype: str
    """
    go_basic_file = os.path.join(outputdir, GO_BASIC_OBO)
    if not os.path.isfile(go_basic_file):
        # Download GO obo file
        r = requests.get(gobasic)
        with open(go_basic_file, 'wb') as f:
            f.write(r.content)
    return go_basic_file


def download_goa_human_gaf(goahuman=None, outputdir=None):
    """

    :param goahuman:
    :param outputdir:
    :return:
    """
    goa_human_file = os.path.join(outputdir, GOA_HUMAN_GAF)
    if not os.path.isfile(goa_human_file):
        # Download goa_human.gaf.gz
        r = requests.get(goahuman)
        with open(goa_human_file, 'wb') as f:
            f.write(r.content)
    return goa_human_file


def create_go_basic_filtered(outputdir=None, namespace=None, keep_obsolete=False):
    """

    :param outputdir:
    :param namespace:
    :param keep_obsolete:
    :return:
    """
    go_ids_to_skip = set()
    # keep only cellular component from go-basic.obo
    with open(os.path.join(outputdir, GO_BASIC_OBO)) as f:
        with open(os.path.join(outputdir, GO_BASIC_FILTERED_OBO), 'w') as out:
            term_list = []
            for line in f:
                if line.startswith('['):
                    if len(term_list) > 0:
                        if filter_termlist(term_list=term_list, go_ids_to_skip=go_ids_to_skip,
                                           keep_obsolete=keep_obsolete,
                                           namespace=namespace) is False:
                            for entry in term_list:
                                out.write(entry)
                    term_list.clear()
                term_list.append(line)

            # Filter and write out the last term too silly
            if len(term_list) > 0:
                if filter_termlist(term_list=term_list, go_ids_to_skip=go_ids_to_skip,
                                   keep_obsolete=keep_obsolete,
                                   namespace=namespace) is False:
                    for entry in term_list:
                        out.write(entry)
            term_list.clear()
    return go_ids_to_skip


def main(args):
    """
    Main entry point for program

    :param args:
    :return:
    """
    desc = """
    Downloads GeneOntology and creates hierarchy using DDOT
    
    """
    theargs = _parse_arguments(desc, args[1:])

    try:
        realoutdir = os.path.abspath(theargs.outdir)

        if not os.path.isdir(realoutdir):
            os.makedirs(realoutdir, mode=0o755)

        download_go_basic(theargs.gobasic, outputdir=realoutdir)

        goa_human_file = download_goa_human_gaf(theargs.goahuman, outputdir=realoutdir)

        go_ids_to_skip = create_go_basic_filtered(outputdir=realoutdir,
                                                  namespace=theargs.namespace,
                                                  keep_obsolete=theargs.keep_obsolete)

        # Parse OBO file
        ddot.parse_obo(os.path.join(realoutdir, 'go-basic-filtered.obo'),
                       os.path.join(realoutdir, 'go.tab'),
                       os.path.join(realoutdir, 'goID_2_name.tab'),
                       os.path.join(realoutdir, 'goID_2_namespace.tab'),
                       os.path.join(realoutdir, 'goID_2_alt_id.tab'))

        hierarchy = pd.read_table(os.path.join(realoutdir, 'go.tab'),
                                  sep='\t',
                                  header=None,
                                  names=['Parent', 'Child', 'Relation', 'Namespace'])

        with gzip.open(goa_human_file, 'rb') as f:
            mapping = ddot.parse_gaf(f)

        # need to remove go_ids_to_skip from mapping
        print('Number of entries in goa_human.gaf.gz before cleanup: ' + str(len(mapping)) + '\n')
        mapping.drop(mapping[mapping['GO ID'].isin(go_ids_to_skip)].index, inplace=True)
        print('Number of entries in goa_human.gaf.gz after cleanup: ' + str(len(mapping)) + '\n')

        go_human = Ontology.from_table(
            table=hierarchy,
            parent='Parent',
            child='Child',
            mapping=mapping,
            mapping_child='DB Object ID',
            mapping_parent='GO ID',
            add_root_name='GO:00SUPER',
            ignore_orphan_terms=True)
        go_human.clear_node_attr()
        go_human.clear_edge_attr()

        go_human = go_human.collapse_ontology(method='python')
        if 'GO:00SUPER' not in go_human.terms: go_human.add_root('GO:00SUPER', inplace=True)
        print(go_human)

        go_descriptions = pd.read_table(os.path.join(realoutdir, 'goID_2_name.tab'),
                                        header=None,
                                        names=['Term', 'Term_Description'],
                                        index_col=0)
        go_human.update_node_attr(go_descriptions)

        go_branches = pd.read_table(os.path.join(realoutdir, 'goID_2_namespace.tab'),
                                    header=None,
                                    names=['Term', 'Branch'],
                                    index_col=0)
        go_human.update_node_attr(go_branches)

        mg = mygene.MyGeneInfo()

        name = 'Human-specific Gene Ontology'
        if theargs.namespace is not None and theargs.namespace.strip() != '':
            name + ' ' + str(theargs.namespace)

        go_human_uniprot = go_human.copy()

        # Write GO to file
        go_human_uniprot.to_table(os.path.join(realoutdir, 'collapsed_go.uniprot'), clixo_format=True)
        go_human_uniprot.to_pickle(os.path.join(realoutdir, 'collapsed_go.uniprot.pkl'))

        if theargs.user is not None:
            url, graph = go_human_uniprot.to_ndex(name='%s, %s' % (name, 'UniProt'),
                                                  ndex_server=theargs.server,
                                                  ndex_user=theargs.user,
                                                  ndex_pass=theargs.password,
                                                  layout=None,
                                                  visibility='PUBLIC')
            print(url)

        uniprot_2_symbol_df = mg.querymany(go_human.genes, scopes='uniprot', fields='symbol', species='human',
                                           as_dataframe=True)

        uniprot_2_symbol = uniprot_2_symbol_df.dropna(subset=['symbol']).groupby('query').apply(convert_symbol)

        go_human_symbol = go_human.delete(to_delete=set(go_human.genes) - set(uniprot_2_symbol.keys()))
        go_human_symbol = go_human_symbol.rename(genes=uniprot_2_symbol.to_dict())
        print(go_human_symbol)

        # Write GO to file
        go_human_symbol.to_table(os.path.join(realoutdir, 'collapsed_go.symbol'), clixo_format=True)
        go_human_symbol.to_pickle(os.path.join(realoutdir, 'collapsed_go.symbol.pkl'))

        if theargs.user is not None:
            url, graph = go_human_symbol.to_ndex(name='%s, %s' % (name, 'Symbol'),
                                                 ndex_server=theargs.server,
                                                 ndex_user=theargs.user,
                                                 ndex_pass=theargs.password,
                                                 layout=None,
                                                 visibility='PUBLIC')
            print(url)

        uniprot_2_entrezgene_df = mg.querymany(go_human.genes, scopes='uniprot', fields='entrezgene', species='human',
                                               as_dataframe=True)
        uniprot_2_entrezgene = uniprot_2_entrezgene_df.dropna(subset=['entrezgene']).groupby('query').apply(convert_entrezgene)

        go_human_entrez = go_human.delete(to_delete=set(go_human.genes) - set(uniprot_2_entrezgene.keys()))
        go_human_entrez = go_human_entrez.rename(genes=uniprot_2_entrezgene.to_dict())
        print(go_human_entrez)

        # Write GO to file
        go_human_entrez.to_table(os.path.join(realoutdir, 'collapsed_go.entrez'), clixo_format=True)
        go_human_entrez.to_pickle(os.path.join(realoutdir, 'collapsed_go.entrez.pkl'))

        if theargs.user is not None:
            url, graph = go_human_entrez.to_ndex(name='%s, %s' % (name, 'Entrez'),
                                                 ndex_server=theargs.server,
                                                 ndex_user=theargs.user,
                                                 ndex_pass=theargs.password,
                                                 layout=None,
                                                 visibility='PUBLIC')
            print(url)

    except Exception as e:
        sys.stderr.write('\n\nCaught Exception: ' + str(e))
        traceback.print_exc()
        return 2


if __name__ == '__main__':  # pragma: no cover
    sys.exit(main(sys.argv))
