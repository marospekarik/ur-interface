from time import time


class App():
    def __init__(self):
        self.prevTime = 0
        self.time = int(round(time() * 1000))
        self.array = []
        self.gen = self.infinite_sequence()
        for x in range(0,200):
            self.array.append([-0.050181311699884656, 0, 1])

    def test(self):
        print('test')

    def infinite_sequence(self):
        num = 0
        length = len(self.array) 
        while num < length: 
            try:
                print(length, num)
                yield num
                num += 1
            except StopIteration:
                break
            #print(self.array[num])
            

    def iterate_recording(self):
        self.time = int(round(time() * 1000))
        if(self.time - self.prevTime > 20):
            self.prevTime = int(round(time() * 1000))
            next(self.gen)
        

if __name__ == '__main__':
    app = App()
    while True:
        app.iterate_recording()
