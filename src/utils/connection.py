from pymavlink import mavutil

class Connection:
    def __init__(self, connection_str='udp:127.0.0.1:14550'):
        # open the connection
        self.master = mavutil.mavlink_connection(connection_str)
        # wait for heartbeat
        self.master.wait_heartbeat()
        self.telemetry = {}
        print(f"Connected: system={self.master.target_system}, component={self.master.target_component}")

    def _wait_for(self, expected_type, condition=lambda msg: True):
        """
        Block until we get a mavlink message of expected_type that
        satisfies `condition(msg)`.  In the meantime, print any telemetry.
        """
        while True:
            msg = self.master.recv_match(blocking=True)
            if not msg:
                continue
            if msg.get_type() == expected_type and condition(msg):
                return msg
            # otherwise treat it as telemetry
            self.update_telemetry(msg)

    def _send_items(self, items, mission_type):
        count = len(items)
        # tell vehicle how many items we will send
        print(f"\n→ Sending {count} items of mission_type={mission_type}")
        self.master.mav.mission_count_send(
            self.master.target_system,
            self.master.target_component,
            count,
            mission_type
        )

        # for each item wait for MISSION_REQUEST, then send it
        for i, itm in enumerate(items):
            print(f"  ● waiting for request seq={i}…")
            # wait for the matching request
            req = self._wait_for(
                'MISSION_REQUEST',
                condition=lambda m: m.seq == i and m.mission_type == mission_type
            )
            # send it
            self.master.mav.mission_item_int_send(
                self.master.target_system,
                self.master.target_component,
                itm['seq'],
                itm['frame'],
                itm['command'],
                itm['current'],
                itm['autocontinue'],
                itm['param1'],
                itm['param2'],
                itm['param3'],
                itm['param4'],
                int(itm['x'] * 1e7),
                int(itm['y'] * 1e7),
                itm['z'],
                mission_type
            )
            print(f"    ▶ sent item seq={i}")
        # finally wait for ACK
        print("  ● waiting for MISSION_ACK…")
        ack = self._wait_for(
            'MISSION_ACK',
            condition=lambda m: m.mission_type == mission_type
        )
        if ack.type != mavutil.mavlink.MAV_MISSION_ACCEPTED:
            raise RuntimeError(f"Upload failed, ACK type={ack.type}")
        print(f"✓ Upload of mission_type={mission_type} done.\n")

    def upload_mission(self, waypoints):
        items = []
        for i, wp in enumerate(waypoints):
            items.append({
                'seq': i,
                'frame': mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
                'command': mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
                'current': 0,
                'autocontinue': 1,
                'param1': wp.get('hold_time', 0),
                'param2': wp.get('acceptance_radius', 0),
                'param3': wp.get('pass_through', 0),
                'param4': wp.get('yaw', 0),
                'x': wp['lat'],
                'y': wp['lon'],
                'z': wp['alt']
            })
        self._send_items(items, mavutil.mavlink.MAV_MISSION_TYPE_MISSION)
        self.telemetry['total_mission_points'] = len(waypoints)

    def upload_fence(self, fence_points):
        items = []
        total = len(fence_points)
        for i, pt in enumerate(fence_points):
            items.append({
                'seq': i,
                'frame': mavutil.mavlink.MAV_FRAME_GLOBAL,
                # ← use the NAV_FENCE_POLYGON_VERTEX_INCLUSION command
                'command': mavutil.mavlink.MAV_CMD_NAV_FENCE_POLYGON_VERTEX_INCLUSION,
                'current': 0,
                'autocontinue': 1,
                # param1 = total number of vertices, param2 = inclusion group (0 by default)
                'param1': total,
                'param2': 0,
                'param3': 0,
                'param4': 0,
                'x': pt['lat'],
                'y': pt['lon'],
                'z': pt.get('alt', 0)
            })
        print(f"Uploading {len(items)} geofence vertices…")
        self._send_items(items, mavutil.mavlink.MAV_MISSION_TYPE_FENCE)

    def upload_rally(self, rally_points):
        items = []
        for i, pt in enumerate(rally_points):
            items.append({
                'seq': i,
                'frame': mavutil.mavlink.MAV_FRAME_GLOBAL,
                # ← use the NAV_RALLY_POINT command
                'command': mavutil.mavlink.MAV_CMD_NAV_RALLY_POINT,
                'current': 0,
                'autocontinue': 1,
                'param1': 0,
                'param2': 0,
                'param3': 0,
                'param4': 0,
                'x': pt['lat'],
                'y': pt['lon'],
                'z': pt.get('alt', 0)
            })
        print(f"Uploading {len(items)} rally points…")
        self._send_items(items, mavutil.mavlink.MAV_MISSION_TYPE_RALLY)
    
    def _download_items(self, mission_type):
        """
        Download all mission items of the given type and return as list of dicts.
        """
        print(f"\n→ Requesting download of mission_type={mission_type}")
        # ask for list
        self.master.mav.mission_request_list_send(
            self.master.target_system,
            self.master.target_component,
            mission_type
        )
        # wait for count
        count_msg = self._wait_for(
            'MISSION_COUNT',
            condition=lambda m: m.mission_type == mission_type
        )
        count = count_msg.count
        print(f"  ← will receive {count} items")

        items = []
        for seq in range(count):
            # request each seq
            self.master.mav.mission_request_int_send(
                self.master.target_system,
                self.master.target_component,
                seq,
                mission_type
            )
            msg = self._wait_for(
                'MISSION_ITEM_INT',
                condition=lambda m: m.seq == seq and m.mission_type == mission_type
            )
            items.append({
                'seq': msg.seq,
                'frame': msg.frame,
                'command': msg.command,
                'current': msg.current,
                'autocontinue': msg.autocontinue,
                'param1': msg.param1,
                'param2': msg.param2,
                'param3': msg.param3,
                'param4': msg.param4,
                'x': msg.x / 1e7,
                'y': msg.y / 1e7,
                'z': msg.z
            })
            print(f"    ← got seq={seq}")
        return items

    def download_and_print_all(self):
        """
        Download mission, fence, and rally, then print them.
        """
        types = [
            (mavutil.mavlink.MAV_MISSION_TYPE_MISSION, "WAYPOINTS"),
            (mavutil.mavlink.MAV_MISSION_TYPE_FENCE,    "FENCE VERTICES"),
            (mavutil.mavlink.MAV_MISSION_TYPE_RALLY,    "RALLY POINTS"),
        ]
        for mtype, title in types:
            items = self._download_items(mtype)
            print(f"\n=== {title} (mission_type={mtype}) ===")
            for itm in items:
                print(f" seq={itm['seq']:>2} cmd={itm['command']:>4} "
                      f"lat={itm['x']:.6f} lon={itm['y']:.6f} alt={itm['z']}")
        print("\nDone downloading and printing all mission items.")

    def update_telemetry(self, msg):
        m = msg.get_type()
        if m == 'HEARTBEAT':
            self.telemetry['mode'] = mavutil.mode_string_v10(msg)
            print(f"[TELEM] HEARTBEAT mode={msg.base_mode}, autopilot={msg.autopilot}")
        elif m == 'ATTITUDE':
            self.telemetry['roll'] = msg.roll
            self.telemetry['pitch'] = msg.pitch
            self.telemetry['yaw'] = msg.yaw
            print(f"[TELEM] ATTITUDE roll={msg.roll:.2f}, pitch={msg.pitch:.2f}, yaw={msg.yaw:.2f}")
        elif m == 'GLOBAL_POSITION_INT':
            self.telemetry['lat'] = msg.lat / 1e7
            self.telemetry['lon'] = msg.lon / 1e7
            self.telemetry['alt'] = msg.relative_alt / 1000.0
            self.telemetry['heading'] = msg.hdg / 100.0 if msg.hdg != 65535 else 0
            
            print(f"[TELEM] POS   lat={self.telemetry['lat']:.6f}, lon={self.telemetry['lon']:.6f}, rel-alt={self.telemetry['alt']:.2f}m, headin={self.telemetry['heading']}")
        elif m == 'BATTERY_STATUS':
            self.telemetry['battery_voltage'] = msg.voltages[0] / 1000.0 if msg.voltages[0] > 0 else None
            self.telemetry['battery_current'] = msg.current_battery / 100.0 if msg.current_battery > -1 else None
            self.telemetry['battery_remaining'] = msg.battery_remaining if msg.battery_remaining > -1 else None
            print(f"[TELEM] BATT  volt={self.telemetry['battery_voltage']}V, curr={self.telemetry['battery_current']}A, left={self.telemetry['battery_remaining']}%")
        elif m == 'GPS_RAW_INT':
            self.telemetry['gps_fix_type'] = msg.fix_type
            self.telemetry['gps_satellites_visible'] = msg.satellites_visible
            print(f"[TELEM] GPS   fix={msg.fix_type}, sats={msg.satellites_visible}")
        elif m == 'MISSION_CURRENT':
            self.telemetry['current_mission_point'] = msg.seq
            print(f'Current mission point {self.telemetry["current_mission_point"]}')

    def listen_for_telemetry(self):
        try:
            while True:
                msg = self.master.recv_match(blocking=True, timeout=1)
                if not msg:
                    continue
                self.update_telemetry(msg)
        except Exception as e:
            print("MAVLink listener error:", e)

    # def mavlink_listener(self):
    #         try:
    #             while True:
    #                 msg = self.mav.recv_match(blocking=True, timeout=1)
    #                 if not msg:
    #                     continue

    #                 if msg.get_type() == 'HEARTBEAT':
    #                     self.telemetry['mode'] = mavutil.mode_string_v10(msg)

    #                 elif msg.get_type() == 'GLOBAL_POSITION_INT':
    #                     self.telemetry['lat'] = msg.lat / 1e7
    #                     self.telemetry['lon'] = msg.lon / 1e7
    #                     self.telemetry['alt'] = msg.relative_alt / 1000.0
    #                     self.telemetry['heading'] = msg.hdg / 100.0 if msg.hdg != 65535 else 0

    #                 elif msg.get_type() == 'MISSION_CURRENT':
    #                     self.telemetry['wp_seq'] = msg.seq

    #                 elif msg.get_type() == 'MISSION_COUNT':
    #                     self.telemetry['wp_total'] = msg.count

    #         except Exception as e:
    #             print("MAVLink listener error:", e)
