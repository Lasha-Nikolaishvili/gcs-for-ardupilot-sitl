from pymavlink import mavutil


def mavlink_listener(self):
        try:
            mav = mavutil.mavlink_connection('udp:127.0.0.1:14550')
            mav.wait_heartbeat()
            print("Connected to MAVLink")

            while True:
                msg = mav.recv_match(blocking=True, timeout=1)
                if not msg:
                    continue

                self.telemetry_lock.lock()

                if msg.get_type() == 'HEARTBEAT':
                    self.telemetry['mode'] = mavutil.mode_string_v10(msg)

                elif msg.get_type() == 'GLOBAL_POSITION_INT':
                    self.telemetry['lat'] = msg.lat / 1e7
                    self.telemetry['lon'] = msg.lon / 1e7
                    self.telemetry['alt'] = msg.relative_alt / 1000.0
                    self.telemetry['heading'] = msg.hdg / 100.0 if msg.hdg != 65535 else 0

                elif msg.get_type() == 'MISSION_CURRENT':
                    self.telemetry['wp_seq'] = msg.seq

                elif msg.get_type() == 'MISSION_COUNT':
                    self.telemetry['wp_total'] = msg.count

                self.telemetry_lock.unlock()

        except Exception as e:
            print("MAVLink listener error:", e)


