import torch
import torch.nn as nn
import matplotlib.pyplot as plt
import pandas as pd
import main

class ai(nn.Module): #TODO add training mode: every x words train the model

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
        # forward pass through the network
        return self.network(x)
    

    def backprop(self, n_epochs, lr=1e-3):
        # init criterion and optimizer
        criterion = torch.nn.BCELoss()  # Binary Cross Entropy Loss
        optimizer = torch.optim.Adam(self.parameters(), lr=lr)

        # go through epochs and backpropagate
        for epoch in range(n_epochs):
            total_loss = 0.0
            for x_batch, y_batch in zip(self.x_data, self.y_data):
                optimizer.zero_grad() # reset gradients
                y_pred = self.forward(x_batch) # forward pass
                loss = criterion(y_pred, y_batch) # get loss
                loss.backward() #apply backpropagation
                optimizer.step() # update weights
                total_loss += loss.item() #calculate total loss for the epoch
            print(f"Epoch {epoch + 1}/{n_epochs}, Loss: {total_loss/len(self.x_data):.5f}")

    def init_data(self):
        feature_data = pd.read_csv("data/feature_data.csv")
        feature_data = main.get_normalized_df(self, feature_data, is_training=True) # normalize the data
        self.x_data = torch.tensor(feature_data, dtype=torch.float32)
        self.y_data = torch.tensor(pd.read_csv("data/reward_data.csv").values, dtype=torch.float32)
    def plot_df(self):
        self.df.hist(figsize=(12,8))
        plt.show()

if __name__ == "__main__":
    pass