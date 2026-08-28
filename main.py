#external libraries
import pandas as pd
import numpy as np
import pygame

#standard libraries
import tkinter
from tkinter import filedialog
import platform
import time
import math
import sys
import os

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"


# TODO intervall timer
# TODO less padding between sliders
# TODO add text for shortcuts

# TODO change gaussian range!!!

# parameters for dev
    #print
print_data_tensor = True # saved data tensor after word input
print_validation = False # explain systems choice to validate or invalidate users input
print_normalized_df = False # complete data for nn
print_exploration_chance = True
print_exploration_validation = False
print_expected_ema = False
    #gui
window_scale = 200
button_scale = 2.5 #divides through button scale
width_ratio = 6
height_ratio = 3 
font_word_ratio = 0.3
font_input_ratio = 0.2
border_radius_ratio = 0.1 
gaussian_font_ratio = 0.1
axis_padding_ratio = 0.05
button_padding = 0.45
first_button_padding = 0.05
    #logic
should_save = True
word_cap = 0 # 0 means no cap. cant be bigger than n_words.
starting_cap = 0 # first word index that may be shown
len_timer = 30
len_timer_min = 0
len_timer_max = 60
min_timer = 15
min_timer_min = 5
min_timer_max = 30
max_fps = 60
max_inactive_ticks = 450 #30ticks/second
    #ai parameters
ema_alpha = 0.3
time_normalization = 495000 #hours
    #standard gauss distribution parameters
std_sigma_factor = 1.0
std_min_gauss_weights = 0.0
std_focused_area = 0.0
    #other gauss distribution parameters
sigma_factor = std_sigma_factor
sigma_factor_min = 0.001
sigma_factor_range = 4.9
min_gauss_weights = std_min_gauss_weights
min_gauss_weights_min = 0
min_gauss_weights_range = 0.9
exploration_factor_min = 0.5
exploration_factor_max = 1.5
slider_snap_sensitivity = 0.05
focused_area = std_focused_area # cant be bigger than word_cap and n_words
ignore_characters = " \x08'/(),-;?!\"\n.…"
feature_columns = [
    "occurrences_session",
    "last_seen",
    "last_seen_index",
    "n_reps",
    "EMA_accuracy",
    "last_correct_score",
    "correct_streak",
    "current_time",
    "current_index",
    "time_since_start",
    "index_since_start",
    "session_ema"
    ]
ai_input_columns =  [
    "occurrences_session",
    "last_seen",
    "last_seen_index",
    "n_reps",
    "EMA_accuracy",
    "last_correct_score",
    "correct_streak",
    "time_since_start",
    "index_since_start",
    "session_ema"
    ]
    #support for german language
short_form_list = [["etwas"], ["jemand", "jemandem", "jemanden"]]
short_form_translation = ["etw", "jmd"]
ignore_words = ["der", "die", "das"] # german articles


