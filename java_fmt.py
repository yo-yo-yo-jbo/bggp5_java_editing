#!/usr/bin/env python3
import sys
import struct
from enum import Enum
import binascii
import colorama
import os

# Initialize colorama
colorama.init()

# Constant types
class ConstType(Enum):
    CONSTANT_Class = 7
    CONSTANT_Fieldref = 9
    CONSTANT_Methodref= 10
    CONSTANT_InterfaceMethodref = 11
    CONSTANT_String = 8
    CONSTANT_Integer = 3
    CONSTANT_Float = 4
    CONSTANT_Long = 5
    CONSTANT_Double = 6
    CONSTANT_NameAndType = 12
    CONSTANT_Utf8 = 1
    CONSTANT_MethodHandle = 15
    CONSTANT_MethodType = 16
    CONSTANT_InvokeDynamic = 18

class JavaObject(object):
    """
        Container for a class that can be freely be added attributes.
    """

    def __init__(self, const_pool, start_offset):
        """
            Constructor.
        """

        # Keep a reference to the constant pool
        self._const_pool = const_pool
        
        # Used for pretty-printing
        self._depth = 0

        # Just tracking
        self._start_offset = start_offset

    def __str__(self):
        """
            Returns a string.
        """

        # Return a reprenting string
        prefix = '  ' * self._depth
        result = []
        for k, v in self.__dict__.items():
            if k.startswith('_'):
                continue
            if k.endswith('_index'):
                result.append(f'{prefix}{colorama.Fore.WHITE}{colorama.Style.BRIGHT}{k}{colorama.Style.RESET_ALL} ({colorama.Fore.RED}{v}{colorama.Style.RESET_ALL}) -->')
                other_obj = self._const_pool[v - 1]
                other_obj._depth = self._depth + 1
                result.append(f'{other_obj}')
            elif isinstance(v, list):
                result.append(f'{prefix}{colorama.Fore.WHITE}{colorama.Style.BRIGHT}{k}{colorama.Style.RESET_ALL}: [')
                for other_obj in v:
                    other_obj._depth = self._depth + 1
                    result.append(f'{other_obj}')
                result.append(f'{prefix}]')
            elif isinstance(v, bytes):
                data = binascii.hexlify(v, ' ').decode()
                result.append(f'{prefix}{colorama.Fore.WHITE}{colorama.Style.BRIGHT}{k}{colorama.Style.RESET_ALL} = {colorama.Fore.RED}{data}{colorama.Style.RESET_ALL}')
            elif isinstance(v, str):
                fore_color = colorama.Fore.YELLOW + colorama.Style.DIM if k == 'tag' else colorama.Fore.LIGHTBLUE_EX
                result.append(f'{prefix}{colorama.Fore.WHITE}{colorama.Style.BRIGHT}{k}{colorama.Style.RESET_ALL} = {fore_color}{v}{colorama.Style.RESET_ALL}')
            else:
                result.append(f'{prefix}{colorama.Fore.WHITE}{colorama.Style.BRIGHT}{k}{colorama.Style.RESET_ALL} = {colorama.Fore.GREEN}{v}{colorama.Style.RESET_ALL}')
        return '\n'.join(result)

