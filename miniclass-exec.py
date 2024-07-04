#!/usr/bin/env python3
import struct
import binascii
import sys
import os

# Logo
LOGO = '''
\x1b[38;5;208m
███╗   ███╗██╗███╗   ██╗██╗ ██████╗██╗      █████╗ ███████╗███████╗      ███████╗██╗  ██╗███████╗ ██████╗
████╗ ████║██║████╗  ██║██║██╔════╝██║     ██╔══██╗██╔════╝██╔════╝      ██╔════╝╚██╗██╔╝██╔════╝██╔════╝
██╔████╔██║██║██╔██╗ ██║██║██║     ██║     ███████║███████╗███████╗█████╗█████╗   ╚███╔╝ █████╗  ██║
██║╚██╔╝██║██║██║╚██╗██║██║██║     ██║     ██╔══██║╚════██║╚════██║╚════╝██╔══╝   ██╔██╗ ██╔══╝  ██║
██║ ╚═╝ ██║██║██║ ╚████║██║╚██████╗███████╗██║  ██║███████║███████║      ███████╗██╔╝ ██╗███████╗╚██████╗
╚═╝     ╚═╝╚═╝╚═╝  ╚═══╝╚═╝ ╚═════╝╚══════╝╚═╝  ╚═╝╚══════╝╚══════╝      ╚══════╝╚═╝  ╚═╝╚══════╝ ╚═════╝
\x1b[0m
                    Coded by:            \x1b[38;5;39mJonathan Bar Or (@yo_yo_yo_jbo)\x1b[0m
                    Writeup:             \x1b[38;5;39mhttps://github.com/yo-yo-yo-jbo/bggp5_java_editing\x1b[0m
'''

# Class header and footer
HEADER = binascii.unhexlify('cafebabe0000003700110a0008000908000a0a0008000b070005010004436f64650100046d61696e010016285b4c6a6176612f6c616e672f537472696e673b295607000c0c000d000e')
FOOTER = binascii.unhexlify('0c000f00100100116a6176612f6c616e672f52756e74696d6501000a67657452756e74696d6501001528294c6a6176612f6c616e672f52756e74696d653b01000465786563010027284c6a6176612f6c616e672f537472696e673b294c6a6176612f6c616e672f50726f636573733b04210004000800000000000100090006000700010005000000150002000100000009b800011202b60003b1000000000000')

# Replacers
REPLACERS = {
    ' '  : '${IFS:0:1}',
    '\t' : '${IFS:1:1}',
    '\n' : '${IFS:2:1}'
}

# Java constant for UTF-8 string tags
CONSTANT_Utf8 = 1

# The expected class name
EXPECTED_CLASS_NAME = 'Code.class'

# The commandline prefix
COMMANDLINE_PREFIX = 'bash -c '

# Byte colors (range, color, is_printable)
BYTE_COLORS = [
    (range(0x00, 0x00 + 1), '\x1b[38;5;240m', False),
    (range(0x01, 0x1f + 1), '\x1b[38;5;219m', False),
    (range(0x20, 0x2f + 1), '\x1b[38;5;27m', True),
    (range(0x30, 0x39 + 1), '\x1b[38;5;81m', True),
    (range(0x3a, 0x40 + 1), '\x1b[38;5;27m', True),
    (range(0x41, 0x5a + 1), '\x1b[38;5;39m', True),
    (range(0x5b, 0x60 + 1), '\x1b[38;5;27m', True),
    (range(0x61, 0x7a + 1), '\x1b[38;5;45m', True),
    (range(0x7b, 0x7e + 1), '\x1b[38;5;27m', True),
    (range(0x7f, 0x7f + 1), '\x1b[38;5;88m', False),
    (range(0x80, 0x80 + 1), '\x1b[38;5;208m', False),
    (range(0x81, 0x8f + 1), '\x1b[38;5;226m', False),
    (range(0x90, 0x90 + 1), '\x1b[38;5;208m', False),
    (range(0x91, 0x9f + 1), '\x1b[38;5;226m', False),
    (range(0xa0, 0xa0 + 1), '\x1b[38;5;208m', False),
    (range(0xa1, 0xaf + 1), '\x1b[38;5;226m', False),
    (range(0xb0, 0xb0 + 1), '\x1b[38;5;208m', False),
    (range(0xb1, 0xbf + 1), '\x1b[38;5;226m', False),
    (range(0xc0, 0xc0 + 1), '\x1b[38;5;208m', False),
    (range(0xc1, 0xcf + 1), '\x1b[38;5;226m', False),
    (range(0xd0, 0xd0 + 1), '\x1b[38;5;208m', False),
    (range(0xd1, 0xdf + 1), '\x1b[38;5;226m', False),
    (range(0xe0, 0xe0 + 1), '\x1b[38;5;208m', False),
    (range(0xe1, 0xef + 1), '\x1b[38;5;226m', False),
    (range(0xf0, 0xf0 + 1), '\x1b[38;5;208m', False),
    (range(0xf1, 0xfe + 1), '\x1b[38;5;91m', False),
    (range(0xff, 0xff + 1), '\x1b[38;5;88m', False)
]

