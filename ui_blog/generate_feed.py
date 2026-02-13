import requests
from bs4 import BeautifulSoup
from datetime import datetime
import xml.etree.ElementTree as ET
from xml.dom import minidom
import re
from urllib.parse import urljoin
import time

class UIBlogRSSGenerator:
    def __init__(self):
        self.base_url = "https://blog.ui.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9'
        }

    def fetch_blog_page(self):
        """Fetch the main blog page"""
        try:
            response = requests.get(self.base_url, headers=self.headers, timeout=15)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            print(f"Error fetching blog page: {e}")
            return None

    def parse_blog_posts(self, html_content):
        """Parse the HTML content to extract blog posts"""
        soup = BeautifulSoup(html_content, 'html.parser')
        posts = []

        # Try multiple common blog post selectors
        # Common patterns for blog posts
        post_containers = (
            soup.find_all('article') or
            soup.find_all('div', class_=re.compile(r'post|article|entry|blog-post', re.I)) or
            soup.find_all('div', class_=re.compile(r'card', re.I))
        )

        if not post_containers:
            print("Could not find blog post containers")
            return posts

        for container in post_containers[:10]:  # Limit to first 10 posts
            post = self.extract_post_info(container)
            if post:
                posts.append(post)

        return posts

    def extract_post_info(self, container):
        """Extract information from a single blog post container"""
        post = {}

        # Find title and link
        title_elem = (
            container.find('h1') or
            container.find('h2') or
            container.find('h3') or
            container.find('a', class_=re.compile(r'title|heading', re.I))
        )

        if title_elem:
            # Try to find link
            link_elem = title_elem.find('a') if title_elem.name != 'a' else title_elem
            if not link_elem:
                link_elem = container.find('a', href=True)

            if link_elem and link_elem.get('href'):
                post['link'] = urljoin(self.base_url, link_elem['href'])
                post['title'] = title_elem.get_text(strip=True)
            else:
                post['title'] = title_elem.get_text(strip=True)
                post['link'] = self.base_url
        else:
            # Try to find any link
            link_elem = container.find('a', href=True)
            if link_elem:
                post['link'] = urljoin(self.base_url, link_elem['href'])
                post['title'] = link_elem.get_text(strip=True) or 'Untitled Post'
            else:
                return None

        # Find date
        date_elem = (
            container.find('time') or
            container.find('span', class_=re.compile(r'date|time|published', re.I)) or
            container.find('div', class_=re.compile(r'date|time|published', re.I))
        )

        if date_elem:
            date_str = date_elem.get('datetime') or date_elem.get_text(strip=True)
            post['date'] = self.parse_date(date_str)
        else:
            post['date'] = datetime.now()

        # Find description/excerpt
        desc_elem = (
            container.find('div', class_=re.compile(r'excerpt|summary|description|content', re.I)) or
            container.find('p')
        )

        if desc_elem:
            post['description'] = desc_elem.get_text(strip=True)[:500]  # Limit to 500 chars
        else:
            post['description'] = post['title']

        # Find image
        img_elem = container.find('img')
        if img_elem and img_elem.get('src'):
            img_url = urljoin(self.base_url, img_elem['src'])
            post['image'] = img_url

        return post if post.get('title') and post.get('link') else None

    def parse_date(self, date_str):
        """Parse various date formats"""
        if not date_str:
            return datetime.now()

        # Try ISO 8601 format first
        try:
            # Handle ISO format with timezone
            if 'T' in date_str:
                # Remove timezone info for simplicity
                date_str = re.sub(r'[+-]\d{2}:\d{2}$', '', date_str)
                date_str = re.sub(r'Z$', '', date_str)
                return datetime.fromisoformat(date_str.split('.')[0])
        except ValueError:
            pass

        # Try common formats
        date_formats = [
            '%Y-%m-%d',
            '%d-%m-%Y',
            '%m/%d/%Y',
            '%d/%m/%Y',
            '%B %d, %Y',
            '%d %B %Y',
            '%b %d, %Y',
            '%d %b %Y',
            '%Y-%m-%d %H:%M:%S',
            '%d-%m-%Y %H:%M:%S',
        ]

        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        # If no format matches, return current date
        print(f"Could not parse date: {date_str}")
        return datetime.now()

    def create_rss_feed(self, posts):
        """Create RSS feed from posts"""
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
        for post in posts:
            item = ET.SubElement(channel, 'item')
            ET.SubElement(item, 'title').text = post.get('title', 'No title')
            ET.SubElement(item, 'link').text = post.get('link', self.base_url)
            
            # Create description with image if available
            description = ""
            if post.get('image'):
                description += f'<img src="{post["image"]}" alt="Post image"><br><br>'
            description += post.get('description', '')
            ET.SubElement(item, 'description').text = description
            
            ET.SubElement(item, 'pubDate').text = post.get('date', datetime.now()).strftime('%a, %d %b %Y %H:%M:%S +0000')
            ET.SubElement(item, 'guid', isPermaLink='true').text = post.get('link', f"{self.base_url}#{hash(post.get('title', ''))}")

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
        print("Fetching UI.com blog posts...")
        html_content = self.fetch_blog_page()

        if not html_content:
            print("Failed to fetch blog page")
            return None

        print("Parsing blog posts...")
        posts = self.parse_blog_posts(html_content)

        if not posts:
            print("No posts found.")
            return None

        print(f"Found {len(posts)} posts:")
        for post in posts:
            print(f"  - {post['title']} ({post['date'].strftime('%Y-%m-%d')})")

        print("\nCreating RSS feed...")
        rss_feed = self.create_rss_feed(posts)

        return rss_feed

# Main execution
if __name__ == "__main__":
    # Generate RSS feed
    generator = UIBlogRSSGenerator()
    rss_feed = generator.generate_feed()

    if rss_feed:
        generator.save_rss_feed(rss_feed)
        print("\nRSS feed generated successfully!")
