# pylint: disable=E1101
# Standard Library
"""
Example of code of capture / draw / show operations.
"""

# Standard Library
import argparse
import sys
from argparse import (
    ArgumentParser,
    RawDescriptionHelpFormatter,
)

# Third Party
import cv2
import numpy as np
from PIL import ImageGrab


def console(msg):
    """
    wrapper function
    """

    sys.stdout.write(f'{str(msg)}\n')


def rgb_color(value):
    """
    parse custom rgb value
    """

    try:
        # convert bgr to rgb logic.
        b, g, r = map(int, value.strip('()').split(','))
        if 0 <= r <= 255 and 0 <= g <= 255 and 0 <= b <= 255:
            return (r, g, b)
        raise argparse.ArgumentTypeError('rgb values must be in the range 0-255')
    except ValueError as exc:
        raise argparse.ArgumentTypeError('invalid RGB color format. Use (R, G, B)') from exc


def main():
    """
    run:
    """

    parser = ArgumentParser(
        formatter_class=RawDescriptionHelpFormatter,
        description='example',
    )

    parser.add_argument(
        '--sx',
        action='store',
        dest='source_x',
        default=0,
        help='set x coordinate of source frame',
        type=int,
    )

    parser.add_argument(
        '--sy',
        action='store',
        dest='source_y',
        default=0,
        help='set y coordinate of source frame',
        type=int,
    )

    parser.add_argument(
        '--sw',
        action='store',
        dest='source_width',
        default=256,
        help='set width of source frame',
        type=int,
    )
    parser.add_argument(
        '--sh',
        action='store',
        dest='source_height',
        default=256,
        help='set height of source frame',
        type=int,
    )

    parser.add_argument(
        '--tx',
        action='store',
        dest='target_x',
        default=0,
        help='set x coordinate of target frame',
        type=int,
    )

    parser.add_argument(
        '--ty',
        action='store',
        dest='target_y',
        default=0,
        help='set y coordinate of target frame',
        type=int,
    )

    parser.add_argument(
        '--tw',
        action='store',
        dest='target_width',
        default=100,
        help='set width of target frame',
        type=int,
    )

    parser.add_argument(
        '--th',
        action='store',
        dest='target_height',
        default=100,
        help='set height of target frame',
        type=int,
    )

    parser.add_argument(
        '--capture-interval',
        action='store',
        dest='capture_interval',
        default=1000,
        help='capture interval as milisecond (1000 is 1 second)',
        type=int,
    )

    parser.add_argument(
        '--box-color',
        action='store',
        dest='box_color',
        default='(0,255,0)',
        help='specify an RGB color as (R, G, B)',
        type=rgb_color,
    )

    parser.add_argument(
        '--border-size',
        action='store',
        dest='border_size',
        default=2,
        help='set border size of target frame',
        type=int,
    )

    args = parser.parse_args()

    sys.stdout.write('running with:\n')
    sys.stdout.write(f'{args}\n')
    sys.stdout.write('press Q to quit\n')

    try:
        while True:
            screenshot = ImageGrab.grab(
                bbox=(
                    args.source_x,
                    args.source_y,
                    args.source_x + args.source_width,
                    args.source_y + args.source_height,
                )
            )
            frame = np.array(screenshot)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            cv2.rectangle(
                frame,
                (args.target_x, args.target_y),
                (args.target_x + args.target_width, args.target_y + args.target_height),
                args.box_color,
                args.border_size,
            )
            cv2.imshow('screen with rectangle', frame)
            if cv2.waitKey(args.capture_interval) & 0xFF == ord('q'):
                break

    except KeyboardInterrupt:
        pass


cv2.destroyAllWindows()
