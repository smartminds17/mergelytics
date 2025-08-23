#!/bin/bash
# Mergelytics GitHub Setup Script for Beginners
# Run this in your mergelytics folder

echo "🚀 Setting up Mergelytics project structure..."

# Create main directories
mkdir -p scraper
mkdir -p dashboard/src/components
mkdir -p dashboard/src/data
mkdir -p dashboard/public
mkdir -p .github/workflows
mkdir -p docs

echo "📁 Created project directories"

# Create scraper requirements
cat > scraper/requirements.txt << 'EOF'
requests==2.31.0
beautifulsoup4==4.12.2
feedparser==6.0.10
pandas==2.1.0
python-dateutil==2.8.2
EOF

echo "📦 Created Python requirements file"

# Create basic package.json for dashboard
cat > dashboard/package.json << 'EOF'
{
  "name": "mergelytics-dashboard",
  "version": "1.0.0",
  "private": true,
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-scripts": "5.0.1",
    "recharts": "^2.8.0",
    "lucide-react": "^0.263.1"
  },
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build",
    "test": "react-scripts test"
  },
  "browserslist": {
    "production": [">0.2%", "not dead", "not op_mini all"],
    "development": ["last 1 chrome version", "last 1 firefox version"]
  },
  "homepage": "https://yourusername.github.io/mergelytics"
}
EOF

echo "📱 Created React package.json"

# Create sample README
cat > README.md << 'EOF'
# 🚀 Mergelytics - European M&A Intelligence Platform

**Live Site**: Coming Soon!

## What is this?
Mergelytics automatically scrapes and analyzes European M&A deals worth €10-500M from Germany, Austria, Switzerland, and Benelux countries.

## Features
- 📊 Daily automated data scraping
- 📈 Interactive financial dashboards  
- 🎯 Focus on mid-market deals
- 🇪🇺 European market coverage

## Status
🚧 **Currently in development**

## Tech Stack
- **Scraper**: Python with BeautifulSoup
- **Dashboard**: React with Recharts
- **Automation**: GitHub Actions
- **Hosting**: GitHub Pages

---
*Built with ❤️ for the European M&A community*
EOF

echo "📄 Created README.md"

# Create gitignore
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*.so
.env
venv/
env/

# Node.js
node_modules/
npm-debug.log*
build/
.DS_Store

# Data files (temporary)
*.csv
*.json
!package*.json

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
Thumbs.db
EOF

echo "🚫 Created .gitignore file"

echo ""
echo "✅ Project structure created successfully!"
echo ""
echo "📋 Next steps:"
echo "1. Add your scraper code to scraper/ folder"
echo "2. Add your React dashboard to dashboard/ folder" 
echo "3. Commit and push to GitHub"
echo ""
echo "🔧 Quick commands:"
echo "git add ."
echo "git commit -m 'Initial project setup'"
echo "git push"
echo ""
echo "🌐 After pushing, enable GitHub Pages in your repository settings!"
