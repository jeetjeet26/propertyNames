from name import PropertyNameValidator
import os
from dotenv import load_dotenv

def test_validator():
    # Load environment variables
    load_dotenv()
    
    # Get API key from environment variable
    api_key = os.getenv('GOOGLE_MAPS_API_KEY')
    
    # Initialize validator
    validator = PropertyNameValidator(api_key)
    
    # Test cases
    test_cases = [
        {
            'name': "Sunset Gardens",
            'address': "123 Main St, Austin, TX",
            'radius': 50
        },
        {
            'name': "Colonial Heights",
            'address': "456 Oak Ave, Dallas, TX",
            'radius': 50
        },
        {
            'name': "Pleasant Valley",
            'address': "789 Pine St, Houston, TX",
            'radius': 50
        }
    ]
    
    # Run tests
    for case in test_cases:
        print(f"\nTesting property name: {case['name']}")
        print("-" * 50)
        
        # First, validate the name
        validation_results = validator.validate_property_name(case['name'])
        
        print("Validation Results:")
        print(f"Valid: {'✓' if validation_results['is_valid'] else '✗'}")
        
        if validation_results['warnings']:
            print("\nWarnings:")
            for warning in validation_results['warnings']:
                print(f"- {warning}")
            
        if validation_results['suggestions']:
            print("\nSuggestions:")
            for suggestion in validation_results['suggestions']:
                print(f"- {suggestion}")
        
        # If name is valid, check for nearby properties
        if validation_results['is_valid']:
            print("\nChecking for nearby properties...")
            search_results = validator.search_property_name(
                case['name'],
                case['address'],
                case['radius']
            )
            
            if 'error' in search_results:
                print(f"Error: {search_results['error']}")
            else:
                print(f"Found {len(search_results.get('potential_conflicts', []))} potential conflicts")

if __name__ == "__main__":
    test_validator()