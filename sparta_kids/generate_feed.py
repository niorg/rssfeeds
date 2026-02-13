import requests
from bs4 import BeautifulSoup
from datetime import datetime
import xml.etree.ElementTree as ET
from xml.dom import minidom
import re
import time

class SpartaKidsRSSGenerator:
    def __init__(self):
        self.base_url = 'https://www.sparta-rotterdam.nl'
        self.site_url = f'{self.base_url}/kidsclub/'
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'nl-NL,nl;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        self.session = requests.Session()

    def parse_nl_datetime(self, dt_str):
        """Parse '27 juni 2025 - 17:00' into datetime object."""
        match = re.search(r'(\d+) (\w+) (\d{4})\s*-\s*(\d{2}):(\d{2})', dt_str)
        if match:
            day, month, year, hour, minute = match.groups()
            month = month.lower()
            maanden = {
                'januari': 1, 'februari': 2, 'maart': 3, 'april': 4, 'mei': 5, 'juni': 6,
                'juli': 7, 'augustus': 8, 'september': 9, 'oktober': 10, 'november': 11, 'december': 12
            }
            month_nr = maanden.get(month, 1)
            return datetime(int(year), month_nr, int(day), int(hour), int(minute))
        return datetime.now()

    def fetch_articles(self):
        """Fetch articles from Sparta Rotterdam Kidsclub website"""
        try:
            response = self.session.get(self.site_url, headers=self.headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            articles = []

            # Try to find news items with various selectors
            news_items = soup.select('article.news_item')
            
            if not news_items:
                # Try alternative selectors
                news_items = soup.find_all('article', class_=lambda x: x and 'news' in str(x).lower())
            
            if not news_items:
                print("No articles found with expected selectors")
                return []

            for art in news_items[:8]:
                article = self.parse_article(art)
                if article:
                    articles.append(article)
                    time.sleep(0.7)  # Be polite

            return articles
            
        except requests.HTTPError as e:
            if e.response.status_code == 403:
                print(f"Access denied (403 Forbidden). The website may be blocking automated requests.")
                print(f"This is a limitation of the Sparta Rotterdam website's anti-bot protection.")
            else:
                print(f"HTTP error fetching articles: {e}")
            return []
        except requests.RequestException as e:
            print(f"Error fetching articles: {e}")
            return []

    def parse_article(self, art):
        """Parse a single article element"""
        try:
            # Find link
            a = art.find('a', class_='item_link')
            if not a or 'href' not in a.attrs:
                return None
                
            link = a['href']
            if not link.startswith('http'):
                link = self.base_url.rstrip('/') + '/' + link.lstrip('/')

            # Find title
            title_elem = art.find('h3')
            title = title_elem.text.strip() if title_elem else 'Untitled'

            # Find label/category
            label_elem = art.find('span', class_='item_label')
            label = label_elem.text.strip() if label_elem else ''

            # Try to get image URL from style attribute
            img_url = ""
            if 'style' in art.attrs:
                match = re.search(r'url\(([^)]+)\)', art['style'])
                if match:
                    img_url = match.group(1)

            # Fetch article details
            print(f"Fetching details for: {title}")
            pub_date, article_html = self.fetch_article_details(link)

            # Compose description
            description = ""
            if label:
                description += f"<strong>{label}</strong><br>"
            if img_url:
                description += f'<img src="{img_url}"><br>'
            description += article_html

            return {
                'title': title,
                'link': link,
                'description': description,
                'pubDate': pub_date
            }
            
        except Exception as e:
            print(f"Error parsing article: {e}")
            return None

    def fetch_article_details(self, url):
        """Visit the article URL and return (published_date, main_html_content)"""
        try:
            resp = self.session.get(url, headers=self.headers, timeout=10)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'html.parser')

            article = soup.find('article', class_='single')
            if not article:
                return datetime.now(), ""

            # Extract date
            date_span = article.find('span', class_='datetime')
            if date_span:
                pub_date = self.parse_nl_datetime(date_span.text.strip())
            else:
                pub_date = datetime.now()

            # Extract article content
            body_html = ""
            for el in article.find_all(['p', 'div', 'img', 'em'], recursive=True):
                if el.name in ('style', 'script'):
                    continue
                if el.name == "div":
                    if "gallery" in el.get("class", []):
                        body_html += str(el)
                    continue
                body_html += str(el)

            return pub_date, body_html

        except Exception as e:
            print(f"Error scraping {url}: {e}")
            return datetime.now(), "Could not fetch article content."

    def create_rss_feed(self, articles):
        """Create RSS feed from articles"""
        from xml.sax.saxutils import escape
        
        # Build RSS feed manually to properly handle CDATA
        rss_parts = ['<?xml version="1.0" encoding="UTF-8"?>']
        rss_parts.append('<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">')
        rss_parts.append('<channel>')
        
        # Add channel metadata
        rss_parts.append(f'<title>{escape("Sparta Rotterdam Kidsclub nieuws (onofficieel)")}</title>')
        rss_parts.append(f'<link>{escape(self.site_url)}</link>')
        rss_parts.append(f'<description>{escape("Ongeofficieel RSS-nieuwsfeed voor Sparta Rotterdam Kidsclub")}</description>')
        rss_parts.append('<language>nl-NL</language>')
        rss_parts.append(f'<lastBuildDate>{datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0000")}</lastBuildDate>')
        rss_parts.append('<generator>Sparta Rotterdam Kidsclub RSS Generator</generator>')

        # Add items
        for article in articles:
            rss_parts.append('<item>')
            rss_parts.append(f'<title>{escape(article["title"])}</title>')
            rss_parts.append(f'<link>{escape(article["link"])}</link>')
            
            # Use CDATA for description to preserve HTML
            rss_parts.append(f'<description><![CDATA[{article["description"]}]]></description>')
            
            pub_date = article['pubDate']
            rss_parts.append(f'<pubDate>{pub_date.strftime("%a, %d %b %Y %H:%M:%S +0100")}</pubDate>')
            rss_parts.append(f'<guid isPermaLink="true">{escape(article["link"])}</guid>')
            rss_parts.append('</item>')

        rss_parts.append('</channel>')
        rss_parts.append('</rss>')
        
        # Pretty print the XML
        xml_str = '\n'.join(rss_parts)
        try:
            dom = minidom.parseString(xml_str)
            return dom.toprettyxml(indent='  ')
        except:
            # If pretty printing fails, return as-is
            return xml_str

    def save_rss_feed(self, rss_content, filename='sparta_rss.xml'):
        """Save RSS feed to file"""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(rss_content)
        print(f"RSS feed saved to {filename}")

    def generate_feed(self):
        """Main method to generate the RSS feed"""
        print("Fetching Sparta Rotterdam Kidsclub articles...")
        articles = self.fetch_articles()

        if not articles:
            print("No articles found.")
            return None

        print(f"\nFound {len(articles)} articles")

        print("\nCreating RSS feed...")
        rss_feed = self.create_rss_feed(articles)

        return rss_feed

# Main execution
if __name__ == "__main__":
    generator = SpartaKidsRSSGenerator()
    rss_feed = generator.generate_feed()

    if rss_feed:
        generator.save_rss_feed(rss_feed)
        print("\nRSS feed generated successfully!")
    else:
        print("\nFailed to generate RSS feed.")
        print("Note: The Sparta Rotterdam website may be blocking automated access.")

