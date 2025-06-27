import requests
from bs4 import BeautifulSoup
from datetime import datetime
from xml.etree.ElementTree import Element, SubElement, tostring
import xml.dom.minidom
import re
import time
import locale

# Set Dutch locale for parsing month names, adjust as necessary:
try:
    locale.setlocale(locale.LC_TIME, 'nl_NL.UTF-8')
except:
    # If not available, fallback
    locale.setlocale(locale.LC_TIME, 'nl_NL')

SITE_URL = 'https://www.sparta-rotterdam.nl/'

def parse_nl_datetime(dt_str):
    """Parse '27 juni 2025 - 17:00' into datetime object."""
    # Remove any extra spaces and take only the needed part
    match = re.search(r'(\d+) (\w+) (\d{4})\s*-\s*(\d{2}):(\d{2})', dt_str)
    if match:
        day, month, year, hour, minute = match.groups()
        month = month.lower()
        # Map Dutch month names to numbers if locale failed
        maanden = {
            'januari': 1, 'februari': 2, 'maart': 3, 'april': 4, 'mei': 5, 'juni': 6,
            'juli':7, 'augustus':8, 'september':9, 'oktober':10, 'november':11, 'december':12
        }
        month_nr = maanden.get(month, 1)
        return datetime(int(year), month_nr, int(day), int(hour), int(minute))
    return datetime.now()

def fetch_article_details(url):
    """Visit the article URL and return (published_date, main_html_content)"""
    try:
        resp = requests.get(url, timeout=10)
        soup = BeautifulSoup(resp.text, 'html.parser')

        article = soup.find('article', class_='single')
        if not article:
            return datetime.now(), ""

        # Extract date
        date_span = article.find('span', class_='datetime')
        if date_span:
            pub_date = parse_nl_datetime(date_span.text.strip())
        else:
            pub_date = datetime.now()

        # Extract only p, div.gallery, img, em in order, skip <style> etc
        body_html = ""
        for el in article.find_all(['p', 'div', 'img', 'em'], recursive=False):
            # Only include the gallery divs and paragraphs, not <style> or <script>
            if el.name == 'div' and not el.get('class') or 'gallery' not in ' '.join(el.get('class', [])):
                continue
            if el.name == 'img':
                body_html += str(el)
            else:
                body_html += str(el)

        # Fallback: if above is empty, get all p/galley inside article
        if not body_html:
            wanted = []
            for x in article.find_all(['p', 'div'], recursive=True):
                if x.name == 'div' and x.get('class') and 'gallery' in x['class']:
                    wanted.append(str(x))
                if x.name == 'p':
                    wanted.append(str(x))
            body_html = "".join(wanted)

        return pub_date, body_html

    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return datetime.now(), "Could not fetch article content."

def fetch_articles():
    resp = requests.get(SITE_URL)
    soup = BeautifulSoup(resp.text, 'html.parser')
    articles = []

    for art in soup.select('article.news_item')[:8]:
        a = art.find('a', class_='item_link')
        title = art.find('h3')
        label = art.find('span', class_='item_label')
        link = a['href'] if a else ''
        if not link.startswith('http'):
            link = SITE_URL.rstrip('/') + '/' + link.lstrip('/')

        # Try to get image URL from style if desired
        img_url = ""
        if 'style' in art.attrs:
            match = re.search(r'url\(([^)]+)\)', art['style'])
            if match:
                img_url = match.group(1)

        print(f"Fetching details for: {link}")
        pub_date, article_html = fetch_article_details(link)
        pub_date_rss = pub_date.strftime('%a, %d %b %Y %H:%M:%S +0100')

        # Compose description (label + optional image + article content)
        description = ""
        if label:
            description += f"<strong>{label.text.strip()}</strong><br>"
        if img_url:
            description += f'<img src="{img_url}"><br>'
        description += article_html

        articles.append({
            'title': title.text.strip() if title else '',
            'link': link,
            'description': description,
            'pubDate': pub_date_rss,
        })

        time.sleep(0.7)  # Be polite

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
