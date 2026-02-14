#external libraries
import pandas as pd
import pygame

#standard libraries
import time
import random
import math
import sys


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
folder = "main"
should_save = True
should_reverse = False #init as bool
word_cap = 0 # 0 means no cap. cant be bigger than n_words.
n_features = 8
len_timer = 30 
max_inactive_ticks = 300 #30ticks/second
    #ai parameters
reverse_translation = 0 #0 means r.t. impossible, 1 always, everything else is a weight. to let the ai decide 0.5 is standard
ema_alpha = 0.3
typing_start_alpha = 4
typing_start_beta = 0.5
time_normalization = 491700 #hours
    #standard gauss distribution parameters
sigma_factor = 1
sigma_factor_min = 0.001
sigma_factor_range = 4.9
min_gauss_weights = 0.2
min_gauss_weights_min = 0
min_gauss_weights_range = 0.9
focused_area = 0 # cant be bigger than word_cap and n_words
    #others
ignore_characters = "'()/,?!\"\n."
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

#init vocab and translation
try:

    # init first language vocab
    with open(f"sets/{folder}/language1.csv", "r") as f:
        l1 = [line.strip().lower() for line in f]
        n_words = len(l1)

        #making sure parameters are in range
        if word_cap > 0 and word_cap > n_words:
            print("Error: word_cap bigger than n_words!")
            sys.exit()

        if focused_area > n_words or (word_cap > 0 and focused_area > word_cap):
            print("Error: focused_area bigger than n_words or word cap!")
            sys.exit()
        
        if word_cap:
            l1 = l1[:word_cap]
            n_words = len(l1)
    # init corresponding second language
    with open(f"sets/{folder}/language2.csv", "r") as f:
        l2 = [line.strip().lower() for line in f]
        if word_cap:
            l2 = l2[:word_cap]

    source = l1
    target = l2

except Exception as e:
    print(e)


