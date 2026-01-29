import random


class Main:

    def __init__(self, folder):
        
        # init target language
        with open(f"{folder}/target.csv", "r") as f:
            self.target = [line for line in f]
        
        # init coresponding source language translation from data
        with open(f"{folder}/source.csv", "r") as f:
            self.source = [line for line in f]

        # get info from info csv
        with open(f"{folder}/info.csv") as f:
            line = f.readline().strip().split(",")
            self.unit_lengths = [int(x) for x in line]

        self.filterlist = " ()."


    def learn(self):
        unit_start = input("unit start: ")

        if unit_start == "alle":
            self.index_range = (0, len(self.target))

        else:
            unit_end = input("unit end: ")
            self.index_range = (sum(self.unit_lengths[0:int(unit_start)-1]), sum(self.unit_lengths[0:int(unit_end)]))
        print()

        # init new queue
        queue = self.add_queue([])

        count = 1

        # repeat until exit is typed
        while True:


            # select index from top of queue
            index = queue[-1]

            # get user input
            print("[",count,"]")
            response = self.filter(input(self.target[index]))
            answer = self.filter(self.source[index])

            if response == "exit":
                print()
                return 0
            elif response in answer and len(response) > 1:
                print("richtig: ", self.source[index])
                queue = self.add_queue(queue, True)
            else:
                print("falsch:", self.source[index])
                queue = self.add_queue(queue, False)
            
            count += 1

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
    
    def filter(self, word):
        for c in self.filterlist:
            word = word.replace(c, "")
        return word.lower()
    
    #!gausche glocke
    #!appl

# run main
application = Main("german-latin")
application.learn()