#!/usr/bin/env python3

import sys
import curses
from pygdbmi.gdbcontroller import GdbController
import traceback

NUM_ROW_BYTES = 16
BYTE_SPACING = 4
LEFT_OFFSET = 18

CONSOLE_LINE = None
LOG_LINE = 20

gdbmi = GdbController()

log_messages = []


def coord_to_byte(y, x):
    # In the byte 4E, 4 is digit 0 and E is digit 1, and bytes always start at
    # an even coordinate
    digit = x % 2

    r = y
    c = (x - LEFT_OFFSET) // BYTE_SPACING

    return r * NUM_ROW_BYTES + c, digit


def byte_to_coord(offset):
    r = offset // NUM_ROW_BYTES
    c = offset % NUM_ROW_BYTES

    y = r
    x = c * BYTE_SPACING + LEFT_OFFSET

    return y, x


def get_stack_bytes(num_bytes):
    response = gdb_cmd('-data-read-memory-bytes $rsp %d' % num_bytes)
    memory = response[0]['payload']['memory'][0]
    begin_addr = int(memory['begin'], 16)
    contents = memory['contents']
    return begin_addr, [
        int(contents[i:i + 2], 16) for i in range(0, len(contents), 2)
    ]


def log(s):
    log_messages.append(s)


def handle_input(stdscr, memory):
    c = stdscr.getch()

    y, x = stdscr.getyx()
    max_y, max_x = stdscr.getmaxyx()
    offset, digit = coord_to_byte(y, x)

    if c == ord('q'):
        return False
    elif c == ord('!'):
        stdscr.hline(
            curses.LINES - 1, 0, ' ', curses.COLS, curses.color_pair(1)
        )

        curses.echo()
        stdscr.attron(curses.color_pair(1))
        cmd = stdscr.getstr(CONSOLE_LINE, 0, 1000).decode('ascii')
        stdscr.attroff(curses.color_pair(1))
        curses.noecho()

        if cmd != '':
            gdb_cmd(cmd)

        stdscr.move(y, x)
    elif c == curses.KEY_UP and y != 0:
        stdscr.move(y - 1, x)
    elif c == curses.KEY_DOWN and y != max_y - 1:
        stdscr.move(y + 1, x)
    elif c == curses.KEY_LEFT and x != LEFT_OFFSET:
        if digit == 0:
            shift = BYTE_SPACING - 1
        else:
            shift = 1
        stdscr.move(y, x - shift)
    elif c == curses.KEY_RIGHT and (
        offset % NUM_ROW_BYTES != NUM_ROW_BYTES - 1 or digit != 1
    ):
        if digit == 0:
            shift = 1
        else:
            shift = BYTE_SPACING - 1
        stdscr.move(y, x + shift)
    elif (c >= ord('0') and c <= ord('9')) or (c >= ord('a') and c <= ord('f')):
        stdscr.addch(chr(c))

        # The cursor automatically moves forward, we need to move it
        # back as we'll shift it ourselves later
        stdscr.move(y, x)

        old_val = memory[offset]
        nibble = int(chr(c), 16)

        if x % 2 == 0:
            new_val = (nibble << 4) | (old_val & 0xF)
        else:
            new_val = (old_val & 0xF0) | nibble

        gdb_cmd(
            '-data-write-memory-bytes $rsp+{} {:02x}'.format(offset, new_val)
        )
        memory[offset] = new_val

        if offset % NUM_ROW_BYTES != NUM_ROW_BYTES - 1 or digit != 1:
            if digit == 0:
                shift = 1
            else:
                shift = BYTE_SPACING - 1
            stdscr.move(y, x + shift)

    return True


def display_log(stdscr):
    old_y, old_x = stdscr.getyx()

    y = LOG_LINE
    x = 0
    stdscr.move(y, x)

    # Last line is reserved for the console
    for message in log_messages[-(curses.LINES - LOG_LINE - 2):]:
        stdscr.addstr(str(message))
        y += 1
        stdscr.move(y, x)

    stdscr.move(old_y, old_x)


def main_loop(stdscr, begin_addr, memory):
    cur_y, cur_x = 0, LEFT_OFFSET

    while True:
        stdscr.clear()

        for i, b in enumerate(memory):
            if i % NUM_ROW_BYTES == 0:
                r = i // NUM_ROW_BYTES
                stdscr.addstr(r, 0, hex(begin_addr + i) + ': ')

            y, x = byte_to_coord(i)

            stdscr.addstr(y, x, '{:02x}'.format(b))

        # Move the cursor back to where it was before we cleared the screen
        stdscr.move(cur_y, cur_x)

        display_log(stdscr)

        # Update the display
        stdscr.refresh()

        if not handle_input(stdscr, memory):
            break

        cur_y, cur_x = stdscr.getyx()


def gdb_cmd(cmd):
    response = gdbmi.write(cmd)

    for res in response:
        if res['type'] == 'result' and res['message'] == 'error':
            log(res)
            raise Exception(res)
        elif res['type'] == 'console':
            log(res['payload'])
        elif res['type'] == 'log':
            log(res['payload'])

    return response


def debug_binary(path):
    gdb_cmd('file %s' % path)
    gdb_cmd('starti')


def main(stdscr):
    if len(sys.argv) < 2:
        log('Usage: ./main.py /path/to/binary')
        return False
    debug_binary(sys.argv[1])
    begin_addr, memory = get_stack_bytes(32)

    height = curses.LINES
    width = curses.COLS
    win = curses.newwin(height, width, 0, 0)
    win.keypad(True)

    if curses.can_change_color():
        # If the terminal supports it, make the background grey
        curses.init_color(curses.COLOR_BLACK, 200, 200, 200)

        # The color of the console background will be a darker shade of grey
        curses.init_color(curses.COLOR_YELLOW, 400, 400, 400)

    curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_YELLOW)

    global CONSOLE_LINE
    CONSOLE_LINE = curses.LINES - 1

    main_loop(win, begin_addr, memory)

    return True


try:
    curses.wrapper(main)
except Exception:
    print(traceback.format_exc())
finally:
    for message in log_messages:
        print(message)
