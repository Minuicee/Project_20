import matplotlib.pyplot as plt
import torch.nn as nn
import torch

class AI:

    def __init__(self, folder, sigma, focused_unit):
        self.sigma = sigma
        self.focused_unit = focused_unit

        # get info from info csv
        with open(f"sets/{folder}/info.csv") as f:
            self.unit_lengths = [int(x) for x in f.readline().strip().split(",")] 

        # init target language
        with open(f"sets/{folder}/target.csv", "r") as f:
            self.target = [line.strip().lower() for line in f]
        
        # init coresponding source language translation from data
        with open(f"sets/{folder}/source.csv", "r") as f:
            self.source = [line.strip().lower() for line in f]


    def get_word(self):
        unit_weights = self.gauss_distribution()
        plt.plot(unit_weights)
        plt.show()

    def is_correct(self, input, target):
        return True if input in target and len(input) > 1 else False
    
    def gauss_distribution(self):
        indices = torch.arange(len(self.unit_lengths), dtype=torch.float32)
        return torch.exp(-0.5*((indices - self.focused_unit)/self.sigma)**2)


# run main
model = AI(folder="german-latin",
                 sigma=1,
                 focused_unit=5)
model.get_word()