from Bio import Entrez
import openai
import requests
import pandas as pd
from urllib import request
import urllib.parse as parse
from utils.openai_query import openai_chat
import os 
import json
import re


def get_genes_from_paragraph(paragraph, config, verbose=False):
    query = f""" 
I have a paragraph
Paragraph:
{paragraph}

I would like to search PubMed to find supporting evidence for the statements in this paragraph. Give me a list of gene symbols from the paragraph. Please only include genes. Return the genes as a comma separated list without spacing, if there are no genes in the statements, please return \"Unknown\" """


    # print(query)
    context = config['CONTEXT']
    gpt_model = config['GPT_MODEL']
    temperature = config['TEMP']
    max_tokens = config['MAX_TOKENS']
    rate_per_token = config['RATE_PER_TOKEN']
    LOG_FILE = config['LOG_NAME']+'log.json'
    DOLLAR_LIMIT = config['DOLLAR_LIMIT']
    
    result, _ = openai_chat(context, query, gpt_model, temperature, max_tokens, rate_per_token, LOG_FILE, DOLLAR_LIMIT)
    if verbose: 
            print("Query:")
            print(query)
            print("Result:")
            print(result)
    if result is not None:
        return [keyword.strip() for keyword in result.split(",")]

def get_molecular_functions_from_paragraph(paragraph, config, verbose=False):

    query = f"""
I would like to search PubMed to find supporting evidence for the statements in a paragraph. Give me a maximum of 3 keywords related to the protein functions or biological processes in the statements. 

Example paragraph:  Involvement of pattern recognition receptors: TLR1, TLR2, and TLR3 are part of the Toll-like receptor family, which recognize pathogen-associated molecular patterns and initiate innate immune responses. NOD2 and NLRP3 are intracellular sensors that also contribute to immune activation.
Example response: immune response,receptors,pathogen

Please don't include gene symbols. Please order keywords by their importance in the paragraph, from high importance to low importance. Return the keywords as a comma separated list without spaces. If there are no keywords matching the criteria, return \"Unknown\" 

Please find keywords for this paragraph:
{paragraph}
    """
    #'''

    context = config['CONTEXT']
    gpt_model = config['GPT_MODEL']
    temperature = config['TEMP']
    max_tokens = config['MAX_TOKENS']
    rate_per_token = config['RATE_PER_TOKEN']
    LOG_FILE = config['LOG_NAME']+'log.json'
    DOLLAR_LIMIT = config['DOLLAR_LIMIT']

    result, _ = openai_chat(context, query, gpt_model, temperature, max_tokens, rate_per_token, LOG_FILE, DOLLAR_LIMIT)
    if verbose: 
            print("Query:")
            print(query)
            print("Result:")
            print(result)
    if result is not None:
        return [keyword.strip() for keyword in result.split(",")]

def is_formated_gene_symbol(symbol):
    # A simple regex to check if the gene symbol is alphanumeric and may contain underscores
    return re.match(r'^\w+$', symbol)
def get_aliased_symbol(gene_symbol):
    encoded_gene_symbol = parse.quote(gene_symbol)  # URL encode the gene symbol
    if not is_formated_gene_symbol(gene_symbol):
        return gene_symbol
    try:
        url = f'http://mygene.info/v3/query?q=symbol:{encoded_gene_symbol}&species=human'
        with request.urlopen(url) as requested:
            result_dict = json.loads(requested.read().decode())

        if len(result_dict['hits']) == 0:
            url = f'http://mygene.info/v3/query?q=alias:{encoded_gene_symbol}&species=human'
            with request.urlopen(url) as requested:
                result_dict = json.loads(requested.read().decode())

            if len(result_dict['hits']) == 0:
                return None
            else:
                return result_dict['hits'][0]['symbol']
        else:
            return gene_symbol
    except Exception as e:
        print("Error detail: ", e)
        return None
    
def get_keywords_combinations(paragraph, config, verbose=False):
    genes = get_genes_from_paragraph(paragraph, config, verbose)
    genes = list(filter(None, [get_aliased_symbol(gene) for gene in genes]))
    functions = get_molecular_functions_from_paragraph(paragraph, config, verbose)
    if (genes is None) or len(genes)==0:
        return None, [], functions, False
    elif genes[0]=='Unknown':
            return None, [], functions, False
    if functions is None or functions[0]=='Unknown': # CH updated the condition
            return None, genes, [], False
        #functions = [] # SA modified binary return
    # CH modify the keywords combination, so search for Titles first then Title/Abstracts
    gene_query_title = " OR ".join(["(%s[Title])"%gene for gene in genes])
    keywords_title = [gene_query_title + " AND (%s[Title])"%function for function in functions]
    
    gene_query = " OR ".join(['"%s"'%gene for gene in genes])
    function_query = " OR ".join(['"%s"'%function for function in functions])
    #keywords = [gene_query + " AND (%s[Title/Abstract])"%function for function in functions]
    #keywords = keywords_title + keywords

    keywords = "(%s) AND (%s) AND (hasabstract[text]) AND humans[mh] NOT Retracted Publication[pt]"%(gene_query, function_query)


    return keywords, genes, functions, False # SA modified
    
