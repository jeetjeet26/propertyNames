import requests
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import googlemaps
from bs4 import BeautifulSoup
import re
import time
from datetime import datetime
import json
from better_profanity import profanity
import nltk
from nltk.corpus import wordnet
import urbandict as ud
from metaphone import doublemetaphone  # Change to use metaphone directly

class PropertyNameValidator:
    def __init__(self, google_api_key):
        """Initialize the validator with necessary API keys and content filters."""
        self.google_maps_client = googlemaps.Client(key=google_api_key)
        self.geolocator = Nominatim(user_agent="property_validator")
        self.search_results = []
        
        # Initialize NLTK
        try:
            nltk.data.find('corpora/wordnet')
        except LookupError:
            nltk.download('wordnet')
        
        # Load custom blocklist
        self.custom_blocklist = self._load_custom_blocklist()
        
        # Initialize profanity filter with custom words
        profanity.load_censor_words()
        profanity.add_censor_words(self.custom_blocklist)
    
    def _load_custom_blocklist(self):
        """Load custom blocklist of terms inappropriate for property names."""
        return [
            "ghetto",
            "hood",
            "sketchy",
        ]
    
    def validate_property_name(self, name):
        """
        Validate the property name for inappropriate content.
        Returns a dictionary with validation results and explanations.
        """
        validation_results = {
            'is_valid': True,
            'warnings': [],
            'suggestions': []
        }
        
        # Convert to lowercase for checking
        name_lower = name.lower()
        words = name_lower.split()
        
        # Check each word and the full name
        for word in words + [name_lower]:
            # 1. Check against profanity filter
            if profanity.contains_profanity(word):
                validation_results['is_valid'] = False
                validation_results['warnings'].append(
                    f"Contains inappropriate language: '{word}'"
                )
        
            # 2. Check for slang meanings using Urban Dictionary API
            try:
                defs = ud.define(word)
                if defs and len(defs) > 0:
                    # Check only the top definition
                    top_def = defs[0]
                    if hasattr(top_def, 'upvotes') and top_def.upvotes > 1000:
                        validation_results['warnings'].append(
                            f"Potential slang meaning for '{word}'"
                        )
            except Exception:
                # Silently continue if Urban Dictionary check fails
                pass
        
            # 3. Check for negative connotations using WordNet
            try:
                synsets = wordnet.synsets(word)
                for synset in synsets:
                    if any(neg_word in synset.definition().lower() for neg_word in 
                        ['offensive', 'derogatory', 'inappropriate', 'slur']):
                        validation_results['warnings'].append(
                            f"Potential negative connotation for '{word}': {synset.definition()}"
                        )
            except Exception:
                pass
        
        # 4. Check for phonetic similarities to inappropriate words
        try:
            name_sound = doublemetaphone(str(name_lower))[0]
            for blocked_word in self.custom_blocklist:
                if name_sound == doublemetaphone(str(blocked_word))[0]:
                    validation_results['warnings'].append(
                        f"Phonetically similar to inappropriate term: '{blocked_word}'"
                    )
        except Exception:
            pass
        
        # 5. Cultural sensitivity check
        self._check_cultural_sensitivity(name, validation_results)
        
        # Generate suggestions if issues found
        if not validation_results['is_valid'] or validation_results['warnings']:
            validation_results['suggestions'] = self._generate_alternative_suggestions(name)
        
        return validation_results
    
    def _check_cultural_sensitivity(self, name, validation_results):
        """Check for cultural appropriation or insensitive terms."""
        cultural_terms = {
            'plantation': "Historical connection to slavery",
            'colonial': "Historical connection to colonialism",
            'savage': "Derogatory term with racist history",
        }
        
        for term, explanation in cultural_terms.items():
            if term in name.lower():
                validation_results['warnings'].append(
                    f"Potentially sensitive term '{term}': {explanation}"
                )
    
    def _generate_alternative_suggestions(self, name):
        """Generate alternative name suggestions if original name has issues."""
        suggestions = []
        words = name.split()
        
        try:
            # Simple word replacement suggestions
            for i, word in enumerate(words):
                synonyms = []
                for syn in wordnet.synsets(word):
                    for lemma in syn.lemmas():
                        if lemma.name().lower() != word.lower():
                            synonyms.append(lemma.name())
                
                if synonyms:
                    # Create new name with synonym replacement
                    for synonym in list(set(synonyms))[:3]:
                        new_words = words.copy()
                        new_words[i] = synonym.title()
                        suggestions.append(' '.join(new_words))
        except Exception:
            pass
        
        return list(set(suggestions))[:5]  # Return up to 5 unique suggestions
    
    def get_property_coordinates(self, address):
        """Get latitude and longitude for a given address."""
        try:
            location = self.geolocator.geocode(address)
            if location:
                return (location.latitude, location.longitude)
            return None
        except Exception as e:
            print(f"Error getting coordinates: {e}")
            return None
    
    def calculate_distance(self, coord1, coord2):
        """Calculate distance between two coordinates in miles."""
        return geodesic(coord1, coord2).miles
    
    def search_property_name(self, property_name, property_address, radius_miles):
        """Search for existing properties with similar names within the specified radius."""
        # First, validate the property name
        validation_results = self.validate_property_name(property_name)
        
        if not validation_results['is_valid']:
            return {
                'error': 'Invalid property name',
                'validation_results': validation_results
            }
        
        self.search_results = []
        property_coords = self.get_property_coordinates(property_address)
        
        if not property_coords:
            return {
                'error': "Could not get coordinates for provided address",
                'validation_results': validation_results
            }
            
        try:
            # Search Google Places API
            places_result = self.google_maps_client.places_nearby(
                location=property_coords,
                radius=radius_miles * 1609.34,  # Convert miles to meters
                keyword=property_name
            )
            
            for place in places_result.get('results', []):
                place_lat = place['geometry']['location']['lat']
                place_lng = place['geometry']['location']['lng']
                distance = self.calculate_distance(
                    property_coords, 
                    (place_lat, place_lng)
                )
                
                if distance <= radius_miles:
                    self.search_results.append({
                        'name': place['name'],
                        'address': place.get('vicinity', 'Address not available'),
                        'distance': round(distance, 2),
                        'source': 'Google Places'
                    })
        except Exception as e:
            return {
                'error': f"Error searching for properties: {str(e)}",
                'validation_results': validation_results
            }
            
        results = self.format_results()
        results['validation_results'] = validation_results
        return results

    def format_results(self):
        """Format and return the search results."""
        return {
            'timestamp': datetime.now().isoformat(),
            'total_results': len(self.search_results),
            'potential_conflicts': sorted(
                self.search_results,
                key=lambda x: x['distance']
            )
        }
    
    def generate_report(self):
        """Generate a detailed report of the findings."""
        return {
            'summary': {
                'total_conflicts': len(self.search_results),
                'closest_match': min(self.search_results, key=lambda x: x['distance']) if self.search_results else None,
                'search_timestamp': datetime.now().isoformat()
            },
            'detailed_results': self.search_results
        }
    
    def save_results(self, filename):
        """Save search results to a JSON file."""
        with open(filename, 'w') as f:
            json.dump(self.search_results, f, indent=4)