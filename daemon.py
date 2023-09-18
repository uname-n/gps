from logging import FileHandler, Logger, basicConfig, getLogger, DEBUG, INFO
basicConfig(format="(%(levelname)s) [%(name)s] %(message)s", level=INFO)

from multiprocessing.connection import Listener

from multiprocessing.connection import Listener
from threading import Thread
from os import system, makedirs, path
from datetime import datetime

from display import display

import gps, json

def system_err(cmd:str, pass_failed:bool=True):
    if system(cmd) != 0:
        if pass_failed: return
        else: raise Exception(cmd)

class daemon:
    def __init__(self, parent_dir:str, debug:bool=False) -> None:
        self.debug:Logger = getLogger("display")
        self.debug_flag:bool = debug
        self.debug.addHandler(FileHandler("daemon.log"))
        self.debug.setLevel(DEBUG if self.debug_flag else INFO)

        self.parent_dir = parent_dir

        self.listener = Listener(('localhost', 6420))
        self.session = None

        self.active = True
        self.gps_active = False
        self.gps_thread = None
        self.gps_set_waypoint = False
        self.gps_waypoint_n = 0
        self.gps_active_id = ""

        self.display = display()

    def ping(self):
        return "pong."

    def toggle_debug(self):
        self.debug_flag = ~self.debug_flag
        if self.debug_flag: 
            self.debug.setLevel(DEBUG)
            return "debug mode enabled."
        else: 
            self.debug.setLevel(INFO)
            return "debug mode disabled."

    # = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =

    def disk_local_mount(self):
        if self.gps_active: return "gps session is active."
        system_err(f"sudo mkdir {self.parent_dir}")
        system_err(f"sudo mount -o loop,rw /boot/usb-drive.img {self.parent_dir}")
        self.debug.info("disk local mounted.")
        return "disk local mounted."

    def disk_local_eject(self):
        if self.gps_active: return "gps session is active."
        system_err(f"sudo umount {self.parent_dir}")
        system_err(f"sudo rm -rf {self.parent_dir}")
        self.debug.info("disk local ejected.")
        return "disk local ejected."

    def disk_mount(self, ro:int=0):
        if self.gps_active: return "gps session is active."
        system_err(f"sudo modprobe g_mass_storage file=/boot/usb-drive.img stall=0 ro={ro}")
        self.debug.info("disk mounted.")
        return "disk mounted."

    def disk_eject(self):
        if self.gps_active: return "gps session is active."
        system_err("sudo modprobe -r g_mass_storage")
        self.debug.info("disk ejected.")
        return "disk ejected."

    def disk_clean(self):
        if self.gps_active: return "gps session is active."
        self.disk_eject()
        self.disk_local_eject()
        self.disk_local_mount()
        system_err(f"sudo rm -rf {self.parent_dir}/*")
        self.disk_local_eject()
        self.debug.info("disk cleaned.")
        return "disk cleaned."

    # = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =

    def __run_gpsd(self):
        system_err("sudo killall gpsd")
        system_err("sudo systemctl stop gpsd.socket")
        system_err("sudo systemctl disable gpsd.socket")
        system_err("sudo gpsd /dev/serial0 -F /var/run/gpsd.sock")
        self.debug.info("gpsd service running.")

    def __create_gpsd_session(self):
        try: self.session = gps.gps(mode=gps.WATCH_ENABLE, reconnect=True)
        except Exception as e: self.debug.error(e)
        self.debug.info("gpsd session created.")

    def __report(self):
        while self.gps_active:
            try:
                report = self.session.next()
                report_data = json.dumps(report, default=lambda o: o.__dict__)
                self.debug.debug(report)
                if report.get("class") == "TPV":

                    self.display.lat = report.get("lat", 0.0)
                    self.display.lon = report.get("lon", 0.0)
                    self.display.alt = report.get("altHAE", 0.0)
                    self.display.climb = report.get("climb", 0.0)
                    self.display.speed = report.get("speed", 0.0)
                    self.display.mode = report.get("mode", 0)

                    with open(path.join(self.parent_dir, self.gps_active_id, "gps"), "a+") as f:
                        f.write(report_data + "\n")
                    if self.gps_set_waypoint:
                        with open(path.join(self.parent_dir, self.gps_active_id, f"waypoint.{self.gps_waypoint_n + 1}"), "w") as f:
                            f.write(report_data)
                        self.display.waypoint_lat = self.display.lat
                        self.display.waypoint_lon = self.display.lon
                        self.gps_set_waypoint = False
                        self.display.waypoint = False
                        self.gps_waypoint_n += 1

                if report.get("class") == "SKY":
                    self.display.satellites_available = report.get("nSat", 0)
                    self.display.satellites_used = report.get("uSat", 0)

            except Exception as e: self.debug.error(e); self.done(); break

    def report(self) -> str:
        if self.gps_active: return "gps session already active."
        self.gps_active = True
        self.gps_active_id = datetime.now().strftime("%Y%m%d%H%M%S")

        self.display.status = "ACTIVE"

        self.disk_eject()
        self.disk_local_eject()
        self.disk_local_mount()

        makedirs(path.join(self.parent_dir, self.gps_active_id), exist_ok=True)

        self.gps_thread = Thread(target=self.__report)
        self.gps_thread.start()

        self.debug.info("gps session started.")
        return "gps session started."

    def waypoint(self):
        if not self.gps_active: return "gps session is not active."
        self.gps_set_waypoint = True
        self.display.waypoint = True
        self.debug.info("waypoint request received.")
        return "waypoint request received."

    def done(self) -> str:
        self.gps_active = False
        self.display.status = "READY"
        if self.gps_thread:
            self.gps_thread.join()
            self.gps_thread = None
            self.debug.info("gps session closed.")
            return "gps session closed."
        return "gps session is not active."

    def shutdown(self):
        self.active = False
        self.display.close()
        self.done()
        self.listener.close()
        self.debug.info("daemon shutdown.")
        return "daemon shutdown."

    def run(self):
        self.debug.info("starting connection.")

        self.__run_gpsd()
        self.__create_gpsd_session()

        self.display.status = "READY"
        self.display.run()

        self.debug.info("starting listener loop.")

        while self.active:
            self.conn = self.listener.accept()
            try:
                msg = self.conn.recv(); self.debug.debug("[msg]: " + msg)
                cmd = msg.split(" ")
                res = self.__getattribute__("_".join(cmd))(); self.debug.debug("[res]: " + res)
                self.conn.send(res)
            except EOFError: continue
            except Exception as e: self.debug.error(e)
            finally: self.conn.close()

if __name__ == "__main__":
    service = daemon("/mnt/usb_drive")

    try: service.run()
    except KeyboardInterrupt: service.shutdown()
    except Exception as e: raise e