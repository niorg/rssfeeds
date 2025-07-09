import requests
from bs4 import BeautifulSoup
from datetime import datetime
import xml.etree.ElementTree as ET
from xml.dom import minidom
import re
from urllib.parse import urljoin

class KiaUpdateRSSGenerator:
    def __init__(self):
        self.base_url = "https://update.kia.com"
        self.updates_url = f"{self.base_url}/EU/NL/updateNoticeList"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'nl-NL,nl;q=0.9,en;q=0.8'
        }

    def fetch_updates(self, page=1):
        """Fetch the update notices from Kia website"""
        try:
            # Add page parameter if needed
            url = self.updates_url
            if page > 1:
                url = f"{url}?page={page}"

            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            print(f"Error fetching updates: {e}")
            return None

    def parse_updates(self, html_content):
        """Parse the HTML content to extract update information"""
        soup = BeautifulSoup(html_content, 'html.parser')
        updates = []

        # Find the table container
        table_container = soup.find('div', class_='tbl')

        if not table_container:
            print("Could not find the table container")
            return updates

        # Find all update rows (they have class 'row' and 'body')
        update_rows = table_container.find_all('div', class_=re.compile(r'row.*body'))

        for row in update_rows:
            update = self.extract_update_info(row)
            if update:
                updates.append(update)

        return updates

    def extract_update_info(self, row):
        """Extract information from a single update row"""
        update = {}

        # Extract columns
        cols = row.find_all('div', class_=re.compile(r'col-'))

        if len(cols) >= 3:
            # Category (first column)
            category = cols[0].get_text(strip=True)

            # Title and link (second column)
            title_col = cols[1]
            link_elem = title_col.find('a')

            if link_elem:
                update['title'] = link_elem.get_text(strip=True)
                href = link_elem.get('href', '')
                update['link'] = urljoin(self.base_url, href)
            else:
                update['title'] = title_col.get_text(strip=True)
                update['link'] = self.updates_url

            # Date (third column)
            date_text = cols[2].get_text(strip=True)
            update['date'] = self.parse_date(date_text)

            # Views (fourth column if exists)
            if len(cols) >= 4:
                views_text = cols[3].get_text(strip=True)
                update['views'] = views_text.replace(',', '')

            # Create description
            update['description'] = f"Category: {category}"
            if 'views' in update:
                update['description'] += f" | Views: {update['views']}"

            # Add category as a separate field for RSS categories
            update['category'] = category

        return update if update.get('title') else None

    def parse_date(self, date_str):
        """Parse date in format like '09-Jul-2025'"""
        try:
            # Handle the specific format from the website
            return datetime.strptime(date_str, '%d-%b-%Y')
        except ValueError:
            # Try other common formats
            date_formats = [
                '%d-%m-%Y', '%d/%m/%Y', '%Y-%m-%d',
                '%d.%m.%Y', '%Y.%m.%d', '%d %B %Y',
                '%B %d, %Y', '%d %b %Y'
            ]

            for fmt in date_formats:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue

            # If no format matches, return current date
            print(f"Could not parse date: {date_str}")
            return datetime.now()

    def create_rss_feed(self, updates):
        """Create RSS feed from updates"""
        rss = ET.Element('rss', version='2.0')
        channel = ET.SubElement(rss, 'channel')

        # Add channel metadata
        ET.SubElement(channel, 'title').text = 'Kia Navigation Updates - Netherlands'
        ET.SubElement(channel, 'link').text = self.updates_url
        ET.SubElement(channel, 'description').text = 'Laatste navigatie-updates en meldingen van Kia Nederland'
        ET.SubElement(channel, 'language').text = 'nl-NL'
        ET.SubElement(channel, 'lastBuildDate').text = datetime.now().strftime('%a, %d %b %Y %H:%M:%S +0000')
        ET.SubElement(channel, 'generator').text = 'Kia Update RSS Generator'

        # Add items
        for update in updates:
            item = ET.SubElement(channel, 'item')
            ET.SubElement(item, 'title').text = update.get('title', 'No title')
            ET.SubElement(item, 'link').text = update.get('link', self.updates_url)
            ET.SubElement(item, 'description').text = update.get('description', '')
            ET.SubElement(item, 'pubDate').text = update.get('date', datetime.now()).strftime('%a, %d %b %Y %H:%M:%S +0000')
            ET.SubElement(item, 'guid', isPermaLink='true').text = update.get('link', f"{self.updates_url}#{hash(update.get('title', ''))}")

            # Add category if available
            if update.get('category'):
                ET.SubElement(item, 'category').text = update['category']

        # Pretty print XML
        xml_str = ET.tostring(rss, encoding='unicode')
        dom = minidom.parseString(xml_str)
        return dom.toprettyxml(indent='  ')

    def save_rss_feed(self, rss_content, filename='kia_updates.xml'):
        """Save RSS feed to file"""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(rss_content)
        print(f"RSS feed saved to {filename}")

    def generate_feed(self):
        """Main method to generate the RSS feed"""
        print("Fetching Kia updates...")
        html_content = self.fetch_updates()

        if not html_content:
            print("Failed to fetch updates")
            return None

        print("Parsing updates...")
        updates = self.parse_updates(html_content)

        if not updates:
            print("No updates found.")
            return None

        print(f"Found {len(updates)} updates:")
        for update in updates:
            print(f"  - {update['title']} ({update['date'].strftime('%d-%b-%Y')})")

        print("\nCreating RSS feed...")
        rss_feed = self.create_rss_feed(updates)

        return rss_feed

# Main execution
if __name__ == "__main__":
    # Generate RSS feed
    generator = KiaUpdateRSSGenerator()
    rss_feed = generator.generate_feed()

    if rss_feed:
        generator.save_rss_feed(rss_feed)
        print("\nRSS feed generated successfully!")

