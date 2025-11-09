#!/usr/bin/env python3
"""
Geocode addresses from correlaid_projects_addresses.json
Uses Nominatim (OpenStreetMap) for free geocoding
"""
import json
import time
import requests
from typing import Optional, Tuple

def geocode_address(street: str, number: str, zip_code: str, place: str, country: str) -> Optional[Tuple[float, float]]:
    """Geocode an address using Nominatim API"""
    if not place or not country:
        return None

    # Build query - prioritize place and country as they're most reliable
    parts = []
    if street and number:
        parts.append(f"{street} {number}")
    if zip_code:
        parts.append(zip_code)
    if place:
        parts.append(place)
    if country:
        parts.append(country)

    query = ", ".join(parts)

    if not query.strip():
        return None

    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": query,
        "format": "json",
        "limit": 1
    }
    headers = {
        "User-Agent": "CorrelAid Map Project"
    }

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data and len(data) > 0:
            lat = float(data[0]["lat"])
            lon = float(data[0]["lon"])
            return (lon, lat)  # Return as [lon, lat] for MapLibre
    except Exception as e:
        print(f"Error geocoding '{query}': {e}")

    return None

def main():
    # Load the JSON data
    with open("correlaid_projects_addresses.json", "r", encoding="utf-8") as f:
        projects = json.load(f)

    locations = []
    seen_addresses = {}  # To avoid duplicate locations

    print(f"Processing {len(projects)} projects...")

    for project in projects:
        org = project.get("organization", {})
        addr = org.get("address", {})

        street = addr.get("street", "").strip()
        number = addr.get("number", "").strip()
        zip_code = addr.get("zip_code", "").strip()
        place = addr.get("place", "").strip()
        country = addr.get("country", "").strip()

        # Skip if no meaningful address
        if not place or not country:
            continue

        # Create a key to check for duplicates
        addr_key = f"{place}|{country}".lower()

        # Check if we've already geocoded this location
        if addr_key in seen_addresses:
            coords = seen_addresses[addr_key]
        else:
            print(f"Geocoding: {place}, {country}")
            coords = geocode_address(street, number, zip_code, place, country)
            time.sleep(1.1)  # Respect Nominatim rate limits (1 req/sec)

            if coords:
                seen_addresses[addr_key] = coords

        if coords:
            location = {
                "name": org.get("name", "Unknown Organization"),
                "project": project.get("title", ""),
                "lon": coords[0],
                "lat": coords[1],
                "address": f"{street} {number}, {zip_code} {place}, {country}".strip(", "),
                "place": place,
                "country": country,
                "url": f"https://correlaid.org{project.get('href', '')}" if project.get('href') else None
            }
            locations.append(location)

    # Save to JSON
    output = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [loc["lon"], loc["lat"]]
                },
                "properties": loc
            }
            for loc in locations
        ]
    }

    with open("locations.geojson", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Successfully geocoded {len(locations)} unique locations")
    print(f"✓ Saved to locations.geojson")

if __name__ == "__main__":
    main()
