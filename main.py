#external libraries
import pandas as pd
import pygame

#standard libraries
import tkinter
from tkinter import filedialog
import platform
import time
import random
import math
import sys
import os

# TODO reverse_translation slider
# TODO gaussian button

# parameters for dev
    #gui
window_scale = 200
button_scale = 2.5 #divides through button scale
width_ratio = 6
height_ratio = 3
font_word_ratio = 0.4
font_input_ratio = 0.3
button_font_ration = 0.4
border_radius_ratio = 0.06
gaussian_font_ratio = 0.1
axis_padding_ratio = 0.05
    #logic
should_save = False
should_reverse = False #init as bool
word_cap = 0 # 0 means no cap. cant be bigger than n_words.
n_features = 8
len_timer = 30 
max_inactive_ticks = 300 #30ticks/second
    #ai parameters
reverse_translation = 0 #0 means r.t. impossible, 1 always, everything else is a weight. to let the ai decide 0.5 is standard
ema_alpha = 0.3
time_normalization = 492200 #hours
    #standard gauss distribution parameters
std_sigma_factor = 1
std_min_gauss_weights = 0.2
std_focused_area = 0
    #other gauss distribution parameters
sigma_factor = std_sigma_factor
sigma_factor_min = 0.001
sigma_factor_range = 4.9
min_gauss_weights = std_min_gauss_weights
min_gauss_weights_min = 0
min_gauss_weights_range = 0.9
focused_area = std_focused_area # cant be bigger than word_cap and n_words
ignore_characters = " '(),?!\"\n."
ignore_words = ["der", "die", "das"] # german articles
feature_columns = [
    "occurrences_session",
    "last_seen",
    "last_seen_index",
    "n_reps",
    "EMA_accuracy",
    "last_correct_score",
    "correct_streak",
    "is_reversed"
]