class JavaClass(object):
    """
        Represents a Java class.
    """

    def __init__(self, file_path):
        """
            Constructor.
        """

        # Save the file path and parse
        self.file_path = file_path
        self._parse()

    @staticmethod
    def _read_bytes_from_fp(fp, struct_fmt):
        """
            Reads a struct format from the given file.
        """

        # Return either a tuple or a single entry
        result = struct.unpack(struct_fmt, fp.read(struct.calcsize(struct_fmt)))
        if len(result) == 1:
            return result[0]
        return result

    def _parse(self):
        """
            Parses the class file.
        """

        # Open the file for reading
        with open(self.file_path, 'rb') as fp:

            # Parse the header
            self.const_pool = []
            self.header = JavaObject(self.const_pool, fp.tell())
            self.header.magic, self.header.version_minor, self.header.major, const_pool_count = JavaClass._read_bytes_from_fp(fp, '>LHHH')
            assert self.header.magic == 0xCAFEBABE, Exception(f'Invalid header magic {hdr_magic}')
            assert const_pool_count > 0, Exception(f'Invalid constant pool count {const_pool_count}')
            
            # Parse the constasnt pool
            for index in range(const_pool_count - 1):

                # Save type and parse it
                curr_obj = JavaObject(self.const_pool, fp.tell())
                curr_obj.tag = JavaClass._read_bytes_from_fp(fp, '>B')
                if curr_obj.tag == ConstType.CONSTANT_Class.value:
                    curr_obj.name_index = JavaClass._read_bytes_from_fp(fp, '>H')
                elif curr_obj.tag in (ConstType.CONSTANT_Fieldref.value, ConstType.CONSTANT_Methodref.value, ConstType.CONSTANT_InterfaceMethodref.value):
                    curr_obj.class_index, curr_obj.name_and_type_index = JavaClass._read_bytes_from_fp(fp, '>HH')
                elif curr_obj.tag == ConstType.CONSTANT_String.value:
                    curr_obj.string_index = JavaClass._read_bytes_from_fp(fp, '>H')
                elif curr_obj.tag in (ConstType.CONSTANT_Integer.value, ConstType.CONSTANT_Float.value):
                    curr_obj.data = JavaClass._read_bytes_from_fp(fp, '>l')
                elif curr_obj.tag in (ConstType.CONSTANT_Long.value, ConstType.CONSTANT_Double.value):
                    hi, lo = JavaClass._read_bytes_from_fp(fp, '>lL')
                    curr_obj.data = hi << 32 + lo
                elif curr_obj.tag == ConstType.CONSTANT_NameAndType.value:
                    curr_obj.name_index, curr_obj.descriptor_index = JavaClass._read_bytes_from_fp(fp, '>HH')
                elif curr_obj.tag == ConstType.CONSTANT_Utf8.value:
                    curr_len = JavaClass._read_bytes_from_fp(fp, '>H')
                    curr_obj.data = fp.read(curr_len).decode('utf-8')
                elif curr_obj.tag == ConstType.CONSTANT_MethodHandle.value:
                    curr_obj.reference_kind, curr_obj.reference_index = JavaClass._read_bytes_from_fp(fp, '>BH')
                elif curr_obj.tag == ConstType.CONSTANT_MethodType.value:
                    curr_obj.descriptor_index = JavaClass._read_bytes_from_fp(fp, '>H')
                elif curr_obj.tag == ConstType.CONSTANT_InvokeDynamic.value:
                    curr_obj.bootstrap_method_attr_index, curr_obj.name_and_type_index = JavaClass._read_bytes_from_fp(fp, '>HH')
                else:
                    raise Exception(f'Invalid tag {curr_obj.tag}')

                # Prettify tag
                curr_obj.tag = ConstType(curr_obj.tag).name

                # Add entry
                self.const_pool.append(curr_obj)

            # Parse the class descriptor
            self.class_descriptor = JavaObject(self.const_pool, fp.tell())
            self.class_descriptor.access_flags, self.class_descriptor.this_class_index, self.class_descriptor.super_class_index, interfaces_count = JavaClass._read_bytes_from_fp(fp, '>HHHH')

            # Save interfaces
            self.interfaces = []
            for interface_index in range(interfaces_count):
                self.interfaces.append(JavaClass._read_bytes_from_fp(fp, '>H'))

            # Parse fields
            fields_count = JavaClass._read_bytes_from_fp(fp, '>H')
            self.fields = []
            for field_index in range(fields_count):
                field = JavaObject(self.const_pool, fp.tell())
                field.access_flags, field.name_index, field.descriptor_index = JavaClass._read_bytes_from_fp(fp, '>HHH')
                field.attributes = self._parse_attributes(fp)
                self.fields.append(field)

            # Parse methods
            methods_count = JavaClass._read_bytes_from_fp(fp, '>H')
            self.methods = []
            for method_index in range(methods_count):
                method = JavaObject(self.const_pool, fp.tell())
                method.access_flags, method.name_index, method.descriptor_index = JavaClass._read_bytes_from_fp(fp, '>HHH')
                method.attributes = self._parse_attributes(fp)
                self.methods.append(method)

            # Parse attributes
            self.attributes = self._parse_attributes(fp)

    def _parse_attributes(self, fp):
        """
            Parses attributes.
        """

        # Read the number of attributes
        attributes_count = JavaClass._read_bytes_from_fp(fp, '>H')

        # Parse
        attributes = []
        for attr_index in range(attributes_count):
            attr = JavaObject(self.const_pool, fp.tell())
            attr.attribute_name_index, attr_len = JavaClass._read_bytes_from_fp(fp, '>HL')
            attr.data = fp.read(attr_len)
            attributes.append(attr)

        # Return attributes
        return attributes

def clear_screen():
    """
        Clears the screen.
    """

    # Clear the screen
    if os.name == 'nt':
        os.system('cls')
    else:
        os.system('clear')

