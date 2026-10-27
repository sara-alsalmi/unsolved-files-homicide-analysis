# Map Boundary Source

`us-states.json` contains simplified boundaries for the 50 US states and the District of Columbia.

- Source: PublicaMundi MappingAPI, `data/geojson/us-states.json`
  https://github.com/PublicaMundi/MappingAPI
- The boundaries are derived from U.S. Census Bureau cartographic boundary files.
- Changes made for this project: removed Puerto Rico (not in the homicide data) and the `density` property. Only `id` (state FIPS code) and `name` are kept.

The map joins this file to the homicide data by full state name. The boundaries show the state of the reporting agency, not exact crime locations.
