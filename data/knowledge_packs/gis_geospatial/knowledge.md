# GIS & Geospatial

## Pick-the-tool cheat sheet
- Desktop analysis/visualization: **QGIS** (free, plugins). Command-line convert/reproject/warp: **GDAL/OGR** (`ogr2ogr`, `gdalwarp`, `gdal_translate`, `gdalinfo`).
- Spatial database: **PostGIS** (PostgreSQL extension) — SQL spatial ops + indexing. Alt: SpatiaLite (SQLite).
- Python: **GeoPandas** (vector, pandas + shapely), **Shapely** (geometry ops), **rasterio** (raster), **Fiona** (I/O), **pyproj** (CRS transforms), **rasterstats**, **xarray/rioxarray** (multidim raster).
- Web maps: **Leaflet** (light), **Mapbox GL JS / MapLibre** (vector tiles, WebGL), **OpenLayers**. Tile server: TileServer GL, Martin.
- Remote sensing: **rasterio/GDAL**, **Google Earth Engine**, **SNAP** (Sentinel).

## Coordinate reference systems (CRS)
- **Geographic CRS**: angular lat/lon degrees on an ellipsoid. **WGS84 = EPSG:4326** (GPS default). Not for measuring area/distance directly (degrees aren't uniform meters).
- **Projected CRS**: flattens to a Cartesian plane in **meters**. **Web Mercator = EPSG:3857** (all web basemaps; distorts area badly near poles — Greenland looks huge). **UTM zones** (EPSG:326xx N / 327xx S) — 6°-wide, low distortion locally. National grids (e.g. State Plane, British National Grid EPSG:27700).
- **Datum**: the ellipsoid + reference frame (WGS84, NAD83, ETRS89, NAD27). Datum shift between NAD27<->WGS84 can be 10s–100s of meters — a real ground error, not rounding.
- **EPSG code** = integer ID for a CRS (from the EPSG registry). Always tag data with its CRS; a CRS-less file is ambiguous.
- **Axis order trap**: EPSG:4326 is officially **(lat, lon)** but GeoJSON/most tools use **(lon, lat = x, y)**. Mismatch flips points across the globe.

## Projections + distortion
- No flat map preserves all of area, shape, distance, direction (Gauss). Choose by purpose:
  - **Equal-area** (Albers, Mollweide, Lambert Azimuthal) -> area stats, choropleths, density.
  - **Conformal** (Mercator, Lambert Conformal Conic, Transverse Mercator/UTM) -> preserves local angles/shape, navigation.
  - **Equidistant** -> true distance from a point/line only.
- Compute area/length in a **projected, appropriate CRS** (UTM or equal-area), never in EPSG:4326 degrees. For long geodesic distances use ellipsoidal `Geod` (pyproj) or PostGIS **geography** type.

## Vector vs raster
- **Vector**: discrete features as coordinates + attributes. **Point** (well, tree), **LineString** (road, river), **Polygon** (parcel, lake; rings — exterior CCW + interior holes CW by convention). Multi* variants. Topology matters.
  - Formats: **Shapefile** (`.shp/.shx/.dbf/.prj` — legacy, 2GB & 10-char field limit, no proper CRS unless `.prj`), **GeoJSON** (`.geojson`, always EPSG:4326 lon/lat per spec), **GeoPackage** (`.gpkg`, modern SQLite-based, preferred), **KML**, **FlatGeobuf**, **GML**. WKT/WKB = geometry text/binary encoding.
- **Raster**: grid of cells/pixels, each a value; has resolution (cell size), extent, bands, nodata. **GeoTIFF** (`.tif` + geo tags; **Cloud-Optimized GeoTIFF/COG** for HTTP range reads), NetCDF/HDF (multidim), imagery, DEMs.
- Rule of thumb: continuous phenomena (elevation, temperature, imagery) -> raster; discrete objects/boundaries -> vector.

## Spatial operations
- Geometry: **buffer** (zone within distance), **intersection/union/difference** (overlay), **convex hull**, **centroid**, **simplify** (Douglas-Peucker), **dissolve** (merge by attribute).
- Predicates (DE-9IM): `intersects`, `contains`, `within`, `overlaps`, `touches`, `crosses`, `disjoint`, `dwithin`.
- **Spatial join**: attach attributes by spatial relationship (points-in-polygons, nearest). GeoPandas `sjoin`, PostGIS `ST_Intersects` join.
- Raster: map algebra (per-cell math), reclassify, zonal statistics (aggregate raster by polygons), resample (nearest/bilinear/cubic), hillshade/slope/aspect from DEM, raster<->vector (polygonize/rasterize).

## PostGIS + indexing
- Types: `geometry` (planar, fast, CRS via SRID) vs **`geography`** (spherical, meters, correct for lat/lon distance/area). Set SRID: `ST_SetSRID(geom, 4326)`; reproject `ST_Transform(geom, 3857)`.
- Common: `ST_Area`, `ST_Length`, `ST_Distance`, `ST_DWithin`, `ST_Intersects`, `ST_Buffer`, `ST_Contains`, `ST_MakePoint`, `ST_AsGeoJSON`.
- **Spatial index = GiST (R-tree)**: `CREATE INDEX idx ON t USING GIST (geom);`. Predicates use the index only via bounding-box (`&&`) prefilter — `ST_Intersects`/`ST_DWithin` do this automatically; plain `ST_Distance < x` does NOT (use `ST_DWithin`). `ANALYZE` after load.

## Web maps + tiling
- **XYZ/slippy tiles**: 256px tiles addressed `{z}/{x}/{y}`, z=0 world -> z increases 4x tiles/level (quadtree). URL template `https://.../{z}/{x}/{y}.png`. Origin top-left; **TMS** flips Y. Almost all web tiles are EPSG:3857.
- **Raster tiles** (pre-rendered PNG) vs **vector tiles** (**MVT/`.pbf`**, styled client-side, retina/rotation, smaller). Package as **MBTiles**/**PMTiles**.
- Geocoding: address <-> coordinates (Nominatim/OSM, Google, Pelias). Reverse geocoding = coords -> address. Watch usage terms/rate limits.

## Geoprocessing workflows & analysis
- **Overlay analysis**: combine layers to answer siting questions (suitability = weighted intersection of slope, distance-to-road, land use). Vector overlay (union/intersect) vs raster map algebra (weighted sum, boolean masks).
- **Proximity**: buffers, distance rasters, cost-distance/least-cost paths, Voronoi/Thiessen polygons, viewshed (from DEM).
- **Interpolation** (point samples -> continuous surface): IDW (inverse distance), **kriging** (geostatistical, gives uncertainty), spline, natural neighbor. Choose by data density + autocorrelation (variogram).
- **Terrain analysis** from DEM: slope, aspect, hillshade, curvature, flow accumulation/direction (D8), watershed delineation, contours.
- **Density/hotspots**: kernel density estimation, point-pattern (Ripley's K), spatial autocorrelation (**Moran's I** global, LISA local, Getis-Ord Gi\* hotspots).

## Data quality & topology
- **Topology rules**: no gaps/overlaps between adjacent polygons, no dangling nodes, closed rings. Enforce with QGIS/PostGIS topology or `ST_MakeValid`.
- **Snapping tolerance**: near-coincident vertices should snap; sliver polygons arise from digitizing mismatch -> clean/simplify with tolerance.
- **Precision & coordinate storage**: store enough decimal places (6 dp ≈ 0.1 m at equator for lat/lon); watch float rounding in repeated transforms.
- **Attribute joins** (tabular key -> spatial feature) vs spatial joins; keep a stable feature ID.

## Remote sensing basics
- Multispectral bands (Landsat 8/9, Sentinel-2 ~10m). **NDVI** = (NIR−Red)/(NIR+Red), vegetation health [−1,1]. NDWI (water), NDBI (built-up).
- Levels: raw DN -> radiance -> **reflectance** (atmospheric correction). Resolution: spatial (cell size), spectral (bands), temporal (revisit), radiometric (bit depth). Supervised/unsupervised classification -> land cover.

## GDAL/OGR & PostGIS quick reference
```bash
gdalinfo img.tif                       # inspect CRS, extent, bands, nodata
gdalwarp -t_srs EPSG:3857 in.tif out.tif   # reproject raster
gdal_translate -of COG in.tif out.tif      # cloud-optimized GeoTIFF
ogr2ogr -t_srs EPSG:4326 out.gpkg in.shp    # convert + reproject vector
ogrinfo -so data.gpkg layer                 # summary of a vector layer
```
- PostGIS load: `shp2pgsql -s 4326 file.shp table | psql`, or `ogr2ogr -f PostgreSQL PG:"dbname=..." in.gpkg`.
- Common tuning: `ST_Simplify` before serving, cluster on the GiST index, `VACUUM ANALYZE`, use `geography` only where spherical accuracy is needed (it's slower than planar `geometry`).

## Standards & services
- **OGC standards**: **WMS** (rendered map images), **WMTS** (tiled), **WFS** (vector features), **WCS** (coverages/raster), **OGC API** (modern REST/JSON successors). CRS declared via URN/EPSG.
- Web mapping stack: tile source (XYZ/vector) + basemap (OSM, satellite) + overlays + interactivity (popups, clustering). Respect attribution + tile usage limits.

## Pitfalls -> Fix
- **CRS mismatch** (layers in different CRS overlaid) -> features don't line up or vanish -> reproject all to one CRS with `ST_Transform`/`to_crs()`; verify every layer has a defined CRS.
- **Measuring area/distance in EPSG:4326 degrees** -> nonsense units -> reproject to UTM/equal-area, or use `geography`/geodesic functions.
- **Lat/lon axis order flipped** (4326 lat,lon vs lon,lat) -> points in the ocean/wrong hemisphere -> confirm tool's convention; GeoJSON is always [lon, lat].
- **Invalid geometries** (self-intersections, unclosed rings) -> ops error/return wrong -> `ST_IsValid`/`ST_MakeValid`, shapely `.buffer(0)` / `make_valid`.
- **Spatial index not used** -> full table scan, slow joins -> use `ST_DWithin`/`ST_Intersects` (bbox-aware), create GiST index, `ANALYZE`, check `EXPLAIN`.
- **Shapefile limits** (10-char fields, truncated names, no CRS without .prj, 2GB) -> data loss -> use GeoPackage; ship the `.prj`.
- **Web Mercator area distortion** -> wrong stats near poles -> never compute area in 3857; reproject to equal-area.
- **Datum ignored** (NAD27 vs WGS84) -> 10s–100s m offset -> apply datum transform, not just a projection change.
- **Mixed nodata / resolution** in raster math -> garbage cells -> align grids (resample to common resolution/extent), set nodata masks.
- **Polygon winding/holes wrong** -> holes fill in or self-overlap -> follow exterior/interior ring order; validate.
- **Interpolating with wrong method/no autocorrelation check** -> misleading surface -> inspect variogram; IDW for quick, kriging when uncertainty matters.
- **Sliver polygons / unsnapped vertices from overlay** -> tiny false features -> set snapping tolerance, `ST_MakeValid`, filter by min area.
- **Antimeridian / pole crossing** (features spanning ±180°) -> geometries wrap wrongly -> split at the dateline, use appropriate CRS.
- **Reprojecting rasters with nearest-neighbor for continuous data** -> blocky artifacts -> bilinear/cubic for continuous, nearest only for categorical.
- **Assuming GeoJSON can hold any CRS** -> spec mandates WGS84 lon/lat -> reproject to 4326 for GeoJSON, or use GeoPackage for other CRS.
- **Too many decimal places / huge geometries** in web maps -> slow tiles -> simplify per zoom, use vector tiles, coordinate precision limits.
