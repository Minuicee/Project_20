import matplotlib.pyplot as plt
import torch.nn as nn

class Main:

    def __init__(self, folder, sigma):
        self.get_data(folder)


    def get_data(self, folder):
        # get info from info csv
        with open(f"{folder}/sets/info.csv") as f:
            unit_lengths = f.readline().strip().split(",")
            self.unit_lengths = [int(x) for x in unit_lengths]    
            self.filter_list = f.readline().strip()

        # init target language
        with open(f"{folder}/sets/target.csv", "r") as f:
            self.target = [line for line in f]
        
        # init coresponding source language translation from data
        with open(f"{folder}/sets/source.csv", "r") as f:
            self.source = [self.filter(line) for line in f]


    def learn(self):
        print(self.target)

    
    def filter(self, word):
        for c in self.filter_list:
            word = word.replace(c, "")
        return word.lower()
    


# run main
application = Main("german-latin", 1)
application.learn()