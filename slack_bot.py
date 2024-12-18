from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import os
from dotenv import load_dotenv
from name import PropertyNameValidator
import re
import logging
logging.basicConfig(level=logging.DEBUG)

load_dotenv()

# Initialize the app with Slack tokens
app = App(token=os.environ["SLACK_BOT_TOKEN"])
validator = PropertyNameValidator(os.environ["GOOGLE_MAPS_API_KEY"])

def parse_command(text):
    """Parse the command text into components"""
    parts = [part.strip() for part in text.split(',')]
    if len(parts) != 3:
        return None
        
    names = [parts[0].strip()]
    address = parts[1].strip()
    try:
        radius = int(parts[2].strip())
        return names, address, radius
    except ValueError:
        return None

def format_conflicts_text(conflicts):
    """Format conflicts into readable text with metadata"""
    texts = []
    for c in conflicts:
        # Filter and format business types
        types = c.get('types', [])
        if types:
            # Mapping of Google Places types to readable names
            type_mappings = {
                'apartment': 'Apartment Complex',
                'doctor': 'Medical Practice',
                'restaurant': 'Restaurant', 
                'store': 'Retail Store',
                'insurance_agency': 'Insurance Agency',
                'lawyer': 'Law Office',
                'real_estate_agency': 'Real Estate Office',
                'shopping_mall': 'Shopping Mall',
                'parking': 'Parking Facility',
                'furniture_store': 'Furniture Store',
                'book_store': 'Book Store',
                'clothing_store': 'Clothing Store',
                'bar': 'Bar/Nightclub',
                'medical_lab': 'Medical Lab',
                'dental_clinic': 'Dental Office',
                'hotel': 'Hotel',
                'cafe': 'Café',
                'bakery': 'Bakery',
                'bank': 'Bank',
                'beauty_salon': 'Beauty Salon',
                'gym': 'Fitness Center',
                'hospital': 'Hospital',
                'health': 'Healthcare',
                'local_government_office': 'Government Office',
                'real_estate': 'Real Estate',
                'shopping_mall': 'Mall'
            }
            
            # Try to find a mapped type
            business_type = 'Business'
            for t in types:
                if t in type_mappings:
                    business_type = type_mappings[t]
                    break
        else:
            business_type = 'Business'

        text_parts = [
            f"• *{c['name']}* ({c['distance']} miles away)",
            f"  Type: {business_type}",
            f"  Address: {c['address']}"
        ]
        
        if c.get('rating') and c['rating'] != 'No rating':
            text_parts.append(f"  Rating: {'⭐' * round(float(c['rating']))} ({c['rating']})")
        
        if c.get('website') and c['website'] != 'No website':
            text_parts.append(f"  <{c['website']}|Website> | <{c.get('google_maps', '')}|Google Maps>")
        
        texts.append("\n".join(text_parts))
    
    return "\n".join(texts)

@app.command("/name")
def handle_name_command(ack, command, say):
    ack()
    try:
        parsed = parse_command(command['text'])
        if not parsed:
            say("Usage: /name PropertyName, Full Address, RadiusInMiles")
            return
            
        names, address, radius = parsed
        results = []
        
        for name in names:
            # Validate name
            validation = validator.validate_property_name(name)
            
            if not validation['is_valid']:
                results.append({
                    'name': name,
                    'status': '❌ Invalid',
                    'warnings': validation['warnings']
                })
                continue
                
            # Check for nearby properties
            search_results = validator.search_property_name(name, address, radius)
            
            if 'error' in search_results:
                results.append({
                    'name': name,
                    'status': '⚠️ Error',
                    'message': search_results['error']
                })
                continue
                
            conflicts = search_results.get('potential_conflicts', [])
            results.append({
                'name': name,
                'status': '✅ Valid' if not conflicts else f'⚠️ Found {len(conflicts)} conflicts',
                'conflicts': conflicts
            })
        
        # Format message
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "Property Name Validation Results"
                }
            }
        ]
        
        for result in results:
            blocks.extend([
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{result['name']}*: {result['status']}"
                    }
                }
            ])
            
            if 'warnings' in result:
                warnings_text = "\n".join([f"• {w}" for w in result['warnings']])
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"Warnings:\n{warnings_text}"
                    }
                })
                
            if 'conflicts' in result and result['conflicts']:
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"Nearby properties:\n{format_conflicts_text(result['conflicts'])}"
                    }
                })
                
            blocks.append({"type": "divider"})
        
        say(blocks=blocks)
        
    except Exception as e:
        say(f"Error: {str(e)}")

if __name__ == "__main__":
    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    handler.start()