// map.js
console.log("map.js loaded...");

window.onload = function () {
    console.log("Leaflet map initializing...");

    // ─── Create map and base layer ────────────────────────────────────────
    const map = L.map('map').setView([41.79071700571516, 44.7580536055492], 13);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);
    window.map = map;

    // ─── Drone marker (unchanged) ─────────────────────────────────────────
    const svgDroneIcon = L.icon({
        iconUrl: 'media/drone.svg',
        iconSize: [36, 36],
        iconAnchor: [24, 24],
        popupAnchor: [0, -24]
    });
    const droneMarker = L.marker(map.getCenter(), { icon: svgDroneIcon }).addTo(map);
    window.updateDroneMarker = (lat, lon) => {
        if (droneMarker) droneMarker.setLatLng([lat, lon]);
    };

    // ─── Global state ─────────────────────────────────────────────────────
    window.waypoints        = [];  // {lat, lng, alt}
    window.waypointMarkers  = [];
    window.polyline         = L.polyline([], { color: 'blue' }).addTo(map);

    window.geofencePoints   = [];  // [lat, lng]
    window.geofenceMarkers  = [];
    window.geofencePolyline = L.polygon([], { color: 'red' }).addTo(map);

    window.rallyPoints      = [];  // [lat, lng]
    window.rallyMarkers     = [];

    // ─── Icon helper ──────────────────────────────────────────────────────
    function numberedIcon(number, color) {
        return L.divIcon({
            className: 'custom-div-icon',
            html: `
                <div style="display:flex;flex-direction:column;align-items:center">
                  <div style="
                    background-color:${color};
                    border-radius:50%;
                    width:32px;height:32px;
                    box-shadow:0 2px 4px rgba(0,0,0,0.3);
                    display:flex;justify-content:center;align-items:center;
                    color:white;font-size:16px;font-weight:bold;
                    border:2px solid white;z-index:1
                  ">${number}</div>
                  <div style="
                    width:0;height:0;
                    border-left:6px solid transparent;
                    border-right:6px solid transparent;
                    border-top:10px solid ${color};
                    margin-top:-2px;z-index:0
                  "></div>
                </div>
            `,
            iconSize: [32,42],
            iconAnchor: [16,42]
        });
    }

    // ─── Refresh the mission polyline ──────────────────────────────────────
    function refreshPolyline() {
        const pts = window.waypoints.map(w => [w.lat, w.lng]);
        window.polyline.setLatLngs(pts);
    }

    // ─── Refresh the geofence polygon ─────────────────────────────────────
    function refreshGeofence() {
        if (window.geofencePoints.length > 2) {
            // polygon closes automatically
            window.geofencePolyline.setLatLngs(window.geofencePoints);
        } else {
            // less than 3 points draws a polyline
            window.geofencePolyline.setLatLngs(window.geofencePoints);
        }
    }

    // ─── Waypoint functions ────────────────────────────────────────────────
    window.addWaypoint = (lat, lng, alt = 15) => {
        const idx = window.waypoints.length;
        window.waypoints.push({ lat, lng, alt });

        const marker = L.marker([lat, lng], {
            icon: numberedIcon(idx + 1, 'blue'),
            draggable: true
        }).addTo(map);

        // Drag to update coords
        marker.on('dragend', e => {
            const p = e.target.getLatLng();
            window.waypoints[idx].lat = p.lat;
            window.waypoints[idx].lng = p.lng;
            map.closePopup();
            refreshPolyline();
        });

        // Click to open editor
        marker.on('click', () => openWaypointEditor(idx));

        window.waypointMarkers.push(marker);
        refreshPolyline();
    };

    window.clearWaypoints = () => {
        window.waypointMarkers.forEach(m => map.removeLayer(m));
        window.waypointMarkers = [];
        window.waypoints = [];
        window.polyline.setLatLngs([]);
    };

    window.getWaypoints = () =>
        window.waypoints.map(w => [w.lat, w.lng, w.alt]);

    window.setWaypoints = arr => {
        window.clearWaypoints();
        arr.forEach(([lat, lng, alt]) => window.addWaypoint(lat, lng, alt));
    };

    // ─── Waypoint Editor ─────────────────────────────────────────────────────
    window.openWaypointEditor = idx => {
        const wp = window.waypoints[idx];
        const html = `
        <div style="
            background: #1a1d21;
            border: 2px solid #0094ff;
            border-radius: 8px;
            padding: 12px;
            min-width: 220px;
            color: #ffffff;
            font-family: 'Segoe UI', Arial, sans-serif;
        ">
            <h4 style="
            margin: 0 0 8px;
            text-align: center;
            font-size: 16px;
            color: #0094ff;
            ">Edit Waypoint ${idx+1}</h4>
            <label style="display:block; margin-bottom:6px; font-size:14px;">
            Lat:<br>
            <input
                id="wp-lat-${idx}"
                type="number" step="0.000001"
                value="${wp.lat.toFixed(6)}"
                style="
                width:100%;
                padding:4px 6px;
                border:1px solid #0094ff;
                border-radius:4px;
                background: #0e0f12;
                color: #ffffff;
                box-sizing:border-box;
                margin-top:2px;
                "
            >
            </label>
            <label style="display:block; margin-bottom:6px; font-size:14px;">
            Lng:<br>
            <input
                id="wp-lng-${idx}"
                type="number" step="0.000001"
                value="${wp.lng.toFixed(6)}"
                style="
                width:100%;
                padding:4px 6px;
                border:1px solid #0094ff;
                border-radius:4px;
                background: #0e0f12;
                color: #ffffff;
                box-sizing:border-box;
                margin-top:2px;
                "
            >
            </label>
            <label style="display:block; margin-bottom:12px; font-size:14px;">
            Alt:<br>
            <input
                id="wp-alt-${idx}"
                type="number" step="1"
                value="${wp.alt}"
                style="
                width:100%;
                padding:4px 6px;
                border:1px solid #0094ff;
                border-radius:4px;
                background: #0e0f12;
                color: #ffffff;
                box-sizing:border-box;
                margin-top:2px;
                "
            >
            </label>
            <div style="text-align:center; margin-top:8px;">
            <button
                onclick="saveWaypoint(${idx})"
                style="
                background: #0094ff;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                cursor: pointer;
                font-weight: 600;
                "
            >Save</button>
            <button
                onclick="deleteWaypoint(${idx})"
                style="
                background: #c0392b;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                cursor: pointer;
                font-weight: 600;
                margin-left:8px;
                "
            >Delete</button>
            </div>
        </div>
        `;
        L.popup({
        closeOnClick: false,
        autoClose:    false,
        offset:       [0, -30]
        })
        .setLatLng(window.waypointMarkers[idx].getLatLng())
        .setContent(html)
        .openOn(map);
    };

    window.saveWaypoint = idx => {
        const lat = parseFloat(document.getElementById(`wp-lat-${idx}`).value);
        const lng = parseFloat(document.getElementById(`wp-lng-${idx}`).value);
        const alt = parseFloat(document.getElementById(`wp-alt-${idx}`).value) || 0;
        window.waypoints[idx] = { lat, lng, alt };
        window.waypointMarkers[idx].setLatLng([lat, lng]);
        map.closePopup();
        refreshPolyline();
    };

    window.deleteWaypoint = idx => {
        map.removeLayer(window.waypointMarkers[idx]);
        window.waypointMarkers.splice(idx, 1);
        window.waypoints.splice(idx, 1);
        // Renumber & rebind
        window.waypointMarkers.forEach((m, i) => {
            m.setIcon(numberedIcon(i + 1, 'blue'));
            m.off('click').off('dragend');
            m.on('click', () => openWaypointEditor(i));
            m.on('dragend', e => {
                const p = e.target.getLatLng();
                window.waypoints[i].lat = p.lat;
                window.waypoints[i].lng = p.lng;
                map.closePopup();
                refreshPolyline();
            });
        });
        map.closePopup();
        refreshPolyline();
    };

    // ─── Geofence functions ────────────────────────────────────────────────
    window.addGeofencePoint = (lat, lng) => {
        const idx = window.geofencePoints.length;
        window.geofencePoints.push([lat, lng]);

        const marker = L.marker([lat, lng], {
            icon: numberedIcon(idx + 1, 'red'),
            draggable: true
        }).addTo(map);

        // Drag to update and redraw
        marker.on('dragend', e => {
            const p = e.target.getLatLng();
            window.geofencePoints[idx] = [p.lat, p.lng];
            map.closePopup();
            refreshGeofence();
        });

        // Click to delete/edit
        marker.on('click', () => openGeofenceEditor(idx));

        window.geofenceMarkers.push(marker);
        refreshGeofence();
    };

    window.clearGeofence = () => {
        window.geofenceMarkers.forEach(m => map.removeLayer(m));
        window.geofenceMarkers = [];
        window.geofencePoints = [];
        window.geofencePolyline.setLatLngs([]);
    };

    window.getGeofence = () => window.geofencePoints;

    window.setGeofence = arr => {
        window.clearGeofence();
        arr.forEach(([lat, lng]) => window.addGeofencePoint(lat, lng));
    };


    // ─── Geofence Editor ───────────────────────────────────────────────────
    window.openGeofenceEditor = idx => {
        const [lat, lng] = window.geofencePoints[idx];
        const html = `
        <div style="
            background: #1a1d21;
            border: 2px solid #0094ff;
            border-radius: 8px;
            padding: 12px;
            min-width: 200px;
            color: #ffffff;
            font-family: 'Segoe UI', Arial, sans-serif;
        ">
            <h4 style="
            margin: 0 0 8px;
            text-align: center;
            font-size: 16px;
            color: #0094ff;
            ">Edit Geofence ${idx+1}</h4>
            <label style="display:block; margin-bottom:6px; font-size:14px;">
            Lat:<br>
            <input
                id="gf-lat-${idx}"
                type="number" step="0.000001"
                value="${lat.toFixed(6)}"
                style="
                width:100%;
                padding:4px 6px;
                border:1px solid #0094ff;
                border-radius:4px;
                background: #0e0f12;
                color: #ffffff;
                box-sizing:border-box;
                margin-top:2px;
                "
            >
            </label>
            <label style="display:block; margin-bottom:12px; font-size:14px;">
            Lng:<br>
            <input
                id="gf-lng-${idx}"
                type="number" step="0.000001"
                value="${lng.toFixed(6)}"
                style="
                width:100%;
                padding:4px 6px;
                border:1px solid #0094ff;
                border-radius:4px;
                background: #0e0f12;
                color: #ffffff;
                box-sizing:border-box;
                margin-top:2px;
                "
            >
            </label>
            <div style="text-align:center;">
            <button
                onclick="saveGeofencePoint(${idx})"
                style="
                background: #0094ff;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                cursor: pointer;
                font-weight: 600;
                "
            >Save</button>
            <button
                onclick="deleteGeofencePoint(${idx})"
                style="
                background: #c0392b;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                cursor: pointer;
                font-weight: 600;
                margin-left:8px;
                "
            >Delete</button>
            </div>
        </div>
        `;
        L.popup({
        closeOnClick: false,
        autoClose:    false,
        offset:       [0, -30]
        })
        .setLatLng(window.geofenceMarkers[idx].getLatLng())
        .setContent(html)
        .openOn(map);
    };


    window.saveGeofencePoint = idx => {
        const lat = parseFloat(document.getElementById(`gf-lat-${idx}`).value);
        const lng = parseFloat(document.getElementById(`gf-lng-${idx}`).value);
        window.geofencePoints[idx] = [lat, lng];
        window.geofenceMarkers[idx].setLatLng([lat, lng]);
        map.closePopup();
        refreshGeofence();
    };

    window.deleteGeofencePoint = idx => {
        map.removeLayer(window.geofenceMarkers[idx]);
        window.geofenceMarkers.splice(idx, 1);
        window.geofencePoints.splice(idx, 1);
        // Renumber & rebind
        window.geofenceMarkers.forEach((m, i) => {
            m.setIcon(numberedIcon(i + 1, 'red'));
            m.off('click').off('dragend');
            m.on('click', () => openGeofenceEditor(i));
            m.on('dragend', e => {
                const p = e.target.getLatLng();
                window.geofencePoints[i] = [p.lat, p.lng];
                map.closePopup();
                refreshGeofence();
            });
        });
        map.closePopup();
        refreshGeofence();
    };

    // ─── Rally‐point functions ──────────────────────────────────────────────
    window.addRallyPoint = (lat, lng) => {
        const idx = window.rallyPoints.length;
        window.rallyPoints.push([lat, lng]);

        const marker = L.marker([lat, lng], {
            icon: numberedIcon(idx + 1, 'green'),
            draggable: true
        }).addTo(map);

        marker.on('dragend', e => {
            const p = e.target.getLatLng();
            window.rallyPoints[idx] = [p.lat, p.lng];
            map.closePopup();
        });

        marker.on('click', () => openRallyEditor(idx));

        window.rallyMarkers.push(marker);
    };

    window.clearRallyPoints = () => {
        window.rallyMarkers.forEach(m => map.removeLayer(m));
        window.rallyMarkers = [];
        window.rallyPoints = [];
    };

    window.getRallyPoints = () => window.rallyPoints;

    window.setRally = arr => {
        window.clearRallyPoints();
        arr.forEach(([lat, lng]) => window.addRallyPoint(lat, lng));
    };

    // ─── Rally Editor ──────────────────────────────────────────────────────
    window.openRallyEditor = idx => {
        const [lat, lng] = window.rallyPoints[idx];
        const html = `
        <div style="
            background: #1a1d21;
            border: 2px solid #0094ff;
            border-radius: 8px;
            padding: 12px;
            min-width: 200px;
            color: #ffffff;
            font-family: 'Segoe UI', Arial, sans-serif;
        ">
            <h4 style="
            margin: 0 0 8px;
            text-align: center;
            font-size: 16px;
            color: #0094ff;
            ">Edit Rally ${idx+1}</h4>
            <label style="display:block; margin-bottom:6px; font-size:14px;">
            Lat:<br>
            <input
                id="ry-lat-${idx}"
                type="number" step="0.000001"
                value="${lat.toFixed(6)}"
                style="
                width:100%;
                padding:4px 6px;
                border:1px solid #0094ff;
                border-radius:4px;
                background: #0e0f12;
                color: #ffffff;
                box-sizing:border-box;
                margin-top:2px;
                "
            >
            </label>
            <label style="display:block; margin-bottom:12px; font-size:14px;">
            Lng:<br>
            <input
                id="ry-lng-${idx}"
                type="number" step="0.000001"
                value="${lng.toFixed(6)}"
                style="
                width:100%;
                padding:4px 6px;
                border:1px solid #0094ff;
                border-radius:4px;
                background: #0e0f12;
                color: #ffffff;
                box-sizing:border-box;
                margin-top:2px;
                "
            >
            </label>
            <div style="text-align:center;">
            <button
                onclick="saveRallyPoint(${idx})"
                style="
                background: #0094ff;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                cursor: pointer;
                font-weight: 600;
                "
            >Save</button>
            <button
                onclick="deleteRallyPoint(${idx})"
                style="
                background: #c0392b;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                cursor: pointer;
                font-weight: 600;
                margin-left:8px;
                "
            >Delete</button>
            </div>
        </div>
        `;
        L.popup({
        closeOnClick: false,
        autoClose:    false,
        offset:       [0, -30]
        })
        .setLatLng(window.rallyMarkers[idx].getLatLng())
        .setContent(html)
        .openOn(map);
    };

    window.saveRallyPoint = idx => {
        const lat = parseFloat(document.getElementById(`ry-lat-${idx}`).value);
        const lng = parseFloat(document.getElementById(`ry-lng-${idx}`).value);
        window.rallyPoints[idx] = [lat, lng];
        window.rallyMarkers[idx].setLatLng([lat, lng]);
        map.closePopup();
    };

    window.deleteRallyPoint = idx => {
        map.removeLayer(window.rallyMarkers[idx]);
        window.rallyMarkers.splice(idx, 1);
        window.rallyPoints.splice(idx, 1);
        window.rallyMarkers.forEach((m, i) => {
            m.setIcon(numberedIcon(i + 1, 'green'));
            m.off('click').off('dragend');
            m.on('click', () => openRallyEditor(i));
            m.on('dragend', e => {
                const p = e.target.getLatLng();
                window.rallyPoints[i] = [p.lat, p.lng];
                map.closePopup();
            });
        });
        map.closePopup();
    };

    // ─── Map click: choose which list to add to ───────────────────────────
    map.on('click', e => {
        if      (e.originalEvent.ctrlKey)  window.addGeofencePoint(e.latlng.lat, e.latlng.lng);
        else if (e.originalEvent.shiftKey) window.addRallyPoint(e.latlng.lat, e.latlng.lng);
        else                                window.addWaypoint(e.latlng.lat, e.latlng.lng);
    });

    console.log("Map and all JS interfaces initialized.");
};
