# Scorer SDK for Python
SCORER Cloud Processing Library for Python

This repository stores all source codes which relate to Scorer Cloud Processing for Python

## NOTICE

Version 0.1.1 has breaking changes.

scorer.VideoCapture.read() returns two element tuple. (0.0.1 returns one element tuple)

## Usage

```
cap = scorer.VideoCapture(ZMQ_TRACKER_ENDPOINT)

meta, image = cap.read()
while meta:
    image_mod = some_image_processing(image)
    meta, image = cap.read()
```

Notice: `meta` (first return value) is not Bool. It contains frame metadata.