import matplotlib.pyplot as plt
import torch.nn as nn
import torch
import pandas as pd
import time
import pygame
import math
import sys


# parameters for dev
    #gui
window_scale = 100
width_ratio = 6
height_ratio = 2
font_word_ratio = 0.6
font_input_ratio = 0.4
    #logic
folder = "test"
n_features = 7
word_cap = 300
len_timer = 30
max_inactive_ticks = 300
    #ai parameters
ema_alpha = 0.3
typing_start_alpha = 4
typing_start_beta = 0.5
time_normalization = 491700 #hours
    #gauss distribution
sigma_factor = 1
min_gauss_weights = 0.2
focused_area = 300
    #others
ignore_characters = "'()/,?!\"\n."
feature_columns = [
    "occurrences_session",
    "last_seen",
    "last_seen_index",
    "n_reps",
    "EMA_accuracy",
    "last_correct_score",
    "correct_streak"
]

#init files
try:
    # init target language
    with open(f"sets/{folder}/target.csv", "r") as f:
        target = [line.strip().lower() for line in f]
            
    # init coresponding source language translation from data
    with open(f"sets/{folder}/source.csv", "r") as f:
        source = [line.strip().lower() for line in f]
        n_words = len(source)
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

        # if something is wrong with vocab data return with error
        if not len(source) == len(target):
            return 1

        # init ai model
        self.model = word_based_AI(n_words=len(source))

        self.init_gui(width_ratio * window_scale, height_ratio * window_scale)
        self.get_new_index()

    def init_gui(self, width, height):
        # Window
        self.WIDTH = width
        self.HEIGHT = height
        self.screen = pygame.display.set_mode((self.WIDTH, self.HEIGHT))
        pygame.display.set_caption("SRS")

        # Fonts
        self.font_word = pygame.font.SysFont(None, int(font_word_ratio*window_scale))
        self.font_input = pygame.font.SysFont(None, int(font_input_ratio*window_scale))

        # colours
        self.DARK = (13, 14, 41)
        self.LIGHT = (203, 204, 247)
        self.BLUE = (87, 207, 201)
        self.GREEN = (44, 212, 44)
        self.RED = (212, 44, 44)
        self.BACKGROUND = self.DARK
        self.FOREGROUND = self.LIGHT

        self.clock = pygame.time.Clock()

    def run(self):
        while True:
            self.screen.fill(self.BACKGROUND)
            self.handle_events()
            self.draw()
            pygame.display.flip()
            self.clock.tick(30)
    
    def handle_events(self):
        found_keydown = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN and not self.timer_running:
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
        if not found_keydown:
            self.inactive_ticks += 1
        if self.inactive_ticks > max_inactive_ticks:
            self.pause_triggered = True

    def check_input(self):
        correct = self.is_correct()

        self.session_index += 1 

        if correct:
            self.save_data(correct=True)
            self.FOREGROUND = self.GREEN
        else:
            self.save_data(correct=False)
            self.FOREGROUND = self.RED

        self.timer_running = True
        self.ticks = len_timer
        self.input_text = ""

    def save_data(self, correct):

        # save new language data
        word_data = self.model.df_tensor[self.current_index] # currently saved data
        old_ema = word_data[4].clone()
        new_ema = self.get_ema(old_ema=word_data[4], accuracy=correct)

        word_data[0] += 1 # occurrences in session (will be reset on new session)
        word_data[1] = round(time.time()/3600 - time_normalization, 4) # last seen (in hours)
        word_data[2] = self.session_index # last seen index
        word_data[3] += 1 # n reps
        word_data[4] = new_ema # exponentially moving average of accuracy
        word_data[5] = round(self.account_typing_start_time(correct, (self.typing_start - self.new_index_time)), 4) # last correct 
        word_data[6] = word_data[6]+1 if correct else 0 # correct streak

        self.model.df_tensor[self.current_index] = word_data
        pd.DataFrame(self.model.df_tensor.numpy()).to_csv(f"sets/{folder}/language_data.csv", mode="w", index=False, header=feature_columns)

        # save data points
        pd.DataFrame(word_data.unsqueeze(0).numpy()).to_csv(f"sets/{folder}/feature_data.csv", mode="a", index=False, header=False)
        pd.DataFrame([[ (new_ema - old_ema).item() ]]).to_csv(f"sets/{folder}/reward_data.csv", mode="a", index=False, header=False)

        self.print_data_tensor(word_data)

    def account_typing_start_time(self, correct, typing_start_time):
        return math.exp(torch.tensor(-typing_start_time / typing_start_alpha)) * (1-typing_start_beta) + typing_start_beta if correct else 0.0

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
        self.current_index = torch.randint(0, len(source), (1,))[0]
        self.new_index_time = time.time()
        self.check_typing_start = True

    def draw(self):
        if self.timer_running:
            if self.ticks == 0:
                self.timer_running = False
                self.FOREGROUND = self.LIGHT
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
        word_surface = self.font_word.render(display_word, True, self.FOREGROUND)
        word_rect = word_surface.get_rect(center=(self.WIDTH // 2, self.HEIGHT // 4))
        self.screen.blit(word_surface, word_rect)

        # text area 
        input_surface = self.font_input.render(self.input_text, True, self.FOREGROUND)
        input_rect = input_surface.get_rect(center=(self.WIDTH // 2, self.HEIGHT * 3 // 4))
        self.screen.blit(input_surface, input_rect)

    def is_correct(self):
        # if the written words come up in the target assume it is a right answer
        input = self.filter(self.input_text)
        target = self.filter(target[self.current_index])
        min_input_len = math.ceil(math.sqrt(sum([len(word) for word in target])))
        input_len = sum([len(word) for word in input])

        self.print_validation_reason(input, target, min_input_len, input_len)

        if input == "idk":
            return False
        
        return True if all(word in target for word in input) and min_input_len <= input_len else False
    
        
    def filter(self, word):
        for c in ignore_characters:
            word = word.replace(c, "")
        return str(word).lower().split()



class word_based_AI:

    def __init__(self, n_words):
        self.n_words = n_words

        # init collected data
        try:
            self.init_df_tensor()
            if not self.n_words == self.df_tensor.shape[0]:
                tensor = torch.zeros([self.n_words - self.df_tensor.shape[0], n_features])
                tensor[:, 4] = 0.5 # bias ema value to 0.5
                pd.DataFrame(tensor.numpy()).to_csv(f"sets/{folder}/language_data.csv", mode="a", index=False, header=False)
                self.init_df_tensor()

        except Exception as _:
            tensor = torch.zeros([self.n_words, n_features])
            tensor[:, 4] = 0.5 # bias ema value to 0.5
            pd.DataFrame(tensor.numpy()).to_csv(f"sets/{folder}/language_data.csv", mode="a", index=False, header=feature_columns)
            self.init_df_tensor()

    def init_df_tensor(self):
        df = pd.read_csv(f"sets/{folder}/language_data.csv", header=0)
        self.df_tensor = torch.tensor(df.values, dtype=torch.float32)
        # reset occurrences in session
        self.df_tensor[:, 0] = 0.0

    def get_word(self):

        distribution_weights = torch.Tensor(self.gauss_distribution())


    def gauss_distribution(self):
        # get a gauss distribution across the units that will be weight for the ai
        indices = torch.arange(self.n_words, dtype=torch.float32)
        upper_distance = self.n_words - 1 - focused_area
        # the parameter sigma is calculated based upon the distance to the first or last unit with respect to the chosen factor
        sigma = (max(focused_area, upper_distance) / 3) * sigma_factor
        return torch.exp(-0.5*((indices - focused_area)/sigma)**2) * (1 - min_gauss_weights) + min_gauss_weights

# run main
if __name__ == "__main__":
    application = SRS()
    application.run()
    