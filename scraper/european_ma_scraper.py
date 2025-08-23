# requirements.txt
requests==2.31.0
beautifulsoup4==4.12.2
feedparser==6.0.10
google-cloud-storage==2.10.0
google-cloud-firestore==2.12.0

# main.py (Cloud Function version)
import functions_framework
from google.cloud import storage, firestore
import json
import os
from datetime import datetime
from european_ma_scraper import EuropeanMAScraper, EuropeanMAScraperConfigure

# Initialize Google Cloud clients
storage_client = storage.Client()
db = firestore.Client()

@functions_framework.http
def scrape_ma_deals(request):
    """Cloud Function entry point for M&A scraping"""
    try:
        # Initialize scraper
        config = EuropeanMAScraperConfigure()
        scraper = EuropeanMAScraper(config)
        
        # Run scraper
        deals = scraper.run_scraper()
        
        if deals:
            # Save to Firestore (NoSQL database)
            save_to_firestore(deals)
            
            # Save to Cloud Storage (for backup/export)
            save_to_cloud_storage(deals)
            
            return {
                'status': 'success',
                'message': f'Scraped {len(deals)} deals',
                'timestamp': datetime.now().isoformat()
            }
        else:
            return {
                'status': 'warning',
                'message': 'No deals found',
                'timestamp': datetime.now().isoformat()
            }
            
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e),
            'timestamp': datetime.now().isoformat()
        }

def save_to_firestore(deals):
    """Save deals to Firestore database"""
    collection_ref = db.collection('ma_deals')
    
    for deal in deals:
        # Use a unique ID based on deal title and date
        doc_id = f"{deal.deal_title}_{deal.date}".replace(' ', '_').replace('/', '_')
        doc_ref = collection_ref.document(doc_id)
        
        deal_dict = {
            'deal_title': deal.deal_title,
            'date': deal.date,
            'deal_value': deal.deal_value,
            'currency': deal.currency,
            'deal_type': deal.deal_type,
            'acquirer_name': deal.acquirer_name,
            'target_name': deal.target_name,
            'industry': deal.industry,
            'country': deal.country,
            'region': deal.region,
            'source_url': deal.source_url,
            'scraped_at': deal.scraped_at
        }
        
        doc_ref.set(deal_dict, merge=True)

def save_to_cloud_storage(deals):
    """Save deals to Cloud Storage as JSON backup"""
    bucket_name = 'mergelytics-data'
    bucket = storage_client.bucket(bucket_name)
    
    # Create filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'ma_deals_{timestamp}.json'
    
    # Convert deals to JSON
    deals_json = json.dumps([deal.__dict__ for deal in deals], 
                           default=str, indent=2)
    
    # Upload to Cloud Storage
    blob = bucket.blob(f'scraping_results/{filename}')
    blob.upload_from_string(deals_json, content_type='application/json')

# deploy.sh (Deployment script)
#!/bin/bash
echo "Deploying Mergelytics M&A Scraper..."

# Deploy Cloud Function
gcloud functions deploy scrape-ma-deals \
    --gen2 \
    --runtime=python311 \
    --region=europe-west1 \
    --source=. \
    --entry-point=scrape_ma_deals \
    --trigger-http \
    --allow-unauthenticated \
    --memory=1GB \
    --timeout=540s \
    --set-env-vars="PROJECT_ID=mergelytics-scraper"

echo "Function deployed! Setting up scheduled execution..."

# Create Cloud Scheduler job (runs daily at 9 AM CET)
gcloud scheduler jobs create http ma-scraper-daily \
    --location=europe-west1 \
    --schedule="0 9 * * *" \
    --uri="https://europe-west1-mergelytics-scraper.cloudfunctions.net/scrape-ma-deals" \
    --http-method=GET \
    --time-zone="Europe/Berlin"

echo "Deployment complete!"
echo "Your scraper will run daily at 9 AM CET"
echo "Manual trigger: https://europe-west1-mergelytics-scraper.cloudfunctions.net/scrape-ma-deals"

# api.py (API endpoints for your React dashboard)
from flask import Flask, jsonify, request
from google.cloud import firestore
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Allow cross-origin requests from your frontend

db = firestore.Client()

@app.route('/api/deals', methods=['GET'])
def get_deals():
    """Get all M&A deals for the dashboard"""
    try:
        # Query parameters
        limit = request.args.get('limit', 100, type=int)
        country = request.args.get('country')
        industry = request.args.get('industry')
        
        # Build Firestore query
        query = db.collection('ma_deals').order_by('date', direction=firestore.Query.DESCENDING)
        
        if country and country != 'All':
            query = query.where('country', '==', country)
        
        if industry and industry != 'All':
            query = query.where('industry', '==', industry)
        
        # Execute query
        docs = query.limit(limit).stream()
        
        deals = []
        for doc in docs:
            deal_data = doc.to_dict()
            deal_data['id'] = doc.id
            deals.append(deal_data)
        
        return jsonify({
            'success': True,
            'data': deals,
            'count': len(deals)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/analytics', methods=['GET'])
def get_analytics():
    """Get analytics data for the dashboard"""
    try:
        deals_ref = db.collection('ma_deals')
        deals = [doc.to_dict() for doc in deals_ref.stream()]
        
        # Calculate analytics
        total_deals = len(deals)
        total_value = sum(deal.get('deal_value', 0) or 0 for deal in deals)
        
        # Group by country
        countries = {}
        for deal in deals:
            country = deal.get('country', 'Unknown')
            countries[country] = countries.get(country, 0) + 1
        
        # Group by industry
        industries = {}
        for deal in deals:
            industry = deal.get('industry', 'Unknown')
            industries[industry] = industries.get(industry, 0) + 1
        
        return jsonify({
            'success': True,
            'data': {
                'total_deals': total_deals,
                'total_value': total_value,
                'deals_by_country': countries,
                'deals_by_industry': industries,
                'latest_scrape': max([deal.get('scraped_at', '') for deal in deals]) if deals else None
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=True, port=8080)

# docker-compose.yml (Alternative: Docker deployment)
version: '3.8'
services:
  mergelytics-scraper:
    build: .
    environment:
      - GOOGLE_APPLICATION_CREDENTIALS=/app/service-account.json
    volumes:
      - ./service-account.json:/app/service-account.json:ro
    ports:
      - "8080:8080"
    restart: unless-stopped

# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "api.py"]
