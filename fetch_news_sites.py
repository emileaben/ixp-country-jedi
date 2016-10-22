from bs4 import BeautifulSoup
import json
import requests

BASE_URL = 'http://abyznewslinks.com/'

def fetch_country_pages():
    """Fetch the map of URLs for the listings for each country"""
    country_map = {}
    country_listing  ='allco.htm'
    response = requests.get(BASE_URL + country_listing)
    soup = BeautifulSoup(response.content, 'html.parser')
    # Not naming things makes me a sad panda and parsing like this exist
    country_table = soup.findAll('table')[5]
    country_links = country_table.findAll('a')
    for country in country_links:
        country_map[country.text.lower()] = BASE_URL + country.attrs['href']
    return country_map

def news_sites_for_country(country_page):
    """Given a URL to the listing of news sites in a country, return a list
    of news sites URL"""
    news_links = []
    response = requests.get(country_page)
    soup = BeautifulSoup(response.content, 'html.parser')
    # Awesome HTML
    for table in soup.findAll('table')[4:-1]:
        website_links = table.findAll('a')
        news_links.extend(link.attrs.get('href') for link in website_links
            if link.attrs.get('href')
        )
    return news_links

if __name__ == '__main__':
    pages = fetch_country_pages()
    country_news_map = {}
    for country, url in pages.items():
        country_news_map[country] = news_sites_for_country(url)
    with open('./country_news_map.json', 'w') as f:
        f.write(json.dumps(country_news_map))

