#!/usr/bin/env python3

import sys
import curses
from pygdbmi.gdbcontroller import GdbController

NUM_ROW_BYTES = 16
BYTE_SPACING = 4

gdbmi = GdbController()


def get_stack_bytes(num_bytes):
    response = gdb_cmd('-data-read-memory-bytes $rsp %d' % num_bytes)
    bytestr = response[0]['payload']['memory'][0]['contents']
    return [int(bytestr[i:i + 2], 16) for i in range(0, len(bytestr), 2)]


def init_screen(stdscr, memory):
    stdscr.clear()

    for i, b in enumerate(memory):
        r = i // NUM_ROW_BYTES
        c = i % NUM_ROW_BYTES

        stdscr.addstr(r, c * BYTE_SPACING, '{:02x}'.format(b))

    stdscr.move(0, 0)


def main_loop(stdscr, memory):
    while True:
        c = stdscr.getch()
        y, x = stdscr.getyx()

        if c == ord('q'):
            break
        elif c == curses.KEY_UP and y != 0:
            stdscr.move(y - 1, x)
        elif c == curses.KEY_DOWN and y != curses.LINES - 1:
            stdscr.move(y + 1, x)
        elif c == curses.KEY_LEFT and x != 0:
            if x % 2 == 0:
                shift = BYTE_SPACING - 1
            else:
                shift = 1
            stdscr.move(y, x - shift)
        elif c == curses.KEY_RIGHT and x < (
            NUM_ROW_BYTES - 1
        ) * BYTE_SPACING + 1:
            if x % 2 == 0:
                shift = 1
            else:
                shift = BYTE_SPACING - 1
            stdscr.move(y, x + shift)
        else:
            if (c >= ord('0')
                and c <= ord('9')) or (c >= ord('a') and c <= ord('f')):
                stdscr.addstr(chr(c))

                # The cursor automatically moves forward, we need to move it
                # back as we'll shift it ourselves later
                stdscr.move(y, x)

                if c <= ord('9'):
                    nibble = c - ord('0')
                else:
                    nibble = c - ord('a') + 10

                offset = y * NUM_ROW_BYTES + (x // BYTE_SPACING)
                old_val = memory[offset]
                if x % 2 == 0:
                    new_val = (nibble << 4) | (old_val & 0xF)
                else:
                    new_val = (old_val & 0xF0) | nibble

                gdb_cmd(
                    '-data-write-memory-bytes $rsp+{} {:02x}'.format(
                        offset, new_val
                    )
                )
                memory[offset] = new_val

                if x >= (NUM_ROW_BYTES - 1) * BYTE_SPACING + 1:
                    continue

                if x % 2 == 0:
                    shift = 1
                else:
                    shift = BYTE_SPACING - 1
                stdscr.move(y, x + shift)

        stdscr.refresh()


def gdb_cmd(cmd):
    response = gdbmi.write(cmd)
    if response[0]['message'] == 'error':
        raise Exception(response)
    return response


def debug_binary(path):
    gdb_cmd('file %s' % path)
    gdb_cmd('starti')


def main(stdscr):
    if len(sys.argv) < 2:
        raise Exception('Usage: ./main.py /path/to/binary')
    debug_binary(sys.argv[1])
    memory = get_stack_bytes(32)
    init_screen(stdscr, memory)
    main_loop(stdscr, memory)


curses.wrapper(main)

print('New value of memory: ', list(map(hex, get_stack_bytes(32))))