def get_mla_citation(doi):
    url = f'https://api.crossref.org/works/{doi}'
    headers = {'accept': 'application/json'}
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        #print(data)
        item = data['message']
        
        authors = item['author']
        formatted_authors = []
        for author in authors:
            formatted_authors.append(f"{author['family']}, {author.get('given', '')}")
        authors_str = ', '.join(formatted_authors)
        
        title = item['title'][0]
        container_title = item['container-title'][0]
        year = item['issued']['date-parts'][0][0]
        volume = item.get('volume', '')
        issue = item.get('issue', '')
        page = item.get('page', '')
        
        mla_citation = f"{authors_str}. \"{title}.\" {container_title}"
        if volume or issue:
            mla_citation += f", vol. {volume}" if volume else ''
            mla_citation += f", no. {issue}" if issue else ''
        mla_citation += f", {year}, pp. {page}."
        
        return mla_citation

## 12/18/2023 IL updated the following main function
def get_mla_citation_from_pubmed_id(paper_dict):
    article = paper_dict['MedlineCitation']['Article']
    #print(article.keys())
    authors = article['AuthorList']
    formatted_authors = []
    for author in authors:
        try:
            last_name = author['LastName'] if author['LastName'] is not None else ''
        except:
            last_name = ''
        try:
            first_name = author['ForeName'] if author['ForeName'] is not None else ''
        except:
            first_name = ''
        formatted_authors.append(f"{last_name}, {first_name}")
    authors_str = ', '.join(formatted_authors)

    title = article['ArticleTitle']
    journal = article['Journal']['Title']
    year = article['Journal']['JournalIssue']['PubDate']['Year']
    try:
        page = article['Pagination']['MedlinePgn']
    except:
        page = " "
    mla_citation = f"{authors_str}. \"{title}\" {journal}"
    if "Volume" in article['Journal']['JournalIssue']['PubDate']:
        volume = article['Journal']['JournalIssue']['PubDate']['Volume']
        mla_citation += f", vol. {volume}" if volume else ''
    elif "Issue" in article['Journal']['JournalIssue']['PubDate']:
        issue = article['Journal']['JournalIssue']['PubDate']['Issue']
        mla_citation += f", no. {issue}" if issue else ''
    mla_citation += f", {year}, pp. {page}"
    no_doi = True
    if "ArticleIdList" in paper_dict['PubmedData'].keys():
        for other_id in paper_dict['PubmedData']['ArticleIdList']:
            if other_id.attributes['IdType']=='doi':
                doi = str(other_id)
                mla_citation += f", doi: https://doi.org/{doi}"
                no_doi = False
    if no_doi:
        mla_citation += "."
    return mla_citation

def get_citation(paper):
    names = ",".join([author['name'] for author in paper['authors']])
    corrected_title = paper['title']
    journal = paper['journal']['name']
    pub_date = paper['publicationDate']
    if 'volume' in paper['journal'].keys(): 
        volume = paper['journal']['volume'].strip()
    else:
        volume = ''
    if 'pages' in paper['journal'].keys():
        pages = paper['journal']['pages'].strip()
    else:
        doi = paper['externalIds']['DOI']
        pages = doi.strip().split(".")[-1]
    citation = f"{names}. {corrected_title} {journal} {volume} ({pub_date[0:4]}):{pages}"
    return citation

## 12/18/2023 IL updated the following main function
def check_title_matching(paper, paragraph, config, n=10, verbose=False):
    ## load config for openai query
    context = config['CONTEXT']
    gpt_model = config['GPT_MODEL']
    temperature = config['TEMP']
    max_tokens = config['MAX_TOKENS']
    rate_per_token = config['RATE_PER_TOKEN']
    LOG_FILE = config['LOG_NAME']+'log.json'
    DOLLAR_LIMIT = config['DOLLAR_LIMIT']
    
    try:
        title = paper['MedlineCitation']['Article']['ArticleTitle']
    except (KeyError, IndexError) as e:
        if verbose:
            print("Error in getting abstract from paper.")
            print("Error detail: ", e)
        return False
    message = f"""
I have a paragraph
Paragraph:
{paragraph}

and an scientific paper title.
Abstract:
{title}

Does this title support paragraph? Please tell me yes or no
"""    
    try:
        result, _ = openai_chat(context, message, gpt_model, temperature, max_tokens, rate_per_token, LOG_FILE, DOLLAR_LIMIT)
    except Exception as e:
        print("Error in openai_chat")
        print("Error detail: ", e)
        result = None
        return False
    if result[:3].lower()=='yes':
        return True
    else:
        return False

