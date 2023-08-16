from Bio import Entrez
import openai
import requests
from utils.openai_query import openai_chat
import os 
import json


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
    
    result = openai_chat(context, query, gpt_model, temperature, max_tokens, rate_per_token, LOG_FILE, DOLLAR_LIMIT)
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

    result = openai_chat(context, query, gpt_model, temperature, max_tokens, rate_per_token, LOG_FILE, DOLLAR_LIMIT)
    if verbose: 
            print("Query:")
            print(query)
            print("Result:")
            print(result)
    if result is not None:
        return [keyword.strip() for keyword in result.split(",")]
    
def get_keywords_combinations(paragraph, config, verbose=False):
    genes = get_genes_from_paragraph(paragraph, config, verbose)
    functions = get_molecular_functions_from_paragraph(paragraph, config, verbose)
    if genes is None or functions is None: # CH updated the condition
        return [], True # SA modified binary return
    if genes[0]=='Unknown' or functions[0]=='Unknown':
        return [], False # SA modified
    # CH modify the keywords combination, so search for Titles first then Title/Abstracts
    gene_query_title = " OR ".join(["(%s[Title])"%gene for gene in genes])
    keywords_title = [gene_query_title + " AND (%s[Title])"%function for function in functions]
    
    gene_query = " OR ".join(["(%s[Title/Abstract])"%gene for gene in genes])
    keywords = [gene_query + " AND (%s[Title/Abstract])"%function for function in functions]
    keywords = keywords_title + keywords

    return keywords, False # SA modified
    
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
    
def get_mla_citation_from_pubmed_id(paper_dict):
    article = paper_dict['MedlineCitation']['Article']
    #print(article.keys())
    authors = article['AuthorList']
    formatted_authors = []
    for author in authors:
        last_name = author['LastName'] if author['LastName'] is not None else ''
        first_name = author['ForeName'] if author['ForeName'] is not None else ''
        formatted_authors.append(f"{last_name}, {first_name}")
    authors_str = ', '.join(formatted_authors)

    title = article['ArticleTitle']
    journal = article['Journal']['Title']
    year = article['Journal']['JournalIssue']['PubDate']['Year']
    page = article['Pagination']['MedlinePgn']
    mla_citation = f"{authors_str}. \"{title}\" {journal}"
    if "Volume" in article['Journal']['JournalIssue']['PubDate']:
        volume = article['Journal']['JournalIssue']['PubDate']['Volume']
        mla_citation += f", vol. {volume}" if volume else ''
    elif "Issue" in article['Journal']['JournalIssue']['PubDate']:
        issue = article['Journal']['JournalIssue']['PubDate']['Issue']
        mla_citation += f", no. {issue}" if issue else ''
    mla_citation += f", {year}, pp. {page}."
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
    for keyword in keywords:
        print("Searching Keyword :", keyword)
        try:
            pubmed_queried_keywords= search_pubmed(keyword, email=email)
            print("%d papers are found"%len(pubmed_queried_keywords))
            total_papers += list(pubmed_queried_keywords[:n])
            
        except:
            print("No paper found")
            pass
    return total_papers

## 06/12/2023 CH updated the following main function
def get_references_for_paragraphs(paragraphs, email, config, n=5, verbose=False, MarkedParagraphs=[], saveto = 'paragraph_ref_data'):
    '''
    paragraphs: list of paragraphs
    email: email address for Entrez
    config: config file for openai query
    n: number of papers to be queried for each paragraph
    verbose: if True, print out the process
    MarkedParagraphs: list of tuples (index, paragraph) that are already marked
    saveto: name of the json file to save the paragraph data
    '''
    
    references_paragraphs = []
    paragraph_data = {}
    for i, paragraph in enumerate(paragraphs):
        if verbose:
            print("""Extracting keywords from paragraph\nParagraph:\n%s"""%paragraph)
            print("="*75)
        keywords, flag_working = get_keywords_combinations(paragraph, config = config, verbose=verbose) # SA: modified
        if flag_working: # collect genes or functions keywords return None and come back later 
            MarkedParagraphs.append((i,paragraph))
        #keywords = list(sorted(keywords, key=len))
        # keyword_joined = ",".join(keywords)
        # print("Keywords: ", keyword_joined)
        print("Serching paper with keywords...")
        pubmed_queried_keywords= get_papers(keywords, n, email)

        print("In paragraph %d, %d references are queried"%(i+1, len(pubmed_queried_keywords)))
        
        if len(pubmed_queried_keywords)==0:
            print("No paper searched!!")
        references = get_references(pubmed_queried_keywords, paragraph, config = config, n=n, verbose=verbose)
        references_paragraphs.append(references) 
        print("In paragraph %d, %d references are matched"%(i+1, len(references)))
        print("")
        print("")
        
        # Store paragraph, keywords, and references in the dictionary
        paragraph_data[paragraph] = {
            'keywords': keywords,
            'references': references
        }
        if os.path.exists(f'{saveto}.json'):
            with open(f'{saveto}.json') as json_file:
                data = json.load(json_file)
            data.update(paragraph_data)
            with open(f'{saveto}.json', 'w') as json_file:
                json.dump(data, json_file) # update the existing json file 
        else: #if not exist, create new one
            with open(f'{saveto}.json', 'w') as json_file:
                json.dump(paragraph_data, json_file)
        
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
        # referenced_paragraphs += "\n\nKeyword combinations: %s"%keyword_joined + '\n\n'

            
    return referenced_paragraphs + footer

