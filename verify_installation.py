import os
from dotenv import load_dotenv

def verify_installations():
    load_dotenv()
    
    # Package verification
    packages = {
        'geopy': 'Geographic calculations',
        'googlemaps': 'Google Maps integration',
        'requests': 'HTTP requests',
        'bs4': 'BeautifulSoup web scraping',
        'better_profanity': 'Content filtering',
        'nltk': 'Natural language processing',
        'urbandict': 'Slang detection',
        'phonetics': 'Phonetic matching'
    }
    
    missing_packages = []
    
    for package, description in packages.items():
        try:
            __import__(package)
            print(f"✅ {package} - {description}")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package} - {description}")
    
    # NLTK data verification
    try:
        import nltk
        nltk.data.find('corpora/wordnet')
        print("✅ NLTK WordNet data")
    except LookupError:
        print("❌ NLTK WordNet data missing")
    
    # Environment variable verification
    api_key = os.getenv('GOOGLE_MAPS_API_KEY')
    if api_key:
        print("✅ Google Maps API key found")
    else:
        print("❌ Google Maps API key missing")
    
    if missing_packages:
        print("\n❌ Missing packages:", ', '.join(missing_packages))
        return False
    
    print("\n✅ All packages installed successfully!")
    return True

if __name__ == "__main__":
    verify_installations()