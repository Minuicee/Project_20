import random


class Main:

    def __init__(self):
        
        # init latin from data
        with open("latin.csv", "r") as f:
            self.latin = [line for line in f]
        
        # init coresponding german translation from data
        with open("german.csv", "r") as f:
            self.german = [line for line in f]

        self.unit_lengths = [
            32, 29, 27, 28, 31, 27, 28, 22, 51, 27, 22, 50, 28, 27, 29, 28,
            23, 20, 24, 20, 38, 42, 19, 19, 21, 24, 23, 41, 23, 16, 23, 20, 21, 24
        ]


    def learn(self):
        unit_start = int(input("unit start: "))
        unit_end = int(input("unit end: "))
        print()

        self.index_range = (sum(self.unit_lengths[0:unit_start-1]), sum(self.unit_lengths[0:unit_end]))

        # init new queue
        queue = self.add_queue([])

        # repeat until exit is typed
        while True:

            # select index from top of queue
            index = queue[-1]

            # get user input
            response = input(self.latin[index]).lower().replace(" ", "")

            if response == "exit":
                print()
                return 0
            elif response in self.german[index].lower().replace(" ", ""):
                print("richtig \n")
                queue = self.add_queue(queue, True)
            else:
                print("falsch:", self.german[index])
                queue = self.add_queue(queue, False)

    def add_queue(self, queue, correct=False):
        if queue == []:
            for i in range(10):
                index = random.randint(self.index_range[0], self.index_range[1])
                queue.append(index)
        elif correct:
            queue.pop()
            index = random.randint(self.index_range[0], self.index_range[1])
            queue.insert(0, index)
        else:
            word = queue.pop()
            queue.insert(0, word)
        return queue
    

# run main
application = Main()
application.learn()