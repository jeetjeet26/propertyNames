from name import PropertyNameValidator
import os
from dotenv import load_dotenv

def test_validator():
    # Load environment variables
    load_dotenv()
    
    # Get API key from environment variable
    api_key = os.getenv('GOOGLE_MAPS_API_KEY')
    
    if not api_key:
        print("Error: GOOGLE_MAPS_API_KEY not found in .env file")
        return
    
    # Initialize validator
    validator = PropertyNameValidator(api_key)
    
    # Test cases with real addresses
    test_cases = [
        {
            'name': "The Domain",
            'address': "12 Garden Gate Lane, Irvine, CA 92620",
            'radius': 50
        },
        {
            'name': "Colonial Heights",
            'address': "6001 W Parmer Lane, Austin, TX 78727",
            'radius': 50
        },
        {
            'name': "Pleasant Valley",
            'address': "1100 South Pleasant Valley Road, Austin, TX 78741",
            'radius': 50
        },
        {
            'name': "The Hood",  # Should trigger warning
            'address': "2525 W Anderson Ln, Austin, TX 78757",
            'radius': 50
        }
    ]
    
    # Run tests
    for case in test_cases:
        print(f"\nTesting property name: {case['name']}")
        print(f"Address: {case['address']}")
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
                conflicts = search_results.get('potential_conflicts', [])
                print(f"Found {len(conflicts)} potential conflicts")
                
                if conflicts:
                    print("\nNearby properties:")
                    for conflict in conflicts:
                        print(f"- {conflict['name']}")
                        print(f"  Distance: {conflict['distance']} miles")
                        print(f"  Address: {conflict['address']}")
        
        print("\nSearch complete.")

if __name__ == "__main__":
    test_validator()