#!/usr/bin/env python3

import sys, os, random, time, signal
import numpy as np
import RPi.GPIO as GPIO
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageOps, ImagePalette
from inky.inky_uc8159 import Inky


class Inkybot:

    # FIXME: a bunch of this needs to be parameterized

    palette = [
        (0, 0, 0),        # black
        (255, 255, 255),  # white
        (0, 255, 0),      # green
        (0, 0, 255),      # blue
        (255, 0, 0),      # red
        (255, 255, 0),    # yellow
        (255, 140, 0),    # orange
        (255, 255, 255)   # white again???
    ]

    font_size = 60

    BUTTONS        = [5,6,16,24]
    BUTTON_LABELS  = ['A', 'B', 'C', 'D']

    inky   = Inky()
    state  = None
    states = {}

    def __init__(self):
        self.font = ImageFont.truetype("fonts/3270NerdFontMono-Regular.ttf", size=self.font_size)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.BUTTONS, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        for pin in self.BUTTONS:
            GPIO.add_event_detect(pin, GPIO.FALLING, self.handle_button, bouncetime=250)

    def color_similarity(self, color1, color2):
        return np.sqrt(np.sum((np.array(color1) - np.array(color2)) ** 2))

    def least_similar_color(self, color):
        return max(self.palette, key=lambda ref_color: self.color_similarity(ref_color, color))

    def average_outer_perimeter_color(self,image):
        # Get image dimensions
        width, height = image.size

        # Extract the outer 1-pixel perimeter
        outer_perimeter_pixels = []
        for x in range(width):
            outer_perimeter_pixels.append(image.getpixel((x, 0)))                   # Top row
            outer_perimeter_pixels.append(image.getpixel((x, height - 1)))          # Bottom row
        for y in range(1, height - 1):
            outer_perimeter_pixels.append(image.getpixel((0, y)))                   # Left column
            outer_perimeter_pixels.append(image.getpixel((width - 1, y)))           # Right column

        # Calculate average color
        total_pixels = len(outer_perimeter_pixels)
        total_red    = sum(pixel[0] for pixel in outer_perimeter_pixels)
        total_green  = sum(pixel[1] for pixel in outer_perimeter_pixels)
        total_blue   = sum(pixel[2] for pixel in outer_perimeter_pixels)

        average_red   = total_red // total_pixels
        average_green = total_green // total_pixels
        average_blue  = total_blue // total_pixels

        return (average_red, average_green, average_blue)

    def resize_with_letterbox(self, image, resolution, letterbox_color=(0, 0, 0)):
        target_width  = resolution[0]
        target_height = resolution[1]

        # Get original width and height
        original_width, original_height = image.size

        # Calculate the aspect ratios
        original_aspect_ratio = original_width / original_height
        target_aspect_ratio   = target_width   / target_height

        # Calculate resizing factors
        if original_aspect_ratio < target_aspect_ratio:
            # Image is narrower than target, resize based on height
            new_width  = int(target_height * original_aspect_ratio)
            new_height = target_height
        else:
            # Image is taller than target, resize based on width
            new_width  = target_width
            new_height = int(target_width / original_aspect_ratio)

        # Resize the image
        resized_image = image.resize((new_width, new_height), Image.ANTIALIAS)

        # Create a new image with letterbox bars
        x_max = target_width - new_width
        if x_max // 2 > self.font_size:
            x = x_max // 2
        else:
            x = min(x_max, x_max // 2 + self.font_size)
        letterbox_image = Image.new(image.mode, (target_width, target_height), letterbox_color)
        letterbox_image.paste(resized_image, (x, (target_height - new_height) // 2))

        return letterbox_image


    def handle_button(self,pin):
        label = self.BUTTON_LABELS[self.BUTTONS.index(pin)]

        if label == 'A':
            self.state.button_a()
        elif label == 'B':
            self.state.button_b()
        elif label == 'C':
            self.state.button_c()
        elif label == 'D':
            self.state.button_d()
        else:
            raise Exception("Unhandled button press!")

    class StateClass:
        button_text =   [  "?",  "?",  "?",  "?" ]
        button_colors = [ None, None, None, None ]
        button_positions = [
            (5,49),
            (5,161),
            (5,273),
            (5,385)
        ]
        font_size  = 60
        saturation = 0.7

        def __init__(self, parent):
            self.parent = parent

        # enter and exit functions can be overridden by the child class
        def enter(self):
            pass
        def exit(self):
            pass

        def change_state(self, state):
            self.parent.change_state(state)

        # button_x functions should be overridden by the child class too
        def button_a(self):
            print("Button A")
        def button_b(self):
            print("Button B")
        def button_c(self):
            print("Button C")
        def button_d(self):
            print("Button D")

        # same applies to the loop
        def loop(self):
            pass

        def set_image(self, image):
            draw = ImageDraw.Draw(image)

            # text colors use the nearest undithered color to what's in the letterbox
            color_border = self.parent.least_similar_color(self.parent.average_outer_perimeter_color(image))
            color        = self.parent.least_similar_color(color_border)

            for i in range(4):
                if self.button_colors[i] is not None:
                    c   = self.button_colors[i]
                    cb  = self.parent.least_similar_color(c)
                else:
                    c   = color
                    cb  = color_border
                txt = self.button_text[i]
                x,y = self.button_positions[i]
                text_width, text_height = draw.textsize(txt, font=self.parent.font)
                dy = int(text_height / 2)

                for xx in range(x - 1, x + 2, 1):
                    for yy in range(y - 1 - dy, y + 2 - dy, 1):
                        draw.text((xx,yy), txt, fill=cb, font=self.parent.font)

                draw.text((x,y - dy), txt, fill=c, font=self.parent.font)

            self.parent.inky.set_image(image, saturation=self.saturation)
            self.parent.inky.show()

        def clear(self, color="white"):
            w,h = self.parent.inky.resolution

            clear_image = Image.new('RGB', (w, h), color)
            self.parent.inky.set_image(clear_image, saturation=1.0)
            self.parent.inky.show()

    def State(self, name):
        def decorator(c):
            self.states[name] = c(parent = self)
            return c
        return decorator

    def change_state(self, state):
        print(f"Changing state to: {state}")
        if self.state:
            self.state.exit()
        self.state = self.states[state]
        self.state.enter()

    def start(self, state):
        self.state = self.states[state]
        self.state.enter()

        while True:
            self.state.loop()
            time.sleep(0.1)



inkybot = Inkybot()

@inkybot.State('picture')
class PictureMode(inkybot.StateClass):
    button_text = [
        "󰸋",
        "",
        "",
        "󱧾"
    ]
    font_size  = 60
    picpath    = '/srv/inkybot/pictures'
    saturation = 0.7
    pic_time   = 60.0

    def enter(self):
        self.imagelist   = []
        self.next_img    = True
        self.time_target = 0.0

    def button_b(self):
        self.change_state('hass')

    def button_d(self):
        print("changing image...")
        self.next_img    = True
        self.time_target = time.time() + self.pic_time

    def loop(self):

        if self.time_target <= time.time():
            self.next_img = True

        if self.next_img:
            self.next_img = False
            self.time_target = time.time() + self.pic_time

            if len(self.imagelist) == 0:
                self.imagelist = os.listdir(self.picpath)
                random.shuffle(self.imagelist)

            fn = self.imagelist.pop()
            print(f"Displaying {fn}")

            image = Image.open(f"{self.picpath}/{fn}") # XXX FIXME: os join function instead

            resizedimage = self.parent.resize_with_letterbox(
                    image,
                    self.parent.inky.resolution,
                    self.parent.average_outer_perimeter_color(image)
            )

            self.set_image(resizedimage)



from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException as selenium_TimeoutException
from io import BytesIO

@inkybot.State('hass')
class HassMode(inkybot.StateClass):
    button_text = [
        " ",
        "",
        " ",
        ""
    ]

    button_colors = [
        None,
        (0,0,255),
        None,
        (0,255,0)
    ]

    driver_path = "/usr/bin/chromedriver"
    driver=None
    refresh_target = 0.0
    screen_scale = 1.0

    def button_b(self):
        self.change_state('picture')

    def button_d(self):
        self.driver.refresh()
        self.update()
        self.refresh_target = time.time() + 5

    def enter(self):
        #self.clear("blue")
        url = "http://localhost:8123/lovelace/1?kiosk"
        print(f"launching selenium and loading {url}")

        service = Service(self.driver_path)
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')  # GPU hardware acceleration isn't needed for headless
        options.add_argument('--no-sandbox')  # Disable the sandbox for all software features
        options.add_argument('--disable-dev-shm-usage')  # Overcome limited resource problems
        options.add_argument('--disable-extensions')  # Disabling extensions can save resources
        options.add_argument('--disable-plugins')  # Disable plugins
        self.driver = webdriver.Chrome(service=service, options=options)
        
        width,height = [self.screen_scale * x for x in self.parent.inky.resolution]
        #width -= self.font_size
        self.driver.set_window_size(width,height)

        self.driver.get(url)
        print("waiting for login button...")
        login_button = WebDriverWait(self.driver, 5).until(EC.visibility_of_element_located((By.CSS_SELECTOR, "mwc-button")))
        #self.driver.execute_script("document.body.style.fontSize = 'larger';") # font scaling
        login_button.click()

        self.update()
        self.refresh_target = time.time() + 5

    def update(self):
        if self.driver is not None:
            print("Updating display...")
            screenshot_bytes = self.driver.get_screenshot_as_png()
            screenshot_image = Image.open(BytesIO(screenshot_bytes)).convert('RGB')
            width, height = screenshot_image.size
            cropped_image = screenshot_image.crop((5,5, width - 5, height - 5))

            resizedimage = self.parent.resize_with_letterbox(
                    cropped_image,
                    self.parent.inky.resolution,
                    self.parent.average_outer_perimeter_color(screenshot_image)
            )

            #enhancer = ImageEnhance.Contrast(resizedimage)
            enhancer = ImageEnhance.Color(resizedimage)
            adjustedimage = enhancer.enhance(4.0)
            enhancer = ImageEnhance.Contrast(adjustedimage)
            adjustedimage = enhancer.enhance(5.0)
            #print(resizedimage.mode)
            #adjustedimage = ImageOps.autocontrast(resizedimage)

            self.set_image(adjustedimage)

            self.driver.refresh() # reloading the page at every refresh will get us any UI updates in the background
            self.refresh_target = time.time() + 60

    def exit(self):
        print("Quitting chrome driver...")
        d = self.driver
        self.driver = None
        d.close()
        d.quit()

    def loop(self):
        if self.driver is not None:

            try:
                refresh_button = WebDriverWait(self.driver, 0.5).until(
                        EC.visibility_of_element_located((By.XPATH, '//*[text()="Refresh"]'))
                )
                refresh_button.click()
                self.refresh_target = time.time() + 2.5
            except selenium_TimeoutException:

                if self.refresh_target <= time.time():
                    self.update()


if __name__ == "__main__":
    inkybot.start('picture')
    #inkybot.start('hass')


