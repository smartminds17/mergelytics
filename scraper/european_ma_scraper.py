#!/usr/bin/env python3
"""
European M&A Deal Scraper for Mergelytics.com
Focuses on Mid-sized deals (€10-500M) in Germany, Austria, Switzerland, Benelux
"""

import requests
import feedparser
import json
import csv
import re
import time
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class MADeal:
    """Data structure for M&A deal information"""
    deal_title: str
    date: str
    deal_value: Optional[float]  # in EUR millions
    currency: str
    deal_type: str  # M&A, IPO, JV, Funding Round, Strategic Partnership
    acquirer_name: str
    target_name: str
    industry: str
    country: str
    region: str  # DACH or Benelux
    source_url: str
    scraped_at: str

class EuropeanMAScraperConfigure:
    """Configuration for the European M&A scraper"""
    
    # Target regions and countries
    TARGET_COUNTRIES = {
        'DACH': ['Germany', 'Austria', 'Switzerland'],
        'Benelux': ['Netherlands', 'Belgium', 'Luxembourg']
    }
    
    # Deal value range (EUR millions)
    MIN_DEAL_VALUE = 10
    MAX_DEAL_VALUE = 500
    
    # RSS feeds for European financial news
    RSS_FEEDS = [
        'https://www.ft.com/rss/companies/mergers-acquisitions',
        'https://feeds.reuters.com/reuters/businessNews',
        'https://www.bloomberg.com/feeds/economics/index.rss',
        'https://www.handelsblatt.com/contentexport/feed/rss/unternehmen',
        'https://www.finanz-nachrichten.de/rss-news-ma.htm',
        'https://www.dealreporter.com/rss',
    ]
    
    # Keywords for deal identification
    DEAL_KEYWORDS = [
        'acquires', 'acquisition', 'merger', 'buyout', 'takeover',
        'investment', 'funding', 'joint venture', 'partnership',
        'erwirbt', 'übernahme', 'fusion', 'investition',  # German
        'koopt', 'overname', 'fusie', 'investering'  # Dutch
    ]
    
    # Industry classification
    INDUSTRIES = [
        'Technology', 'Healthcare', 'Financial Services', 'Energy',
        'Manufacturing', 'Retail', 'Real Estate', 'Media',
        'Telecommunications', 'Automotive', 'Pharma', 'Biotech'
    ]

