import { useEffect, useRef } from 'react';
import mapboxgl from 'mapbox-gl';

import type { Checkpoint, HeatmapFrame, RouteResult } from '../api/routeAnalysis';

import 'mapbox-gl/dist/mapbox-gl.css';

interface Props {
  routes: RouteResult[];
  origin: [number, number];
  destination: [number, number];
  selectedIndex: number;
  heatmapOffset: number;
  onCheckpointSelect: (checkpoint: Checkpoint) => void;
}

const riskColors: Record<string, string> = {
  low: '#28a36a', moderate: '#f2b134', high: '#ed7b24', severe: '#d95050', 'no-travel': '#6f1d1b', unavailable: '#718096',
};

export function RouteMap({ routes, origin, destination, selectedIndex, heatmapOffset, onCheckpointSelect }: Props) {
  const element = useRef<HTMLDivElement>(null);
  const map = useRef<mapboxgl.Map | null>(null);
  const markers = useRef<mapboxgl.Marker[]>([]);
  const routeIds = useRef(new Set<number>());

  useEffect(() => {
    const token = import.meta.env.VITE_MAPBOX_ACCESS_TOKEN;
    if (!element.current || !token || map.current) return;
    mapboxgl.accessToken = token;
    map.current = new mapboxgl.Map({ container: element.current, style: 'mapbox://styles/mapbox/light-v11', center: [-97.2, 31.5], zoom: 6 });
    map.current.addControl(new mapboxgl.NavigationControl(), 'top-right');
    return () => { map.current?.remove(); map.current = null; };
  }, []);

  useEffect(() => {
    const current = map.current;
    if (!current || !routes.length) return;
    const draw = () => {
      markers.current.forEach((marker) => marker.remove());
      markers.current = [];
      const activeRouteIds = new Set(routes.map((route) => route.index));
      routeIds.current.forEach((routeIndex) => {
        if (activeRouteIds.has(routeIndex)) return;
        const sourceId = `route-${routeIndex}`;
        const layerId = `${sourceId}-line`;
        if (current.getLayer(layerId)) current.removeLayer(layerId);
        if (current.getSource(sourceId)) current.removeSource(sourceId);
      });
      routeIds.current = activeRouteIds;

      const orderedRoutes = [...routes].sort((left, right) => Number(left.index === selectedIndex) - Number(right.index === selectedIndex));
      orderedRoutes.forEach((route) => {
        const sourceId = `route-${route.index}`;
        const layerId = `${sourceId}-line`;
        const source = current.getSource(sourceId) as mapboxgl.GeoJSONSource | undefined;
        const data = { type: 'Feature' as const, properties: {}, geometry: route.geometry };
        if (source) source.setData(data);
        else {
          current.addSource(sourceId, { type: 'geojson', data });
          current.addLayer({ id: layerId, type: 'line', source: sourceId, paint: { 'line-color': route.index === selectedIndex ? '#147d64' : '#7b8794', 'line-width': route.index === selectedIndex ? 6 : 3, 'line-opacity': route.index === selectedIndex ? 1 : 0.55 } });
        }
        current.setPaintProperty(layerId, 'line-color', route.index === selectedIndex ? '#147d64' : '#7b8794');
        current.setPaintProperty(layerId, 'line-width', route.index === selectedIndex ? 6 : 3);
        current.setPaintProperty(layerId, 'line-opacity', route.index === selectedIndex ? 1 : 0.55);
        if (route.index === selectedIndex) {
          route.checkpoints.forEach((checkpoint) => {
            const color = riskColors[checkpoint.risk.level ?? 'unavailable'];
            const marker = new mapboxgl.Marker({ color }).setLngLat(checkpoint.coordinate).addTo(current);
            marker.getElement().addEventListener('click', () => onCheckpointSelect(checkpoint));
            markers.current.push(marker);
          });
        }
      });
      const selectedLayerId = `route-${selectedIndex}-line`;
      if (current.getLayer(selectedLayerId)) current.moveLayer(selectedLayerId);
      const selected = routes.find((route) => route.index === selectedIndex) ?? routes[0];
      const heatmapFrame = selected.heatmapFrames.find((frame) => frame.offsetHours === heatmapOffset);
      drawHeatmap(current, selected, heatmapFrame);
      markers.current.push(
        new mapboxgl.Marker({ color: '#147d64' }).setLngLat(origin).setPopup(new mapboxgl.Popup({ offset: 20 }).setText('Origin')).addTo(current),
        new mapboxgl.Marker({ color: '#b42318' }).setLngLat(destination).setPopup(new mapboxgl.Popup({ offset: 20 }).setText('Destination')).addTo(current),
      );
      const bounds = new mapboxgl.LngLatBounds();
      selected.geometry.coordinates.forEach((coordinate) => bounds.extend(coordinate));
      current.fitBounds(bounds, { padding: 55, maxZoom: 9, duration: 500 });
    };
    if (current.isStyleLoaded()) draw(); else current.once('load', draw);
    return () => { current.off('load', draw); };
  }, [routes, origin, destination, selectedIndex, heatmapOffset, onCheckpointSelect]);

  if (!import.meta.env.VITE_MAPBOX_ACCESS_TOKEN) {
    return <div className="map-placeholder">Add `VITE_MAPBOX_ACCESS_TOKEN` to `frontend/.env` to render the interactive Mapbox map.</div>;
  }
  return <div className="route-map" ref={element} aria-label="Route map" />;
}

