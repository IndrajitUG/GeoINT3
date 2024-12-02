import streamlit as st
import pandas as pd
import requests
from openai import OpenAI
import os
from dotenv import load_dotenv
from PIL import Image
import json
from wfs import get_traffic_url, get_footfall_url
from wms import get_footfall_wms_url, get_wms_traffic_url

# Load environment variables
load_dotenv()

# Page config
st.set_page_config(page_title="GeoInt Analysis", layout="wide")

def create_map_html(wfs_urls, wms_urls):
    """
    Create the HTML for the OpenLayers map with improved layer loading
    Args:
        wfs_urls: List of WFS URL strings
        wms_urls: List of WMS URL strings
    """
    # Convert single URLs to lists for consistent handling
    if isinstance(wfs_urls, str):
        wfs_urls = [wfs_urls]
    if isinstance(wms_urls, str):
        wms_urls = [wms_urls]

    # Create the JavaScript array initialization for URLs
    wfs_urls_js = "[" + ",".join(f"'{url}'" for url in wfs_urls) + "]"
    wms_urls_js = "[" + ",".join(f"'{url}'" for url in wms_urls) + "]"

    return f"""
    <!DOCTYPE html>
    <html lang="en">
      <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="initial-scale=1,maximum-scale=1,user-scalable=no" />
        <title>Display WFS and WMS Data with Layer Switcher</title>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/ol@v10.1.0/ol.css" />
        <link rel="stylesheet" href="https://unpkg.com/ol-layerswitcher@4.0.0/dist/ol-layerswitcher.css" />
        <script src="https://cdn.jsdelivr.net/npm/ol@v10.1.0/dist/ol.js"></script>
        <script src="https://unpkg.com/ol-layerswitcher@4.0.0/dist/ol-layerswitcher.js"></script>
        <style>
          #map {{
            width: 100%;
            height: 600px;
            margin: 0;
            padding: 0;
          }}
          .map {{
            width: 100%;
            height: 100%;
          }}
        </style>
      </head>
      <body>
        <div id="map" class="map"></div>
        <script>
          // Base layer (OpenStreetMap)
          const baseLayer = new ol.layer.Tile({{
            source: new ol.source.OSM(),
            title: 'OSM Base Map',
            type: 'base'
          }});

          // Map view
          const view = new ol.View({{
            center: ol.proj.fromLonLat([28.060564, -26.059083]),
            zoom: 12
          }});

          // Initialize map with base layer
          const map = new ol.Map({{
            target: 'map',
            layers: [baseLayer],
            view: view
          }});

          // Create layer groups
          const wmsGroup = new ol.layer.Group({{
            title: 'WMS Layers',
            layers: []
          }});

          const wfsGroup = new ol.layer.Group({{
            title: 'WFS Layers',
            layers: []
          }});

          map.addLayer(wmsGroup);
          map.addLayer(wfsGroup);

          // Add WMS layers
          const wmsUrls = {wms_urls_js};
          wmsUrls.forEach((url, index) => {{
            const layer = new ol.layer.Tile({{
              source: new ol.source.TileWMS({{
                url: url,
                params: {{
                  'LAYERS': url.includes('traffic') ? 'mtn:mtn_rivonia_geom_traffic' : 'mtn:mtn_rivonia_ff_dataset',
                  'TILED': true
                }},
                serverType: 'geoserver'
              }})
            }});
            wmsGroup.getLayers().push(layer);
          }});

          // Add WFS layers
          const wfsUrls = {wfs_urls_js};
          const colors = ['rgba(0, 0, 255, 0.2)', 'rgba(255, 0, 0, 0.2)'];
          
          wfsUrls.forEach((url, index) => {{
            fetch(url)
              .then(response => response.json())
              .then(data => {{
                const layer = new ol.layer.Vector({{
                  source: new ol.source.Vector({{
                    features: new ol.format.GeoJSON().readFeatures(data, {{
                      featureProjection: 'EPSG:3857'
                    }})
                  }}),
                  style: new ol.style.Style({{
                    fill: new ol.style.Fill({{
                      color: colors[index]
                    }}),
                    stroke: new ol.style.Stroke({{
                      color: colors[index].replace('0.2', '1'),
                      width: 2
                    }})
                  }})
                }});
                wfsGroup.getLayers().push(layer);
                
                // Fit to the extent of all features
                const extent = layer.getSource().getExtent();
                map.getView().fit(extent, {{
                  padding: [50, 50, 50, 50],
                  duration: 1000
                }});
              }});
          }});

          // Add layer switcher
          const layerSwitcher = new ol.control.LayerSwitcher({{
            tipLabel: 'Layers',
            groupSelectStyle: 'children',
            activationMode: 'click',
            startActive: true
          }});
          map.addControl(layerSwitcher);

          // Add click interaction to display coordinates
          map.on('click', function(evt) {{
            const coords = ol.proj.transform(evt.coordinate, 'EPSG:3857', 'EPSG:4326');
            console.log('Coordinates:', coords);
          }});
        </script>
      </body>
    </html>
    """

