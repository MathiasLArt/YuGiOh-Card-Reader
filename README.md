Dependencies
------------
* [`tesseract`](https://github.com/tesseract-ocr/)
* `python` and `pip` then run `pip install -r requirements.txt`

Card data
------------
`cardinfo.php` has been scraped via instructions [`here`](https://ygoprodeck.com/api-guide/).

It contains up to date information on all the released cards, so it should be occasionally updated if the recognition on new cards fails a lot.

Usage
------------
```
usage: detector_final.py [-h] [--image IMAGE] [--tesseract TESSERACT] [--visualize]

options:
  -h, --help            show this help message and exit
  --image IMAGE         path to image
  --tesseract TESSERACT
                        path to tesseract.exe
  --visualize           show intermediate steps
```

`--visualize` is very optional, useful for bugtesting purposes.

Future Work:
------------
* Improve 4-point contour detection mechanism
* Optimize the code speed for real-time video usage (remove unnecessary contour detection, use a faster Tesseract wrapper)
* Dynamic text box size so it doesn't go over the edge of the image
