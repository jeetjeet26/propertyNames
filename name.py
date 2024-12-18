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
from metaphone import doublemetaphone

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
                if defs:
                    total_upvotes = 0
                    negative_definitions = []
                    
                    for definition in defs:
                        if hasattr(definition, 'definition'):
                            definition_text = definition.definition.lower()
                            votes = getattr(definition, 'thumbs_up', 0) or getattr(definition, 'upvotes', 0)
                            total_upvotes += votes
                            
                            negative_themes = [
                                'drug', 'sexual', 'offensive', 'racist', 'vulgar', 
                                'slur', 'explicit', 'nsfw', 'derogatory', 'inappropriate',
                                'adult', 'porn', 'fetish', 'sex', 'butt', 'ass', 
                                'penis', 'vagina', 'dick'
                            ]
                            
                            if votes > 1000 and any(theme in definition_text for theme in negative_themes):
                                negative_definitions.append({
                                    'text': definition_text[:100],
                                    'upvotes': votes
                                })
                    
                    if total_upvotes > 3000:
                        validation_results['warnings'].append(
                            f"'{word}' has significant slang usage ({total_upvotes} upvotes)"
                        )
                    
                    if negative_definitions:
                        most_upvoted = max(negative_definitions, key=lambda x: x['upvotes'])
                        validation_results['is_valid'] = False
                        validation_results['warnings'].append(
                            f"'{word}' has inappropriate slang meaning: {most_upvoted['text']}..."
                        )
                        
            except Exception as e:
                print(f"Urban Dictionary API error: {str(e)}")
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
            # Try Google Maps Geocoding first
            geocode_result = self.google_maps_client.geocode(address)
            if geocode_result and len(geocode_result) > 0:
                location = geocode_result[0]['geometry']['location']
                return (location['lat'], location['lng'])
            
            # Fallback to Nominatim if Google geocoding fails
            location = self.geolocator.geocode(address)
            if location:
                return (location.latitude, location.longitude)
            
            return None
        except Exception as e:
            print(f"Geocoding error: {str(e)}")
            return None
    
    def calculate_distance(self, coord1, coord2):
        """Calculate distance between two coordinates in miles."""
        return geodesic(coord1, coord2).miles
    
    def similar_names(self, name1, name2):
        """Check if names are similar using fuzzy matching and contains logic"""
        n1 = name1.lower()
        n2 = name2.lower()
        
        # Direct substring matching
        if n1 in n2 or n2 in n1:
            return True
            
        # Split into words and check for significant word overlap
        words1 = set(n1.split())
        words2 = set(n2.split())
        common_words = words1.intersection(words2)
        
        # If any significant words match (excluding common words like 'the', 'at', etc)
        common_words.discard('the')
        common_words.discard('at')
        common_words.discard('of')
        common_words.discard('in')
        
        return len(common_words) > 0

    def search_property_name(self, property_name, property_address, radius_miles):
        """Search for existing properties with similar names within the specified radius."""
        print(f"\nSearching for property: {property_name}")
        print(f"Address: {property_address}")
        print(f"Radius: {radius_miles} miles")
        
        validation_results = self.validate_property_name(property_name)
        print(f"Validation results: {validation_results}")
        
        if not validation_results['is_valid']:
            return {
                'error': 'Invalid property name',
                'validation_results': validation_results
            }
        
        self.search_results = []
        property_coords = self.get_property_coordinates(property_address)
        print(f"Coordinates: {property_coords}")
        
        if not property_coords:
            return {
                'error': "Could not get coordinates for provided address",
                'validation_results': validation_results
            }
            
        try:
            places_result = self.google_maps_client.places_nearby(
                location=property_coords,
                radius=radius_miles * 1609.34,
                keyword=property_name,
                type='establishment'
            )
            print(f"Places API results: {places_result}")
            
            for place in places_result.get('results', []):
                if property_name.lower() in place['name'].lower():
                    print(f"Found matching place: {place['name']}")
                    try:
                        # Get detailed place info
                        place_details = self.google_maps_client.place(
                            place['place_id'],
                            fields=['name', 'formatted_address', 'rating', 'website', 'types', 'url', 'business_status']
                        )['result']
                        print(f"Place details: {place_details}")
                        
                        distance = self.calculate_distance(
                            property_coords, 
                            (place['geometry']['location']['lat'], 
                             place['geometry']['location']['lng'])
                        )
                        
                        if distance <= radius_miles:
                            self.search_results.append({
                                'name': place['name'],
                                'address': place_details.get('formatted_address', place.get('vicinity', 'Address not available')),
                                'distance': round(distance, 2),
                                'rating': place_details.get('rating', 'No rating'),
                                'website': place_details.get('website', 'No website'),
                                'google_maps': place_details.get('url', ''),
                                'types': place_details.get('types', ['business']),
                                'source': 'Google Places'
                            })
                    except Exception as e:
                        print(f"Error getting place details: {str(e)}")
                        # Add basic info without details
                        distance = self.calculate_distance(
                            property_coords, 
                            (place['geometry']['location']['lat'], 
                             place['geometry']['location']['lng'])
                        )
                        if distance <= radius_miles:
                            self.search_results.append({
                                'name': place['name'],
                                'address': place.get('vicinity', 'Address not available'),
                                'distance': round(distance, 2),
                                'types': place.get('types', ['business']),
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