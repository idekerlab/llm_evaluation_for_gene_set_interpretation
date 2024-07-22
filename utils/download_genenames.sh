#!/bin/bash

curl -o ../hgnc_genes.tsv 'https://www.genenames.org/cgi-bin/download/custom?col=gd_app_sym&col=gd_prev_sym&col=gd_aliases&status=Approved&hgnc_dbtag=on&order_by=gd_app_sym_sort&format=text&submit=submit'