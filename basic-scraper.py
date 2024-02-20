import requests
from bs4 import BeautifulSoup
import re
import time
import spacy
from pprint import pprint
import sqlite3
import json

def main():
    base_url = 'https://www.aljazeera.com'

    # Store data in local sqlite db
    con = sqlite3.connect("tutorial.db")
    cur = con.cursor()

    # Get list of target urls
    url_suffixes = get_target_urls()
    url_suffixes = filter_urls(url_suffixes, cur)

    # Actually visit the urls and parse the content
    texts = extract_target_texts(base_url, url_suffixes)
    dicts = create_entity_dicts(texts)

    # In case the sqllite db needs to be created again
    setup_db()
    
    # Save data
    save_data_in_db(url_suffixes, texts, dicts, cur, con)


def setup_db():
    # Basic try except to ensure there's actually a table to write to
    try:
        cur.execute("CREATE TABLE articles(url, text, people)")
    except:
        None


def save_data_in_db(url_suffixes, texts, dicts, cur, con):
    # Iterate over the collected data, adding rows in the table
    sqlite_insert_with_param = """INSERT INTO articles
                                  (url, text, people) 
                                  VALUES (?, ?, ?);"""

    for i in range(len(url_suffixes)):
        url = url_suffixes[i]
        text = texts[i]
        if "PERSON" in dicts[i].keys():
            PERSON = dicts[i]["PERSON"]
        else:
            PERSON = []

        data_tuple = (url, text, json.dumps(PERSON))
        cur.execute(sqlite_insert_with_param, data_tuple)
        con.commit()


def extract_target_texts(base_url, url_suffixes):
    # For every suffix url, visit the url and pull content
    # Then parse said content
    return_texts = []
    
    for url_suffix in url_suffixes:
        target_url = f"{base_url}{url_suffix}"
        html_str = get_html_content(target_url)

        try:
            soup = BeautifulSoup(html_str, features="html.parser") # Basic html parser
            soup = clean_html_content(soup, target_url)
        except Exception as e:
            print(e)
        
        return_texts.append(soup.text)
        
        time.sleep(5)

    return return_texts


def get_html_content(target_url):
    # Basic error handling on a get request
    r = requests.get(target_url)

    if r.status_code == 200:
        return r.text
    else:
        return ''


def get_target_urls():
    # Visit the homepage and pull all urls that appear
    r = requests.get('https://www.aljazeera.com')

    if r.status_code == 200:
        return parse_urls(r.text)
    else:
        print("It failed")
        return []


def parse_urls(html_str):
    # In case there's an issue
    try:
        soup = BeautifulSoup(html_str, features="html.parser") # Basic html parser
    except Exception as e:
        print(e)
        return []

    # Pull urls and filter    
    urls = soup.find_all('a')
    urls = [a.get("href") for a in urls]

    # Filter out base annoying urls
    urls = [url for url in urls if "http" not in url]

    pattern = re.compile("\d{4}") # Check if urls have 4 digit in them, usually for year
    urls = [url for url in urls if pattern.search(url)]
    return list(set(urls))


def filter_urls(url_suffixes, cur):
    # Clean out list of target urls
    url_suffixes = remove_previous_urls(url_suffixes, cur)
    url_suffixes = [url_suffix for url_suffix in url_suffixes if 'author' not in url_suffix]
    return url_suffixes


def remove_previous_urls(urls, cur):
    # Check to see if any urls were previously saved.
    # If there are any, filter them out
    ret_urls = []
    try:
        res = cur.execute("SELECT url FROM articles")
        prev_urls = [item[0] for item in res.fetchall()]
    except:
        return urls

    for url in urls:
        if not url in prev_urls:
            ret_urls.append(url)
    return ret_urls


def clean_html_content(soup, target_url):
    # Remove a bunch of content
    # in order to ensure a more clean view

    target_div_classes = ["container--header", "article-source", "article-featured-image", 
                          "bread-crumb", "article-info-block", "article-dates", 
                          "navigation-bar--sticky", "responsive-image", "article__featured-video-wrapper"]
    
    target_tags = ["title", "footer", "header", "aside"]

    for target_class in target_div_classes:
        for div in soup.find_all("div", {"class": target_class}):
            div.clear()

    for div in soup.find_all("figure", {"class": "article-featured-image"}):
        div.clear()
    
    for tag in target_tags:
        for div in soup.find_all(tag):
            div.clear()

    return soup


def create_entity_dicts(texts):
    # Parse content using nlp
    # and pull out all entities

    dicts = []
    for text in texts:
        nlp = spacy.load("en_core_web_sm")
        doc = nlp(text)

        ent_dict = {}

        if doc.ents:
            ent_dict = sort_doc_entities(doc)

        dicts.append(ent_dict)

    return dicts


def sort_doc_entities(doc):
    # Function to take a doc object, and extract all
    # entities into a dictionary
    ent_dict = {}

    labels = list(set([ent.label_ for ent in doc.ents]))

    for ent in doc.ents:
        if str(ent.label_) in ent_dict.keys():
            if str(ent) not in ent_dict[str(ent.label_)]:
                ent_dict[str(ent.label_)] += [str(ent)]
            else:
                ent_dict[str(ent.label_)] = [str(ent)]
    
    return ent_dict


if __name__ == "__main__":
    main()