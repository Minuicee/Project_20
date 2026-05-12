import torch
import torch.nn as nn


class ai(nn.Module):

    def __init__(self, input_dim):
        super().__init__()

        # init nn
        self.network = nn.Sequential(
            nn.Linear(input_dim, 32),
            nn.ReLU(),
            nn.Linear(32, 16),
            nn.ReLU(),
            nn.Linear(16, 1),
            nn.Sigmoid()
        )
    
    def forward(self, x):
        self.network(x)

