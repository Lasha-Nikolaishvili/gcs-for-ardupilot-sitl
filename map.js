console.log("map.js loaded...");

window.onload = function () {
    console.log("Leaflet map initializing...");

    // Create map
    const map = L.map('map').setView([41.79071700571516, 44.7580536055492], 13);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);

    // Make available globally
    window.map = map;

    // Drone marker
    const svgDroneIcon = L.icon({
        iconUrl: 'media/drone.svg',
        iconSize: [36, 36],
        iconAnchor: [24, 24],
        popupAnchor: [0, -24]
    });

    const droneMarker = L.marker(map.getCenter(), { icon: svgDroneIcon }).addTo(map);
    window.updateDroneMarker = function (lat, lon) {
        // console.log(`Updating drone marker to: ${lat}, ${lon}`);
        if (droneMarker) {
            droneMarker.setLatLng([lat, lon]);
        } else {
            console.warn("Drone marker is not defined.");
        }
    };

    // Initialize all global variables
    window.waypoints = [];
    window.waypointMarkers = [];
    window.polyline = L.polyline([], { color: 'blue' }).addTo(map);

    window.geofencePoints = [];
    window.geofenceMarkers = [];
    window.geofencePolyline = L.polyline([], { color: 'red' }).addTo(map);

    window.rallyPoints = [];
    window.rallyMarkers = [];

    // Utility icon generator
    function numberedIcon(number, color) {
        return L.divIcon({
            className: 'custom-div-icon',
            html: `
                <div style="display: flex; flex-direction: column; align-items: center;">
                    <div style="
                        background-color: ${color};
                        border-radius: 50%;
                        width: 32px;
                        height: 32px;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.3);
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        color: white;
                        font-size: 16px;
                        font-weight: bold;
                        font-family: 'Arial', sans-serif;
                        border: 2px solid white;
                        z-index: 1;
                    ">${number}</div>
                    <div style="
                        width: 0;
                        height: 0;
                        border-left: 6px solid transparent;
                        border-right: 6px solid transparent;
                        border-top: 10px solid ${color};
                        margin-top: -2px;
                        z-index: 0;
                    "></div>
                </div>
            `,
            iconSize: [32, 42],
            iconAnchor: [16, 42]
        });
    }

    // Expose all interaction functions to PySide
    window.addWaypoint = function (lat, lng) {
        const number = window.waypoints.length + 1;
        const marker = L.marker([lat, lng], { icon: numberedIcon(number, 'blue') }).addTo(map);
        window.waypointMarkers.push(marker);
        window.waypoints.push([lat, lng]);
        window.polyline.setLatLngs(window.waypoints);
    };

    window.clearWaypoints = function () {
        window.waypoints = [];
        window.waypointMarkers.forEach(marker => map.removeLayer(marker));
        window.waypointMarkers = [];
        window.polyline.setLatLngs([]);
    };

    window.getWaypoints = function () {
        console.log("Returning waypoints:", window.waypoints);
        return window.waypoints;
    };

    window.setWaypoints = function (newWpts) {
        window.clearWaypoints();
        newWpts.forEach(([lat, lng]) => window.addWaypoint(lat, lng));
    };

    window.addGeofencePoint = function (lat, lng) {
        const number = window.geofencePoints.length + 1;
        const marker = L.marker([lat, lng], { icon: numberedIcon(number, 'red') }).addTo(map);
        window.geofenceMarkers.push(marker);
        window.geofencePoints.push([lat, lng]);
        window.updateGeofence();
    };

    window.clearGeofence = function () {
        window.geofencePoints = [];
        window.geofenceMarkers.forEach(marker => map.removeLayer(marker));
        window.geofenceMarkers = [];
        window.geofencePolyline.setLatLngs([]);
    };

    window.updateGeofence = function () {
        const points = window.geofencePoints;
        if (points.length > 1) {
            window.geofencePolyline.setLatLngs([...points, points[0]]);
        } else {
            window.geofencePolyline.setLatLngs(points);
        }
    };

    window.getGeofence = function () {
        console.log("Returning geofence points:", window.geofencePoints);
        return window.geofencePoints;
    };

    window.setGeofence = function (newFence) {
        window.clearGeofence();
        newFence.forEach(([lat, lng]) => window.addGeofencePoint(lat, lng));
    };

    window.addRallyPoint = function (lat, lng) {
        const number = window.rallyPoints.length + 1;
        const marker = L.marker([lat, lng], { icon: numberedIcon(number, 'green') }).addTo(map);
        window.rallyMarkers.push(marker);
        window.rallyPoints.push([lat, lng]);
    };

    window.clearRallyPoints = function () {
        window.rallyPoints = [];
        window.rallyMarkers.forEach(marker => map.removeLayer(marker));
        window.rallyMarkers = [];
    };

    window.getRallyPoints = function () {
        console.log("Returning rally points:", window.rallyPoints);
        return window.rallyPoints;
    };

    window.setRally = function (newRally) {
        window.clearRallyPoints();
        newRally.forEach(([lat, lng]) => window.addRallyPoint(lat, lng));
    };

    // Map click behavior
    map.on('click', function (e) {
        if (e.originalEvent.ctrlKey) {
            window.addGeofencePoint(e.latlng.lat, e.latlng.lng);
        } else if (e.originalEvent.shiftKey) {
            window.addRallyPoint(e.latlng.lat, e.latlng.lng);
        } else {
            window.addWaypoint(e.latlng.lat, e.latlng.lng);
        }
    });

    console.log("Map and all JS interfaces initialized.");
};