def segregate_query(query):
    """Use GPT-4 to segregate the query into traffic and footfall components"""
    system_prompt = '''You are a query analysis expert specializing in separating mixed queries into distinct traffic and footfall components. 
    Your task is to analyze a user query and split it into separate traffic-related and footfall-related queries while maintaining the original intent and parameters of each part.
    
    For traffic data, look for:
    - "traffic density" or "avg_traffic_den"
    - References to "roads" and "traffic"
    - Numerical thresholds related to traffic (e.g., "> 8")
    - Time periods specifically related to traffic
    
    For footfall data, look for:
    - References to "visitors", "footfall", or "competitors"
    - "ff_" or "ffc_" prefixed metrics
    - Evening/morning/afternoon visitor patterns
    - References to mall visitors or competitor locations
    
    Each component should maintain its own:
    - Distance/radius conditions
    - Time period specifications
    - Numerical thresholds
    
    If a condition is ambiguous (like a number threshold), assign it based on nearby context words:
    - If near traffic/roads/density words → traffic query
    - If near footfall/visitors/mall words → footfall query
    
    Return ONLY a JSON with two keys: 'traffic_query' and 'footfall_query'. If either component is not present, set that key to null.
    '''

    prompt = f'''Analyze the following query and separate it into traffic and footfall components.
    Maintain any radius/distance conditions, thresholds, and time periods specific to each component.
    
    Query: {query}
    '''

    client = OpenAI()
    response = client.chat.completions.create(
        model='gpt-4',
        messages=[
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': prompt}
        ],
        temperature=0.1
    )

    try:
        # Parse the response using json.loads instead of eval
        result = json.loads(response.choices[0].message.content)
        return result
    except Exception as e:
        st.error(f"Error parsing query segregation response: {str(e)}")
        return {"traffic_query": None, "footfall_query": None}

def process_query(query):
    """Process the query and generate map with both WFS and WMS layers"""
    try:
        with st.spinner("Analyzing query..."):
            segregated_queries = segregate_query(query)
            wfs_urls = []
            wms_urls = []
            
            # Process traffic query if present
            if segregated_queries['traffic_query']:
                with st.spinner("Processing traffic data..."):
                    # Generate WFS URL
                    traffic_wfs_url = get_traffic_url(segregated_queries['traffic_query'])
                    wfs_urls.append(traffic_wfs_url)
                    st.session_state.traffic_wfs_url = traffic_wfs_url
                    
                    # Generate WMS URL
                    traffic_wms_url = get_wms_traffic_url(segregated_queries['traffic_query'])
                    wms_urls.append(traffic_wms_url)
                    st.session_state.traffic_wms_url = traffic_wms_url
                    
                    st.success("Traffic URLs Generated Successfully!")
                    st.subheader("Generated Traffic URLs")
                    st.code(f"WFS: {traffic_wfs_url}\nWMS: {traffic_wms_url}")
            
            # Process footfall query if present
            if segregated_queries['footfall_query']:
                with st.spinner("Processing footfall data..."):
                    # Generate WFS URL
                    footfall_wfs_url = get_footfall_url(segregated_queries['footfall_query'])
                    wfs_urls.append(footfall_wfs_url)
                    st.session_state.footfall_wfs_url = footfall_wfs_url
                    
                    # Generate WMS URL
                    footfall_wms_url = get_footfall_wms_url(segregated_queries['footfall_query'])
                    wms_urls.append(footfall_wms_url)
                    st.session_state.footfall_wms_url = footfall_wms_url
                    
                    st.success("Footfall URLs Generated Successfully!")
                    st.subheader("Generated Footfall URLs")
                    st.code(f"WFS: {footfall_wfs_url}\nWMS: {footfall_wms_url}")
            
            # Generate map if we have any URLs
            if wfs_urls or wms_urls:
                st.subheader("Geographic Visualization")
                # map_html = create_map_html(wfs_urls, wms_urls)
                # st.components.v1.html(map_html, height=600)
                map_html = create_map_html(wfs_urls, wms_urls)
                st.components.v1.html(map_html, height=600)
            
            # If neither query was generated
            if not (segregated_queries['traffic_query'] or segregated_queries['footfall_query']):
                st.warning("Could not identify any specific traffic or footfall related queries. Please rephrase your query.")
                    
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
    
def main():
    # Try to load logo
    try:
        logo = Image.open("./geoInt.png")
        st.image(logo, width=200)
    except:
        pass

    st.title("GeoInt Analysis Dashboard")

    # Initialize session state
    for key in ['traffic_wfs_url', 'traffic_wms_url', 'footfall_wfs_url', 'footfall_wms_url']:
        if key not in st.session_state:
            st.session_state[key] = None

    # Query input section
    st.subheader("Query Input")
    query = st.text_area(
        "Enter your query:",
        placeholder="Example: Within 5km radius of my mall, show me roads with traffic density > 8 and evening footfall > 4",
        help="Enter your query to analyze traffic and/or footfall data"
    )

    if st.button("Analyze Data"):
        process_query(query)
    else:
        st.info("Enter a query and click 'Analyze Data' to begin analysis")

if __name__ == "__main__":
    main()