## 12/18/2023 IL updated the following main function
def check_abstract_match(paper, paragraph, config, verbose=False):
    ## load config for openai query
    context = config['CONTEXT']
    gpt_model = config['GPT_MODEL']
    temperature = config['TEMP']
    max_tokens = config['MAX_TOKENS']
    rate_per_token = config['RATE_PER_TOKEN']
    LOG_FILE = config['LOG_NAME']+'log.json'
    DOLLAR_LIMIT = config['DOLLAR_LIMIT']

    try:
        abstract = "\n".join(paper['MedlineCitation']['Article']['Abstract']['AbstractText'])
    except (KeyError, IndexError) as e:
        if verbose:
            print("Error in getting abstract from paper.")
            print("Error detail: ", e)
        return False
    message = f"""
I have a paragraph
Paragraph:
{paragraph}

and an abstract.
Abstract:
{abstract}

Does this abstract support paragraph? Please tell me yes or no
        """
        
    try:
        result, _ = openai_chat(context, message, gpt_model, temperature, max_tokens, rate_per_token, LOG_FILE, DOLLAR_LIMIT)
    except Exception as e:
        print("Error in openai_chat")
        print("Error detail: ", e)
        result = None
    if result is not None:
        if verbose:
            print("Query: ", message)
            print("Result: ", result)
        if result[:3].lower()=='yes':
            return True
        else:
            return False

## 12/18/2023 IL updated the following main function
def get_genes_in_abstract(paper, genes, verbose=False):
    ## load config for openai query
    try:
        title = paper['MedlineCitation']['Article']['ArticleTitle']
        abstract = paper['MedlineCitation']['Article']['Abstract']['AbstractText'][0]
    except (KeyError, IndexError) as e:
        if verbose:
            print("Error in getting abstract from paper.")
            print("Error detail: ", e)
        return []
    gene_counts = 0
    genes_in_abstract = []
    for gene in genes:
        if gene.lower() in abstract.lower():
            gene_counts += 1
            genes_in_abstract.append(gene)
    if verbose:
        print("Title: ", title)
        print("Abstract: ", abstract)
        print("Genes: ", ", ".join(genes_in_abstract))
        print(" ")
    return genes_in_abstract
    
def get_n_citation(paper):
    links = Entrez.elink(dbfrom="pubmed", id=paper["MedlineCitation"]["PMID"], linkname="pubmed_pubmed_citedin")
    link_list = []
    record = Entrez.read(links)
    if len(record[0][u'LinkSetDb'])==0:
        return 0
    records = record[0][u'LinkSetDb'][0][u'Link']
    for link in records:
        link_list.append(link[u'Id'])
    return len(link_list)

## 12/18/2023 IL updated the following main function
def sort_paper_by_n_genes_in_abstract(papers, genes, verbose=False):
    return sorted(papers, key=lambda paper: (-len(get_genes_in_abstract(paper, genes, verbose=verbose)), -get_n_citation(paper)))

def get_references(queried_papers, paragraph, config, n=10, verbose=False):
    ## load config for openai query
    context = config['CONTEXT']
    gpt_model = config['GPT_MODEL']
    temperature = config['TEMP']
    max_tokens = config['MAX_TOKENS']
    rate_per_token = config['RATE_PER_TOKEN']
    LOG_FILE = config['LOG_NAME']+'log.json'
    DOLLAR_LIMIT = config['DOLLAR_LIMIT']
        
    citations = []
    for paper in queried_papers:
        try:
            abstract = paper['MedlineCitation']['Article']['Abstract']['AbstractText'][0]
        except (KeyError, IndexError) as e:
            if verbose:
                print("Error in getting abstract from paper.")
                print("Error detail: ", e)
            continue

        message = f"""
I have a paragraph
Paragraph:
{paragraph}

and an abstract.
Abstract:
{abstract}

Does this abstract support one or more statements in this paragraph? Please tell me yes or no
        """
        
        try:
            result = openai_chat(context, message, gpt_model, temperature, max_tokens, rate_per_token, LOG_FILE, DOLLAR_LIMIT)
        except Exception as e:
            print("Error in openai_chat")
            print("Error detail: ", e)
            result = None
        
        if result is not None:
            if result[:3].lower()=='yes':
                try:
                    citation = get_mla_citation_from_pubmed_id(paper)
                    if citation not in citations:
                        citations.append(citation)
                except Exception as e:
                    print("Cannot parse citation even though this paper support pargraph")
                    print("Error detail: ", e)
                    pass
                if len(citations)>=n:
                    return citations
        else:
            result = "No"  
          
        if verbose:
            print("Title: ", paper['MedlineCitation']['Article']['ArticleTitle'])
            print("Query: ")
            print(message)
            print("Result:")
            print(result)
            print("="*200)

    return citations

