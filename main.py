from input_process import *

DATASET = "hh104"
FILENAME = "data/" + DATASET + "/ann.txt"

def main():
    preprocess(FILENAME)

if __name__ == "__main__":
    main()