class SRS:

    def __init__(self):
        pygame.init()

        # init variables
            # data
        self.folder = ""
        self.df = pd.DataFrame()
        self.image_cache = {}

            # index
        self.current_index = -1
        self.last_index = -1
        self.index = 0
        self.starting_index = 0
        self.n_words = 0
        self.total_words = 0
        self.next_button_index = 0

            # timers
        self.ticks = 0
        self.timer_running = False
        self.new_index_time = 0
        self.starting_time = 0
        self.inactive_ticks = 0

            # text input
        self.check_typing_start = True
        self.typing_start = 0
        self.input_text = ""
        self.pause_triggered = False
            # mouse / keyboard
        self.ctrl_hold = False
        self.mouse_hold = False
        self.exploration_slider_active = False
        self.timer_slider_active = False
        self.timer_min_slider_active = False
        self.starting_cap_slider_active = False
        self.word_cap_slider_active = False
        self.coordinate_click_start_time = 0
        self.ignore_next_button_up = False

        # --- UI/Settings ---
        self.settings_clicked = False
        self.editing_step = 0
        self.selected_focused_area = 0

        # --- Plattform ---
        self.is_linux = False

        # --- Gaussian/Weights ---
        self.get_new_gaussian = False
        self.selected_sigma_factor = 0
        self.selected_min_gauss_weights = 0

        # --- KI / Lernlogik ---
        self.ignore_ai = False
        self.use_gaussian = False
        self.previous_word_correct = False
        self.normalization_stats = np.zeros((len(ai_input_columns), 2))
        self.exploration_factor = 1
        self.exploitation_count = 0
        self.session_ema = 0.5

        self.init_gui(width_ratio * window_scale, height_ratio * window_scale)

        self.check_os()

        self.init_data_folder()
        self.init_user_data_info()
        self.init_folder()
        self.init_set_config()
        self.init_data()

        self.trigger_pause()

    def delete_row(self, row_index):
        row_index -= 1 #account css starting at 0
        #Delete row at row_index from data, language1, and language2
        files = [
            f"sets/{self.folder}/data.csv",
            f"sets/{self.folder}/language1.csv",
            f"sets/{self.folder}/language2.csv",
        ]

        for path in files:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            is_csv_with_header = path.endswith(".csv")

            if is_csv_with_header:
                header = lines[0]
                data_lines = lines[1:]
                if row_index >= len(data_lines):
                    print(f"Error: row_index {row_index} out of range in {path}")
                    return
                del data_lines[row_index]
                new_lines = [header] + data_lines
            else:
                if row_index >= len(lines):
                    print(f"Error: row_index {row_index} out of range in {path}")
                    return
                del lines[row_index]
                new_lines = lines

            with open(path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)

        # Keep in-memory data in sync
        if row_index < len(self.df):
            self.df = self.df.drop(index=row_index).reset_index(drop=True)
        if row_index < len(self.l1):
            del self.l1[row_index]
        if row_index < len(self.l2):
            del self.l2[row_index]

        self.n_words = len(self.l1)
        print(f"Deleted row {row_index}. Remaining words: {self.n_words}")

    def check_os(self):
        # look if linux is used because filedialog doesnt properly work there
        if platform.system().lower() == "linux":
            self.is_linux = True

    def init_data_folder(self):
        os.makedirs("data", exist_ok=True)

        feature_path = "data/feature_data.csv"
        reward_path = "data/reward_data.csv"

        if not os.path.exists(feature_path):
            pd.DataFrame().to_csv(feature_path, index=False, header=False)

        if not os.path.exists(reward_path):
            pd.DataFrame().to_csv(reward_path, index=False, header=False)

    def init_set_config(self):
        global min_gauss_weights
        global focused_area
        global sigma_factor
        global min_timer

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

            with open(f"sets/{self.folder}/config/min_timer.csv", "r", encoding="utf-8") as f:
                line = f.readline().strip()
                min_timer = float(line)

        except FileNotFoundError:
            os.makedirs(f"sets/{self.folder}/config", exist_ok=True)
            min_timer = 15

            # init new standard parameters
            with open(f"sets/{self.folder}/config/sigma_factor.csv", "w", encoding="utf-8") as f:
                    f.write(str(std_sigma_factor) + "\n")
            with open(f"sets/{self.folder}/config/min_gauss_weights.csv", "w", encoding="utf-8") as f:
                    f.write(str(std_min_gauss_weights) + "\n")
            with open(f"sets/{self.folder}/config/focused_area.csv", "w", encoding="utf-8") as f:
                    f.write(str(std_focused_area) + "\n")
            with open(f"sets/{self.folder}/config/min_timer.csv", "w", encoding="utf-8") as f:
                    f.write(str(min_timer) + "\n")

            sigma_factor = std_sigma_factor
            min_gauss_weights = std_min_gauss_weights
            focused_area = std_focused_area

    def init_user_data_info(self):
        try:
            with open("user_data/folder.csv", "r", encoding="utf-8") as f:
                line = f.readline().strip()
                self.folder = line
            with open("user_data/index.csv", "r", encoding="utf-8") as f:
                line = f.readline().strip()
                self.index = int(line)
                self.starting_index = self.index
                self.starting_time = self.get_scaled_time()

        except FileNotFoundError:
            os.makedirs("user_data", exist_ok=True)

        if self.folder == "":
            self.prompt_folder()
        # if no folder is found again, quit
        if self.folder == "":
            pygame.quit()

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
                self.all_l1 = self.l1.copy()
                self.total_words = len(self.l1)
                self.n_words = self.total_words

                #making sure parameters are in range
                last_word_index = word_cap if word_cap > 0 else self.total_words - 1
                if starting_cap < 0 or word_cap < 0 or last_word_index >= self.total_words:
                    print("Error: word range outside dataset!")
                    sys.exit()

                if starting_cap + 1 > last_word_index:
                    print("Error: word_cap must be at least 1 above starting_cap")
                    sys.exit()
                
                self.l1 = self.all_l1[starting_cap:last_word_index + 1]
                self.n_words = len(self.l1)
            # init corresponding second language
            with open(f"sets/{self.folder}/language2.csv", "r", encoding="utf-8") as f:
                self.l2 = [line.strip().lower() for line in f]
                self.l2 = self.l2[starting_cap:last_word_index + 1]

            self.source = self.l1
            self.target = self.l2

            # if something is wrong with vocab data return with error
            if not len(self.l1) == len(self.l2):
                return 1
            
            if self.n_words <= 1:
                return 1

        except Exception as e:
            print(e)

    def init_gui(self, width, height):

        # Window
        self.WIDTH = width
        self.HEIGHT = height

        # Fonts
        self.font_word = pygame.font.SysFont("calibri", int(font_word_ratio*window_scale))
        self.font_input = pygame.font.SysFont("calibri", int(font_input_ratio*window_scale))
        self.gaussian_font = pygame.font.SysFont("calibri", int(gaussian_font_ratio*window_scale))

        # Buttons in order

        self.settings_button = pygame.Rect(self.get_button_x()*window_scale, 0.05*window_scale, self.WIDTH // (width_ratio * button_scale),self.HEIGHT // (height_ratio * button_scale))
        self.edit_button = pygame.Rect(self.get_button_x(2)*window_scale, 0.05* window_scale, self.WIDTH // (width_ratio * button_scale),self.HEIGHT // (height_ratio * button_scale))
        self.loop_button = pygame.Rect(self.get_button_x()*window_scale, 0.05* window_scale, self.WIDTH // (width_ratio * button_scale),self.HEIGHT // (height_ratio * button_scale))
        self.gaussian_button = pygame.Rect(self.get_button_x()*window_scale, 0.05* window_scale, self.WIDTH // (width_ratio * button_scale),self.HEIGHT // (height_ratio * button_scale))
        self.folder_button = pygame.Rect(self.get_button_x()*window_scale, 0.05* window_scale, self.WIDTH // (width_ratio * button_scale),self.HEIGHT // (height_ratio * button_scale))
        self.coordinate_system_rect = pygame.Rect(self.WIDTH // 7, self.HEIGHT // 5, self.WIDTH * 7 // 10, self.HEIGHT * 7 // 10)
        slider_gap = int(0.04 * window_scale)
        slider_width = self.WIDTH // 6
        slider_height = int(0.1 * window_scale)
        slider_column_gap = int(0.225 * window_scale) + 25
        right_slider_left = self.WIDTH * 4 // 5
        middle_slider_left = right_slider_left - slider_width - slider_column_gap
        left_slider_left = middle_slider_left - slider_width - slider_column_gap
        self.exploration_slider_rect = pygame.Rect(
            middle_slider_left,
            slider_gap * 2,
            slider_width,
            slider_height,
        )
        self.timer_slider_rect = pygame.Rect(
            self.exploration_slider_rect.left,
            self.exploration_slider_rect.bottom + slider_gap * 4,
            slider_width,
            slider_height,
        )
        self.starting_cap_slider_rect = pygame.Rect(
            right_slider_left,
            self.exploration_slider_rect.top,
            slider_width,
            slider_height,
        )
        self.timer_min_slider_rect = pygame.Rect(
            left_slider_left,
            self.starting_cap_slider_rect.top,
            slider_width,
            slider_height,
        )
        self.start_button = pygame.Rect(
            self.timer_min_slider_rect.left,
            self.timer_min_slider_rect.bottom + int(0.07 * window_scale) + self.gaussian_font.get_linesize() + slider_gap - 10,
            slider_width,
            int(0.18 * window_scale),
        )
        self.word_cap_slider_rect = pygame.Rect(
            right_slider_left,
            self.timer_slider_rect.top,
            slider_width,
            slider_height,
        )

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
        self.button_tooltips = {
            "settings": "Open settings",
            "loop": "Ignore AI and loop through all words in order",
            "gaussian": "Let selected gaussian curve affect AI",
            "edit": "Edit recent word",
            "folder": "Change dataset",
        }
        self.COORDINATE_SYSTEM = "#1D3873"
        self.COORDINATE_SYSTEM_GRAPH = "#0DE5F0"
        self.GRID_COLOR = "#14264F"

        self.coordinate_system_line_thickness = 5

        self.clock = pygame.time.Clock()

    def get_button_x(self, num=None):
        if num:
            return (num - 1)*button_padding + first_button_padding
        else:
            self.next_button_index += 1
            return (self.next_button_index - 1)*button_padding + first_button_padding


    def run(self):
        self.screen = pygame.display.set_mode((self.WIDTH, self.HEIGHT))
        pygame.display.set_caption("SRS")

        while True:
            self.screen.fill(self.BACKGROUND)
            self.handle_events()
            self.draw()
            pygame.display.flip()
            self.clock.tick(max_fps)
    
    def handle_events(self):
        global focused_area
        global sigma_factor
        global min_gauss_weights
        global len_timer
        global len_timer_min

        found_keydown = False

        mouse_pos = pygame.mouse.get_pos()
        self.settings_button_hover = self.settings_button.collidepoint(mouse_pos)
        self.folder_button_hover = self.folder_button.collidepoint(mouse_pos)
        self.edit_button_hover = self.edit_button.collidepoint(mouse_pos)
        self.loop_button_hover = self.loop_button.collidepoint(mouse_pos)
        self.gaussian_button_hover = self.gaussian_button.collidepoint(mouse_pos)
        self.exploration_slider_hover = self.exploration_slider_rect.collidepoint(mouse_pos)
        self.timer_slider_hover = self.timer_slider_rect.collidepoint(mouse_pos)
        self.timer_min_slider_hover = self.timer_min_slider_rect.collidepoint(mouse_pos)
        self.start_button_hover = self.start_button.collidepoint(mouse_pos)
        self.starting_cap_slider_hover = self.starting_cap_slider_rect.collidepoint(mouse_pos)
        self.word_cap_slider_hover = self.word_cap_slider_rect.collidepoint(mouse_pos)
        self.coordinate_system_hover = mouse_pos if self.coordinate_system_rect.collidepoint(mouse_pos) else None

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            elif event.type == pygame.KEYDOWN and not self.timer_running:
                if event.key == pygame.K_LCTRL:
                    self.ctrl_hold = True

                elif self.ctrl_hold:
                    if event.key == pygame.K_f:
                        self.trigger_folder_button()
                    elif event.key == pygame.K_g:
                        self.trigger_settings_button()
                    elif event.key == pygame.K_e:
                        self.trigger_edit_button()
                    elif event.key == pygame.K_s:
                        self.trigger_pause()
                    elif event.key == pygame.K_l:
                        self.trigger_loop_button()
                    elif event.key == pygame.K_d:
                        if self.last_index != -1:
                            self.delete_row(self.last_index)
                            self.last_index = -1
                            print()
                            print(f"..deleted word {self.l2[self.last_index]}..")
                    elif event.key == pygame.K_BACKSPACE:
                        self.input_text = "" if self.input_text == "" else " ".join(self.input_text.split()[:-1])

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
                                    self.rewrite_line(self.last_index, self.input_text, f"sets/{self.folder}/language1.csv")
                                    self.input_text = self.target[self.last_index]
                                    self.editing_step = 2
                                elif self.editing_step == 2:
                                    self.rewrite_line(self.last_index, self.input_text, f"sets/{self.folder}/language2.csv")
                                    self.editing_step = 0
                                    self.input_text = ""
                                else:
                                    self.check_input()
                        elif event.key == pygame.K_BACKSPACE:
                            # add a seperate if statement so backspace character is not printed in the input text
                            if not self.ctrl_hold:
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

                elif self.settings_clicked and self.exploration_slider_hover:
                    self.exploration_slider_active = True
                    self.exploration_factor = self.update_slider(
                        self.exploration_slider_rect,
                        exploration_factor_min,
                        exploration_factor_max,
                        mouse_pos[0],
                    )

                elif self.settings_clicked and self.timer_slider_hover:
                    self.timer_slider_active = True
                    self.update_timer_slider(mouse_pos[0])

                elif self.settings_clicked and self.timer_min_slider_hover:
                    self.timer_min_slider_active = True
                    self.update_timer_min_slider(mouse_pos[0])

                elif self.settings_clicked and self.start_button_hover:
                    #! add logic
                    pass

                elif self.settings_clicked and self.starting_cap_slider_hover:
                    self.starting_cap_slider_active = True
                    self.update_starting_cap_slider(mouse_pos[0])

                elif self.settings_clicked and self.word_cap_slider_hover:
                    self.word_cap_slider_active = True
                    self.update_word_cap_slider(mouse_pos[0])

                elif self.settings_clicked and self.folder_button_hover and not self.is_linux:
                    self.trigger_folder_button()

                elif not self.settings_clicked and self.edit_button_hover and not self.last_index == -1:
                    self.trigger_edit_button()

                elif self.settings_clicked and self.loop_button_hover:
                    self.trigger_loop_button()

                elif self.settings_clicked and self.gaussian_button_hover:
                    self.trigger_gaussian_button()
                    
                elif self.coordinate_system_hover:
                    self.coordinate_click_start_time = time.time()
                    if not self.get_new_gaussian:
                        self.ignore_next_button_up = True
                        self.get_new_gaussian = True
                        self.mouse_hold = False

            elif event.type == pygame.MOUSEBUTTONUP:
                self.mouse_hold = False
                if self.exploration_slider_active:
                    self.exploration_factor = self.snap_slider_value(
                        self.exploration_factor,
                        exploration_factor_min,
                        exploration_factor_max,
                        [0.5, 0.75, 1.0, 1.25, 1.5],
                    )
                if self.timer_slider_active:
                    self.timer_value = self.snap_slider_value(
                        self.timer_value,
                        len_timer_min,
                        len_timer_max,
                        [0, 15, 30, 45, 60],
                    )
                    len_timer = round(self.timer_value)
                if self.timer_min_slider_active:
                    global min_timer
                    min_timer = min(
                        [5, 10, 15, 20, 25, 30],
                        key=lambda value: abs(value - self.min_timer_value),
                    )
                    with open(f"sets/{self.folder}/config/min_timer.csv", "w", encoding="utf-8") as f:
                        f.write(str(min_timer) + "\n")
                self.exploration_slider_active = False
                self.timer_slider_active = False
                self.timer_min_slider_active = False
                caps_changed = self.starting_cap_slider_active or self.word_cap_slider_active
                self.starting_cap_slider_active = False
                self.word_cap_slider_active = False
                if caps_changed:
                    self.apply_word_caps()
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
                    self.ctrl_hold = False

        if self.exploration_slider_active:
            self.exploration_factor = self.update_slider(
                self.exploration_slider_rect,
                exploration_factor_min,
                exploration_factor_max,
                pygame.mouse.get_pos()[0],
            )

        if self.timer_slider_active:
            self.update_timer_slider(pygame.mouse.get_pos()[0])

        if self.timer_min_slider_active:
            self.update_timer_min_slider(pygame.mouse.get_pos()[0])

        if self.starting_cap_slider_active:
            self.update_starting_cap_slider(pygame.mouse.get_pos()[0])

        if self.word_cap_slider_active:
            self.update_word_cap_slider(pygame.mouse.get_pos()[0])
            
        if not found_keydown and not self.editing_step:
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

    def trigger_loop_button(self):
        if self.ignore_ai:
            self.ignore_ai = False
        else:
            self.ignore_ai = True
        self.trigger_pause()

    def trigger_gaussian_button(self):
        self.use_gaussian = not self.use_gaussian
        self.trigger_pause()

    def update_slider(self, slider_rect, minimum, maximum, mouse_x, snap_values=None):
        slider_left = slider_rect.left
        slider_right = slider_rect.right
        if maximum <= minimum:
            return minimum
        slider_ratio = (mouse_x - slider_left) / (slider_right - slider_left)
        slider_ratio = max(0.0, min(1.0, slider_ratio))
        value = minimum + slider_ratio * (maximum - minimum)
        if snap_values:
            return min(snap_values, key=lambda snap_value: abs(snap_value - value))
        return value

    def snap_slider_value(self, value, minimum, maximum, snap_values):
        if maximum <= minimum or not snap_values:
            return value
        closest_value = min(snap_values, key=lambda snap_value: abs(snap_value - value))
        if abs(closest_value - value) <= (maximum - minimum) * slider_snap_sensitivity:
            return closest_value
        return value

    def update_timer_slider(self, mouse_x):
        self.timer_value = self.update_slider(
            self.timer_slider_rect,
            len_timer_min,
            len_timer_max,
            mouse_x,
        )
        global len_timer
        len_timer = round(self.timer_value)

    def update_timer_min_slider(self, mouse_x):
        self.min_timer_value = self.update_slider(
            self.timer_min_slider_rect,
            min_timer_min,
            min_timer_max,
            mouse_x,
        )

    def update_starting_cap_slider(self, mouse_x):
        global starting_cap
        maximum_word_index = word_cap if word_cap > 0 else self.total_words - 1
        starting_cap = round(self.update_slider(
            self.starting_cap_slider_rect,
            0,
            max(0, maximum_word_index - 2),
            mouse_x,
        ))

    def update_word_cap_slider(self, mouse_x):
        global word_cap
        word_cap = round(self.update_slider(
            self.word_cap_slider_rect,
            starting_cap + 2,
            self.total_words - 1,
            mouse_x,
        ))
        if word_cap == self.total_words - 1:
            word_cap = 0

    def apply_word_caps(self):
        self.init_folder()
        self.init_data()
        self.current_index = -1
        self.last_index = -1
        self.trigger_pause()

    def trigger_pause(self):
        self.input_text = ""
        self.pause_triggered = True

    def check_input(self): 
        correct = self.is_correct()
        self.increment_index()

        if correct == 1:
            self.TEXT = self.GREEN
        else:
            self.TEXT = self.RED

        self.save_data(correct)

        self.timer_running = True
        self.ticks = len_timer
        self.input_text = ""

    def increment_index(self):
        print(self.use_gaussian)
        self.index += 1
        with open("user_data/index.csv", "w", encoding="utf-8") as f:
            f.write(str(self.index) + "\n")

    def save_data(self, correct):

        # get old word data
        word_data = self.df.iloc[self.current_index] # currently saved data

        # only save data if word_data is not the init value
        usable_for_ai = word_data.iloc[3] > 1

        if should_save:
            if usable_for_ai:

                #save old word data (and resulting reward after)
                pd.DataFrame([word_data]).to_csv("data/feature_data.csv", mode="a", index=False, header=False)

            #get new word data
            time_now = time.time()
            time_now_scaled = self.scale_time(time_now)
            time_since_last_seen = time_now_scaled - word_data.iloc[7]

            correct_score = self.account_typing_start_time(correct, (self.typing_start - self.new_index_time), self.previous_word_correct)
            old_ema = word_data.iloc[4] if word_data.iloc[4] != 0 else 0.5
            new_ema = self.get_ema(old_ema=old_ema, accuracy=correct_score)

            # update session ema
            self.session_ema = self.get_ema(old_ema=self.session_ema, accuracy=correct_score)
            word_data.iloc[0] += 1.0 # occurrences in session (will be reset on new session)
            word_data.iloc[1] = time_since_last_seen # last seen (in hours)
            word_data.iloc[2] = float(self.index - word_data.iloc[8]) # last seen index
            word_data.iloc[3] += 1.0 # n reps
            word_data.iloc[4] = new_ema # exponentially moving average of accuracy
            word_data.iloc[5] = correct_score # last correct 
            word_data.iloc[6] = word_data.iloc[6]+1 if correct == 1.0 else 0.0 # correct streak
            word_data.iloc[7] = time_now_scaled # current time (in hours)
            word_data.iloc[8] = float(self.index) # current index
            word_data.iloc[9] = time_now_scaled - self.starting_time # current time since start of session (in hours)
            word_data.iloc[10] = self.index - self.starting_index # current index since start of session
            word_data.iloc[11] = self.session_ema
        
            if print_data_tensor:
                self.print_data_tensor(word_data) # print data for debugging

            # save whether last word was correct
            self.previous_word_correct = correct
            
            # save new word data in language data
            self.df.iloc[self.current_index] = word_data

            pd.DataFrame(self.df).to_csv(f"sets/{self.folder}/data.csv", mode="w", index=False, header=feature_columns)
            
            if usable_for_ai:
                # save reward resulting from old data
                pd.DataFrame([self.get_reward(old_ema, new_ema, time_since_last_seen)]).to_csv("data/reward_data.csv", mode="a", index=False, header=False)

    def get_normalized_df(self, df=None, is_training=False):
        df = self.df if df is None else df
        normalized_df = np.zeros((len(df), 10))

        normalized_df[:, 0] = self.log_and_normalize(df.iloc[:, 0], is_training, 0) # occurrences in session
        normalized_df[:, 1] = self.log_and_normalize(df.iloc[:, 1] if is_training else self.get_scaled_time() - df.iloc[:, 7], is_training, 1) # time since last seen: either use finished datapoint (for training) or use saved data to make a new one
        normalized_df[:, 2] = self.log_and_normalize(df.iloc[:, 2] if is_training else self.index - df.iloc[:, 8], is_training, 2) # index since last seen: same as above
        normalized_df[:, 3] = self.log_and_normalize(df.iloc[:, 3], is_training, 3) # n_reps
        normalized_df[:, 4] = self.normalize(df.iloc[:, 4]) # ema:because accuracy is always between 0 and 1, we can just subtract 0.5 to center it around 0
        normalized_df[:, 5] = self.normalize(df.iloc[:, 5]) # last correct score: same as above
        normalized_df[:, 6] = self.log_and_normalize(df.iloc[:, 6], is_training, 6) # correct streak
        normalized_df[:, 7] = self.log_and_normalize(60*(df.iloc[:, 9] if is_training else self.get_scaled_time() - self.starting_time), is_training, 7) # time since start of session (in minutes)
        normalized_df[:, 8] = self.log_and_normalize(df.iloc[:, 10] if is_training else self.index - self.starting_index, is_training, 8) # index since start of session
        normalized_df[:, 9] = self.normalize(df.iloc[:, 11]) # session ema between 0 and 1
        if print_normalized_df: 
            self.print_normalized_df(normalized_df[self.current_index])

        return normalized_df
    
    def log_and_normalize(self, x, is_training, id):
        log = np.log1p(x) 

        # if its training get new stat data from training data
        if is_training:
            self.save_stats([np.mean(log),np.std(log)]) # use stats so inference and training get the same values for normalization

        # use saved stats for computing
        return (log - self.normalization_stats[id, 0]) / self.normalization_stats[id, 1] if self.normalization_stats[id, 1] != 0 else log

    def normalize(self, x):
        return x - 0.5

    def get_scaled_time(self):
        return self.scale_time(time.time())
    
    def scale_time(self, x):
        return round(x/3600 - time_normalization, 4)

    def get_reward(self, old_ema, new_ema, time_since_last_seen, decay_lambda=0.005):
        expected_ema = old_ema * math.exp(-decay_lambda * time_since_last_seen)
        if print_expected_ema:
            print(f"expected ema: {expected_ema}")
        return new_ema - expected_ema

    def save_sigma_factor(self, selected_sigma_factor):
        global sigma_factor
        if selected_sigma_factor:
            sigma_factor = selected_sigma_factor
            try:
                with open(f"sets/{self.folder}/config/sigma_factor.csv", "w", encoding="utf-8") as f:
                    f.write(f"{sigma_factor:.4f}".rstrip('0').rstrip('.') + "\n")
            except FileNotFoundError:
                os.makedirs(f"sets/{self.folder}/config", exist_ok=True)
                with open(f"sets/{self.folder}/config/sigma_factor.csv", "w", encoding="utf-8") as f:
                    f.write(f"{sigma_factor:.4f}".rstrip('0').rstrip('.') + "\n")

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

    def account_typing_start_time(self, correct, typing_start_time, previous_word_correct):
        # view curve README file
        val = ((math.exp((-typing_start_time + 1) / 4) * (0.6) + 0.4)+0.1 if not previous_word_correct else math.exp((-typing_start_time + 1) / 4) * (0.6) + 0.4) if correct else 0.0 if correct else 0.0
        return min(1.0, val)

    def get_ema(self, old_ema, accuracy):
        return ema_alpha*accuracy + (1-ema_alpha)*old_ema

    def print_data_tensor(self, tensor : pd.Series):
        print()
        print(f" ---{self.l1[self.current_index]} (id: {self.current_index})--- ")
        for i in range(len(feature_columns)):
            print(f"({i}) {feature_columns[i]}: {tensor.iloc[i]}")

    def print_normalized_df(self, tensor : pd.Series):
        print()
        print(f" ---{self.l1[self.current_index]} (id: {self.current_index})--- ")
        for i in range(len(ai_input_columns)):
            print(f"({i}) {ai_input_columns[i]}: {tensor[i]}")

    def print_validation_reason(self, input, target, min_input_len, input_len, distance):
        print()
        print(f"All words ({list(input)}) are in target ({list(target)}): {all(word in target for word in input)}")
        print(f"Input length ({input_len}) is bigger than or equal min input length ({min_input_len}): {input_len >= min_input_len}")
        print(f"Word distances: {distance}")

    def get_new_index(self):

        if self.current_index != -1:
            self.last_index = self.current_index

        # get new index
        if not self.ignore_ai:
            selection_weights = self.gauss_distribution() if self.use_gaussian else np.ones(self.n_words)
            explored_mask = self.df.iloc[:, 3] != 0
            # determine whether to exploit or explore
            if not self.should_explore():
                self.exploitation_count += 1
                self.word_vals = np.random.rand(self.n_words) * selection_weights #! change
                masked_vals = np.where(explored_mask, self.word_vals, -np.inf)
                self.current_index = int(np.argmax(masked_vals))

            else:
                self.exploitation_count = 0
                self.word_vals = np.random.rand(self.n_words) * selection_weights
                masked_vals = np.where(explored_mask == 0, self.word_vals, -np.inf)
                self.current_index = int(np.argmax(masked_vals))        
        else:
            #mode to just loop through all words
            self.current_index = self.index % self.n_words # ignore ai and go through words in order
        self.new_index_time = time.time()
        self.check_typing_start = True

    def should_explore(self):
        A = 4.8
        B = 4.7
        C = 0.05
        D = 2
        E = 1.06

        n_explored = np.sum(self.df.iloc[:, 3] != 0) # get sum of explored items
        current_certainty = 0.5 + self.session_ema # use last correct score. if avrg score is below 0.5, multiplication will make exploration less likely. opposite for above 0.5
        filtered = self.df.iloc[:, 4][self.df.iloc[:, 4] != 0]
        avrg_certainty = 0.5 + np.mean(filtered) if len(filtered) > 0 else 1 # use average of all saved accuracies

        exploration_chance = ((A/(n_explored+B)) + C) * (current_certainty ** D) * (avrg_certainty ** D) * self.exploration_factor * (E ** self.exploitation_count)
        return_val = True if np.random.random() < exploration_chance else False # generate a number to see whether to explore

        if print_exploration_chance:
            print()
            print(f"Exploration likelihood: {exploration_chance*100:.2f}%")#
            print(f"Output: {return_val}")

        if print_exploration_validation:
            print()
            print("Exploration chance factors:")
            print(f"n_explored: {n_explored}")
            print(f"current_certainty: {current_certainty:.3f}")
            print(f"avrg_certainty: {avrg_certainty:.3f}")
            print(f"exploration_factor: {self.exploration_factor}")
            print(f"exploitation_count: {self.exploitation_count}")
        
        return return_val

    def use_forward(self):

        normalized_df = self.get_normalized_df() #!

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

                        delta_start_time = time.time() - self.coordinate_click_start_time
                        if self.mouse_hold and delta_start_time > 0.2:
                            y_axis = ((rect_down - y) / (rect_down - rect_up))
                            # draw curve based on selected values
                            self.draw_gaussian_curve(self.screen, self.coordinate_system_rect, focused_area_local, self.selected_sigma_factor, y_axis, self.RED)
                            self.selected_min_gauss_weights = round(y_axis, 1) # round tenth
                            self.selected_focused_area = focused_area_local
                        else:
                            y_axis = (sigma_factor_min + (((rect_down - y) / (rect_down - rect_up))**2) * sigma_factor_range)
                            # draw curve based on selected values
                            self.draw_gaussian_curve(self.screen, self.coordinate_system_rect, focused_area_local, y_axis, self.selected_min_gauss_weights , self.RED)
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


        #* draw buttons
        # open settings
        self.draw_button(self.settings_button, self.settings_button_hover, self.settings_clicked, image="settings_button.png")

        if not self.settings_clicked:
            # edit prev word
            self.draw_button(self.edit_button, self.edit_button_hover, False, image="edit_button.png")
        else:
            # loop through words
            self.draw_button(self.loop_button, self.loop_button_hover, self.ignore_ai, image="loop_button.png")

            # use Gaussian weights for the next word selection
            self.draw_button(self.gaussian_button, self.gaussian_button_hover, self.use_gaussian, label="GAUSS")

            if not self.is_linux:
                # select other folder
                self.draw_button(self.folder_button,  self.folder_button_hover, False, image="folder_button.png")

        #* draw sliders
        if self.settings_clicked:
            self.draw_slider(
                self.timer_min_slider_rect,
                min_timer,
                min_timer_min,
                min_timer_max,
                "Min timer",
                integer_value=True,
                snap_values=[5, 10, 15, 20, 25, 30],
                align_left=True,
                label_offset=int(0.07 * window_scale),
            )
            self.draw_slider(
                self.starting_cap_slider_rect,
                starting_cap,
                0,
                max(0, (word_cap if word_cap > 0 else self.total_words - 1) - 2),
                "First word",
                value_text=f"({starting_cap}) {self.get_word_preview(starting_cap)}",
                integer_value=True,
                align_left=True,
                label_offset=int(0.07 * window_scale),
            )
            self.draw_slider(
                self.word_cap_slider_rect,
                word_cap if word_cap > 0 else self.total_words - 1,
                starting_cap + 2,
                self.total_words - 1,
                "Last word",
                value_text=f"({word_cap if word_cap > 0 else self.total_words - 1}) {self.get_word_preview(word_cap if word_cap > 0 else self.total_words - 1)}",
                integer_value=True,
                align_left=True,
                label_offset=int(0.07 * window_scale),
            )
            self.draw_exploration_slider()
            self.draw_timer_slider()
            self.draw_button(self.start_button, self.start_button_hover, False, label="Start")

        #* draw hovering messages after:
        if self.settings_button_hover:
            self.draw_tooltip(self.button_tooltips["settings"])
        elif self.settings_clicked:
            if self.loop_button_hover:
                self.draw_tooltip(self.button_tooltips["loop"])
            elif self.gaussian_button_hover:
                self.draw_tooltip(self.button_tooltips["gaussian"])
            elif not self.is_linux and self.folder_button_hover:
                self.draw_tooltip(self.button_tooltips["folder"])
        elif self.edit_button_hover:
            self.draw_tooltip(self.button_tooltips["edit"])

    def rewrite_line(self, line, replacement, file):
        with open(file, "r", encoding="utf-8") as f:
            lines = f.readlines()
        replacement = replacement.replace("\x05", "")
        lines[line] = replacement.rstrip("\n") + "\n"
        with open(file, "w", encoding="utf-8") as f:
            f.writelines(lines)

    def delete_last_dp(self):
        tmp = pd.read_csv("data/feature_data.csv")
        tmp.iloc[:-1].to_csv("data/feature_data.csv", index=False, header=False)
        tmp = pd.read_csv("data/reward_data.csv")
        tmp.iloc[:-1].to_csv("data/reward_data.csv", index=False, header=False)

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

    def draw_button(self, rect, hover, pressed, image=None, label=None):
        if pressed:
            color = self.BUTTON_CLICKED_HOVER if hover else self.BUTTON_CLICKED
        else:
            color = self.BUTTON_HOVER if hover else self.BUTTON_NORMAL

        pygame.draw.rect(self.screen, color, rect, border_radius=int(border_radius_ratio*window_scale))

        if image:
            self.load_image(image, rect)
        elif label:
            label_surface = self.gaussian_font.render(label, True, self.BUTTON_TEXT)
            label_rect = label_surface.get_rect(center=rect.center)
            self.screen.blit(label_surface, label_rect)

    def draw_exploration_slider(self):
        self.draw_slider(
            self.exploration_slider_rect,
            self.exploration_factor,
            exploration_factor_min,
            exploration_factor_max,
            "Exploration",
            ["very low", "low", "normal", "high", "very high"],
            [0.5, 0.75, 1.0, 1.25, 1.5],
            align_left=True,
            label_offset=int(0.07 * window_scale),
        )

    def draw_timer_slider(self):
        self.draw_slider(
            self.timer_slider_rect,
            len_timer,
            len_timer_min,
            len_timer_max,
            "Timer",
            ["very slow", "slow", "normal", "fast", "very fast"],
            [0, 15, 30, 45, 60],
            align_left=True,
            label_offset=int(0.07 * window_scale),
        )

    def get_word_preview(self, word_index):
        word = self.all_l1[word_index]
        preview = word[:8]
        return f"{preview}.." if len(word) > 8 else preview

    def draw_slider(self, slider_rect, value, minimum, maximum, label, levels=None, snap_values=None, integer_value=False, value_text=None, align_left=False, label_offset=None):
        slider_ratio = 0.5 if maximum <= minimum else (value - minimum) / (maximum - minimum)
        handle_x = int(slider_rect.left + slider_ratio * slider_rect.width)
        slider_y = slider_rect.centery
        line_width = max(1, int(0.03 * window_scale))
        handle_radius = max(1, int(0.04 * window_scale))

        pygame.draw.line(self.screen, self.COORDINATE_SYSTEM, slider_rect.midleft, slider_rect.midright, line_width)
        if snap_values:
            for snap_value in snap_values:
                snap_ratio = (snap_value - minimum) / (maximum - minimum)
                snap_x = int(slider_rect.left + snap_ratio * slider_rect.width)
                pygame.draw.circle(self.screen, self.COORDINATE_SYSTEM, (snap_x, slider_y), max(1, int(0.03 * window_scale)))
        pygame.draw.circle(self.screen, self.COORDINATE_SYSTEM_GRAPH, (handle_x, slider_y), handle_radius)

        direction_font = self.gaussian_font
        minus_surface = direction_font.render("-", True, self.TEXT)
        plus_surface = direction_font.render("+", True, self.TEXT)
        self.screen.blit(minus_surface, minus_surface.get_rect(center=(slider_rect.left, slider_y)))
        self.screen.blit(plus_surface, plus_surface.get_rect(center=(slider_rect.right, slider_y)))

        if value_text is not None:
            display_value = value_text
        elif levels:
            display_value = self.get_slider_level(value, minimum, maximum, levels)
        elif integer_value:
            display_value = str(round(value))
        else:
            display_value = f"{value:.2f}"
        label_surface = self.gaussian_font.render(f"{label}: {display_value}", True, self.TEXT)
        label_y = slider_rect.bottom + (label_offset if label_offset is not None else int(0.02 * window_scale))
        if align_left:
            label_rect = label_surface.get_rect(midleft=(slider_rect.left, label_y))
        else:
            label_rect = label_surface.get_rect(midtop=(slider_rect.centerx, label_y))
        self.screen.blit(label_surface, label_rect)

    def get_slider_level(self, value, minimum, maximum, levels):
        level_width = (maximum - minimum) / len(levels)
        level_index = int((value - minimum) / level_width)
        level_index = max(0, min(level_index, len(levels) - 1))
        return levels[level_index]

    def draw_tooltip(self, text):
        if not text:
            return

        mouse_x, mouse_y = pygame.mouse.get_pos()
        max_width = int(self.WIDTH * 0.33)
        words = text.split()
        lines = []
        current_line = ""

        for word in words:
            candidate = f"{current_line} {word}".strip()
            if current_line and self.gaussian_font.size(candidate)[0] > max_width:
                lines.append(current_line)
                current_line = word
            else:
                current_line = candidate
        if current_line:
            lines.append(current_line)

        padding = int(0.04 * window_scale)
        line_height = self.gaussian_font.get_linesize()
        tooltip_width = max(self.gaussian_font.size(line)[0] for line in lines) + 2 * padding
        tooltip_height = len(lines) * line_height + 2 * padding
        tooltip_x = min(mouse_x + 12, self.WIDTH - tooltip_width - padding)
        tooltip_y = min(mouse_y + 12, self.HEIGHT - tooltip_height - padding)
        tooltip_rect = pygame.Rect(tooltip_x, tooltip_y, tooltip_width, tooltip_height)

        pygame.draw.rect(self.screen, self.LIGHT, tooltip_rect, border_radius=int(border_radius_ratio * window_scale))
        for line_number, line in enumerate(lines):
            line_surface = self.gaussian_font.render(line, True, self.BUTTON_TEXT)
            line_position = (tooltip_x + padding, tooltip_y + padding + line_number * line_height)
            self.screen.blit(line_surface, line_position)

    def load_image(self, image, rect):
        if image not in self.image_cache:
            img = pygame.image.load(f"img/{image}").convert_alpha()
            self.image_cache[image] = img
        else:
            img = self.image_cache[image]

        img_scaled = pygame.transform.smoothscale(img, (rect.width*3//4, rect.height*3//4))
        img_rect = img_scaled.get_rect(center=rect.center)
        self.screen.blit(img_scaled, img_rect)

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

        if print_validation:
            self.print_validation_reason(input, target_word, min_input_len, input_len, distances)

        return correct
    
    def filter(self, word):
        # replace all characters on list with space
        for c in ignore_characters:
            word = word.replace(c, " ")

        # replace every listed short form with its matching translation
        words = str(word).lower().split()
        short_form_translations = {
            form: translation
            for forms, translation in zip(short_form_list, short_form_translation)
            for form in forms
        }
        words = [short_form_translations.get(current_word, current_word) for current_word in words]

        return [x for x in words if x not in ignore_words]


    def init_data(self):
        # init collected data
        try:
            self.init_df_tensor()
            if self.n_words != len(self.df):
                # file doesnt have enough rows ( in case vocab was added later on )
                self.df_tensor_add_missing_rows()

        except Exception as _:
            # file doesnt exist
            self.df_tensor_add_missing_rows()

        # init stats for log_and_normalize
        try:
            self.init_stats()

        except Exception as _:
            #file doesnt exist
            init_stats = np.zeros((len(ai_input_columns), 2))
            self.save_stats(init_stats)

    def save_stats(self, stats):
        pd.DataFrame(stats).to_csv(f"data/normalization_stats.csv", mode="w", index=False, header=False)
        self.normalization_stats = stats

    def init_stats(self):
        self.normalization_stats = pd.read_csv(f"data/normalization_stats.csv", header=None).values

    def df_tensor_add_missing_rows(self):
        header = feature_columns if len(self.df) == 0 else False
        rows = pd.DataFrame([[0.0]*len(feature_columns) for _ in range(self.n_words-len(self.df))])
        pd.DataFrame(rows).to_csv(f"sets/{self.folder}/data.csv", mode="a", index=False, header=header)
        self.init_df_tensor()

    def init_df_tensor(self):
        df = pd.read_csv(f"sets/{self.folder}/data.csv", header=0)
        last_word_index = word_cap if word_cap > 0 else self.total_words - 1
        df = df.iloc[starting_cap:last_word_index + 1].reset_index(drop=True)
        # reset occurrences in session and save as self.df
        self.df = self.set_row_val(df, 0, 0.0)
        # also reset session ema
        self.df = self.set_row_val(df, 11, 0)

    def set_row_val(self, df: pd.DataFrame, col, val):
        df.iloc[:, col] = val
        if not isinstance(col, pd.DataFrame):
            df = pd.DataFrame(df)
        return df
    
    def word_distance(self, s1, s2):
        # levensthein word distance
        len1, len2 = len(s1), len(s2)
        dp = [[0] * (len2 + 1) for _ in range(len1 + 1)]
        for i in range(len1 + 1): dp[i][0] = i
        for j in range(len2 + 1): dp[0][j] = j
        for i in range(1, len1 + 1):
            for j in range(1, len2 + 1):
                dp[i][j] = dp[i-1][j-1] if s1[i-1] == s2[j-1] else 1 + min(dp[i-1][j-1], dp[i-1][j], dp[i][j-1])
        return dp[len1][len2]

    def gauss_distribution(self):
        global sigma_factor
        global min_gauss_weights
        global focused_area
        # get a gauss distribution across the units that will be weight for the ai
        upper_distance = self.n_words - 1 - focused_area
        # the parameter sigma is calculated based upon the distance to the first or last unit with respect to the chosen factor
        sigma = (max(focused_area, upper_distance) / 3) * sigma_factor

        weights = []
        for i in range(self.n_words):
            val = math.exp(-0.5*((i - focused_area)/sigma)**2) * (1 - min_gauss_weights) + min_gauss_weights
            weights.append(val)
        return weights

    
# run main
if __name__ == "__main__":
    application = SRS()
    application.run()
    