def search_pubmed(keywords, email, sort_by='relevance', retmax=10): ### CH: sort by relevance
    Entrez.email = email

    search_query = f"{keywords} AND (hasabstract[text])"
    search_handle = Entrez.esearch(db='pubmed', term=search_query, sort=sort_by, retmax=retmax)
    search_results = Entrez.read(search_handle)
    search_handle.close()

    id_list = search_results['IdList']

    if not id_list:
        print("No results found.")
        return []

    fetch_handle = Entrez.efetch(db='pubmed', id=id_list, retmode='xml')
    articles = Entrez.read(fetch_handle)['PubmedArticle']
    fetch_handle.close()

    return articles

def get_papers(keywords, n, email):
    total_papers = []
    #for keyword in keywords:
    print("Searching Keyword :", keywords)
    try:
        pubmed_queried_keywords= search_pubmed(keywords, email=email)
        print("%d papers are found"%len(pubmed_queried_keywords))
        total_papers += list(pubmed_queried_keywords[:n])

    except:
        print("No paper found")
        pass
    return total_papers

def get_references_for_paragraph(paragraph, email, config, n=5, papers_query=20, verbose=False):
    if verbose:
        print("""Extracting keywords from paragraph\nParagraph:\n%s"""%paragraph)
        print("="*75)
    keywords, genes, functions, flag_working = get_keywords_combinations(paragraph, config=config, verbose=verbose) # SA: modified
    if keywords is None:
        print("No keyword generated skip referencing")
        return None
    if verbose:
        print("PubMed Keywords: ", keywords)
    print("Serching paper with keywords...")
    papers = search_pubmed(keywords, email, retmax=papers_query)
    print("%d references are queried"%(len(papers)))
    
    if len(papers)==0:
        print("No paper searched!!")
    sorted_papers = sort_paper_by_n_genes_in_abstract(papers, genes, verbose=False)
    
    #title_matchings = check_title_matching(paper, paragraph, config, verbose=verbose) for paper in sorted_papers]
    title_matching_papers = []
    genes_to_be_searched = genes.copy()
    for paper in sorted_papers:
        genes_in_abstract = get_genes_in_abstract(paper, genes, verbose=False)
        title = paper['MedlineCitation']['Article']['ArticleTitle']
        if len(genes)==1:
            single_gene = True
        else:
            single_gene = False
        if len(genes_in_abstract)>=1:
            title_matching = check_title_matching(paper, paragraph, config, verbose=verbose)
            if title_matching:
                abstract = paper['MedlineCitation']['Article']['Abstract']['AbstractText'][0]
                title_matching_papers.append(paper)
                if verbose:
                    print(title, genes_in_abstract, get_n_citation(paper))
                for gene_in_abstract in genes_in_abstract:
                    if gene_in_abstract in genes_to_be_searched:
                        genes_to_be_searched.remove(gene_in_abstract)
                #print(title)
    print("The number of title matching paper: %d"%len(title_matching_papers))
    paper_for_references = []
    genes_to_be_searched = genes.copy()
    for paper in title_matching_papers:
        if check_abstract_match(paper, paragraph, config, verbose=verbose):
            genes_in_abstract = get_genes_in_abstract(paper, genes, verbose=False)
            if verbose:
                print("Remained genes: ", ",".join(genes_to_be_searched))
            paper_for_references.append(paper)
            for gene_in_abstract in genes_in_abstract:
                if gene_in_abstract in genes_to_be_searched:
                    genes_to_be_searched.remove(gene_in_abstract)
                    print(title)
            if (len(paper_for_references)>=n):
                if not single_gene:
                    if len([ gene_in_abstract for gene_in_abstract in genes_in_abstract if gene_in_abstract in genes_to_be_searched])==0:
                        break
                else:
                    break
    references = [get_mla_citation_from_pubmed_id(paper) for paper in paper_for_references]
    return {"paragraph": paragraph, "keyword": keywords, "references": references}