class EuropeanMAScraper:
    """Main scraper class for European M&A deals"""
    
    def __init__(self, config: EuropeanMAScraperConfigure):
        self.config = config
        self.deals: List[MADeal] = []
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def scrape_rss_feeds(self) -> List[Dict]:
        """Scrape RSS feeds for M&A news"""
        articles = []
        
        for feed_url in self.config.RSS_FEEDS:
            try:
                logger.info(f"Scraping RSS feed: {feed_url}")
                feed = feedparser.parse(feed_url)
                
                for entry in feed.entries:
                    # Check if article is about M&A
                    if self._is_ma_related(entry.title + " " + entry.get('summary', '')):
                        articles.append({
                            'title': entry.title,
                            'link': entry.link,
                            'published': entry.get('published', ''),
                            'summary': entry.get('summary', ''),
                            'source': feed_url
                        })
                
                time.sleep(1)  # Rate limiting
                
            except Exception as e:
                logger.error(f"Error scraping {feed_url}: {e}")
        
        logger.info(f"Found {len(articles)} potential M&A articles")
        return articles
    
    def _is_ma_related(self, text: str) -> bool:
        """Check if text contains M&A-related keywords"""
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in self.config.DEAL_KEYWORDS)
    
    def extract_deal_info(self, article: Dict) -> Optional[MADeal]:
        """Extract structured deal information from article"""
        try:
            # Get full article content
            response = self.session.get(article['link'], timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            full_text = soup.get_text()
            
            # Extract deal components
            deal_info = self._parse_deal_details(article['title'], full_text)
            
            if not deal_info:
                return None
            
            # Check if deal meets criteria
            if not self._meets_criteria(deal_info):
                return None
            
            return MADeal(
                deal_title=deal_info.get('title', article['title']),
                date=self._parse_date(article.get('published', '')),
                deal_value=deal_info.get('value'),
                currency=deal_info.get('currency', 'EUR'),
                deal_type=deal_info.get('type', 'M&A'),
                acquirer_name=deal_info.get('acquirer', ''),
                target_name=deal_info.get('target', ''),
                industry=deal_info.get('industry', self._classify_industry(full_text)),
                country=deal_info.get('country', self._identify_country(full_text)),
                region=deal_info.get('region', ''),
                source_url=article['link'],
                scraped_at=datetime.now().isoformat()
            )
            
        except Exception as e:
            logger.error(f"Error extracting deal info from {article['link']}: {e}")
            return None
    
    def _parse_deal_details(self, title: str, text: str) -> Dict:
        """Parse deal details from title and text"""
        deal_info = {}
        
        # Extract deal value and currency
        value_patterns = [
            r'€(\d+(?:\.\d+)?)\s*(?:million|billion|m|b)',
            r'\$(\d+(?:\.\d+)?)\s*(?:million|billion|m|b)',
            r'(\d+(?:\.\d+)?)\s*(?:million|billion)\s*(?:euro|eur|€)',
        ]
        
        for pattern in value_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = float(match.group(1))
                if 'billion' in match.group(0).lower() or 'b' in match.group(0).lower():
                    value *= 1000  # Convert to millions
                deal_info['value'] = value
                
                if '€' in match.group(0) or 'euro' in match.group(0).lower():
                    deal_info['currency'] = 'EUR'
                else:
                    deal_info['currency'] = 'USD'
                break
        
        # Extract company names
        acquirer_patterns = [
            r'(\w+(?:\s+\w+)*)\s+(?:acquires|buys|purchases)',
            r'(\w+(?:\s+\w+)*)\s+to acquire',
        ]
        
        for pattern in acquirer_patterns:
            match = re.search(pattern, title + " " + text, re.IGNORECASE)
            if match:
                deal_info['acquirer'] = match.group(1).strip()
                break
        
        target_patterns = [
            r'acquires\s+(\w+(?:\s+\w+)*)',
            r'buys\s+(\w+(?:\s+\w+)*)',
            r'purchases\s+(\w+(?:\s+\w+)*)',
        ]
        
        for pattern in target_patterns:
            match = re.search(pattern, title + " " + text, re.IGNORECASE)
            if match:
                deal_info['target'] = match.group(1).strip()
                break
        
        return deal_info
    
    def _meets_criteria(self, deal_info: Dict) -> bool:
        """Check if deal meets scraping criteria"""
        # Check deal value range
        value = deal_info.get('value')
        if value and not (self.config.MIN_DEAL_VALUE <= value <= self.config.MAX_DEAL_VALUE):
            return False
        
        return True
    
    def _classify_industry(self, text: str) -> str:
        """Classify industry based on text content"""
        text_lower = text.lower()
        
        industry_keywords = {
            'Technology': ['tech', 'software', 'digital', 'ai', 'cloud', 'saas'],
            'Healthcare': ['health', 'medical', 'pharma', 'biotech', 'drug'],
            'Financial Services': ['bank', 'finance', 'fintech', 'insurance'],
            'Energy': ['energy', 'oil', 'gas', 'renewable', 'solar'],
            'Manufacturing': ['manufacturing', 'industrial', 'factory'],
            'Retail': ['retail', 'consumer', 'shopping', 'e-commerce'],
            'Real Estate': ['real estate', 'property', 'construction'],
            'Media': ['media', 'entertainment', 'broadcasting', 'publishing'],
            'Telecommunications': ['telecom', 'mobile', 'network', '5g'],
            'Automotive': ['automotive', 'car', 'vehicle', 'mobility']
        }
        
        for industry, keywords in industry_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                return industry
        
        return 'Other'
    
    def _identify_country(self, text: str) -> str:
        """Identify country from text"""
        text_lower = text.lower()
        
        country_keywords = {
            'Germany': ['germany', 'german', 'deutschland', 'berlin', 'munich', 'frankfurt'],
            'Austria': ['austria', 'austrian', 'vienna', 'österreich'],
            'Switzerland': ['switzerland', 'swiss', 'zurich', 'geneva', 'schweiz'],
            'Netherlands': ['netherlands', 'dutch', 'amsterdam', 'rotterdam'],
            'Belgium': ['belgium', 'belgian', 'brussels', 'antwerp'],
            'Luxembourg': ['luxembourg', 'luxembourgish']
        }
        
        for country, keywords in country_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                return country
        
        return 'Unknown'
    
    def _parse_date(self, date_str: str) -> str:
        """Parse date string to ISO format"""
        if not date_str:
            return datetime.now().date().isoformat()
        
        try:
            # Try parsing common RSS date formats
            dt = datetime.strptime(date_str[:19], '%Y-%m-%dT%H:%M:%S')
            return dt.date().isoformat()
        except:
            try:
                dt = datetime.strptime(date_str.split(',')[1].strip()[:11], '%d %b %Y')
                return dt.date().isoformat()
            except:
                return datetime.now().date().isoformat()
    
    def run_scraper(self) -> List[MADeal]:
        """Main scraper execution"""
        logger.info("Starting European M&A deal scraper")
        
        # Step 1: Scrape RSS feeds
        articles = self.scrape_rss_feeds()
        
        # Step 2: Extract deal information
        for article in articles:
            deal = self.extract_deal_info(article)
            if deal:
                self.deals.append(deal)
                logger.info(f"Extracted deal: {deal.deal_title}")
            
            time.sleep(0.5)  # Rate limiting
        
        logger.info(f"Scraping completed. Found {len(self.deals)} deals")
        return self.deals
    
    def save_to_csv(self, filename: str = 'european_ma_deals.csv'):
        """Save deals to CSV file"""
        if not self.deals:
            logger.warning("No deals to save")
            return
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [field.name for field in MADeal.__dataclass_fields__.values()]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for deal in self.deals:
                writer.writerow(asdict(deal))
        
        logger.info(f"Saved {len(self.deals)} deals to {filename}")
    
    def save_to_json(self, filename: str = 'european_ma_deals.json'):
        """Save deals to JSON file"""
        if not self.deals:
            logger.warning("No deals to save")
            return
        
        deals_dict = [asdict(deal) for deal in self.deals]
        
        with open(filename, 'w', encoding='utf-8') as jsonfile:
            json.dump(deals_dict, jsonfile, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved {len(self.deals)} deals to {filename}")

def main():
    """Main execution function"""
    config = EuropeanMAScraperConfigure()
    scraper = EuropeanMAScraper(config)
    
    # Run the scraper
    deals = scraper.run_scraper()
    
    # Save results
    scraper.save_to_csv('mergelytics_deals.csv')
    scraper.save_to_json('mergelytics_deals.json')
    
    # Print summary
    if deals:
        print(f"\n=== SCRAPING SUMMARY ===")
        print(f"Total deals found: {len(deals)}")
        
        # Country breakdown
        countries = {}
        for deal in deals:
            countries[deal.country] = countries.get(deal.country, 0) + 1
        
        print("\nDeals by country:")
        for country, count in countries.items():
            print(f"  {country}: {count}")
        
        # Industry breakdown
        industries = {}
        for deal in deals:
            industries[deal.industry] = industries.get(deal.industry, 0) + 1
        
        print("\nDeals by industry:")
        for industry, count in sorted(industries.items(), key=lambda x: x[1], reverse=True):
            print(f"  {industry}: {count}")

if __name__ == "__main__":
    main()

# Additional utility functions for API integration

class MergelyticsAPI:
    """API integration for Mergelytics dashboard"""
    
    def __init__(self, deals_data: List[MADeal]):
        self.deals = deals_data
    
    def get_deals_json(self) -> str:
        """Return deals in JSON format for frontend"""
        return json.dumps([asdict(deal) for deal in self.deals], ensure_ascii=False, indent=2)
    
    def get_market_analytics(self) -> Dict:
        """Generate market analytics for dashboard"""
        if not self.deals:
            return {}
        
        total_value = sum(deal.deal_value for deal in self.deals if deal.deal_value)
        avg_value = total_value / len([d for d in self.deals if d.deal_value]) if total_value else 0
        
        return {
            'total_deals': len(self.deals),
            'total_value': total_value,
            'average_deal_size': avg_value,
            'deals_by_country': self._group_by_field('country'),
            'deals_by_industry': self._group_by_field('industry'),
            'deals_by_month': self._group_by_month(),
            'recent_deals': [asdict(deal) for deal in self.deals[-10:]]
        }
    
    def _group_by_field(self, field: str) -> Dict:
        """Group deals by specified field"""
        groups = {}
        for deal in self.deals:
            value = getattr(deal, field, 'Unknown')
            groups[value] = groups.get(value, 0) + 1
        return groups
    
    def _group_by_month(self) -> Dict:
        """Group deals by month"""
        monthly = {}
        for deal in self.deals:
            try:
                month = deal.date[:7]  # YYYY-MM format
                monthly[month] = monthly.get(month, 0) + 1
            except:
                continue
        return monthly

# Example usage for integration
"""
# To integrate with your React dashboard:
1. Run the scraper: python european_ma_scraper.py
2. Load the JSON data in your React app
3. Replace the sample data with real scraped data

# For automated scraping:
# Set up a cron job or scheduled task to run this script daily/weekly
# Use the MergelyticsAPI class to serve data to your frontend
"""
