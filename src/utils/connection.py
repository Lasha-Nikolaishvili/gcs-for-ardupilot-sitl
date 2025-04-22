import threading, queue, time
from pymavlink import mavutil

class Connection:
    def __init__(self, connection_str='udp:127.0.0.1:14550'):
        # open the connection
        self.master = mavutil.mavlink_connection(connection_str)
        # wait for heartbeat
        self.master.wait_heartbeat()
        self.telemetry = {}

        # this is where all incoming messages land:
        self._msg_queue = queue.Queue()

        # start the single reader thread
        t = threading.Thread(target=self._message_loop, daemon=True)
        t.start()
        self.set_param("AUTO_OPTIONS", 3)
        print(f"Connected: system={self.master.target_system}, component={self.master.target_component}")
    
    def set_param(self, param_id, value,
                  param_type=mavutil.mavlink.MAV_PARAM_TYPE_UINT16,
                  timeout=5):
        """
        Set a vehicle parameter and wait for it to echo back.
        Handles msg.param_id as either bytes or str.
        Returns the new param_value.
        """
        # send the PARAM_SET
        self.master.mav.param_set_send(
            self.master.target_system,
            self.master.target_component,
            param_id.encode('ascii'),
            float(value),
            param_type
        )
        # wait for the PARAM_VALUE ack
        deadline = time.time() + timeout
        while True:
            if time.time() > deadline:
                raise TimeoutError(f"Timed out waiting for {param_id}")
            msg = self._wait_for('PARAM_VALUE', timeout=timeout)
            # unify the incoming param_id
            raw = msg.param_id
            if isinstance(raw, (bytes, bytearray)):
                name = raw.decode('ascii').rstrip('\x00')
            else:
                name = raw.rstrip('\x00')
            if name == param_id:
                print(f"✓ {name} set to {msg.param_value}")
                return msg.param_value

    def get_param(self, param_id, timeout=5):
        """
        Request a vehicle parameter and return the PARAM_VALUE message.
        """
        self.master.mav.param_request_read_send(
            self.master.target_system,
            self.master.target_component,
            param_id.encode('ascii'),
            -1
        )
        deadline = time.time() + timeout
        while True:
            if time.time() > deadline:
                raise TimeoutError(f"Timed out waiting for {param_id}")
            msg = self._wait_for('PARAM_VALUE', timeout=timeout)
            raw = msg.param_id
            if isinstance(raw, (bytes, bytearray)):
                name = raw.decode('ascii').rstrip('\x00')
            else:
                name = raw.rstrip('\x00')
            if name == param_id:
                return msg

    def _message_loop(self):
        """ Continuously read from the MAVLink socket and enqueue messages. """
        while True:
            msg = self.master.recv_match(blocking=True)
            if not msg:
                continue
            # immediately update telemetry
            self.update_telemetry(msg)
            # then hand it off to anyone waiting
            self._msg_queue.put(msg)

    def _wait_for(self, expected_type, condition=lambda m: True, timeout=None):
        """
        Pull messages off the shared queue until you get the one you want.
        Everything else has already updated telemetry in the reader.
        """
        while True:
            try:
                msg = self._msg_queue.get(timeout=timeout)
            except queue.Empty:
                raise TimeoutError(f"Timed out waiting for {expected_type}")
            if msg.get_type() == expected_type and condition(msg):
                return msg
            # otherwise just drop it (telemetry is already updated)

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
        # 1) Takeoff as seq=0
        items = []
        for i, wp in enumerate(waypoints):
            cmd = mavutil.mavlink.MAV_CMD_NAV_WAYPOINT
            if i == 0:
                cmd = mavutil.mavlink.MAV_CMD_NAV_TAKEOFF
            elif i == len(waypoints) - 1:
                cmd = mavutil.mavlink.MAV_CMD_NAV_LAND

            items.append({
                'seq': i,
                'frame': mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
                'command': cmd,
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
            armed = bool(msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED)
            self.telemetry['armed'] = armed
            # print(f"[TELEM] HEARTBEAT mode={msg.base_mode}, autopilot={msg.autopilot}")
        elif m == 'ATTITUDE':
            self.telemetry['roll'] = msg.roll
            self.telemetry['pitch'] = msg.pitch
            self.telemetry['yaw'] = msg.yaw
            # print(f"[TELEM] ATTITUDE roll={msg.roll:.2f}, pitch={msg.pitch:.2f}, yaw={msg.yaw:.2f}")
        elif m == 'GLOBAL_POSITION_INT':
            self.telemetry['lat'] = msg.lat / 1e7
            self.telemetry['lon'] = msg.lon / 1e7
            self.telemetry['alt'] = msg.relative_alt / 1000.0
            self.telemetry['heading'] = msg.hdg / 100.0 if msg.hdg != 65535 else 0
            
            # print(f"[TELEM] POS   lat={self.telemetry['lat']:.6f}, lon={self.telemetry['lon']:.6f}, rel-alt={self.telemetry['alt']:.2f}m, headin={self.telemetry['heading']}")
        elif m == 'BATTERY_STATUS':
            self.telemetry['battery_voltage'] = msg.voltages[0] / 1000.0 if msg.voltages[0] > 0 else None
            self.telemetry['battery_current'] = msg.current_battery / 100.0 if msg.current_battery > -1 else None
            self.telemetry['battery_remaining'] = msg.battery_remaining if msg.battery_remaining > -1 else None
            # print(f"[TELEM] BATT  volt={self.telemetry['battery_voltage']}V, curr={self.telemetry['battery_current']}A, left={self.telemetry['battery_remaining']}%")
        elif m == 'GPS_RAW_INT':
            self.telemetry['gps_fix_type'] = msg.fix_type
            self.telemetry['gps_satellites_visible'] = msg.satellites_visible
            # print(f"[TELEM] GPS   fix={msg.fix_type}, sats={msg.satellites_visible}")
        elif m == 'MISSION_CURRENT':
            self.telemetry['current_mission_point'] = msg.seq
            # print(f'Current mission point {self.telemetry["current_mission_point"]}')

    # def listen_for_telemetry(self):
    #     try:
    #         while True:
    #             msg = self.master.recv_match(blocking=True, timeout=1)
    #             if not msg:
    #                 continue
    #             self.update_telemetry(msg)
    #     except Exception as e:
    #         print("MAVLink listener error:", e)

    def arm(self):
        """
        Arm the vehicle (param1=1) and wait for motors to confirm armed.
        """
        # send arm command
        self.master.mav.command_long_send(
            self.master.target_system,
            self.master.target_component,
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            0,
            1,  # param1=1 → arm
            0, 0, 0, 0, 0, 0
        )
        # block until we see the vehicle report armed
        print("Arming…")
        self.master.motors_armed_wait()
        print("✓ Armed!")  # :contentReference[oaicite:0]{index=0}

    def disarm(self):
        """
        Disarm the vehicle (param1=0) and wait for motors to confirm disarmed.
        """
        self.master.mav.command_long_send(
            self.master.target_system,
            self.master.target_component,
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            0,
            0,  # param1=0 → disarm
            0, 0, 0, 0, 0, 0
        )
        print("Disarming…")
        self.master.motors_disarmed_wait()
        print("✓ Disarmed!")  # :contentReference[oaicite:1]{index=1}

    def set_mode(self, mode):
        """
        Change flight mode. Pass a string (e.g. "AUTO", "GUIDED", "STABILIZE")
        or an integer mode ID.
        """
        # resolve string → mode ID
        if isinstance(mode, str):
            mode_map = self.master.mode_mapping()
            if mode not in mode_map:
                raise ValueError(f"Unknown mode '{mode}'. Available modes: {list(mode_map.keys())}")
            mode_id = mode_map[mode]
        else:
            mode_id = int(mode)

        print(f"Setting mode → {mode} ({mode_id})…")
        # send the SET_MODE message
        self.master.mav.set_mode_send(
            self.master.target_system,
            mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
            mode_id
        )

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
