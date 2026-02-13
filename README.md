# RSS Feeds Generator

This repository generates RSS feeds for websites that don't provide them.

## Feeds

### ✅ Working Feeds

#### UI.com Blog
- **Location**: `ui_blog/`
- **URL**: https://blog.ui.com
- **Status**: ✅ Working
- **Method**: API-based (uses blog.ui.com/api/articles)
- **Output**: `ui_blog_rss.xml`

#### Kia Navigation Updates
- **Location**: `kia_updates/`
- **URL**: https://update.kia.com/EU/NL/updateNoticeList
- **Status**: ✅ Working
- **Method**: HTML scraping (table-based)
- **Output**: `kia_updates.xml`
- **Note**: Updated to handle new website structure (Feb 2026)

### ⚠️ Feeds with Known Issues

#### Sparta Rotterdam Main
- **Location**: `sparta_main/`
- **URL**: https://www.sparta-rotterdam.nl/
- **Status**: ⚠️ Limited
- **Issue**: Website returns 403 Forbidden for automated requests
- **Note**: May work when run from GitHub Actions due to different IP addresses

#### Sparta Rotterdam Kidsclub
- **Location**: `sparta_kids/`
- **URL**: https://www.sparta-rotterdam.nl/kidsclub/
- **Status**: ⚠️ Limited
- **Issue**: Website returns 403 Forbidden for automated requests
- **Note**: May work when run from GitHub Actions due to different IP addresses

## Running Locally

### Prerequisites
- Python 3.8+
- pip

### Generate a Feed

```bash
cd [feed_directory]
pip install -r requirements.txt
python generate_feed.py
```

Example:
```bash
cd ui_blog
pip install -r requirements.txt
python generate_feed.py
```

## GitHub Actions

The feeds are automatically generated every 2 hours using GitHub Actions and deployed to GitHub Pages.

See `.github/workflows/generate-feed.yaml` for the workflow configuration.

## Troubleshooting

### Sparta Feeds Fail Locally

The Sparta Rotterdam website has anti-bot protection that may block requests from certain IP addresses. The feeds may work when run from GitHub Actions even if they fail locally.

### Kia Feed Fails

If the Kia feed fails, the website structure may have changed again. Check the HTML structure at https://update.kia.com/EU/NL/updateNoticeList and update the parser accordingly.

## Contributing

When adding new feeds or fixing existing ones:

1. Use proper User-Agent headers
2. Implement rate limiting (time.sleep) between requests
3. Add proper error handling
4. Follow the structure of existing feeds (use classes, similar to `ui_blog`)
5. Update this README with feed status

## License

This project generates RSS feeds for informational purposes only. The content belongs to the respective website owners.
