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
import random
from datetime import datetime

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"


# TODO change gaussian range!!!

# TODO rethink ai logic. what to predict? lower probability due to time?
# TODO datensatz editor
# TODO mixed translation probability by avrg certainty

# parameters for dev
    #print
print_everything = False
print_nothing = False    
print_data_tensor = True # saved data tensor after word input
print_validation = True # explain systems choice to validate or invalidate users input
print_normalized_df = True # complete data for nn
print_exploration_chance = True
print_exploration_validation = True
    #gui
window_scale = 200
button_scale = 2.5 #divides through button scale
width_ratio = 6
height_ratio = 3 
font_word_ratio = 0.3
font_input_ratio = 0.2
border_radius_ratio = 0.05 
gaussian_font_ratio = 0.1
axis_padding_ratio = 0.05
button_padding = 0.43
first_button_padding = 0.05
button_img_scale = 0.8
    #logic
should_save = True
word_cap = 0 # 0 means no cap. cant be bigger than n_words.
starting_cap = 0 # first word index that may be shown
len_timer = 45
len_timer_min = 0
len_timer_max = 90
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
ignore_words = ["der", "die", "das", # german articles
                "el", "la"] # spanish articles


class OutputTee:

    def __init__(self, terminal_stream, log_file):
        self.terminal_stream = terminal_stream
        self.log_file = log_file

    def write(self, text):
        self.terminal_stream.write(text)
        self.log_file.write(text)

    def flush(self):
        self.terminal_stream.flush()
        self.log_file.flush()


