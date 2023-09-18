from logging import Logger, getLogger
from PIL import Image, ImageDraw, ImageFont
from os.path import dirname, abspath, join

from subprocess import check_output
from threading import Thread
from time import sleep

def get_battery(debug:bool):
    if debug: return 96
    raw = check_output("echo 'get battery' | nc -q 0 127.0.0.1 8423", shell=True).decode("utf-8").strip()
    return  int(float(raw.split(" ")[-1]))

class display:
    def __splash(self):
        image = Image.open(join(dirname(abspath(__file__)), "splash.png"))
        if not self.debug_flag: self.lcd.ShowImage(image)
        else: image.save("debug.display.png")

    def __init__(self, debug:bool=False) -> None:
        self.debug:Logger = getLogger("display")
        self.debug_flag:bool = debug
        if self.debug_flag: self.debug.info("debug mode enabled.")

        self.width, self.height = 240, 280
        self.background_color = (255, 255, 255)
        self.font_path:str = join(dirname(abspath(__file__)), "sometype-mono-bold.ttf")
        self.font = ImageFont.truetype(self.font_path, 16)
        self.font_sm = ImageFont.truetype(self.font_path, 14)
        self.text_color = "white"

        self.state:str = ""
        self.status:str = "LOADING"
        self.lat:float = 0.0
        self.lon:float = 0.0
        self.alt:float = 0.0
        self.climb:float = 0.0
        self.speed:float = 0.0
        self.mode:int = 0

        self.waypoint = False
        self.waypoint_lat:float = 0.0
        self.waypoint_lon:float = 0.0

        self.satellites_available:int = 0
        self.satellites_used:int = 0

        if not self.debug_flag:
            from display.lcd import LCD

            self.lcd:LCD = LCD()
            self.lcd.Init()
            self.__splash()
            self.debug.info("lcd display setup.")
        
        self.active:bool = False
        self.thread:Thread = Thread(target=self.__render)
        self.debug.info("display thread created.")

    def __state(self):
        return "{}{:0.6f}{:0.6f}{}{}{}{}{}{}".format(
            self.status, self.lat, self.lon,
            self.alt, self.climb, self.speed,
            self.satellites_available, self.satellites_used,
            self.mode
        )

    def __display(self):
        image = Image.new("RGB", (self.width, self.height), self.background_color)
        draw = ImageDraw.Draw(image)

        draw.rectangle([(0, 0), (240, 280)], fill="black")

        draw.text((20, 20), "SATELLITES", fill=self.text_color, font=self.font)
        draw.text((220, 20), f"{['UKN', 'NOFIX', '2D', '3D'][self.mode]}", fill=self.text_color, font=self.font, anchor="ra")

        draw.line([(20, 43), (220, 43)], fill=self.text_color)

        draw.text((20, 50), "AVAILABLE", fill=self.text_color, font=self.font_sm)
        draw.text((220, 50), f"{self.satellites_available}", fill=self.text_color, font=self.font_sm, anchor="ra")

        draw.text((20, 65), "USED", fill=self.text_color, font=self.font_sm)
        draw.text((220, 65), f"{self.satellites_used}", fill=self.text_color, font=self.font_sm, anchor="ra")

        draw.line([(20, 86), (220, 86)], fill=self.text_color)

        draw.text((20, 95), "LAT", fill=self.text_color, font=self.font_sm)
        draw.text((220, 95), f"{self.lat:0.6f}", fill=self.text_color, font=self.font_sm, anchor="ra")

        draw.text((20, 110), "LON", fill=self.text_color, font=self.font_sm)
        draw.text((220, 110), f"{self.lon:0.6f}", fill=self.text_color, font=self.font_sm, anchor="ra")

        draw.line([(20, 132), (220, 132)], fill=self.text_color)

        draw.text((20, 140), "ALT", fill=self.text_color, font=self.font_sm)
        draw.text((220, 140), f"{int(self.alt)}", fill=self.text_color, font=self.font_sm, anchor="ra")

        draw.text((20, 155), "CLIMB", fill=self.text_color, font=self.font_sm)
        draw.text((220, 155), f"{int(self.climb)}", fill=self.text_color, font=self.font_sm, anchor="ra")

        draw.text((20, 170), "SPD", fill=self.text_color, font=self.font_sm)
        draw.text((220, 170), f"{int(self.speed)}", fill=self.text_color, font=self.font_sm, anchor="ra")

        draw.line([(20, 192), (220, 192)], fill=self.text_color)

        draw.text((20, 200), "WAYPOINT", fill=self.text_color, font=self.font_sm)
        draw.text((220, 200), f"{self.waypoint_lat:0.6f}", fill=self.text_color, font=self.font_sm, anchor="ra")
        draw.text((220, 215), f"{self.waypoint_lon:0.6f}", fill=self.text_color, font=self.font_sm, anchor="ra")

        draw.line([(20, 238), (220, 238)], fill=self.text_color)

        draw.text((20, 246), f"{self.status}", fill=self.text_color, font=self.font, anchor="la")

        battery_level = get_battery(self.debug_flag)
        draw.text((220, 246), f"{battery_level}%", fill=(
            "#FF5151" if battery_level < 30 else
            "#FFE351" if battery_level < 60 else
            "white"
        ), font=self.font, anchor="ra")
        
        if not self.debug_flag:
            self.lcd.ShowImage(image)
        else:
            image.save("debug.display.png")

    def __render(self):
        passive = 0
        while self.active:
            state = self.__state()
            self.debug.debug((self.state, state))
            if state != self.state or passive > 60:
                self.state = state
                self.debug.info("updating display.")
                self.debug.debug((self.state, state))
                self.__display()
                passive = 0
            else: passive += 1; 
            if not self.waypoint: sleep(.5)

    def close(self):
        self.active = False
        if not self.debug_flag:
            self.thread.join()
            self.__splash()
            self.lcd.reset()
            self.lcd.module_exit()
        self.debug.info("display closed.")
    
    def run(self):
        self.active = True
        self.thread.start()
        self.debug.info("display thread started.")

if __name__ == "__main__":
    d = display(debug=True)
    d.run()
    d.close()
