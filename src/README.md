## README

### Overview

This directory contains the source code for the project. There are two primary python files: `data_retrieval.py` and `main.py`. The first file handles the downloading and parsing of all of the historical data. Once the dictionaries are created, they're written to the disk to prevent the lengthy and network-intensive retrieval task.

`main.py` calls `data_retrieval.get_data()` to get the dictionaries of data. Then the HTML pages for the current box score and play-by-play log are scraped through to retrieve the stats relevant for the new match. The play-by-play log for each set is vectorized and classified so that the summarization templates can be properly decided. 

Once the historical and current data has been retrieved, the template HTML page is filled with the template sentences that contain the proper names, stats, and language to describe the current game and that HTML page is saved to the `/results` directory. 

### Instructions

In order to generate a new article, the 