class SRS:

    def __init__(self):
        log_directory = "data/log"
        os.makedirs(log_directory, exist_ok=True)
        log_filename = datetime.now().strftime("session_%Y-%m-%d_%H-%M-%S.log")
        self.log_file = open(os.path.join(log_directory, log_filename), "w", encoding="utf-8")
        sys.stdout = OutputTee(sys.stdout, self.log_file)
        sys.stderr = OutputTee(sys.stderr, self.log_file)
        self.set_print_statements()
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
        self.settings_timer_state = "stopped"
        self.settings_timer_remaining = 0.0
        self.settings_timer_end_time = 0.0
        self.settings_timer_duration = 0.0
        self.settings_timer_ended_at = 0.0
        self.timer_reveal_started_at = 0.0
        self.timer_halfway_announced = False
        self.timer_one_minute_announced = False
        self.settings_closed_time = 0.0
        self.new_index_time = 0
        self.starting_time = 0
        self.inactive_ticks = 0

            # text input
        self.check_typing_start = True
        self.typing_start = 0
        self.input_text = ""
        self.pause_triggered = False
        self.pause_message = ""
        self.has_shown_initial_pause_message = False
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
        self.ui_languages = ("en", "de")
        self.ui_language_index = 0
        self.ui_language = self.ui_languages[self.ui_language_index]
        self.translation_mode = 0  # 0=normal (l1->l2), 1=mixed, 2=reverse (l2->l1)
        self.translation_mode_labels = ("→", "⇄", "←")

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
        self.init_set_config()
        self.init_folder()
        self.init_data()

        self.trigger_pause()

    def set_print_statements(self):
        global print_data_tensor, print_validation, print_normalized_df
        global print_exploration_chance, print_exploration_validation

        if print_everything or print_nothing:
            enabled = print_everything
            (
                print_data_tensor,
                print_validation,
                print_normalized_df,
                print_exploration_chance,
                print_exploration_validation,
            ) = (enabled,) * 5


    def delete_row(self, row_index):
        if not 0 <= row_index < self.n_words:
            print(f"Error: row_index {row_index} out of range")
            return None

        deleted_word = self.l2[row_index]
        file_row_index = self.get_file_row_index(row_index)
        data_path = f"sets/{self.folder}/data.csv"
        language_paths = [
            f"sets/{self.folder}/language1.csv",
            f"sets/{self.folder}/language2.csv",
        ]

        with open(data_path, "r", encoding="utf-8") as file:
            data_lines = file.readlines()
        language_lines = []
        for path in language_paths:
            with open(path, "r", encoding="utf-8") as file:
                language_lines.append(file.readlines())

        if (
            file_row_index + 1 >= len(data_lines)
            or any(file_row_index >= len(lines) for lines in language_lines)
        ):
            print(f"Error: row_index {file_row_index} out of range in dataset")
            return None

        del data_lines[file_row_index + 1]
        for lines in language_lines:
            del lines[file_row_index]

        with open(data_path, "w", encoding="utf-8") as file:
            file.writelines(data_lines)
        for path, lines in zip(language_paths, language_lines):
            with open(path, "w", encoding="utf-8") as file:
                file.writelines(lines)

        # Keep in-memory data in sync
        if row_index < len(self.df):
            self.df = self.df.drop(index=row_index).reset_index(drop=True)
        if row_index < len(self.l1):
            del self.l1[row_index]
        if row_index < len(self.l2):
            del self.l2[row_index]

        self.n_words = len(self.l1)
        return deleted_word

    def get_file_row_index(self, row_index):
        return starting_cap + row_index

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
        global starting_cap
        global word_cap
        global len_timer

        config_dir = f"sets/{self.folder}/config"
        os.makedirs(config_dir, exist_ok=True)

        def load_config_value(filename, value_type, default):
            path = os.path.join(config_dir, filename)
            try:
                with open(path, "r", encoding="utf-8") as file:
                    return value_type(file.readline().strip())
            except (FileNotFoundError, ValueError):
                with open(path, "w", encoding="utf-8") as file:
                    file.write(f"{default}\n")
                return default

        min_gauss_weights = load_config_value("min_gauss_weights.csv", float, std_min_gauss_weights)
        focused_area = load_config_value("focused_area.csv", float, std_focused_area)
        sigma_factor = load_config_value("sigma_factor.csv", float, std_sigma_factor)
        starting_cap = load_config_value("starting_cap.csv", int, starting_cap)
        word_cap = load_config_value("word_cap.csv", int, word_cap)
        len_timer = load_config_value("len_timer.csv", int, len_timer)
        self.exploration_factor = load_config_value("exploration_factor.csv", float, self.exploration_factor)
        self.translation_mode = load_config_value("translation_mode.csv", int, self.translation_mode)

    def save_set_config_value(self, filename, value):
        config_dir = f"sets/{self.folder}/config"
        os.makedirs(config_dir, exist_ok=True)
        with open(os.path.join(config_dir, filename), "w", encoding="utf-8") as file:
            file.write(f"{value}\n")

    def init_user_data_info(self):
        os.makedirs("user_data", exist_ok=True)
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
            pass

        try:
            with open("user_data/language_index.csv", "r", encoding="utf-8") as f:
                self.ui_language_index = int(f.readline().strip()) % len(self.ui_languages)
        except (FileNotFoundError, ValueError):
            self.save_ui_language()
        self.ui_language = self.ui_languages[self.ui_language_index]

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
            if hasattr(self, 'translation_mode'):
                self.apply_translation_mode()

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
        self.help_font = pygame.font.SysFont("calibri", int(0.21 * window_scale), bold=False)
        self.language_font = pygame.font.SysFont("calibri", int(0.13 * window_scale), bold=False)
        self.translation_mode_font = pygame.font.SysFont("calibri", int(0.2 * window_scale), bold=False)

        # Buttons in order

        sidebar_button_count = 7
        button_gap = self.HEIGHT // 50
        button_height = (self.HEIGHT - (sidebar_button_count + 1) * button_gap) // sidebar_button_count
        button_width = button_height
        button_left = button_gap
        button_top = button_gap
        button_step = button_height + button_gap
        self.settings_button = pygame.Rect(button_left, button_top, button_width, button_height)
        self.edit_button = pygame.Rect(button_left + button_step, button_top, button_width, button_height)
        self.gaussian_button = pygame.Rect(button_left, button_top + button_step, button_width, button_height)
        self.loop_button = pygame.Rect(button_left, button_top + 2 * button_step, button_width, button_height)
        self.translation_mode_button = pygame.Rect(button_left, button_top + 3 * button_step, button_width, button_height)
        self.folder_button = pygame.Rect(button_left, button_top + 4 * button_step, button_width, button_height)
        self.language_button = pygame.Rect(button_left, button_top + 5 * button_step, button_width, button_height)
        coordinate_system_width = self.WIDTH * 7 // 10
        coordinate_system_height = self.HEIGHT * 7 // 10
        self.coordinate_system_rect = pygame.Rect(
            (self.WIDTH - coordinate_system_width) // 2,
            self.HEIGHT // 5 + 15,
            coordinate_system_width,
            coordinate_system_height,
        )
        slider_gap = int(0.04 * window_scale)
        slider_width = self.WIDTH // 6
        slider_height = int(0.1 * window_scale)
        slider_column_gap = int(0.225 * window_scale) + 25
        middle_slider_left = (self.WIDTH - slider_width) // 2
        left_slider_left = middle_slider_left - slider_width - slider_column_gap
        right_slider_left = middle_slider_left + slider_width + slider_column_gap
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
        self.word_cap_slider_rect = pygame.Rect(
            right_slider_left,
            self.timer_slider_rect.top,
            slider_width,
            slider_height,
        )
        timer_button_gap = int(0.04 * window_scale)
        timer_button_width = (slider_width - timer_button_gap) // 2
        self.cancel_button = pygame.Rect(
            self.timer_min_slider_rect.left,
            self.timer_slider_rect.top,
            timer_button_width,
            slider_height * 2,
        )
        self.start_button = pygame.Rect(
            self.cancel_button.right + timer_button_gap,
            self.timer_slider_rect.top,
            timer_button_width,
            slider_height * 2,
        )
        self.help_button = pygame.Rect(
            button_left,
            button_top + 6 * button_step,
            button_width,
            button_height,
        )
        self.shortcut_overlay_rect = pygame.Rect(
            self.WIDTH // 2 - int(1.4 * window_scale),
            self.HEIGHT // 2 - int(0.95 * window_scale),
            int(2.8 * window_scale),
            int(1.9 * window_scale),
        )

        # colors
        self.DARK = "#0D0E29"
        self.LIGHT = "#CBCCF7"
        self.BLUE = "#57CFC9"
        self.GREEN = "#2CD42C"
        self.RED = "#D42C2C"
        self.BACKGROUND = self.DARK
        self.TEXT = self.LIGHT
        self.BUTTON_NORMAL = self.DARK      # normal
        self.BUTTON_HOVER = "#393B6B"      # hover
        self.BUTTON_CLICKED = "#7A7DBB"     # clicked
        self.BUTTON_CLICKED_HOVER = "#9094EC"  # clicked + hover
        self.BUTTON_TEXT = "#130C1D"
        self.COORDINATE_SYSTEM = "#1D3873"
        self.COORDINATE_SYSTEM_GRAPH = "#0DE5F0"
        self.SLIDER_HANDLE = "#7A7DBB"
        self.GRID_COLOR = "#14264F"
        self.TIMER_START_BORDER = "#28734B"
        self.TIMER_STOP_BORDER = "#8A3B3B"

        # tooltip settings
        self.active_tooltip_text = None
        self.tooltip_position = None
        self.shortcuts_visible = False
        self.tooltip_alpha = 0
        self.tooltip_fade_speed = 28
        self.tooltip_delay_ms = 500
        self.tooltip_timer = 0
        self.tooltip_mouse_pos = None
        self.tooltip_stationary_ms = 0
        self.coordinate_system_line_thickness = 2
        self.button_tooltips = {
            "settings": ("Open/Close settings", "Einstellungen öffnen/schließen"),
            "help": ("Show keyboard shortcuts", "Tastenkürzel anzeigen"),
            "language": ("Switch interface language", "Oberflächensprache wechseln"),
            "loop": ("Ignore AI and loop through all words in order", "KI ignorieren und Wörter der Reihe nach lernen"),
            "gaussian": ("Let selected gaussian curve affect AI", "Gewählte Gaußkurve für die KI verwenden"),
            "edit": ("Edit last word", "Letztes Wort bearbeiten"),
            "folder": ("Change dataset", "Datensatz wechseln"),
            "translation_mode": ("Switch translation direction: normal / mixed / reverse", "Übersetzungsrichtung wechseln: normal / gemischt / umgekehrt"),
            "start": ("Start a timer", "Timer starten"),
        }

        self.clock = pygame.time.Clock()

    def get_button_x(self, num=None):
        if num:
            return (num - 1)*button_padding + first_button_padding
        else:
            self.next_button_index += 1
            return (self.next_button_index - 1)*button_padding + first_button_padding

    def get_ui_text(self, english, german):
        return german if self.ui_language == "de" else english

    def get_button_tooltip(self, button_name):
        return self.button_tooltips[button_name][1 if self.ui_language == "de" else 0]

    def save_ui_language(self):
        with open("user_data/language_index.csv", "w", encoding="utf-8") as file:
            file.write(f"{self.ui_language_index}\n")

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
        if mouse_pos == self.tooltip_mouse_pos:
            self.tooltip_stationary_ms += self.clock.get_time()
        else:
            self.tooltip_mouse_pos = mouse_pos
            self.tooltip_stationary_ms = 0
        self.settings_button_hover = self.settings_button.collidepoint(mouse_pos)
        self.folder_button_hover = self.folder_button.collidepoint(mouse_pos)
        self.translation_mode_button_hover = self.translation_mode_button.collidepoint(mouse_pos)
        self.edit_button_hover = self.edit_button.collidepoint(mouse_pos)
        self.loop_button_hover = self.loop_button.collidepoint(mouse_pos)
        self.gaussian_button_hover = self.gaussian_button.collidepoint(mouse_pos)
        self.exploration_slider_hover = self.exploration_slider_rect.collidepoint(mouse_pos)
        self.timer_slider_hover = self.timer_slider_rect.collidepoint(mouse_pos)
        self.timer_min_slider_hover = self.timer_min_slider_rect.collidepoint(mouse_pos)
        self.start_button_hover = self.start_button.collidepoint(mouse_pos)
        self.cancel_button_hover = self.cancel_button.collidepoint(mouse_pos)
        self.help_button_hover = self.help_button.collidepoint(mouse_pos)
        self.language_button_hover = self.language_button.collidepoint(mouse_pos)
        self.starting_cap_slider_hover = self.starting_cap_slider_rect.collidepoint(mouse_pos)
        self.word_cap_slider_hover = self.word_cap_slider_rect.collidepoint(mouse_pos)
        self.coordinate_system_hover = mouse_pos if self.coordinate_system_rect.collidepoint(mouse_pos) else None

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE and self.shortcuts_visible:
                    self.shortcuts_visible = False
                    continue

                if self.shortcuts_visible:
                    continue

                if self.timer_running:
                    continue

                if event.key == pygame.K_LCTRL:
                    self.ctrl_hold = True

                elif self.ctrl_hold:
                    if event.key == pygame.K_f:
                        self.trigger_folder_button()
                    elif event.key == pygame.K_g:
                        self.trigger_settings_button()
                    elif event.key == pygame.K_e:
                        self.trigger_edit_button()
                    elif event.key == pygame.K_l:
                        self.trigger_loop_button()
                    elif event.key == pygame.K_d:
                        if self.last_index != -1:
                            deleted_word = self.delete_row(self.last_index)
                            self.last_index = -1
                            if deleted_word is not None:
                                print(f"..deleted word {deleted_word}..")
                    elif event.key == pygame.K_t:
                        self.trigger_gaussian_button()
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
                                    self.rewrite_line(self.get_file_row_index(self.last_index), self.input_text, f"sets/{self.folder}/language1.csv")
                                    self.input_text = self.target[self.last_index]
                                    self.editing_step = 2
                                elif self.editing_step == 2:
                                    self.rewrite_line(self.get_file_row_index(self.last_index), self.input_text, f"sets/{self.folder}/language2.csv")
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
                if self.help_button_hover:
                    self.shortcuts_visible = not self.shortcuts_visible
                elif self.shortcuts_visible:
                    if not self.shortcut_overlay_rect.collidepoint(mouse_pos):
                        self.shortcuts_visible = False
                elif self.settings_button_hover and not self.editing_step:
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
                    if self.settings_timer_state != "stopped":
                        self.stop_timer()
                    self.timer_min_slider_active = True
                    self.update_timer_min_slider(mouse_pos[0])

                elif self.settings_clicked and self.cancel_button_hover:
                    self.stop_timer()

                elif self.settings_clicked and self.start_button_hover:
                    self.handle_start_button_click()

                elif self.settings_clicked and self.starting_cap_slider_hover:
                    self.starting_cap_slider_active = True
                    self.update_starting_cap_slider(mouse_pos[0])

                elif self.settings_clicked and self.word_cap_slider_hover:
                    self.word_cap_slider_active = True
                    self.update_word_cap_slider(mouse_pos[0])

                elif self.settings_clicked and self.folder_button_hover and not self.is_linux:
                    self.trigger_folder_button()

                elif self.settings_clicked and self.translation_mode_button_hover:
                    self.trigger_translation_mode_button()

                elif self.settings_clicked and self.language_button_hover:
                    self.ui_language_index = (self.ui_language_index + 1) % len(self.ui_languages)
                    self.ui_language = self.ui_languages[self.ui_language_index]
                    self.save_ui_language()

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
                    self.save_set_config_value("exploration_factor.csv", self.exploration_factor)
                if self.timer_slider_active:
                    self.timer_value = self.snap_slider_value(
                        self.timer_value,
                        len_timer_min,
                        len_timer_max,
                        [0, 22.5, 45, 67.5, 90],
                    )
                    len_timer = round(self.timer_value)
                    self.save_set_config_value("len_timer.csv", len_timer)
                if self.timer_min_slider_active:
                    global min_timer
                    min_timer = self.round_to_nearest_step(self.min_timer_value, 5)
                self.exploration_slider_active = False
                self.timer_slider_active = False
                self.timer_min_slider_active = False
                caps_changed = self.starting_cap_slider_active or self.word_cap_slider_active
                if self.starting_cap_slider_active:
                    self.save_set_config_value("starting_cap.csv", starting_cap)
                if self.word_cap_slider_active:
                    self.save_set_config_value("word_cap.csv", word_cap)
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
        if self.inactive_ticks > max_inactive_ticks and not self.pause_triggered:
            self.trigger_pause()

    def trigger_folder_button(self):
        self.prompt_folder()
        self.trigger_pause()

    def trigger_translation_mode_button(self):
        self.translation_mode = (self.translation_mode + 1) % 3
        self.apply_translation_mode()
        self.save_set_config_value("translation_mode.csv", self.translation_mode)
        self.trigger_pause()
        if self.translation_mode == 2 and set(self.l1).intersection(self.l2):
            self.pause_message = self.get_ui_text(
                "Warning: identical phrases exist in both languages",
                "Warnung: Es gibt gleiche Phrasen in beiden Sprachen",
            )

    def apply_translation_mode(self):
        if self.translation_mode == 0:  # normal: l1 -> l2
            self.source = self.l1
            self.target = self.l2
        elif self.translation_mode == 2:  # reverse: l2 -> l1
            self.source = self.l2
            self.target = self.l1
        # mode 1 (mixed) is handled per-word in get_new_index

    def trigger_settings_button(self):
        if self.settings_clicked:
            self.settings_clicked = False
            self.settings_closed_time = time.time()
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

    def update_slider(self, slider_rect, minimum, maximum, mouse_x, snap_values=None, reverse=False):
        slider_left = slider_rect.left
        slider_right = slider_rect.right
        if maximum <= minimum:
            return minimum
        slider_ratio = (mouse_x - slider_left) / (slider_right - slider_left)
        slider_ratio = max(0.0, min(1.0, slider_ratio))
        if reverse:
            slider_ratio = 1.0 - slider_ratio
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
            reverse=True,
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
        global min_timer
        min_timer = self.round_to_nearest_step(self.min_timer_value, 5)

    def round_to_nearest_step(self, value, step):
        rounded = int(round(value / step) * step)
        return max(min_timer_min, min(min_timer_max, rounded))

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
        self.pause_message = self.get_pause_message()

    def get_pause_message(self):
        if not self.has_shown_initial_pause_message:
            self.has_shown_initial_pause_message = True
            return self.get_ui_text("Press any key to proceed..", "Beliebige Taste drücken, um fortzufahren..")

        # add phrases for every language
        messages = {
            "en": [
                "Use the keyboard to get started",
                "Make a move to begin",
                "Ready when you are. Start typing",
                "Press a key and let us go",
                "Your next word is waiting",
                "Time to put the keyboard to work",
                "Start whenever you are ready",
                "One key is all it takes",
                "A small step starts the session",
                "Type your way into the next round",
            ],
            "de": [
                "Tastatur bedienen, um loszulegen",
                "Mach was, damit es losgehen kann",
                "Bereit? Fang an zu tippen",
                "Drücke eine Taste und weiter geht's",
                "Dein nächstes Wort wartet schon",
                "Zeit, die Tastatur einzusetzen",
                "Starte, sobald du bereit bist",
                "Eine Taste genügt",
                "Ein kleiner Schritt startet die Runde",
                "Tipp dich in die nächste Runde",
            ],
        }
        return random.choice(messages[self.ui_language])

    def handle_start_button_click(self):
        if self.settings_timer_state == "stopped":
            self.settings_timer_state = "running"
            self.settings_timer_remaining = float(min_timer * 60)
            self.settings_timer_duration = self.settings_timer_remaining
            self.settings_timer_end_time = time.time() + self.settings_timer_remaining
            self.timer_halfway_announced = False
            self.timer_one_minute_announced = False
            self.input_text = ""
            self.pause_triggered = False
        elif self.settings_timer_state == "running":
            self.settings_timer_state = "paused"
            self.settings_timer_remaining = max(0.0, self.settings_timer_end_time - time.time())
        elif self.settings_timer_state == "paused":
            self.settings_timer_state = "running"
            self.settings_timer_end_time = time.time() + self.settings_timer_remaining

    def stop_timer(self):
        self.settings_timer_state = "stopped"
        self.settings_timer_remaining = 0.0
        self.settings_timer_end_time = 0.0
        self.settings_timer_duration = 0.0
        self.settings_timer_ended_at = 0.0
        self.timer_reveal_started_at = 0.0
        self.timer_halfway_announced = False
        self.timer_one_minute_announced = False

    def get_remaining_timer_seconds(self):
        if self.settings_timer_state == "running":
            return max(0, int(self.settings_timer_end_time - time.time()))
        elif self.settings_timer_state == "paused":
            return max(0, int(self.settings_timer_remaining))
        else:
            return max(0, int(min_timer * 60))

    def get_timer_display_text(self):
        remaining_seconds = self.get_remaining_timer_seconds()
        minutes, seconds = divmod(remaining_seconds, 60)
        return f"{minutes:02d}:{seconds:02d}"

    def check_input(self): 
        correct = self.is_correct()
        self.increment_index()

        if correct == 1:
            self.TEXT = self.GREEN
        else:
            self.TEXT = self.RED

        self.save_data(correct)

        self.timer_running = True
        self.ticks = len_timer if correct == 1 else len_timer * 2
        self.input_text = ""

    def increment_index(self):
        self.index += 1
        with open("user_data/index.csv", "w", encoding="utf-8") as f:
            f.write(str(self.index) + "\n")

    def save_data(self, correct):

        # get old word data
        word_data = self.df.iloc[self.current_index] # currently saved data

        # Save only after the first answer has established a valid last_seen interval.
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

            #save new word_data tensor
            word_data.iloc[0] += 1.0 # occurrences in session (will be reset on new session)
            word_data.iloc[1] = time_since_last_seen # last seen (in hours)
            word_data.iloc[2] = float(self.index - word_data.iloc[8]) # last seen index
            word_data.iloc[3] += 1.0 # n reps
            word_data.iloc[4] = new_ema # exponentially moving average of accuracy
            word_data.iloc[5] = correct_score  
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

            data_path = f"sets/{self.folder}/data.csv"
            all_word_data = pd.read_csv(data_path, header=0)
            first_file_row = self.get_file_row_index(0)
            last_file_row = first_file_row + len(self.df)
            all_word_data.iloc[first_file_row:last_file_row] = self.df.to_numpy()
            all_word_data.to_csv(data_path, mode="w", index=False, header=feature_columns)
            
            if usable_for_ai:
                # save score resulting from old data
                pd.DataFrame([correct_score]).to_csv("data/reward_data.csv", mode="a", index=False, header=False)

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
        exploitation_count_before_pause = self.exploitation_count
        if self.current_index != -1:
            self.last_index = self.current_index

        # get new index
        if not self.ignore_ai:

            selection_weights = self.gauss_distribution() if self.use_gaussian else np.ones(self.n_words)
            explored_mask = self.df.iloc[:, 3] != 0


            # determine whether to exploit or explore
            if sum(explored_mask) == self.n_words or not self.should_explore():
                self.exploitation_count += 1
                self.word_vals = np.random.rand(self.n_words) * selection_weights #! change
                masked_vals = np.where(explored_mask, self.word_vals, 0.0)
                self.current_index = self.get_random_from_probability(self.get_probablity(masked_vals))

            else:
                self.exploitation_count = 0
                self.word_vals = np.random.rand(self.n_words) * selection_weights
                masked_vals = np.where(explored_mask == 0, self.word_vals, 0)
                self.current_index = self.get_random_from_probability(self.get_probablity(masked_vals))

                        
            if self.pause_triggered:
                self.exploitation_count = exploitation_count_before_pause

        else:
            #mode to just loop through all words
            self.current_index = self.index % self.n_words # ignore ai and go through words in order
        self.new_index_time = time.time()
        self.check_typing_start = True

        # for mixed mode, randomly swap direction per word
        if self.translation_mode == 1:
            if random.random() < 0.5:
                self.source = self.l1
                self.target = self.l2
            else:
                self.source = self.l2
                self.target = self.l1

    def get_probablity(self, x):
        weights = np.asarray(x, dtype=float)
        total_weight = weights.sum()
        if total_weight <= 0:
            raise ValueError("No eligible words available for selection")
        return weights / total_weight

    def get_random_from_probability(self, probability):
        return int(np.searchsorted(np.cumsum(probability), np.random.random(), side="right"))


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
                display_word = f"{self.get_ui_text('Edit source', 'Quelle bearbeiten')}: {self.source[self.last_index]}"
            elif self.editing_step == 2:
                display_word = f"{self.get_ui_text('Edit target', 'Ziel bearbeiten')}: {self.target[self.last_index]}"
            else:
                if self.pause_triggered:
                    display_word = self.pause_message
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
        settings_button_alpha = 255
        if not self.settings_clicked and self.settings_timer_state in ("running", "paused", "ended"):
            settings_button_alpha = self.get_timer_visibility_alpha(self.settings_button, self.get_remaining_timer_seconds(), y_scale=1)
        self.draw_button(self.settings_button, self.settings_button_hover, self.settings_clicked, image="settings_button.png", alpha=settings_button_alpha)

        if not self.settings_clicked and self.last_index != -1:
            # edit prev word
            edit_button_alpha = 255
            if self.settings_timer_state in ("running", "paused", "ended"):
                edit_button_alpha = self.get_timer_visibility_alpha(self.edit_button, self.get_remaining_timer_seconds(), y_scale=1)
            self.draw_button(self.edit_button, self.edit_button_hover, False, image="edit_button.png", alpha=edit_button_alpha)
        elif self.settings_clicked:
            self.draw_button(self.help_button, self.help_button_hover, self.shortcuts_visible, label="?", font=self.help_font, label_color="#FFFFFF")
            # use Gaussian weights for the next word selection
            self.draw_button(self.gaussian_button, self.gaussian_button_hover, self.use_gaussian, image="gauss_button.png")

            # loop through words
            self.draw_button(self.loop_button, self.loop_button_hover, self.ignore_ai, image="loop_button.png")

            # translation mode (normal/mixed/reverse)
            mode_active = self.translation_mode != 0
            self.draw_button(self.translation_mode_button, self.translation_mode_button_hover, mode_active, label=self.translation_mode_labels[self.translation_mode], font=self.translation_mode_font, label_color="#FFFFFF")

            # select other folder
            self.draw_button(self.folder_button,  self.folder_button_hover, False, image="folder_button.png")
            self.draw_button(self.language_button, self.language_button_hover, False, label=self.ui_language.upper(), font=self.language_font, label_color="#FFFFFF")

        #* draw sliders
        if self.settings_clicked:
            is_timer_active = self.settings_timer_state in ("running", "paused")
            timer_label = "            " if is_timer_active else self.get_ui_text("Set timer", "    Timer einstellen")
            self.draw_slider(
                self.timer_min_slider_rect,
                min_timer,
                min_timer_min,
                min_timer_max,
                timer_label,
                integer_value=not is_timer_active,
                value_text=self.get_timer_display_text() if is_timer_active else None,
                snap_values=[5, 10, 15, 20, 25, 30],
                align_left=True,
                label_offset=int(0.07 * window_scale),
            )
            self.draw_slider(
                self.starting_cap_slider_rect,
                starting_cap,
                0,
                max(0, (word_cap if word_cap > 0 else self.total_words - 1) - 2),
                self.get_ui_text("First word", "Erstes Wort"),
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
                self.get_ui_text("Last word", "Letztes Wort"),
                value_text=f"({word_cap if word_cap > 0 else self.total_words - 1}) {self.get_word_preview(word_cap if word_cap > 0 else self.total_words - 1)}",
                integer_value=True,
                align_left=True,
                label_offset=int(0.07 * window_scale),
            )
            self.draw_exploration_slider()
            self.draw_timer_slider()
            cancel_border_color = self.TIMER_STOP_BORDER if is_timer_active else self.COORDINATE_SYSTEM
            self.draw_button(self.cancel_button, self.cancel_button_hover, False, image="stop_button.png", border=True, border_color=cancel_border_color, img_scale=1)
            if self.settings_timer_state == "running":
                button_image = "pause_button.png"
                start_border_color = self.BLUE
            else:
                button_image = "start_button.png"
                start_border_color = self.TIMER_START_BORDER
            self.draw_button(self.start_button, self.start_button_hover, False, image=button_image, border=True, border_color=start_border_color, img_scale=1)

        #* draw hovering messages after:
        hovered_tooltip = None
        slider_tooltip = None
        if self.settings_button_hover:
            hovered_tooltip = self.get_button_tooltip("settings")
        elif self.settings_clicked:
            if self.help_button_hover:
                hovered_tooltip = self.get_button_tooltip("help")
            elif self.language_button_hover:
                hovered_tooltip = self.get_button_tooltip("language")
            elif self.cancel_button_hover:
                hovered_tooltip = self.get_ui_text("Cancel timer", "Timer abbrechen")
            elif self.start_button_hover:
                if self.settings_timer_state == "running":
                    hovered_tooltip = self.get_ui_text("Pause timer", "Timer pausieren")
                elif self.settings_timer_state == "paused":
                    hovered_tooltip = self.get_ui_text("Resume timer", "Timer fortsetzen")
                else:
                    hovered_tooltip = self.get_button_tooltip("start")
            elif self.loop_button_hover:
                hovered_tooltip = self.get_button_tooltip("loop")
            elif self.gaussian_button_hover:
                hovered_tooltip = self.get_button_tooltip("gaussian")
            elif self.folder_button_hover:
                hovered_tooltip = self.get_button_tooltip("folder")
            elif self.translation_mode_button_hover:
                hovered_tooltip = self.get_button_tooltip("translation_mode")
            elif self.timer_min_slider_hover:
                slider_tooltip = self.get_ui_text("Set the timer duration", "Timerdauer einstellen")
            elif self.timer_slider_hover:
                slider_tooltip = self.get_ui_text("Set how long the answer remains on screen", "Anzeigedauer der Antwort einstellen")
            elif self.exploration_slider_hover:
                slider_tooltip = self.get_ui_text("Adjust the probability to explore unseen words", "Wahrscheinlichkeit für unbekannte Wörter anpassen")
            elif self.starting_cap_slider_hover:
                slider_tooltip = self.get_ui_text("Choose the first word in the learning range", "Erstes Wort des Lernbereichs wählen")
            elif self.word_cap_slider_hover:
                slider_tooltip = self.get_ui_text("Choose the last word in the learning range", "Letztes Wort des Lernbereichs wählen")
        elif self.last_index != -1 and self.edit_button_hover:
            hovered_tooltip = self.get_button_tooltip("edit")

        if slider_tooltip is not None and self.tooltip_stationary_ms >= self.tooltip_delay_ms:
            hovered_tooltip = slider_tooltip

        if hovered_tooltip is not None:
            if self.active_tooltip_text != hovered_tooltip:
                self.active_tooltip_text = hovered_tooltip
                self.tooltip_position = None
                self.tooltip_timer = 0
                self.tooltip_alpha = 0

            self.tooltip_timer += self.clock.get_time()
            if self.tooltip_timer >= self.tooltip_delay_ms:
                self.tooltip_alpha = min(255, self.tooltip_alpha + self.tooltip_fade_speed)
        elif self.active_tooltip_text is not None:
            self.tooltip_timer = 0
            self.tooltip_alpha = max(0, self.tooltip_alpha - self.tooltip_fade_speed)
            if self.tooltip_alpha == 0:
                self.active_tooltip_text = None
                self.tooltip_position = None

        if self.active_tooltip_text is not None and self.tooltip_alpha > 0:
            self.draw_tooltip(self.active_tooltip_text, self.tooltip_alpha)

        if not self.settings_clicked and self.settings_timer_state in ("running", "paused", "ended"):
            remaining = self.get_remaining_timer_seconds()
            if remaining <= 0 and self.settings_timer_state == "running":
                self.settings_timer_state = "ended"
                self.settings_timer_ended_at = time.time()
                self.settings_timer_remaining = 0.0
                self.settings_timer_end_time = 0.0
            elif self.settings_timer_state == "ended" and time.time() - self.settings_timer_ended_at >= 5.0:
                self.stop_timer()
            else:
                timer_font = pygame.font.Font(pygame.font.get_default_font(), max(56, int(0.18 * window_scale)))
                timer_text = self.get_ui_text("Timer ended", "Timer beendet") if self.settings_timer_state == "ended" else self.get_timer_display_text()
                timer_surface = timer_font.render(timer_text, True, self.TEXT)
                timer_rect = timer_surface.get_rect(center=(self.WIDTH // 2, self.HEIGHT * 3 // 16))
                time_outside = time.time() - self.settings_closed_time
                if time_outside < 1.0:
                    base_alpha = 255
                else:
                    fade_time = time_outside - 1.0
                    base_alpha = max(0, int(255 - fade_time * 200))

                if self.settings_timer_state == "running" and remaining <= self.settings_timer_duration / 2 and not self.timer_halfway_announced:
                    self.timer_halfway_announced = True
                    self.timer_reveal_started_at = time.time()
                if self.settings_timer_state == "running" and remaining <= 60 and not self.timer_one_minute_announced:
                    self.timer_one_minute_announced = True
                    self.timer_reveal_started_at = time.time()

                alpha = self.get_timer_visibility_alpha(timer_rect, remaining, base_alpha)
                if alpha > 0:
                    timer_surface.set_alpha(alpha)
                    self.screen.blit(timer_surface, timer_rect)

        if self.shortcuts_visible:
            self.draw_shortcut_overlay()

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

    def get_timer_visibility_alpha(self, timer_rect, remaining, base_alpha=None, y_scale=2):
        if base_alpha is None:
            time_outside = time.time() - self.settings_closed_time
            base_alpha = 255 if time_outside < 1.0 else max(0, int(255 - (time_outside - 1.0) * 200))

        mouse_x, mouse_y = pygame.mouse.get_pos()
        dist = math.hypot(mouse_x - timer_rect.centerx, (mouse_y - timer_rect.centery) * y_scale)
        inner_radius = max(88, int(0.35 * window_scale))
        outer_radius = max(245, int(0.875 * window_scale))
        if dist <= inner_radius:
            hover_alpha = 255
        elif dist >= outer_radius:
            hover_alpha = 0
        else:
            hover_alpha = int(255 * (1.0 - (dist - inner_radius) / (outer_radius - inner_radius)))

        reveal_age = time.time() - self.timer_reveal_started_at
        if self.settings_timer_state == "ended" or remaining <= 10:
            alert_alpha = 255
        elif reveal_age <= 1.5:
            alert_alpha = 255
        elif reveal_age <= 3.5:
            alert_alpha = int(255 * (1.0 - (reveal_age - 1.5) / 2.0))
        else:
            alert_alpha = 0
        return max(base_alpha, hover_alpha, alert_alpha)

    def draw_button(self, rect, hover, pressed, image=None, label=None, border=False, border_color=None, img_scale=button_img_scale, font=None, label_color=None, alpha=255):
        if pressed:
            color = self.BUTTON_CLICKED_HOVER if hover else self.BUTTON_CLICKED
        else:
            color = self.BUTTON_HOVER if hover else self.BUTTON_NORMAL

        button_surface = pygame.Surface(rect.size, pygame.SRCALPHA)
        button_rect = button_surface.get_rect()
        pygame.draw.rect(button_surface, color, button_rect, border_radius=int(border_radius_ratio*window_scale))
        if border:
            outline_color = border_color if border_color is not None else "#0B234F"
            pygame.draw.rect(
            button_surface,
                outline_color,
            button_rect,
                width=max(1, int(0.012 * window_scale)),
                border_radius=int(border_radius_ratio * window_scale),
            )

        if image:
            self.load_image(image, button_rect, img_scale, button_surface)
        elif label:
            label_surface = (font or self.gaussian_font).render(label, True, label_color or self.BUTTON_TEXT)
            label_rect = label_surface.get_rect(center=button_rect.center)
            button_surface.blit(label_surface, label_rect)
        button_surface.set_alpha(alpha)
        self.screen.blit(button_surface, rect)

    def draw_shortcut_overlay(self):
        backdrop = pygame.Surface((self.WIDTH, self.HEIGHT), pygame.SRCALPHA)
        backdrop.fill((0, 0, 0, 150))
        self.screen.blit(backdrop, (0, 0))

        panel = self.shortcut_overlay_rect
        pygame.draw.rect(self.screen, "#171A3B", panel, border_radius=int(border_radius_ratio * window_scale))
        pygame.draw.rect(
            self.screen,
            self.COORDINATE_SYSTEM,
            panel,
            width=max(1, int(0.012 * window_scale)),
            border_radius=int(border_radius_ratio * window_scale),
        )

        title_font = pygame.font.Font(pygame.font.get_default_font(), max(24, int(0.13 * window_scale)))
        row_font = pygame.font.Font(pygame.font.get_default_font(), max(16, int(0.075 * window_scale)))
        title_surface = title_font.render(self.get_ui_text("Keyboard shortcuts", "Tastenkürzel"), True, self.TEXT)
        self.screen.blit(title_surface, title_surface.get_rect(midtop=(panel.centerx, panel.top + int(0.12 * window_scale))))

        shortcut_groups = [
            (self.get_ui_text("General", "Allgemein"), [("Ctrl + G", self.get_ui_text("Open settings", "Einstellungen öffnen")), ("Ctrl + E", self.get_ui_text("Edit previous word", "Vorheriges Wort bearbeiten")), ("Ctrl + F", self.get_ui_text("Change dataset", "Datensatz wechseln")), ("Ctrl + D", self.get_ui_text("Delete recent word from dataset", "Letztes Wort löschen"))]),
            (self.get_ui_text("Toggle settings", "Einstellungen"), [("Ctrl + L", self.get_ui_text("Toggle word order", "Wortreihenfolge umschalten")), ("Ctrl + T", self.get_ui_text("Toggle Gaussian weights", "Gauß-Gewichte umschalten"))]),
        ]
        row_height = max(20, int(0.12 * window_scale))
        group_gap = max(8, int(0.045 * window_scale))
        content_left = panel.left + int(0.18 * window_scale)
        shortcut_right = panel.centerx - int(0.10 * window_scale)
        action_left = panel.centerx + int(0.10 * window_scale)
        y = panel.top + int(0.38 * window_scale)

        for group_name, shortcuts in shortcut_groups:
            group_surface = self.gaussian_font.render(group_name, True, self.BLUE)
            self.screen.blit(group_surface, group_surface.get_rect(topleft=(content_left, y)))
            y += row_height
            for shortcut, action in shortcuts:
                shortcut_surface = row_font.render(shortcut, True, self.LIGHT)
                action_surface = row_font.render(action, True, self.TEXT)
                self.screen.blit(shortcut_surface, shortcut_surface.get_rect(right=shortcut_right, centery=y))
                self.screen.blit(action_surface, action_surface.get_rect(left=action_left, centery=y))
                y += row_height
            y += group_gap

    def draw_exploration_slider(self):
        self.draw_slider(
            self.exploration_slider_rect,
            self.exploration_factor,
            exploration_factor_min,
            exploration_factor_max,
            self.get_ui_text("Exploration", "Erkundung"),
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
            self.get_ui_text("Timer", "Antwortzeit"),
            ["very fast", "fast", "normal", "slow", "very slow"],
            [0, 22.5, 45, 67.5, 90],
            align_left=True,
            label_offset=int(0.07 * window_scale),
            reverse=True,
        )

    def get_word_preview(self, word_index):
        word = self.all_l1[word_index]
        preview = word[:8]
        return f"{preview}.." if len(word) > 8 else preview

    def draw_slider(self, slider_rect, value, minimum, maximum, label, levels=None, snap_values=None, integer_value=False, value_text=None, align_left=False, label_offset=None, reverse=False):
        slider_ratio = 0.5 if maximum <= minimum else (value - minimum) / (maximum - minimum)
        if reverse:
            slider_ratio = 1.0 - slider_ratio
        handle_x = int(slider_rect.left + slider_ratio * slider_rect.width)
        slider_y = slider_rect.centery
        line_width = max(1, int(0.03 * window_scale))
        handle_radius = max(1, int(0.035 * window_scale))

        pygame.draw.line(self.screen, self.COORDINATE_SYSTEM, slider_rect.midleft, slider_rect.midright, line_width)
        if snap_values:
            for snap_value in snap_values:
                snap_ratio = (snap_value - minimum) / (maximum - minimum)
                if reverse:
                    snap_ratio = 1.0 - snap_ratio
                snap_x = int(slider_rect.left + snap_ratio * slider_rect.width)
                pygame.draw.circle(self.screen, self.COORDINATE_SYSTEM, (snap_x, slider_y), max(1, int(0.03 * window_scale)))
        pygame.draw.circle(self.screen, self.SLIDER_HANDLE, (handle_x, slider_y), handle_radius)

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

    def draw_tooltip(self, text, alpha=255):
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
        if self.tooltip_position is None:
            tooltip_x = min(mouse_x + 12, self.WIDTH - tooltip_width - padding)
            tooltip_y = min(mouse_y + 12, self.HEIGHT - tooltip_height - padding)
            self.tooltip_position = (tooltip_x, tooltip_y)
        else:
            tooltip_x, tooltip_y = self.tooltip_position

        tooltip_surface = pygame.Surface((tooltip_width, tooltip_height), pygame.SRCALPHA)
        tooltip_rect = tooltip_surface.get_rect()
        bg_color = pygame.Color("#585C87")
        bg_color.a = int(alpha * 0.72)
        pygame.draw.rect(tooltip_surface, bg_color, tooltip_rect, border_radius=int(border_radius_ratio * window_scale))

        for line_number, line in enumerate(lines):
            line_surface = self.gaussian_font.render(line, True, "#FFFFFF")
            line_surface.set_alpha(alpha)
            line_position = (padding, padding + line_number * line_height)
            tooltip_surface.blit(line_surface, line_position)

        self.screen.blit(tooltip_surface, (tooltip_x, tooltip_y))

    def load_image(self, image, rect, img_scale, surface=None):
        if image not in self.image_cache:
            img = pygame.image.load(f"img/{image}").convert_alpha()
            self.image_cache[image] = img
        else:
            img = self.image_cache[image]

        max_width = rect.width
        max_height = rect.height
        scale = min(max_width / img.get_width(), max_height / img.get_height())
        draw_width = max(1, int(img.get_width() * scale))
        draw_height = max(1, int(img.get_height() * scale))
        img_scaled = pygame.transform.smoothscale(img, (int(draw_width*img_scale), int(draw_height*img_scale)))
        img_rect = img_scaled.get_rect(center=rect.center)
        (surface or self.screen).blit(img_scaled, img_rect)

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
        data_path = f"sets/{self.folder}/data.csv"
        df = pd.read_csv(data_path, header=0)
        last_word_index = word_cap if word_cap > 0 else self.total_words - 1
        if len(df) == self.n_words and self.n_words != self.total_words:
            full_df = pd.DataFrame(0.0, index=range(self.total_words), columns=feature_columns)
            full_df.iloc[starting_cap:last_word_index + 1] = df.to_numpy()
            full_df.to_csv(data_path, index=False, header=feature_columns)
            df = full_df
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