import requests
from datetime import datetime
import xml.etree.ElementTree as ET
from xml.dom import minidom

class UIBlogRSSGenerator:
    def __init__(self):
        self.base_url = "https://blog.ui.com"
        self.api_url = "https://blog.ui.com/api/articles"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json',
        }

    def fetch_articles(self):
        """Fetch articles from the blog API"""
        try:
            response = requests.get(self.api_url, headers=self.headers, timeout=15)
            response.raise_for_status()
            data = response.json()
            return data.get('data', [])
        except requests.RequestException as e:
            print(f"Error fetching articles: {e}")
            return []

    def parse_date(self, date_str):
        """Parse ISO 8601 date format"""
        if not date_str:
            return datetime.now()

        try:
            # Handle ISO format with timezone (e.g., "2026-02-11T10:37:33.074Z")
            if 'T' in date_str:
                # Remove timezone suffix (Z) and milliseconds
                date_str = date_str.rstrip('Z')
                date_str = date_str.split('.')[0]
                return datetime.fromisoformat(date_str)
        except ValueError:
            pass

        return datetime.now()

    def create_rss_feed(self, articles):
        """Create RSS feed from articles"""
        rss = ET.Element('rss', version='2.0')
        rss.set('xmlns:atom', 'http://www.w3.org/2005/Atom')
        channel = ET.SubElement(rss, 'channel')

        # Add channel metadata
        ET.SubElement(channel, 'title').text = 'UI.com Blog - Unofficial RSS Feed'
        ET.SubElement(channel, 'link').text = self.base_url
        ET.SubElement(channel, 'description').text = 'Unofficial RSS feed for Ubiquiti UI.com blog posts'
        ET.SubElement(channel, 'language').text = 'en-US'
        ET.SubElement(channel, 'lastBuildDate').text = datetime.now().strftime('%a, %d %b %Y %H:%M:%S +0000')
        ET.SubElement(channel, 'generator').text = 'UI Blog RSS Generator'

        # Add atom:link for self-reference
        atom_link = ET.SubElement(channel, '{http://www.w3.org/2005/Atom}link')
        atom_link.set('href', self.base_url + '/rss')
        atom_link.set('rel', 'self')
        atom_link.set('type', 'application/rss+xml')

        # Add items
        for article in articles:
            if not article.get('isVisible', True):
                continue
                
            item = ET.SubElement(channel, 'item')
            
            # Title
            title = article.get('title', 'No title')
            ET.SubElement(item, 'title').text = title
            
            # Link
            slug = article.get('slug', '')
            link = f"{self.base_url}/article/{slug}" if slug else self.base_url
            ET.SubElement(item, 'link').text = link
            
            # Description with cover image
            description = ""
            cover = article.get('cover', {})
            if cover:
                # Use the large format if available, otherwise use the url
                cover_url = None
                if cover.get('formats', {}).get('large'):
                    cover_url = cover['formats']['large'].get('url')
                elif cover.get('url'):
                    cover_url = cover['url']
                    
                if cover_url:
                    description += f'<img src="{cover_url}" alt="{title}"><br><br>'
            
            # Add article description
            article_desc = article.get('description', '')
            description += article_desc
            
            ET.SubElement(item, 'description').text = description
            
            # Publication date
            pub_date_str = article.get('publishedAt') or article.get('createdAt')
            if pub_date_str:
                pub_date = self.parse_date(pub_date_str)
                ET.SubElement(item, 'pubDate').text = pub_date.strftime('%a, %d %b %Y %H:%M:%S +0000')
            
            # GUID
            ET.SubElement(item, 'guid', isPermaLink='true').text = link
            
            # Author
            author = article.get('author', {})
            if author:
                author_name = author.get('name', '')
                if author_name:
                    ET.SubElement(item, 'author').text = author_name

        # Pretty print XML
        xml_str = ET.tostring(rss, encoding='unicode')
        dom = minidom.parseString(xml_str)
        return dom.toprettyxml(indent='  ')

    def save_rss_feed(self, rss_content, filename='ui_blog_rss.xml'):
        """Save RSS feed to file"""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(rss_content)
        print(f"RSS feed saved to {filename}")

    def generate_feed(self):
        """Main method to generate the RSS feed"""
        print("Fetching UI.com blog articles from API...")
        articles = self.fetch_articles()

        if not articles:
            print("No articles found.")
            return None

        print(f"Found {len(articles)} articles:")
        for article in articles:
            pub_date = article.get('publishedAt') or article.get('createdAt', '')
            pub_date_obj = self.parse_date(pub_date) if pub_date else datetime.now()
            print(f"  - {article.get('title', 'Untitled')} ({pub_date_obj.strftime('%Y-%m-%d')})")

        print("\nCreating RSS feed...")
        rss_feed = self.create_rss_feed(articles)

        return rss_feed

# Main execution
if __name__ == "__main__":
    # Generate RSS feed
    generator = UIBlogRSSGenerator()
    rss_feed = generator.generate_feed()

    if rss_feed:
        generator.save_rss_feed(rss_feed)
        print("\nRSS feed generated successfully!")
