import selenium
from selenium import webdriver
import time
import subprocess
import math
import os
import random
import tempfile
from pyvirtualdisplay import Display

from selenium.webdriver.chrome.options import Options


from selenium.webdriver.common.keys import Keys


class Shot(object):
    def __init__(self, height, width, url, clip_prefix="media/tmp_clip", clip_number=0):
        self.offset = 80
        self.height = height
        self.width = width
        self.clip_prefix = clip_prefix

        self.display = Display(visible=1, size=(width, height + self.offset))
        self.display.start()
        self.display_id = self.display.cmd[-1]

        chrome_options = Options()
        chrome_options.add_argument("--disable-infobars")

        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.set_window_size(width, height + self.offset)
        self.driver.get(url)

        self.clip_number = clip_number

        self.grab_process = None
        a, _ = os.path.split(clip_prefix)
        if not os.path.isdir(a):
            os.makedirs(a)

    def shutdown(self):
        print("shutdown")
        self.driver.close()
        self.display.stop()

    def start_record(self):
        dst = f"{self.clip_prefix}_{str(self.clip_number).zfill(2)}.mp4"

        ffmpegcmd = (
            f"ffmpeg -loglevel panic  -hide_banner -y -f x11grab -r 60 -s {self.width}x{self.height+self.offset}"
            f" -i {self.display_id} -an -vcodec libx264"
            f" -vf crop={self.width}:{self.height}:0:{self.offset} {dst}"
        )
        print("start record command:", ffmpegcmd)
        self.grab_process = subprocess.Popen(ffmpegcmd.split())
        return dst

    def stop_record(self):
        print("stop record")

        self.grab_process.terminate()

        pass

    def get_view_height(self):
        return int(self.driver.execute_script("return window.innerHeight"))

    def pan(self, top, bottom, step_size):
        print(f"pan: {top} -> {bottom} ({step_size}) ")
        self.driver.execute_script(f"window.scrollTo(0,{top});")

        for h in range(top, bottom, step_size):
            self.driver.execute_script(f"window.scrollTo({{'top': {h}}});")

    def pan_element(self, selector, step_size=1):
        el = self.driver.find_element_by_css_selector(selector)

        top = el.location["y"]
        bottom = int(el.location["y"] + el.size["height"] - self.get_view_height())
        self.pan(top, bottom, step_size)

    def pan_between(self, selector_from, selector_to, step_size):
        el_top = self.driver.find_element_by_css_selector(selector_from)
        el_bottom = self.driver.find_element_by_css_selector(selector_to)

        top = el_top.location["y"]
        bottom = int(
            el_bottom.location["y"] + el_bottom.size["height"] - self.get_view_height()
        )
        self.pan(top, bottom, step_size)

    def linger(self, selector, duration, align=None, offset=None, smooth=None):
        el = self.driver.find_element_by_css_selector(selector)
        if align is None:
            align = "middle"

        if offset is None:
            offset = 0

        if align == "middle":
            offset -= self.get_view_height() / 2 - el.size["height"] / 2

        if align == "bottom":
            offset -= self.get_view_height()

        if align == "top":
            offset = offset

        if smooth is None:
            smooth = False

        offset += el.location["y"]

        if smooth:
            self.driver.execute_script(
                f"window.scrollTo({{'top': {offset}, 'behavior': 'smooth'}});"
            )

        else:
            self.driver.execute_script(f"window.scrollTo(0,{offset});")

        time.sleep(duration)


class Film(object):
    def __init__(self, script, outfile):
        self.outfile = outfile
        self.script = script

    def start(self):
        clips = []
        for clip_number, script_shot in enumerate(self.script["shots"]):
            shot = Shot(
                self.script["width"],
                self.script["width"],
                script_shot["url"],
                clip_number=clip_number,
            )
            clips.append(shot.start_record())
            for action in script_shot["actions"]:
                fn = getattr(shot, action["type"])
                fn(**action["params"])
            shot.stop_record()
            shot.shutdown()
        with open("temp_concat.txt", "w") as f:
            f.write("\n".join([f"file '{x}'" for x in clips]))
        time.sleep(1)
        subprocess.check_call(
            f"ffmpeg -y -f concat -i temp_concat.txt -c copy {self.outfile}".split()
        )
