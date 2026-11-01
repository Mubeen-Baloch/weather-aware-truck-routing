import { useEffect, useRef } from 'react';
import mapboxgl from 'mapbox-gl';

import type { Checkpoint, RouteResult } from '../api/routeAnalysis';

import 'mapbox-gl/dist/mapbox-gl.css';

interface Props {
  routes: RouteResult[];
  origin: [number, number];
  destination: [number, number];
  selectedIndex: number;
  onCheckpointSelect: (checkpoint: Checkpoint) => void;
}

const riskColors: Record<string, string> = {
  low: '#28a36a', moderate: '#f2b134', high: '#ed7b24', severe: '#d95050', 'no-travel': '#6f1d1b', unavailable: '#718096',
};

export function RouteMap({ routes, origin, destination, selectedIndex, onCheckpointSelect }: Props) {
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
      markers.current.push(
        new mapboxgl.Marker({ color: '#147d64' }).setLngLat(origin).setPopup(new mapboxgl.Popup({ offset: 20 }).setText('Origin')).addTo(current),
        new mapboxgl.Marker({ color: '#b42318' }).setLngLat(destination).setPopup(new mapboxgl.Popup({ offset: 20 }).setText('Destination')).addTo(current),
      );
      const selected = routes.find((route) => route.index === selectedIndex) ?? routes[0];
      const bounds = new mapboxgl.LngLatBounds();
      selected.geometry.coordinates.forEach((coordinate) => bounds.extend(coordinate));
      current.fitBounds(bounds, { padding: 55, maxZoom: 9, duration: 500 });
    };
    if (current.isStyleLoaded()) draw(); else current.once('load', draw);
    return () => { current.off('load', draw); };
  }, [routes, origin, destination, selectedIndex, onCheckpointSelect]);

  if (!import.meta.env.VITE_MAPBOX_ACCESS_TOKEN) {
    return <div className="map-placeholder">Add `VITE_MAPBOX_ACCESS_TOKEN` to `frontend/.env` to render the interactive Mapbox map.</div>;
  }
  return <div className="route-map" ref={element} aria-label="Route map" />;
}
