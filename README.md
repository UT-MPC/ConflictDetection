# Enabling probabilistic conflict prediction in smart space through context-awareness
[![License](https://img.shields.io/badge/license-BSD-blue.svg)](LICENSE)

This project proposes a data-driven approach to predict conflicts of IoT devices among multiple user based on their previous interaction histories. Here, a conflict is a situation when two users' preferences over the state of an IoT device differ. For example, a user wants to turn off the light while another user wants to maintain illumination with the same light.

## Getting started
### **Python version**
This project is tested with python3 only

### **Installing prerequisites**
All the required packages are listed in the requirements.txt. The most simple way to install the depencies is by running

`pip install -r requirements.txt`

### **Prepare the data**
- Find the REFIT dataset from this [DOI](https://doi.org/10.15129/9ab14b0e-19ac-4279-938f-27f643078cec). Download and unzip **CLEAN_REFIT_081116.7z** in the listed files.
- Create folders `./data/refit` under the root directory of this project. And put all files from the downloaded dataset to `./data/refit`. Expected file structure:
```
ConflictDetection
│   README.md
│   main.py    
│
└───data
│   └───refit
│       │   CLEAN_House1.csv
│       │   CLEAN_House2.csv
│       │   ...
```
- run `data_prepare.py` from the root directory: `python3 data_prepare/data_prepare.py`
 
### **Run example**
To verify the project is set up correctly and to see some real conflict scenarios, run:

`python3 main.py`

Other than the debug messages (starts with `DEBUG`) the expected results is:
```
The number of conflicts we found for the devices are:
{'TV': 21, 'WashingMachine': 4, 'PC': 0}
Top 5 conflict scenarios with the highest probability for TV
House4 and House3 have 53.32% to have conflicts over TV at {'min_of_day#NUM': [1140.0, 1320.0], 'weatherDesc#CAT': {'Rain', 'HeavyRain', 'Fog', 'Cloudy'}, 'day_of_week#NUM': [0.0, 7.0]}
House4 and House3 have 44.29% to have conflicts over TV at {'min_of_day#NUM': [1080, 1140.0], 'weatherDesc#CAT': {'Rain', 'HeavyRain', 'Fog', 'Cloudy'}, 'day_of_week#NUM': [0.0, 7.0]}
House4 and House3 have 38.02% to have conflicts over TV at {'min_of_day#NUM': [1140.0, 1320.0], 'weatherDesc#CAT': {'Clear'}, 'day_of_week#NUM': [0.0, 7.0]}
House4 and House3 have 31.59% to have conflicts over TV at {'min_of_day#NUM': [1020.0, 1140.0], 'weatherDesc#CAT': {'Clear'}, 'day_of_week#NUM': [0.0, 7.0]}
House3 and House4 have 26.94% to have conflicts over TV at {'min_of_day#NUM': [1020.0, 1080], 'weatherDesc#CAT': {'Rain', 'Fog', 'Cloudy'}, 'day_of_week#NUM': [0.0, 7.0]}
House4 and House3 have 17.09% to have conflicts over TV at {'min_of_day#NUM': [1320.0, 1380.0], 'weatherDesc#CAT': {'Rain', 'HeavyRain', 'Fog', 'Cloudy'}, 'day_of_week#NUM': [0.0, 7.0]}
House3 and House4 have 11.30% to have conflicts over TV at {'min_of_day#NUM': [420.0, 600], 'weatherDesc#CAT': {'HeavyRain', 'Rain', 'HeavySnow', 'Snow'}, 'day_of_week#NUM': [0.0, 7.0]}
House3 and House4 have 11.14% to have conflicts over TV at {'min_of_day#NUM': [1320.0, 1380.0], 'weatherDesc#CAT': {'Clear'}, 'day_of_week#NUM': [0.0, 7.0]}
House3 and House4 have 10.17% to have conflicts over TV at {'min_of_day#NUM': [420.0, 600], 'weatherDesc#CAT': {'Fog', 'Clear', 'Cloudy'}, 'day_of_week#NUM': [0.0, 7.0]}
House3 and House4 have 8.27% to have conflicts over TV at {'min_of_day#NUM': [780.0, 1020.0], 'weatherDesc#CAT': {'Cloudy', 'HeavySnow', 'Rain', 'Snow', 'HeavyRain', 'Clear', 'Fog'}, 'day_of_week#NUM': [0.0, 7.0]}
```
