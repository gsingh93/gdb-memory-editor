# GDB Memory Editor

![Demo Video](./demo.gif)


This is small proof of concept of a `curses`-based hex editor for the memory of an application being debugged with GDB. To run it:
```
./main.py /usr/bin/ls
```

It will launch the supplied binary with GDB, break on the first instruction, and display 32 bytes of memory starting at the stack pointer. You can use the arrow keys to move to each byte and modify the value. Pressing 'q' will exit the application.

Pressing '!' will allow you to directly type GDB commands and see the output. In the demo above, you can see that the command `x/32/xb $rsp` confirms that the bytes were modified.
