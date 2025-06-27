import requests
from bs4 import BeautifulSoup
from datetime import datetime
from xml.etree.ElementTree import Element, SubElement, tostring
import xml.dom.minidom
import re
import time

SITE_URL = 'https://www.sparta-rotterdam.nl/'

def fetch_article_details(url):
    """Visit the article URL and return (published_date, content_html)"""
    try:
        resp = requests.get(url, timeout=10)
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Adjust selectors below as needed!
        # Example for WordPress/themes:
        date_elem = soup.find('time')
        if date_elem and (date_elem.has_attr('datetime') or date_elem.text.strip()):
            if date_elem.has_attr('datetime'):
                pub_date_str = date_elem['datetime']
            else:
                pub_date_str = date_elem.text.strip()
            try:
                pub_date = datetime.fromisoformat(pub_date_str.replace('Z', '+00:00'))
            except:
                pub_date = datetime.now()
        else:
            pub_date = datetime.now()

        # Content: try both common names, tweak as needed
        content_elem = soup.find('div', class_='entry-content') or soup.find('div', class_='content')
        if content_elem:
            content_html = str(content_elem)
        else:
            # Fallback to whole page
            content_html = soup.get_text()
        
        return pub_date, content_html

    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return datetime.now(), "Could not fetch article content."

def fetch_articles():
    resp = requests.get(SITE_URL)
    soup = BeautifulSoup(resp.text, 'html.parser')
    articles = []

    # Limit to first 8 for speed
    for art in soup.select('article.news_item')[:8]:
        a = art.find('a', class_='item_link')
        title = art.find('h3')
        label = art.find('span', class_='item_label')
        link = a['href'] if a else ''
        if not link.startswith('http'):
            link = SITE_URL.rstrip('/') + '/' + link.lstrip('/')

        # Try to get image URL from style
        img_url = ""
        if 'style' in art.attrs:
            match = re.search(r'url\(([^)]+)\)', art['style'])
            if match:
                img_url = match.group(1)

        print(f"Fetching details for: {link}")
        pub_date, content_html = fetch_article_details(link)
        # For output, RFC822 date, which RSS readers expect
        pub_date_rss = pub_date.strftime('%a, %d %b %Y %H:%M:%S +0100')

        # Compose article description with optional image and content
        description = label.text.strip() if label else ""
        if img_url:
            description += f'<br><img src="{img_url}">'
        description += content_html

        articles.append({
            'title': title.text.strip() if title else '',
            'link': link,
            'description': description,
            'pubDate': pub_date_rss,
        })

        time.sleep(0.5)  # Be polite to server!

    return articles

def build_rss(articles):
    rss = Element('rss')
    rss.set('version', '2.0')
    channel = SubElement(rss, 'channel')

    title = SubElement(channel, 'title')
    title.text = "Sparta Rotterdam nieuws (onofficieel)"
    link = SubElement(channel, 'link')
    link.text = SITE_URL
    description = SubElement(channel, 'description')
    description.text = "Ongeofficieel RSS-nieuwsfeed voor Sparta Rotterdam"

    for article in articles:
        item = SubElement(channel, 'item')
        for key, value in article.items():
            elem = SubElement(item, key)
            elem.text = value

    raw_xml = tostring(rss, 'utf-8')
    dom = xml.dom.minidom.parseString(raw_xml)
    pretty_xml = dom.toprettyxml(indent="  ")
    return pretty_xml

if __name__ == "__main__":
    articles = fetch_articles()
    if not articles:
        print("Geen artikelen gevonden!")
    else:
        rss_feed = build_rss(articles)
        with open("sparta_rss.xml", "w", encoding='utf-8') as f:
            f.write(rss_feed)
        print("RSS geschreven naar sparta_rss.xml")
