# GDB Memory Editor

![Demo Video](./demo.gif)


This is small proof of concept of a `curses`-based hex editor for the memory of an application being debugged with GDB. Currently, it will allow you to launch a binary and break on the first instruction, view and edit 32 bytes of memory starting at the stack pointer, and then after exiting it re-reads the memory from GDB and prints it to confirm if your changes were actually made.

To run it:
```
./main.py /usr/bin/ls
```

Use the arrow keys to move around, modify any byte with the hex digits you want, and then press 'q' to quit. You should see your changes printed out.
