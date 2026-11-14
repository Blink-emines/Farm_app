import { TileLayer } from 'react-leaflet';

// Esri World Imagery. The attribution text matches the service's own copyrightText.
// TODO before any public launch: check Esri's terms of use for this tile service.
export function SatelliteTiles() {
  return (
    <TileLayer
      url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
      maxNativeZoom={17}
      attribution="Tiles &copy; Esri &mdash; Source: Esri, Vantor, Earthstar Geographics, and the GIS User Community"
    />
  );
}

export function StreetTiles() {
  return (
    <TileLayer
      url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
      attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    />
  );
}