class SRS:

    def __init__(self):
        pygame.init()

        self.folder = ""
        self.current_index = -1
        self.ticks = 0
        self.timer_running = False
        self.check_typing_start = True
        self.pause_triggered = False
        self.new_index_time = 0
        self.typing_start = 0
        self.session_index = 0
        self.input_text = ""
        self.inactive_ticks = 0
        self.n_words = 0
        self.editing_step = 0
        self.is_linux = False
        self.last_index = -1
        self.was_reversed = False
        self.ctrl_held = False
        self.df1 = []
        self.df2 = []

        self.settings_clicked = False
        self.get_new_gaussian = False
        self.ignore_next_button_up = False
        self.selected_focused_area = 0
        self.selected_sigma_factor = 0
        self.selected_min_gauss_weights = 0

        self.init_gui(width_ratio * window_scale, height_ratio * window_scale)

        self.check_os()

        self.init_folder_info()
        self.init_folder()
        self.init_set_config()
        self.init_data()

        self.trigger_pause()

    def check_os(self):
        # look if linux is used because filedialog doesnt properly work there
        if platform.system().lower() == "linux":
            self.is_linux = True

    def init_set_config(self):
        global min_gauss_weights
        global focused_area
        global sigma_factor

        try:
            # init min gauss weights
            with open(f"sets/{self.folder}/config/min_gauss_weights.csv", "r", encoding="utf-8") as f:
                line = f.readline().strip()
                min_gauss_weights = float(line)

            # init focused_area
            with open(f"sets/{self.folder}/config/focused_area.csv", "r", encoding="utf-8") as f:
                line = f.readline().strip()
                focused_area = float(line)

            # init sigma_factor
            with open(f"sets/{self.folder}/config/sigma_factor.csv", "r", encoding="utf-8") as f:
                line = f.readline().strip()
                sigma_factor = float(line)

        except FileNotFoundError:
            os.makedirs(f"sets/{self.folder}/config", exist_ok=True)

            # init new standard parameters
            with open(f"sets/{self.folder}/config/sigma_factor.csv", "w", encoding="utf-8") as f:
                    f.write(str(std_sigma_factor) + "\n")
            with open(f"sets/{self.folder}/config/min_gauss_weights.csv", "w", encoding="utf-8") as f:
                    f.write(str(std_min_gauss_weights) + "\n")
            with open(f"sets/{self.folder}/config/focused_area.csv", "w", encoding="utf-8") as f:
                    f.write(str(std_focused_area) + "\n")

            sigma_factor = std_sigma_factor
            min_gauss_weights = std_min_gauss_weights
            focused_area = std_focused_area

    def init_folder_info(self):
        try:
            with open("user_data/folder.csv", "r", encoding="utf-8") as f:
                line = f.readline().strip()
                self.folder = line

        except FileNotFoundError:
            os.makedirs("user_data", exist_ok=True)

        while self.folder == "":
            self.prompt_folder()

    def prompt_folder(self):
        root = tkinter.Tk()
        root.withdraw()

        start_dir = os.path.abspath("./sets")

        tmp_folder = os.path.basename(filedialog.askdirectory(
            title="Select file",
            initialdir=start_dir
        ))

        if tmp_folder and tmp_folder != "sets":
            self.folder = tmp_folder

            with open("user_data/folder.csv", "w", encoding="utf-8") as f:
                f.write(self.folder + "\n")

            # init data again for new folder
            self.init_set_config()
            self.init_folder()
            self.init_data()

            self.last_index = -1


        root.destroy()

    def init_folder(self):
        #init vocab and translation
        try:

            # init first language vocab
            with open(f"sets/{self.folder}/language1.csv", "r", encoding="utf-8") as f:
                self.l1 = [line.strip().lower() for line in f]
                self.n_words = len(self.l1)

                #making sure parameters are in range
                if word_cap > 0 and word_cap > self.n_words:
                    print("Error: word_cap bigger than n_words!")
                    sys.exit()

                if focused_area > self.n_words or (word_cap > 0 and focused_area > word_cap):
                    print("Error: focused_area bigger than n_words or word cap!")
                    sys.exit()
                
                if word_cap:
                    self.l1 = self.l1[:word_cap]
                    self.n_words = len(self.l1)
            # init corresponding second language
            with open(f"sets/{self.folder}/language2.csv", "r", encoding="utf-8") as f:
                self.l2 = [line.strip().lower() for line in f]
                if word_cap:
                    self.l2 = self.l2[:word_cap]

            self.source = self.l1
            self.target = self.l2

            # if something is wrong with vocab data return with error
            if not len(self.l1) == len(self.l2):
                return 1

        except Exception as e:
            print(e)

    def init_gui(self, width, height):
        # Window
        self.WIDTH = width
        self.HEIGHT = height

        # Fonts
        self.font_word = pygame.font.SysFont("Arial", int(font_word_ratio*window_scale))
        self.font_input = pygame.font.SysFont("Arial", int(font_input_ratio*window_scale))
        self.button_font = pygame.font.SysFont("DejaVu Sans", int(button_font_ration*window_scale))
        self.gaussian_font = pygame.font.SysFont("Arial", int(gaussian_font_ratio*window_scale))

        # Buttons in order
        self.folder_button = pygame.Rect(0.05*window_scale, 0.05* window_scale, self.WIDTH // (width_ratio * button_scale),self.HEIGHT // (height_ratio * button_scale))
        self.settings_button = pygame.Rect(0.55*window_scale,0.05*window_scale,self.WIDTH // (width_ratio * button_scale),self.HEIGHT // (height_ratio * button_scale))
        self.edit_button = pygame.Rect(1.05*window_scale, 0.05* window_scale, self.WIDTH // (width_ratio * button_scale),self.HEIGHT // (height_ratio * button_scale))
        self.coordinate_system_rect = pygame.Rect(self.WIDTH // 7, self.HEIGHT // 5, self.WIDTH * 7 // 10, self.HEIGHT * 7 // 10)

        # colours
        self.DARK = "#0D0E29"
        self.LIGHT = "#CBCCF7"
        self.BLUE = "#57CFC9"
        self.GREEN = "#2CD42C"
        self.RED = "#D42C2C"
        self.BACKGROUND = self.DARK
        self.TEXT = self.LIGHT
        self.BUTTON_NORMAL = "#A67FEF"      # normal
        self.BUTTON_HOVER = "#C2A6FF"       # hover
        self.BUTTON_CLICKED = "#7A4CE6"     # clicked
        self.BUTTON_CLICKED_HOVER = "#9460F0"  # clicked + hover
        self.BUTTON_TEXT = "#130C1D"
        self.COORDINATE_SYSTEM = "#1D3873"
        self.COORDINATE_SYSTEM_GRAPH = "#0DE5F0"
        self.GRID_COLOR = "#14264F"

        self.coordinate_system_line_thickness = 5
        self.mouse_hold = False

        self.clock = pygame.time.Clock()

    def run(self):
        self.screen = pygame.display.set_mode((self.WIDTH, self.HEIGHT))
        pygame.display.set_caption("SRS")

        while True:
            self.screen.fill(self.BACKGROUND)
            self.handle_events()
            self.draw()
            pygame.display.flip()
            self.clock.tick(30)
    
    def handle_events(self):
        global focused_area
        global sigma_factor
        global min_gauss_weights

        found_keydown = False

        mouse_pos = pygame.mouse.get_pos()
        self.settings_button_hover = self.settings_button.collidepoint(mouse_pos)
        self.folder_button_hover = self.folder_button.collidepoint(mouse_pos)
        self.edit_button_hover = self.edit_button.collidepoint(mouse_pos)
        self.coordinate_system_hover = mouse_pos if self.coordinate_system_rect.collidepoint(mouse_pos) else None

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            elif event.type == pygame.KEYDOWN and not self.timer_running:
                if event.key == pygame.K_LCTRL:
                    self.ctrl_held = True

                elif self.ctrl_held:
                    if event.key == pygame.K_f:
                        self.trigger_folder_button()
                    elif event.key == pygame.K_g:
                        self.trigger_settings_button()
                    elif event.key == pygame.K_e:
                        self.trigger_edit_button()

                if not self.settings_clicked:
                    found_keydown = True
                    self.inactive_ticks = 0

                    if self.pause_triggered and not self.editing_step:
                        self.get_new_index()
                        self.pause_triggered = False
                        self.new_index_time = time.time()
                        self.check_typing_start = True

                    else:
                        if event.key == pygame.K_RETURN:
                            if self.input_text != "": #add a second if statement since we want it to do nothing if return is pressed but text is empty
                                if self.editing_step == 1:
                                    language_num = 2 if should_reverse else 1
                                    self.rewrite_line(self.last_index, self.input_text, f"sets/{self.folder}/language{language_num}.csv")
                                    self.input_text = self.target[self.last_index]
                                    self.editing_step = 2
                                elif self.editing_step == 2:
                                    language_num = 1 if should_reverse else 2
                                    self.rewrite_line(self.last_index, self.input_text, f"sets/{self.folder}/language{language_num}.csv")
                                    self.editing_step = 0
                                    self.input_text = ""
                                else:
                                    self.check_input()
                        elif event.key == pygame.K_BACKSPACE:
                            self.input_text = self.input_text[:-1]
                        else:
                            if self.check_typing_start:
                                self.typing_start = time.time()
                                self.check_typing_start = False
                            self.input_text += event.unicode

            elif event.type == pygame.MOUSEBUTTONDOWN:
                self.mouse_hold = True
                if self.settings_button_hover and not self.editing_step:
                    self.trigger_settings_button()

                elif self.folder_button_hover and not self.is_linux:
                    self.trigger_folder_button()

                elif self.edit_button_hover and not self.last_index == -1:
                    self.trigger_edit_button()
                    
                elif self.coordinate_system_hover:
                    if not self.get_new_gaussian:
                        self.ignore_next_button_up = True
                        self.get_new_gaussian = True

            elif event.type == pygame.MOUSEBUTTONUP:
                self.mouse_hold = False
                if self.ignore_next_button_up == True:
                    self.ignore_next_button_up = False
                else:
                    if self.get_new_gaussian and self.coordinate_system_hover:
                        self.save_sigma_factor(self.selected_sigma_factor)
                        self.save_min_gauss_weights(self.selected_min_gauss_weights)
                        self.save_focused_area(self.selected_focused_area)
                        self.get_new_gaussian = False
            
            elif event.type == pygame.KEYUP:
                if event.key == pygame.K_LCTRL:
                    self.ctrl_held = False
            
        if not found_keydown:
            self.inactive_ticks += 1
        if self.inactive_ticks > max_inactive_ticks:
            self.trigger_pause()

    def trigger_folder_button(self):
        self.prompt_folder()
        self.trigger_pause()

    def trigger_settings_button(self):
        if self.settings_clicked:
            self.settings_clicked = False
        else:
            self.settings_clicked = True
            self.get_new_gaussian = True
            self.trigger_pause()

    def trigger_edit_button(self):
        if self.editing_step != 0:
            self.editing_step = 0
            self.input_text = ""

        elif not self.settings_clicked:
            self.trigger_pause()
            self.input_text = self.source[self.last_index]
            self.editing_step = 1

    def trigger_pause(self):
        self.input_text = ""
        self.pause_triggered = True

    def check_input(self): 
        correct = self.is_correct()
        self.session_index += 1 

        if correct == 1:
            self.TEXT = self.GREEN
        else:
            self.TEXT = self.RED

        self.save_data(correct)

        self.timer_running = True
        self.ticks = len_timer
        self.input_text = ""

    def save_data(self, correct):

        # save new language data
        if should_reverse:
            word_data = self.df2[self.current_index] # currently saved data
        else:
            word_data = self.df1[self.current_index] # currently saved data
        old_ema = word_data[4]
        new_ema = self.get_ema(old_ema=word_data[4], accuracy=correct)

        word_data[0] += 1 # occurrences in session (will be reset on new session)
        word_data[1] = round(time.time()/3600 - time_normalization, 4) # last seen (in hours)
        word_data[2] = self.session_index # last seen index
        word_data[3] += 1 # n reps
        word_data[4] = new_ema # exponentially moving average of accuracy
        word_data[5] = round(self.account_typing_start_time(correct, (self.typing_start - self.new_index_time)), 4) # last correct 
        word_data[6] = word_data[6]+1 if correct == 1 else 0 # correct streak
        word_data[7] = should_reverse

        if should_save:
            # save language data
            if should_reverse:
                self.df2[self.current_index] = word_data
                pd.DataFrame(self.df2).to_csv(f"sets/{self.folder}/l2_data.csv", mode="w", index=False, header=feature_columns)
            else:
                self.df1[self.current_index] = word_data
                pd.DataFrame(self.df1).to_csv(f"sets/{self.folder}/l1_data.csv", mode="w", index=False, header=feature_columns)
            
            # save data points
            pd.DataFrame([word_data]).to_csv("data/feature_data.csv", mode="a", index=False, header=False)
            pd.DataFrame([new_ema - old_ema]).to_csv("data/reward_data.csv", mode="a", index=False, header=False)

        self.print_data_tensor(word_data) #*

    def save_sigma_factor(self, selected_sigma_factor):
        global sigma_factor
        sigma_factor = selected_sigma_factor
        if selected_sigma_factor:
            try:
                with open(f"sets/{self.folder}/config/sigma_factor.csv", "w", encoding="utf-8") as f:
                    f.write(str(sigma_factor) + "\n")
            except FileNotFoundError:
                os.makedirs(f"sets/{self.folder}/config", exist_ok=True)
                with open(f"sets/{self.folder}/config/sigma_factor.csv", "w", encoding="utf-8") as f:
                    f.write(str(sigma_factor) + "\n")

    def save_min_gauss_weights(self, selected_min_gauss_weights):
        global min_gauss_weights
        min_gauss_weights = selected_min_gauss_weights
        if selected_min_gauss_weights:
            try:
                with open(f"sets/{self.folder}/config/min_gauss_weights.csv", "w", encoding="utf-8") as f:
                    f.write(str(min_gauss_weights) + "\n")
            except FileNotFoundError:
                os.makedirs(f"sets/{self.folder}/config", exist_ok=True)
                with open(f"sets/{self.folder}/config/min_gauss_weights.csv", "w", encoding="utf-8") as f:
                    f.write(str(min_gauss_weights) + "\n")

    def save_focused_area(self, selected_focused_area):
        global focused_area
        focused_area = selected_focused_area
        if selected_focused_area:
            try:
                with open(f"sets/{self.folder}/config/focused_area.csv", "w", encoding="utf-8") as f:
                    f.write(str(focused_area) + "\n")
            except FileNotFoundError:
                os.makedirs(f"sets/{self.folder}/config", exist_ok=True)
                with open(f"sets/{self.folder}/config/focused_area.csv", "w", encoding="utf-8") as f:
                    f.write(str(focused_area) + "\n")            

    def account_typing_start_time(self, correct, typing_start_time):
        # view curve README file
        return min(1.0, math.exp((-typing_start_time + 1) / 4) * (0.6) + 0.4 if correct else 0.0)

    def get_ema(self, old_ema, accuracy):
        return ema_alpha*accuracy + (1-ema_alpha)*old_ema

    def print_data_tensor(self, tensor):
        print()
        for i in range(len(feature_columns)):
            print(f"{feature_columns[i]}: {tensor[i]}")

    def print_validation_reason(self, input, target, min_input_len, input_len, distance):
        print()
        print(f"All words ({list(input)}) are in target ({list(target)}): {all(word in target for word in input)}")
        print(f"Input length ({input_len}) is bigger than or equal min input length ({min_input_len}): {input_len >= min_input_len}")
        print(f"Word distances: {distance}")

    def get_new_index(self):
        global should_reverse

        if self.current_index != -1:
            self.last_index = self.current_index
            self.was_reversed = should_reverse

        should_reverse = False

        if should_reverse:
            self.source = self.l2
            self.target = self.l1

        else:
            self.source = self.l1
            self.target = self.l2

        self.current_index = random.randint(0, self.n_words-1)
        self.new_index_time = time.time()
        self.check_typing_start = True

    def draw(self):
        if not self.settings_clicked:
            if self.timer_running:
                if self.ticks == 0:
                    self.timer_running = False
                    self.TEXT = self.LIGHT
                    self.input_text = ""
                    self.get_new_index()
                else:
                    self.ticks -= 1
                    self.input_text = self.target[self.current_index]
                
            # decide what to display
            if self.editing_step == 1:
                display_word = f"Edit source: {self.source[self.last_index]}"
            elif self.editing_step == 2:
                display_word = f"Edit target: {self.target[self.last_index]}"
            else:
                if self.pause_triggered:
                    display_word = "Press any key to proceed.."
                else:
                    display_word = self.source[self.current_index]
            word_surface = self.font_word.render(display_word, True, self.TEXT)
            word_rect = word_surface.get_rect(center=(self.WIDTH // 2, self.HEIGHT *3 // 8))
            self.screen.blit(word_surface, word_rect)
            # text area 
            input_surface = self.font_input.render(self.input_text, True, self.TEXT)
            input_rect = input_surface.get_rect(center=(self.WIDTH // 2, self.HEIGHT * 3 // 4))
            self.screen.blit(input_surface, input_rect)
            
        else:
            global focused_area
            global sigma_factor

            axis_padding = axis_padding_ratio * window_scale
            
            #draw a grid
            self.draw_grid(self.coordinate_system_rect, self.n_words,  self.GRID_COLOR)

            #draw current selected curve
            self.draw_gaussian_curve(self.screen, self.coordinate_system_rect, focused_area, sigma_factor, min_gauss_weights, self.COORDINATE_SYSTEM_GRAPH)

            #settings for gaussian distribution
            pygame.draw.rect(self.screen, self.COORDINATE_SYSTEM, self.coordinate_system_rect, self.coordinate_system_line_thickness, 0)
            if self.coordinate_system_hover:

                if self.get_new_gaussian:
                    x, y = self.coordinate_system_hover
                    # rect coordinates
                    rect_left = self.coordinate_system_rect.left
                    rect_right = self.coordinate_system_rect.right
                    rect_up = self.coordinate_system_rect.top
                    rect_down = self.coordinate_system_rect.bottom

                    if rect_left < x < rect_right and rect_up < y < rect_down:

                        focused_area_local = int(((x - rect_left) / (rect_right - rect_left)) * self.n_words)

                        if self.mouse_hold:
                            y_axis = ((rect_down - y) / (rect_down - rect_up))
                            # draw curve based on selected values
                            self.draw_gaussian_curve(self.screen, self.coordinate_system_rect, focused_area_local, self.selected_sigma_factor, y_axis, self.RED)
                            self.selected_min_gauss_weights = y_axis
                            self.selected_focused_area = focused_area_local
                        else:
                            y_axis = (sigma_factor_min + (((rect_down - y) / (rect_down - rect_up))**2) * sigma_factor_range)
                            # draw curve based on selected values
                            self.draw_gaussian_curve(self.screen, self.coordinate_system_rect, focused_area_local, y_axis, 0 , self.RED)
                            self.selected_sigma_factor = y_axis
                            self.selected_focused_area = focused_area_local

            # label y axis
            amount = 11
            for i in range(amount):
                ratio = i / (amount - 1)
                label_y = self.coordinate_system_rect.bottom - ratio * (self.coordinate_system_rect.height - 2*axis_padding) - axis_padding
                label_surf = self.gaussian_font.render(f"{ratio:.2f}", True, self.COORDINATE_SYSTEM)
                label_rect = label_surf.get_rect(right=self.coordinate_system_rect.left - 5, centery=label_y)
                self.screen.blit(label_surf, label_rect)

            # label x axis
            amount = self.dim_to_grid(self.n_words) +1 
            for i in range(amount):
                ratio = i / (amount - 1)
                label_val = int(ratio * self.n_words) 
                label_x = self.coordinate_system_rect.left + ratio * (self.coordinate_system_rect.width - 2*axis_padding) + axis_padding
                label_surf = self.gaussian_font.render(f"{label_val}", True, self.COORDINATE_SYSTEM)
                label_rect = label_surf.get_rect(centerx=label_x, top=self.coordinate_system_rect.bottom + 5)
                self.screen.blit(label_surf, label_rect)



        # open settings
        self.draw_button(self.settings_button, self.settings_button_hover, self.settings_clicked, image="settings_button.png")

        # select other folder
        self.draw_button(self.folder_button,  self.folder_button_hover, False, image="folder_button.png")

        # edit prev word
        self.draw_button(self.edit_button, self.edit_button_hover, False, image="edit_button.png")

    def rewrite_line(self, line, replacement, file):
        with open(file, "r", encoding="utf-8") as f:
            lines = f.readlines()
        lines[line] = replacement.rstrip("\n") + "\n"
        with open(file, "w", encoding="utf-8") as f:
            f.writelines(lines)


    def draw_grid(self, rect, max_x, color):
        rows = 10
        cols = self.dim_to_grid(max_x)
        cell_width = rect.width / cols
        cell_height = rect.height / rows

        for i in range(cols + 1):
            x = (rect.x + i * cell_width)
            pygame.draw.line(self.screen, color, (x, rect.y), (x, rect.y + rect.height))

        for j in range(rows + 1):
            y = (rect.y + j * cell_height)
            pygame.draw.line(self.screen, color, (rect.x, y), (rect.x + rect.width, y))

    def dim_to_grid(self, dim):
        exponent = math.floor(math.log10(dim))
        val = 0
        if exponent == 0:
            val = 10
        elif exponent == 1:
            val = dim
        elif exponent == 2:
            val = dim/10
        elif exponent == 3:
            val = dim/1000
        else:
            val = 0
        while not val < 15:
            val /= 2
        return int(val)

    def draw_gaussian_curve(self, surface, rect, focused_area, sigma_factor, min_gauss_weights, color):
        upper_distance = self.n_words - 1 - focused_area
        sigma = (max(focused_area, upper_distance) / 3) * sigma_factor

        weights = []
        for i in range(self.n_words):
            val = math.exp(-0.5 * ((i - focused_area) / sigma) ** 2)
            val = val * (1 - min_gauss_weights) + min_gauss_weights
            weights.append(val)

        padding = self.coordinate_system_line_thickness

        inner_left = rect.left + padding
        inner_right = rect.right - padding
        inner_top = rect.top + padding
        inner_bottom = rect.bottom - padding

        inner_width = inner_right - inner_left
        inner_height = inner_bottom - inner_top

        points = []
        for i, w in enumerate(weights):
            px = inner_left + (i / (self.n_words - 1)) * inner_width
            py = inner_bottom - w * inner_height
            points.append((px, py))

        if len(points) > 1:
            pygame.draw.lines(surface, color, False, points, self.coordinate_system_line_thickness)

    def draw_button(self, rect, hover, pressed, image):
        if pressed:
            color = self.BUTTON_CLICKED_HOVER if hover else self.BUTTON_CLICKED
        else:
            color = self.BUTTON_HOVER if hover else self.BUTTON_NORMAL

        pygame.draw.rect(self.screen, color, rect, border_radius=int(border_radius_ratio*window_scale))

        self.load_image(image, rect)

    def load_image(self, image, rect):
        # draw image if exists

        image = pygame.image.load(f"img/{image}").convert_alpha()
        image = pygame.transform.smoothscale(image, (rect.width*3//4, rect.height*3//4))    

        img_rect = image.get_rect(center=rect.center)
        self.screen.blit(image, img_rect)

    def is_correct(self):
        # if the written words come up in the target assume it is a right answer
        input = self.filter(self.input_text)
        target_word = self.filter(self.target[self.current_index])
        min_input_len = math.ceil(math.sqrt(sum([len(word) for word in target_word])))
        input_len = sum([len(word) for word in input])

        if input == ["idk"]:
            return False
        
        distances = [min([self.word_distance(input_word, word) for word in target_word]) for input_word in input]
        correct = all(input[i] in target_word if len(input[i]) <= 4 else distances[i] <= 1 for i in range(len(input))) and min_input_len <= input_len

        self.print_validation_reason(input, target_word, min_input_len, input_len, distances) 

        return correct
    
    def filter(self, word):
        # replace all characters on list with space
        for c in ignore_characters:
            word = word.replace(c, " ")
        return [x for x in str(word).lower().split() if x not in ignore_words]

    def init_data(self):
        # init collected data
        try:
            self.init_df_tensor(1)
            if self.n_words != len(self.df1):
                # file doesnt have enough rows ( in case vocab was added later on )
                rows = [[0.0]*n_features for _ in range(self.n_words - len(self.df1))]
                # asign start bias to ema
                rows = self.set_row_val(rows, 4, 0.5)
                pd.DataFrame(rows).to_csv(f"sets/{self.folder}/l1_data.csv", mode="a", index=False, header=False)
                self.init_df_tensor(1)

        except Exception as _:
            # file doesnt exist
            rows = [[0.0]*n_features for _ in range(self.n_words)]
            # asign start bias to ema
            rows = self.set_row_val(rows, 4, 0.5)
            pd.DataFrame(rows).to_csv(f"sets/{self.folder}/l1_data.csv", mode="a", index=False, header=feature_columns)
            self.init_df_tensor(1)

        try:
            self.init_df_tensor(2)
            if self.n_words != len(self.df2):
                # file doesnt have enough rows ( in case vocab was added later on )
                rows = [[0.0]*n_features for _ in range(self.n_words - len(self.df2))]
                # asign start bias to ema
                rows = self.set_row_val(rows, 4, 0.5)
                pd.DataFrame(rows).to_csv(f"sets/{self.folder}/l2_data.csv", mode="a", index=False, header=False)
                self.init_df_tensor(2)

        except Exception as _:
            # file doesnt exist
            rows = [[0.0]*n_features for _ in range(self.n_words)]
            # asign start bias to ema
            rows = self.set_row_val(rows, 4, 0.5)
            # set should reverse true
            rows = self.set_row_val(rows, 7, 1.0)
            pd.DataFrame(rows).to_csv(f"sets/{self.folder}/l2_data.csv", mode="a", index=False, header=feature_columns)
            self.init_df_tensor(2)

    def init_df_tensor(self, num):
        if num == 1:
            df1 = pd.read_csv(f"sets/{self.folder}/l1_data.csv", header=0)
            # reset occurrences in session and save as self.df
            self.df1 = self.set_row_val(df1.values.tolist(), 0, 0.0)
        else:
            df2 = pd.read_csv(f"sets/{self.folder}/l2_data.csv", header=0)
            # reset occurrences in session and save as self.df
            self.df2 = self.set_row_val(df2.values.tolist(), 0, 0.0)

    def set_row_val(self, df, col, val):
        for row in df:
            row[col] = val
        return df
    
    def word_distance(self, s1, s2):
        # levensthein word distance
        # (copy pasted)
        len1, len2 = len(s1), len(s2)
        dp = [[0] * (len2 + 1) for _ in range(len1 + 1)]
        for i in range(len1 + 1): dp[i][0] = i
        for j in range(len2 + 1): dp[0][j] = j
        for i in range(1, len1 + 1):
            for j in range(1, len2 + 1):
                dp[i][j] = dp[i-1][j-1] if s1[i-1] == s2[j-1] else 1 + min(dp[i-1][j-1], dp[i-1][j], dp[i][j-1])
        return dp[len1][len2]


# run main
if __name__ == "__main__":
    application = SRS()
    application.run()
    
