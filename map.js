var map = L.map('map').setView([37.7749, -122.4194], 13);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);

// Waypoints
var waypoints = [];
var waypointMarkers = [];
var polyline = L.polyline([], { color: 'blue' }).addTo(map);

// Geofence
var geofencePoints = [];
var geofenceMarkers = [];
var geofencePolyline = L.polyline([], { color: 'red' }).addTo(map);

// Rally Points
var rallyPoints = [];
var rallyMarkers = [];

// Utility: create a DivIcon with number and color
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
                ">
                    ${number}
                </div>
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



// Add Waypoint
function addWaypoint(lat, lng) {
    var number = waypoints.length + 1;
    var marker = L.marker([lat, lng], { icon: numberedIcon(number, 'blue') }).addTo(map);
    waypointMarkers.push(marker);
    waypoints.push([lat, lng]);
    updatePolyline();
}

function updatePolyline() {
    polyline.setLatLngs(waypoints);
}

// Add Geofence Point
function addGeofencePoint(lat, lng) {
    var number = geofencePoints.length + 1;
    var marker = L.marker([lat, lng], { icon: numberedIcon(number, 'red') }).addTo(map);
    geofenceMarkers.push(marker);
    geofencePoints.push([lat, lng]);
    updateGeofence();
}

function updateGeofence() {
    if (geofencePoints.length > 1) {
        geofencePolyline.setLatLngs([...geofencePoints, geofencePoints[0]]);
    } else {
        geofencePolyline.setLatLngs(geofencePoints);
    }
}

// Add Rally Point
function addRallyPoint(lat, lng) {
    var number = rallyPoints.length + 1;
    var marker = L.marker([lat, lng], { icon: numberedIcon(number, 'green') }).addTo(map);
    rallyMarkers.push(marker);
    rallyPoints.push([lat, lng]);
}

// Map Click Behavior
map.on('click', function (e) {
    if (e.originalEvent.ctrlKey) {
        addGeofencePoint(e.latlng.lat, e.latlng.lng);
    } else if (e.originalEvent.shiftKey) {
        addRallyPoint(e.latlng.lat, e.latlng.lng);
    } else {
        addWaypoint(e.latlng.lat, e.latlng.lng);
    }
});

// Clear Functions
function clearWaypoints() {
    waypoints = [];
    waypointMarkers.forEach(marker => map.removeLayer(marker));
    waypointMarkers = [];
    polyline.setLatLngs([]);
}

function clearGeofence() {
    geofencePoints = [];
    geofenceMarkers.forEach(marker => map.removeLayer(marker));
    geofenceMarkers = [];
    geofencePolyline.setLatLngs([]);
}

function clearRallyPoints() {
    rallyPoints = [];
    rallyMarkers.forEach(marker => map.removeLayer(marker));
    rallyMarkers = [];
}

// Getters
function getWaypoints() {
    return waypoints;
}

function getGeofence() {
    return geofencePoints;
}

function getRallyPoints() {
    return rallyPoints;
}