def do_menu(jclass):
    """
        Present a menu and act accordingly.
    """

    # Run forever
    is_first = True
    while True:

        # Show the menu
        if not is_first:
            print('')
        is_first = False
        print(f'{colorama.Fore.CYAN}MENU{colorama.Style.RESET_ALL}')
        print(f'{colorama.Fore.WHITE}{colorama.Style.BRIGHT}FILE{colorama.Style.RESET_ALL}: {colorama.Fore.GREEN}{os.path.basename(jclass.file_path)}{colorama.Style.RESET_ALL}')
        print(f'[{colorama.Fore.WHITE}{colorama.Style.BRIGHT}H{colorama.Style.RESET_ALL}]eader')
        print(f'[{colorama.Fore.WHITE}{colorama.Style.BRIGHT}C{colorama.Style.RESET_ALL}]onstant pool ({colorama.Fore.LIGHTBLUE_EX}{len(jclass.const_pool)}{colorama.Style.RESET_ALL})')
        print(f'[{colorama.Fore.WHITE}{colorama.Style.BRIGHT}D{colorama.Style.RESET_ALL}]escriptor for the class')
        print(f'[{colorama.Fore.WHITE}{colorama.Style.BRIGHT}I{colorama.Style.RESET_ALL}nterfaces ({colorama.Fore.LIGHTBLUE_EX}{len(jclass.interfaces)}{colorama.Style.RESET_ALL})')
        print(f'[{colorama.Fore.WHITE}{colorama.Style.BRIGHT}F{colorama.Style.RESET_ALL}]ields ({colorama.Fore.LIGHTBLUE_EX}{len(jclass.fields)}{colorama.Style.RESET_ALL})')
        print(f'[{colorama.Fore.WHITE}{colorama.Style.BRIGHT}M{colorama.Style.RESET_ALL}]ethods ({colorama.Fore.LIGHTBLUE_EX}{len(jclass.methods)}{colorama.Style.RESET_ALL})')
        print(f'[{colorama.Fore.WHITE}{colorama.Style.BRIGHT}A{colorama.Style.RESET_ALL}]ttributes ({colorama.Fore.LIGHTBLUE_EX}{len(jclass.attributes)}{colorama.Style.RESET_ALL})')
        print(f'[{colorama.Fore.WHITE}{colorama.Style.BRIGHT}Q{colorama.Style.RESET_ALL}]uit')
    
        # Get choice and parse number
        choice = input('> ').upper()
        num = None
        clear_screen()
        try:
            if len(choice) > 1:
                num = int(choice[1:])
                choice = choice[0]
        except Exception:
            print(f'{colorama.Fore.RED}INVALID CHOICE{colorama.Style.RESET_ALL}')
            continue

        # Handle quitting
        if choice == 'Q':
            break

        # Print the header
        elif choice == 'H':
            print(f'{colorama.Fore.CYAN}HEADER{colorama.Style.RESET_ALL}')
            print(jclass.header)
            continue

        # Print the class descriptor
        elif choice == 'D':
            print(f'{colorama.Fore.CYAN}CLASS DESCRIPTOR{colorama.Style.RESET_ALL}')
            print(jclass.class_descriptor)
            continue

        # Maps choices to lists and use it to print list items
        choice_to_list = { 'C' : (jclass.const_pool, 'CONSTANT POOL'),
                           'I' : (jclass.interfaces, 'INTERFACES'),
                           'F' : (jclass.fields, 'FIELDS'),
                           'M' : (jclass.methods, 'METHODS'),
                           'A' : (jclass.attributes, 'ATTRIBUTES') }
        if choice not in choice_to_list:
            print(f'{colorama.Fore.RED}INVALID CHOICE{colorama.Style.RESET_ALL}')
            continue
        if num is None:
            print(f'{colorama.Fore.CYAN}{choice_to_list[choice][1]}{colorama.Style.RESET_ALL}')
            for obj in choice_to_list[choice][0]:
                print(obj)
            continue
        if num <= 0 or num > len(choice_to_list[choice][0]):
            print(f'{colorama.Fore.RED}INVALID CHOICE{colorama.Style.RESET_ALL}')
            continue
        print(f'{colorama.Fore.CYAN}{choice_to_list[choice][1]}{colorama.Style.RESET_ALL} ({colorama.Fore.RED}{num}{colorama.Style.RESET_ALL})')
        print(choice_to_list[choice][0][num - 1])
        continue

        # Invalid choice
        print(f'{colorama.Fore.RED}INVALID CHOICE{colorama.Style.RESET_ALL}')

        # Print one more linebreak
        print('')

# Catch exceptions
try:

    # Parse the Java class
    jclass = JavaClass(sys.argv[1])

    # Run menu
    clear_screen()
    do_menu(jclass)

except Exception as e:
    print(f'{colorama.Fore.RED}ERROR{colorama.Style.RESET_ALL}: {e}')
