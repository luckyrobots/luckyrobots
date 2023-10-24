![Version](https://img.shields.io/badge/version-0.0.0-orange.svg?style=for-the-badge)
![Python](https://img.shields.io/badge/python-3.11.0-orange.svg?style=for-the-badge)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg?style=for-the-badge)](https://github.com/psf/black)

# Examples

You can find quick-dirty tests here.

## Capture, Draw, Show

This example captures given screen area, draws box to given view port and shows.

![Screenshot Example1](screenshots/screenshot-example1.png)

### Requirements

This script requires `python 3.9` or higher.

Install required python packages via;

```bash
cd lucky-robots/examples/
pip install -r requirements.txt            # or
pip install --user -r requirements.txt     # don’t forget to fix your $PATH according to you python setup
```

If you want to develop/improve code, you can additionally install linters;

```bash
cd lucky-robots/examples/
pip install -r requirements-dev.txt            # or
pip install --user -r requirements-dev.txt     # don’t forget to fix your $PATH according to you python setup
```

Configure your editor to handle;

- isort
- black
- pylint
- flake8

checkers.

Run example:

```bash
$ python capture_draw_show -h
usage: capture_draw_show [-h] [--sx SOURCE_X] [--sy SOURCE_Y]
                         [--sw SOURCE_WIDTH] [--sh SOURCE_HEIGHT]
                         [--tx TARGET_X] [--ty TARGET_Y] [--tw TARGET_WIDTH]
                         [--th TARGET_HEIGHT]
                         [--capture-interval CAPTURE_INTERVAL]
                         [--box-color BOX_COLOR] [--border-size BORDER_SIZE]

example

options:
  -h, --help            show this help message and exit
  --sx SOURCE_X         set x coordinate of source frame
  --sy SOURCE_Y         set y coordinate of source frame
  --sw SOURCE_WIDTH     set width of source frame
  --sh SOURCE_HEIGHT    set height of source frame
  --tx TARGET_X         set x coordinate of target frame
  --ty TARGET_Y         set y coordinate of target frame
  --tw TARGET_WIDTH     set width of target frame
  --th TARGET_HEIGHT    set height of target frame
  --capture-interval CAPTURE_INTERVAL
                        capture interval as milisecond (1000 is 1 second)
  --box-color BOX_COLOR
                        specify an RGB color as (R, G, B)
  --border-size BORDER_SIZE
                        set border size of target frame
```

Example usage:

    S : source x,y
    T : target x,y
    
            source width
    S-------------------------------------------+
    |                                           | 
    |     T--------------+                      | 
    |     |              |                      | source height
    |     |              | target height        | 
    |     |              |                      | 
    |     +--------------+                      |
    |       target width                        |
    |                                           |
    +-------------------------------------------+

Press <kbd>Q</kbd> to exit application.

```bash
# uses default source and target metrics (x,y,width,height,border,interval etc...)

python capture_draw_show --box-color "(255,0,0)"                    # rectangle color is red in R,G,B format
python capture_draw_show --box-color "(255,255,0)" --border-size 5  # rectangle color is yellow in R,G,B format
                                                                    # and border size is 5
```

---
