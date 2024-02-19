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

    url_suffixes = get_target_data()
    url_suffixes = [url_suffix for url_suffix in url_suffixes if 'author' not in url_suffix]
    # url_suffixes = url_suffixes[0:5]
    
    texts = get_content(base_url, url_suffixes)
    dicts = parse_content(texts)


    con = sqlite3.connect("tutorial.db")
    cur = con.cursor()

    try:
        cur.execute("CREATE TABLE articles(url, text, people)")
    except:
        None

    for i in range(len(url_suffixes)):
        url = url_suffixes[i]
        text = texts[i]
        PERSON = dicts[i]["PERSON"]

        sqlite_insert_with_param = """INSERT INTO articles
                                      (url, text, people) 
                                      VALUES (?, ?, ?);"""

        data_tuple = (url, text, json.dumps(PERSON))
        cur.execute(sqlite_insert_with_param, data_tuple)
        con.commit()



def parse_content(texts):
    dicts = []
    for text in texts:
        print(text)
        nlp = spacy.load("en_core_web_sm")
        doc = nlp(text)

        if doc.ents:
            ent_dict = {}

            labels = list(set([ent.label_ for ent in doc.ents]))

            for ent in doc.ents:
                if str(ent.label_) in ent_dict.keys():
                    if str(ent) not in ent_dict[str(ent.label_)]:
                        ent_dict[str(ent.label_)] += [str(ent)]
                else:
                    ent_dict[str(ent.label_)] = [str(ent)]

        dicts.append(ent_dict)

    return dicts

def get_content(base_url, url_suffixes):
    return_texts = []
    
    for url_suffix in url_suffixes:
        target_url = f"{base_url}{url_suffix}"
        print(target_url)
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
    r = requests.get(target_url)

    if r.status_code == 200:
        return r.text
    else:
        return ''


def get_target_data():

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


def clean_html_content(soup, target_url):

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


if __name__ == "__main__":
    main()