function drawHeatmap(map: mapboxgl.Map, route: RouteResult, frame: HeatmapFrame | undefined) {
  const sourceId = 'selected-route-heatmap';
  const layerId = `${sourceId}-line`;
  if (!frame) {
    if (map.getLayer(layerId)) map.removeLayer(layerId);
    if (map.getSource(sourceId)) map.removeSource(sourceId);
    return;
  }
  const checkpointPositions = route.checkpoints.map((checkpoint) => geometryPositionAtRouteDistance(route, checkpoint.distanceMeters));
  const features = frame.segments.map((segment, index) => ({
    type: 'Feature' as const,
    properties: { color: riskColors[segment.risk.level ?? 'unavailable'] },
    geometry: {
      type: 'LineString' as const,
      coordinates: geometrySlice(
        route.geometry.coordinates,
        checkpointPositions[index],
        checkpointPositions[index + 1],
      ),
    },
  }));
  const data = { type: 'FeatureCollection' as const, features };
  const source = map.getSource(sourceId) as mapboxgl.GeoJSONSource | undefined;
  if (source) source.setData(data);
  else {
    map.addSource(sourceId, { type: 'geojson', data });
    map.addLayer({ id: layerId, type: 'line', source: sourceId, paint: { 'line-color': ['get', 'color'], 'line-width': 8, 'line-opacity': 0.8 } });
  }
  if (map.getLayer(layerId)) map.moveLayer(layerId);
}

interface GeometryPosition {
  segmentIndex: number;
  coordinate: [number, number];
}

/**
 * The backend positions checkpoints by mapping provider-distance progress onto
 * geometric route progress. Repeating that mapping here keeps every heatmap
 * segment on the original polyline, including all road turns between markers.
 */
function geometryPositionAtRouteDistance(route: RouteResult, routeDistanceMeters: number): GeometryPosition {
  const coordinates = route.geometry.coordinates;
  if (coordinates.length < 2 || route.distanceMeters <= 0) {
    throw new Error('Route geometry must contain at least two coordinates with a positive distance.');
  }

  const segmentLengths = coordinates.slice(1).map((coordinate, index) => haversineMeters(coordinates[index], coordinate));
  const geometryLength = segmentLengths.reduce((sum, length) => sum + length, 0);
  if (!Number.isFinite(geometryLength) || geometryLength <= 0) {
    throw new Error('Route geometry has no measurable length.');
  }

  const boundedRouteDistance = Math.min(Math.max(routeDistanceMeters, 0), route.distanceMeters);
  const targetDistance = (boundedRouteDistance / route.distanceMeters) * geometryLength;
  let travelled = 0;
  for (let index = 0; index < segmentLengths.length; index += 1) {
    const segmentLength = segmentLengths[index];
    if (targetDistance <= travelled + segmentLength || index === segmentLengths.length - 1) {
      const progress = segmentLength === 0 ? 0 : (targetDistance - travelled) / segmentLength;
      return {
        segmentIndex: index,
        coordinate: interpolate(coordinates[index], coordinates[index + 1], Math.min(Math.max(progress, 0), 1)),
      };
    }
    travelled += segmentLength;
  }
  return { segmentIndex: coordinates.length - 2, coordinate: coordinates.at(-1) as [number, number] };
}

function geometrySlice(
  coordinates: [number, number][],
  start: GeometryPosition | undefined,
  end: GeometryPosition | undefined,
): [number, number][] {
  if (!start || !end || end.segmentIndex < start.segmentIndex) {
    throw new Error('Heatmap frame checkpoints do not align with the route geometry.');
  }
  const sliced: [number, number][] = [start.coordinate];
  for (let vertexIndex = start.segmentIndex + 1; vertexIndex <= end.segmentIndex; vertexIndex += 1) {
    appendIfDistinct(sliced, coordinates[vertexIndex]);
  }
  appendIfDistinct(sliced, end.coordinate);
  return sliced;
}

function appendIfDistinct(coordinates: [number, number][], coordinate: [number, number]) {
  const previous = coordinates.at(-1);
  if (!previous || previous[0] !== coordinate[0] || previous[1] !== coordinate[1]) coordinates.push(coordinate);
}

function interpolate(start: [number, number], end: [number, number], progress: number): [number, number] {
  return [start[0] + ((end[0] - start[0]) * progress), start[1] + ((end[1] - start[1]) * progress)];
}

function haversineMeters(start: [number, number], end: [number, number]): number {
  const toRadians = (degrees: number) => (degrees * Math.PI) / 180;
  const latitudeDelta = toRadians(end[1] - start[1]);
  const longitudeDelta = toRadians(end[0] - start[0]);
  const latitudeStart = toRadians(start[1]);
  const latitudeEnd = toRadians(end[1]);
  const arc = (Math.sin(latitudeDelta / 2) ** 2)
    + (Math.cos(latitudeStart) * Math.cos(latitudeEnd) * (Math.sin(longitudeDelta / 2) ** 2));
  return 6_371_000 * 2 * Math.atan2(Math.sqrt(arc), Math.sqrt(1 - arc));
}
