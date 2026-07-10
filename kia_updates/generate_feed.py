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

        # The site now uses a card/list layout: each update is an <a> linking to
        # updateNoticeView, containing a category chip, title h3, date and view count.
        update_links = soup.find_all('a', href=re.compile(r'/updateNoticeView/'))

        if not update_links:
            print("Could not find any update notice entries")
            return updates

        for link in update_links:
            update = self.extract_update_info(link)
            if update:
                updates.append(update)

        return updates

    def extract_update_info(self, link):
        """Extract information from a single update card (anchor element)"""
        update = {}

        # Title from h3
        h3 = link.find('h3')
        if not h3:
            return None
        update['title'] = h3.get_text(strip=True)

        # Link from href attribute
        href = link.get('href', '')
        update['link'] = urljoin(self.base_url, href) if href else self.updates_url

        # Category from the chip/badge span
        chip = link.find('span', class_=re.compile(r'\bchip\b'))
        update['category'] = chip.get_text(strip=True) if chip else ''

        # Date and view count from the meta div (grey text)
        meta_div = link.find('div', class_=re.compile(r'\btext-grey-60\b'))
        if meta_div:
            spans = meta_div.find_all('span')
            date_text = spans[0].get_text(strip=True) if spans else ''
            if date_text:
                update['date'] = self.parse_date(date_text)
            else:
                print(f"Warning: no date found for update '{update.get('title', '')}'")
                update['date'] = datetime.now()

            if len(spans) > 1:
                views_raw = spans[1].get_text(strip=True)
                # Strip any localized "views" label prefix (e.g. "Weergaven29,496" → "29,496")
                # before extracting the numeric view count
                views_clean = re.sub(r'^[^\d]+', '', views_raw)
                update['views'] = views_clean.replace(',', '').replace('.', '')
        else:
            print(f"Warning: no metadata div found for update '{update.get('title', '')}'")
            update['date'] = datetime.now()

        # Build description
        update['description'] = f"Category: {update.get('category', '')}"
        if 'views' in update:
            update['description'] += f" | Views: {update['views']}"

        return update

    def parse_date(self, date_str):
        """Parse date in various formats"""
        try:
            # Handle YYYY-MM-DD format (ISO 8601, current site format)
            if re.match(r'\d{4}-\d{2}-\d{2}$', date_str):
                return datetime.strptime(date_str, '%Y-%m-%d')

            # Handle MM-DD-YYYY format (e.g., '12-15-2025')
            # Note: Kia website uses MM-DD-YYYY format (US style)
            if re.match(r'\d{2}-\d{2}-\d{4}', date_str):
                parts = date_str.split('-')
                month, day, year = int(parts[0]), int(parts[1]), int(parts[2])
                # Validate month is in valid range
                if 1 <= month <= 12:
                    return datetime.strptime(date_str, '%m-%d-%Y')
            
            # Handle DD-Mon-YYYY format (e.g., '09-Sep-2025')
            if re.match(r'\d{2}-\w{3}-\d{4}', date_str):
                return datetime.strptime(date_str, '%d-%b-%Y')
                
        except ValueError:
            pass
            
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