## 12/18/2023 IL updated the following main function
def get_references_for_paragraphs(paragraphs, email, config, n=5, papers_query=20, verbose=False, return_paragraph_ref_data=False):
    '''
    paragraphs: list of paragraphs
    email: email address for Entrez
    config: config file for openai query
    n: number of papers to be queried for each paragraph
    papers_query: number of papersf paper td
    verbose: if True, print out the process
    MarkedParagraphs: list of tuples (index, paragraph) that are already marked
    saveto: name of the json file to save the paragraph data
    '''
    
    references_paragraphs = []
    paragraph_ref_data = []
    # paragraph_data = {}
    for i, paragraph in enumerate(paragraphs):
        #abstract_paragraph = ["\n".join(paper['MedlineCitation']['Article']['Abstract']['AbstractText']) for paper in paper_for_references]
        reference_search_result = get_references_for_paragraph(paragraph, email, config, n=n, papers_query=papers_query, verbose=verbose)
        if reference_search_result is None:
            references = []
        else:
            references = reference_search_result['references']
        references_paragraphs.append(references)
        paragraph_ref_data.append(reference_search_result)
        print("In paragraph %d, %d references are matched"%(i+1, len(references)))
        print("")
        print("")
        # # Store paragraph, keywords, and references in the dictionary
        # paragraph_data[i] = reference_search_result
        # if os.path.exists(f'{saveto}.json'):
        #     with open(f'{saveto}.json') as json_file:
        #         data = json.load(json_file)
        #     data.update(paragraph_data)
        #     with open(f'{saveto}.json', 'w') as json_file:
        #         json.dump(data, json_file) # update the existing json file 
        # else: #if not exist, create new one
        #     with open(f'{saveto}.json', 'w') as json_file:
        #         json.dump(paragraph_data, json_file)

    n_refs = sum([len(refs) for refs in references_paragraphs])
    print("Total %d references are queried"%n_refs)
    print(references_paragraphs)
    j = 1
    referenced_paragraphs = ""
    footer = "="*200+"\n"
    for paragraph, references in zip(paragraphs, references_paragraphs):
        referenced_paragraphs += paragraph
        
        for reference in references:
            referenced_paragraphs += "[%d]"%j
            footer += "[%d] %s"%(j, reference) + '\n'
            j+=1
        referenced_paragraphs += "\n\n"
    referenced_paragraphs += footer
        # referenced_paragraphs += "\n\nKeyword combinations: %s"%keyword_joined + '\n\n'
    if return_paragraph_ref_data:
        return referenced_paragraphs, paragraph_ref_data#, abstracts
    else:
        return referenced_paragraphs

def iter_dataframe(df, email, config, n=5, papers_query=20, verbose=False, return_paragraph_ref_data=False, id_col='ID', paragraph_col='paragraph', runVersion = "initial", save_path = None):
    df.set_index(id_col, inplace=True)
    if runVersion == "initial":
        df.loc[:,'referenced_analysis'] = None
        
    result_dict = {}
    i = 0
    for paragraph_id, paragraphs in zip(df.index.values, df[paragraph_col].values):
        
        if not pd.isna(df.loc[paragraph_id, 'referenced_analysis']):
            continue # skip this row because already done
        paragraph_list = list(filter(lambda p: len(p.split()) > 5, paragraphs.split("\n")))
        # paragraph_result_dict = {}
        # paragraph_result_dict['paragraphs'] = paragraphs

        referenece_paragraphs, paragraph_ref_data = get_references_for_paragraphs(paragraph_list, email, config, n=n, papers_query=papers_query, verbose=verbose, MarkedParagraphs=[], return_paragraph_ref_data=True)
        # paragraph_result_dict['referenced_paragraphs'] = referenece_paragraphs
        # paragraph_result_dict['paragraph_data'] = paragraph_ref_data
        # result_dict[paragraph_id] = paragraph_result_dict
        result_dict[paragraph_id] = paragraph_ref_data

        df.loc[paragraph_id, 'referenced_analysis'] = referenece_paragraphs
        
        if save_path:
            if i % 10 == 0:
                df.to_csv(save_path +'.tsv', sep='\t', index=True)
                with open(save_path + '_result.json', 'w') as f:
                    json.dump(result_dict, f)
            df.to_csv(save_path +'.tsv', sep='\t', index=True)
            with open(save_path + '_result.json', 'w') as f:
                json.dump(result_dict, f)
        i += 1
        
    
    return df, result_dict