class SRS:

    def __init__(self):
        pygame.init()

        self.current_index = 0
        self.ticks = 0
        self.timer_running = False
        self.check_typing_start = True
        self.pause_triggered = False
        self.new_index_time = 0
        self.typing_start = 0
        self.session_index = 0
        self.input_text = ""
        self.inactive_ticks = 0

        self.settings_clicked = False
        self.get_new_gaussian = False
        self.ignore_next_button_up = False
        self.selected_focused_area = 0
        self.selected_sigma_factor = 0
        self.selected_min_gauss_weights = 0

        # if something is wrong with vocab data return with error
        if not len(l1) == len(l2):
            return 1

        # init ai model
        self.model = word_based_AI()

        self.init_gui(width_ratio * window_scale, height_ratio * window_scale)
        self.get_new_index()

    def init_gui(self, width, height):
        # Window
        self.WIDTH = width
        self.HEIGHT = height

        # Fonts
        self.font_word = pygame.font.SysFont("Arial", int(font_word_ratio*window_scale))
        self.font_input = pygame.font.SysFont("Arial", int(font_input_ratio*window_scale))
        self.button_font = pygame.font.SysFont("DejaVu Sans", int(button_font_ration*window_scale))
        self.gaussian_font = pygame.font.SysFont("Arial", int(gaussian_font_ratio*window_scale))

        # Buttons
        self.settings_button = pygame.Rect(0.05*window_scale,0.05*window_scale,self.WIDTH // (width_ratio * button_scale),self.HEIGHT // (height_ratio * button_scale))
        self.coordinate_system_rect = pygame.Rect(self.WIDTH // 7, self.HEIGHT // 10, self.WIDTH * 7 // 10, self.HEIGHT * 7 // 10)

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
        self.coordinate_system_hover = mouse_pos if self.coordinate_system_rect.collidepoint(mouse_pos) else None

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN and not self.timer_running and not self.settings_clicked:
                found_keydown = True
                self.inactive_ticks = 0

                if self.pause_triggered:
                    self.pause_triggered = False
                    self.new_index_time = time.time()
                    self.check_typing_start = True

                else:
                    if event.key == pygame.K_RETURN:
                        if self.input_text != "": #add a second if statement since we want it to do nothing if return is pressed but text is empty
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
                if self.settings_button_hover:
                    if self.settings_clicked:
                        self.settings_clicked = False
                    else:
                        self.settings_clicked = True
                        self.get_new_gaussian = True
                        self.trigger_pause()
                if self.coordinate_system_hover:
                    if not self.get_new_gaussian:
                        self.ignore_next_button_up = True
                        self.get_new_gaussian = True

            elif event.type == pygame.MOUSEBUTTONUP:
                self.mouse_hold = False
                if self.ignore_next_button_up == True:
                    self.ignore_next_button_up = False
                else:
                    if self.get_new_gaussian and self.coordinate_system_hover:
                        sigma_factor = self.selected_sigma_factor
                        min_gauss_weights = self.selected_min_gauss_weights
                        focused_area = self.selected_focused_area
                        self.get_new_gaussian = False
            
            


        if not found_keydown:
            self.inactive_ticks += 1
        if self.inactive_ticks > max_inactive_ticks:
            self.trigger_pause()

    def trigger_pause(self):
        self.input_text = ""
        self.pause_triggered = True

    def check_input(self):
        correct = self.is_correct()

        self.session_index += 1 

        if correct:
            self.save_data(correct=True)
            self.TEXT = self.GREEN
        else:
            self.save_data(correct=False)
            self.TEXT = self.RED

        self.timer_running = True
        self.ticks = len_timer
        self.input_text = ""

    def save_data(self, correct):

        # save new language data
        if should_reverse:
            word_data = self.model.df2[self.current_index] # currently saved data
        else:
            word_data = self.model.df1[self.current_index] # currently saved data
        old_ema = word_data[4]
        new_ema = self.get_ema(old_ema=word_data[4], accuracy=correct)

        word_data[0] += 1 # occurrences in session (will be reset on new session)
        word_data[1] = round(time.time()/3600 - time_normalization, 4) # last seen (in hours)
        word_data[2] = self.session_index # last seen index
        word_data[3] += 1 # n reps
        word_data[4] = new_ema # exponentially moving average of accuracy
        word_data[5] = round(self.account_typing_start_time(correct, (self.typing_start - self.new_index_time)), 4) # last correct 
        word_data[6] = word_data[6]+1 if correct else 0 # correct streak
        word_data[7] = should_reverse

        if should_save:
            # save language data
            if should_reverse:
                self.model.df2[self.current_index] = word_data
                pd.DataFrame(self.model.df2).to_csv(f"sets/{folder}/l2_data.csv", mode="w", index=False, header=feature_columns)
            else:
                self.model.df1[self.current_index] = word_data
                pd.DataFrame(self.model.df1).to_csv(f"sets/{folder}/l1_data.csv", mode="w", index=False, header=feature_columns)
            
            # save data points
            pd.DataFrame([word_data]).to_csv("data/feature_data.csv", mode="a", index=False, header=False)
            pd.DataFrame([new_ema - old_ema]).to_csv("data/reward_data.csv", mode="a", index=False, header=False)

        self.print_data_tensor(word_data) #*

    def account_typing_start_time(self, correct, typing_start_time):
        return math.exp(-typing_start_time / typing_start_alpha) * (1-typing_start_beta) + typing_start_beta if correct else 0.0

    def get_ema(self, old_ema, accuracy):
        return ema_alpha*accuracy + (1-ema_alpha)*old_ema

    def print_data_tensor(self, tensor):
        print()
        for i in range(len(feature_columns)):
            print(f"{feature_columns[i]}: {tensor[i]}")

    def print_validation_reason(self, input, target, min_input_len, input_len):
        print()
        print(f"all words ({input}) are in target ({target}): {all(word in target for word in input)}")
        print(f"input length ({input_len}) is bigger than or equal min input length ({min_input_len}): {input_len >= min_input_len}")

    def get_new_index(self):
        global source
        global target

        should_reverse = False

        if should_reverse:
            source = l2
            target = l1

        else:
            source = l1
            target = l2

        self.current_index = random.randint(0, n_words-1)
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
                    self.input_text = target[self.current_index]
                
            # source word
            if self.pause_triggered:
                display_word = "Press any key to proceed.."
            else:
                display_word = source[self.current_index]
            word_surface = self.font_word.render(display_word, True, self.TEXT)
            word_rect = word_surface.get_rect(center=(self.WIDTH // 2, self.HEIGHT // 4))
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
            self.draw_grid(self.coordinate_system_rect, n_words, axis_padding, self.GRID_COLOR)

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

                        focused_area_local = int(((x - rect_left) / (rect_right - rect_left)) * n_words)

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
            amount = self.dim_to_grid(n_words) +1 
            for i in range(amount):
                ratio = i / (amount - 1)
                label_val = int(ratio * n_words) 
                label_x = self.coordinate_system_rect.left + ratio * (self.coordinate_system_rect.width - 2*axis_padding) + axis_padding
                label_surf = self.gaussian_font.render(f"{label_val}", True, self.COORDINATE_SYSTEM)
                label_rect = label_surf.get_rect(centerx=label_x, top=self.coordinate_system_rect.bottom + 5)
                self.screen.blit(label_surf, label_rect)



        # open settings
        self.draw_button(self.settings_button, "≡", self.settings_button_hover, self.settings_clicked)
    
    def draw_grid(self, rect, max_x, axis_padding, color):
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
        upper_distance = n_words - 1 - focused_area
        sigma = (max(focused_area, upper_distance) / 3) * sigma_factor

        weights = []
        for i in range(n_words):
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
            px = inner_left + (i / (n_words - 1)) * inner_width
            py = inner_bottom - w * inner_height
            points.append((px, py))

        if len(points) > 1:
            pygame.draw.lines(surface, color, False, points, self.coordinate_system_line_thickness)

    def draw_button(self, rect, text, hover, pressed):
        if pressed:
            color = self.BUTTON_CLICKED_HOVER if hover else self.BUTTON_CLICKED
        else:
            color = self.BUTTON_HOVER if hover else self.BUTTON_NORMAL
        pygame.draw.rect(self.screen, color, rect, border_radius=int(border_radius_ratio*window_scale))
        label = self.button_font.render(text, True, self.BUTTON_TEXT)
        self.screen.blit(label, label.get_rect(center=rect.center))

    def is_correct(self):
        # if the written words come up in the target assume it is a right answer
        input = self.filter(self.input_text)
        target_word = self.filter(target[self.current_index])
        min_input_len = math.ceil(math.sqrt(sum([len(word) for word in target_word])))
        input_len = sum([len(word) for word in input])

        self.print_validation_reason(input, target_word, min_input_len, input_len) #*

        if input == "idk":
            return False
        
        return True if all(word in target_word for word in input) and min_input_len <= input_len else False
    
    def filter(self, word):
        for c in ignore_characters:
            word = word.replace(c, "")
        return str(word).lower().split()



class word_based_AI:

    def __init__(self):
        # init collected data
        try:
            self.init_df_tensor(1)
            if n_words != len(self.df1):
                # file doesnt have enough rows ( in case vocab was added later on )
                rows = [[0.0]*n_features for _ in range(n_words - len(self.df1))]
                # asign start bias to ema
                rows = self.set_row_val(rows, 4, 0.5)
                pd.DataFrame(rows).to_csv(f"sets/{folder}/l1_data.csv", mode="a", index=False, header=False)
                self.init_df_tensor(1)

        except Exception as _:
            # file doesnt exist
            rows = [[0.0]*n_features for _ in range(n_words)]
            # asign start bias to ema
            rows = self.set_row_val(rows, 4, 0.5)
            pd.DataFrame(rows).to_csv(f"sets/{folder}/l1_data.csv", mode="a", index=False, header=feature_columns)
            self.init_df_tensor(1)

        try:
            self.init_df_tensor(2)
            if n_words != len(self.df2):
                # file doesnt have enough rows ( in case vocab was added later on )
                rows = [[0.0]*n_features for _ in range(n_words - len(self.df2))]
                # asign start bias to ema
                rows = self.set_row_val(rows, 4, 0.5)
                pd.DataFrame(rows).to_csv(f"sets/{folder}/l2_data.csv", mode="a", index=False, header=False)
                self.init_df_tensor(2)

        except Exception as _:
            # file doesnt exist
            rows = [[0.0]*n_features for _ in range(n_words)]
            # asign start bias to ema
            rows = self.set_row_val(rows, 4, 0.5)
            # set should reverse true
            rows = self.set_row_val(rows, 7, 1.0)
            pd.DataFrame(rows).to_csv(f"sets/{folder}/l2_data.csv", mode="a", index=False, header=feature_columns)
            self.init_df_tensor(2)

    def init_df_tensor(self, num):
        if num == 1:
            df1 = pd.read_csv(f"sets/{folder}/l1_data.csv", header=0)
            # reset occurrences in session and save as self.df
            self.df1 = self.set_row_val(df1.values.tolist(), 0, 0.0)
        else:
            df2 = pd.read_csv(f"sets/{folder}/l2_data.csv", header=0)
            # reset occurrences in session and save as self.df
            self.df2 = self.set_row_val(df2.values.tolist(), 0, 0.0)

    def set_row_val(self, df, col, val):
        for row in df:
            row[col] = val
        return df

    def get_word(self):

        distribution_weights = self.gauss_distribution()

    def gauss_distribution(self):
        # get a gauss distribution across the units that will be weight for the ai
        upper_distance = n_words - 1 - focused_area
        # the parameter sigma is calculated based upon the distance to the first or last unit with respect to the chosen factor
        sigma = (max(focused_area, upper_distance) / 3) * sigma_factor

        weights = []
        for i in range(n_words):
            val = math.exp(-0.5*((i - focused_area)/sigma)**2) * (1 - min_gauss_weights) + min_gauss_weights
            weights.append(val)
        return weights

# run main
if __name__ == "__main__":
    application = SRS()
    application.model.get_word()
    application.run()
    