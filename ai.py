import torch
import math

class ai:

    def __init__(self):
        self.focused_area = 0
        self.sigma_factor = 0
        self.min_gauss_weights = 0

    def gauss_distribution(self):
        # get a gauss distribution across the units that will be weight for the ai
        upper_distance = self.n_words - 1 - self.focused_area
        # the parameter sigma is calculated based upon the distance to the first or last unit with respect to the chosen factor
        sigma = (max(self.focused_area, upper_distance) / 3) * self.sigma_factor

        weights = []
        for i in range(self.n_words):
            val = math.exp(-0.5*((i - self.focused_area)/sigma)**2) * (1 - self.min_gauss_weights) + self.min_gauss_weights
            weights.append(val)
        return weights