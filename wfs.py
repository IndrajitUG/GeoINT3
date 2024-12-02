from openai import OpenAI

# def clean_url(url):
#     """Clean the URL by removing any extra quotes but preserve trailing quote for date filters"""
#     cleaned_url = url.strip().strip('"')
#     if "daily_ts=" in cleaned_url and not cleaned_url.endswith("'"):
#         cleaned_url += "'"
#     return cleaned_url

def clean_url(url):
    """Clean the URL by removing backticks, extra quotes, and preserve trailing quote for date filters"""
    cleaned_url = url.strip().replace('`', '').strip()
    cleaned_url = cleaned_url.strip('"')
    if "daily_ts=" in cleaned_url and not cleaned_url.endswith("'"):
        cleaned_url += "'"
    return cleaned_url

def get_traffic_url(query):
    """Generate traffic data URL using OpenAI API"""
    system_prompt = '''I want you to act as a GeoServer WFS API expert specializing in traffic data analysis. Your role is to generate WFS API URLs with simple, efficient CQL filters for traffic pattern analysis. Focus on creating straightforward filters using basic operators (=, >, <, OR, AND) rather than complex operators like EXCEPT or IN.'''

    prompt = f'''Based on the following base URL and parameters, generate a complete WFS request URL with the specified filters.

    Base URL: "https://mapstack2.mapit.co.za/geoserver/mtn/ows"
    Service: WFS
    Version: 1.1.0
    TypeName: mtn:mtn_rivonia_geom_traffic
    OutputFormat: application/json
    Given that avg_traffic_den = 2.426102
    Longitude of mall = 28.060564
    Latitude of mall = -26.059083 
    date format is: 'yyyy-mm-ddT00:00:00Z'

    Given query:
    {query}

    Available Properties:
    - day: Day of week (Monday-Sunday)
    - avg_traffic_den: Average daily traffic density
    - avg_hits: Average daily traffic count
    - total_hits: Total traffic count for period
    - daily_ts: Timestamp for start of day

    Note: Use simple operators (=, >, <, OR, AND) and avoid complex operators like EXCEPT or IN.

    Note: If the query mentions locations within a z km radius of the mall, calculate the bounding box coordinates using:
    degree_offset = z / 111.32  # Convert km to degrees (1 degree ≈ 111.32 km)
    min_lon = mall_longitude - degree_offset
    max_lon = mall_longitude + degree_offset
    min_lat = mall_latitude - degree_offset
    max_lat = mall_latitude + degree_offset
    THEN APPEND to the CQL filter: AND BBOX(geom,min_lat,min_lon,max_lat,max_lon)

    ONLY USE THE BBOX PARAMETER MENTIONED ABOVE

    Please provide the complete, properly encoded URL that meets these requirements.
    Just provide the URL, no explanation is required.
    Generated URL:
    '''

    client = OpenAI()
    response = client.chat.completions.create(
        model='gpt-4o',
        messages=[
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': prompt}
        ],
        temperature=0.2
    )

    url = response.choices[0].message.content
    return clean_url(url)

def get_footfall_url(query):
    """Generate footfall data URL using OpenAI API"""
    system_prompt = '''I want you to act as a GeoServer WFS API expert. Your role is to generate correct WFS API URLs based on user requirements for filtering and querying spatial datasets. You should understand CQL filters, WFS parameters, and how to properly encode URLs.'''

    prompt = f'''Based on the following base URL and parameters, generate a complete WFS request URL with the specified filters.

    Base URL: "https://mapstack2.mapit.co.za/geoserver/mtn/ows"
    Service: WFS
    Version: 1.1.0
    TypeName: "mtn:mtn_rivonia_ff_dataset"
    OutputFormat: application/json
    Longitude of mall = 28.060564
    Latitude of mall = -26.059083

    Given query:
    {query}
    
    "ff_rivil": total footfall mall only,
    "ffc_rivil": total footfall competitors only,
    "ffmc_rivil":total footfall mall and competitors,
    "ff_morning_rivil": morning footfall mall,
    "ff_midday_rivil":midday footfall mall,
    "ff_afternoon_rivil":afternoon footfall mall,
    "ff_evening_rivil":evening footfall mall,
    "ffc_morning_rivil":morning footfall competitors,
    "ffc_midday_rivil":midday footfall competitors,
    "ffc_afternoon_rivil":afternoon footfall competitors,
    "ffc_evening_rivil":evening footfall competitors,
    "ffc_week_rivil":weekday footfall competitors,
    "ffc_weekend_rivil":weekend footfall competitors,
    "income_class": dominant income class,'Uses capital first letter for each word'
    "ff_week_rivil":weekday footfall mall,
    "ff_weekend_rivil":weekend footfall mall

    Note: If the query mentions locations within a z km radius of the mall, calculate the bounding box coordinates using:
    degree_offset = z / 111.32  # Convert km to degrees (1 degree ≈ 111.32 km)
    min_lon = mall_longitude - degree_offset
    max_lon = mall_longitude + degree_offset
    min_lat = mall_latitude - degree_offset
    max_lat = mall_latitude + degree_offset
    THEN APPEND to the CQL filter: AND BBOX(geom,min_lat,min_lon,max_lat,max_lon)

    ONLY USE THE BBOX PARAMETER MENTIONED ABOVE

    Please provide the complete, properly encoded URL that meets these requirements.
    Just provide the URL, no explanation is required.
    Generated URL:
    '''

    client = OpenAI()
    response = client.chat.completions.create(
        model='gpt-4o',
        messages=[
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': prompt}
        ],
        temperature=0.2
    )

    url = response.choices[0].message.content
    return clean_url(url)