def get_colored_byte(byte):
    """
        Get the byte with its color (hex_form, text_form).
    """

    # Find the byte color
    for entry in BYTE_COLORS:
        if byte in entry[0]:
            text = chr(byte) if entry[2] else '.'
            return (f'{entry[1]}{byte:02x}\x1b[0m', f'{entry[1]}{text}\x1b[0m')

    # Should never happen
    raise Exception(f'Could not find color for byte {byte}')

def print_bytes(data):
    """
        Pretty-prints the given bytes data.
    """

    # Iterate all 16-byte chunks
    for offset in range(0, len(data), 16):

        # Prepare bytes part and text part
        bytes_part = ''
        text_part = ''

        # Will be used for pretty printing
        hex_raw_len = 0

        # Prepare bytes
        chunk = data[offset:offset + 16]
        for i in range(len(chunk)):

            # Get the colors
            hex_form, text_form = get_colored_byte(chunk[i])

            # Add byte
            bytes_part += hex_form
            text_part += text_form
            hex_raw_len += 2

            # Add space if necessary
            if i % 2 == 1 and i < len(chunk) - 1:
                bytes_part += ' '
                hex_raw_len += 1

        # Optionally append spaces
        bytes_part += ' ' * (39 - hex_raw_len)

        # Print the line
        print(f'                    \x1b[38;5;246m{offset:08x}\x1b[0m\x1b[38;5;235m|\x1b[0m{bytes_part}\x1b[38;5;235m|\x1b[0m{text_part}')

def main():
    """
        Main routine.
    """

    # Initialize colors and print logo
    print(LOGO)

    # Best-effort
    try:

        # Parse arguments
        assert len(sys.argv) > 2, Exception(f'Wrong arguments (out_filename, commandline).')
        out_filename = sys.argv[1]
        commandline = ' '.join(sys.argv[2:])
        assert os.path.basename(out_filename) == EXPECTED_CLASS_NAME, Exception(f'Output filename must be "{EXPECTED_CLASS_NAME}".') 

        # Will contain the sanitized commandline
        cmd = commandline[:]
        
        # Build the replaced commandline with no whitespaces
        var_name = 'A'
        for k, v in REPLACERS.items():

            # Skip if the type of whitespace doesn't appear
            if k not in cmd:
                continue

            # Replace whitespace with the $IFS substring if necessary
            cmd_ifs = cmd.replace(k, v)

            # Try to replace using intermediate variables
            cmd_var = f'{var_name}={v};' + cmd.replace(k, '${' + var_name + '}')

            # Take the better of the two
            if len(cmd_var) < len(cmd_ifs):
                cmd = cmd_var
                var_name = chr(ord(var_name) + 1)
            else:
                cmd = cmd_ifs

        # Add the bash prefix
        cmd = f'{COMMANDLINE_PREFIX}{cmd}'

        # Encode string as bytes and ensure length
        cmd_bytes = cmd.encode('utf-8')
        assert len(cmd_bytes) < 2 ** (8 * struct.calcsize('>H')), Exception(f'Resulting commandline is too long ({len(cmd_bytes)} bytes)')

        # Encode the string in the constant pool
        class_bytes = HEADER + struct.pack('>BH', CONSTANT_Utf8, len(cmd_bytes)) + cmd_bytes + FOOTER

        # Print data
        print(f'                    Output path:         \x1b[38;5;39m{out_filename}\x1b[0m')
        print(f'                    Original string:     \x1b[38;5;39m{commandline}\x1b[0m')
        print(f'                    Encoded string size: \x1b[38;5;39m{len(cmd_bytes)} bytes\x1b[0m')
        print(f'                    Total class size:    \x1b[38;5;39m{len(class_bytes)} bytes\x1b[0m')
        print(f'                    New string:          \x1b[38;5;39m{cmd}\x1b[0m')
        
        # Print the file bytes
        print('')
        print_bytes(class_bytes)

        # Write output
        with open(out_filename, 'wb') as fp:
            fp.write(class_bytes)

    except Exception as ex:

        # Output exception
        print(f'                    Error:               \x1b[38;5;88m{ex}\x1b[0m')

if __name__ == '__main__':
    main()

