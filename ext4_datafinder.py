import sys
import builtins
import time
import argparse
from pytsk3 import FS_Info, Img_Info

def fs_parser(device):
    fs_info = FS_Info(device, offset=0)
    return fs_info.info.block_size

def read_superblock(device, block_size):
    # Start at the 2048 byte because of bootsector and superblock 
    # a block is 4096 long so read the size of slackspace. if 0 stop.
    # Check to find if more bytes exist in the slackspace or not
    offset = 2048
    slackspace = block_size - 2048
    device.seek(slackspace)
    buf = bytearray()
    for i in device.read(slackspace):
        if not i:
            break
        buf.append(i)
    _print(buf)

def parse(image, offset, length, structure, byteorder='little'):
    data_dict = {}
    image.seek(offset)

    data = image.read(length)
    for key in structure:
        offset = structure[key]['offset']
        size = structure[key]['size']

        bytes = data[offset:offset+size]
        value = int.from_bytes(bytes, byteorder=byteorder)

        if "format" in structure[key]:
            if structure[key]["format"] == "ascii":
                value = bytes.decode('ascii')
            elif structure[key]["format"] == "raw":
                value = bytes
            elif structure[key]["format"] == "time":
                value = time.gmtime(value)
            else:
                form = getattr(builtins, structure[key]["format"])
                value = form(value)

        data_dict[key] = value
    return data_dict

def read_inodes(device, block_size):
    inode_structure = {
        "size":         {"offset": 0x4, "size": 4},
        "blocks":       {"offset": 0x1C, "size": 4},
        "extent_tree":  {"offset": 0x28, "size": 60, "format": "raw"},
        "obso_faddr":   {"offset": 0x70, "size": 4},
        "osd2":         {"offset": 0x74, "size": 12, "format": "raw"},
    }
    extent_leaf_nodes = {
        "block": {"offset": 0x0, "size": 4},
        "len": {"offset": 0x4, "size": 2},
        "start_hi": {"offset": 0x6, "size": 2},
        "start_lo": {"offset": 0x8, "size": 4},
    }
    inodes = []
    device.seek(block_size+8)

    bytes = device.read(4)
    value = int.from_bytes(bytes, byteorder='little')
    inode_table_start = value * block_size
    device.seek(1024+0x58)
    bytes = device.read(4)
    inode_size = int.from_bytes(bytes, byteorder='little')
    device.seek(1024+0x28)
    bytes = device.read(4)
    inodes_per_group = int.from_bytes(bytes, byteorder='little')*inode_size
    
    for address in range(inode_table_start, inode_table_start+inodes_per_group, inode_size):
        inode = parse(device, address, inode_size, inode_structure) 
        extents = inode["extent_tree"]
        leaf_nodes = extents[12:24]
        data = {}
        for key, value in extent_leaf_nodes.items():
            field_offset = value["offset"]
            field_size = value["size"]
            bytes = leaf_nodes[field_offset:field_offset+field_size]
            data[key] = int.from_bytes(bytes, byteorder='little')
            inode[key] = int.from_bytes(bytes, byteorder='little')
            inode["address"] = address
        inodes.append(inode)
    return inodes, inode_table_start, inode_size

def find_fileslack(device, inodes):
    for inode in inodes:
        # First inodes in the fs are reserved.
        if inode["start_lo"] > 20:
            device.seek(inode["start_lo"] * 4096 + inode["size"])
            buf = device.read(4096 - inode["size"])
            _print(buf)

def find_osd2(device, inodes, inode_table_start, inode_size):
    for inode in inodes:
        device.seek(inode["address"] + 0x74 + 0xA)
        if not device.read(2) == b'\x00\x00':
            device.seek(inode["address"] + 0x74 + 0xA)
            buf = device.read(2)
            _print(buf)

def find_obso_faddr(device, inodes, inode_table_start, inode_size):
    for inode in inodes:
        device.seek(inode["address"] + 0x70)
        if not device.read(4) ==  b'\x00\x00\x00\x00':
            device.seek(inode["address"] + 0x70)
            buf = device.read(4)
            _print(buf)

def find_gdt_reserve(device, total_block_count, block_size):
    gdt_size = 1
    block_gdt_id = total_block_count + gdt_size + 2
    offset = block_size * block_gdt_id
    device.seek(offset)
    buf = device.read(block_size)
    _print(buf)

def _print(data):
    """
    If data is bytes, write to stdout using sys.stdout.buffer.write,
    otherwise, assume it's str and convert to bytes with utf-8
    encoding before writing.
    """
    sys.stdout.buffer.write(data)

superblock_structure = {"blocks_per_group":   {"offset": 0x20, "size": 4}, "total_block_count":  {"offset": 0x4, "size": 4}}

parser = argparse.ArgumentParser(description="Find hidden files inside of an ext4 filesystem")
parser.add_argument("Diskdump",
                type=str,
                help="The location of the designated drive.")
parser.add_argument("Option",
                type=str,
                help="The detection method. Available options are: [osd2|superblock|reserved_gdt|fileslack|obsofaddr]")

args = parser.parse_args()

disk_location = args.Diskdump
mode = args.Option

# Start doing cool things.
# read disk
imported_image = Img_Info(disk_location)
block_size = fs_parser(imported_image)
fs_stream = open(disk_location, "rb")

parsed_superblock = parse(fs_stream, 1024, 1024, superblock_structure)
m, inode_table_size, inode_size = read_inodes(fs_stream,block_size)

if "osd2" in mode:
    find_osd2(fs_stream, m, inode_table_size, inode_size)
elif "superblock" in mode:
    read_superblock(fs_stream,block_size)
elif "reserved_gdt" in mode:
    find_gdt_reserve(fs_stream, parsed_superblock["blocks_per_group"], block_size)
elif "fileslack" in mode:
    find_fileslack(fs_stream, m)
elif "obso_faddr" in mode:
    find_obso_faddr(fs_stream, m, inode_table_size, inode_size)
else:
    print("That mode does not exist. Use either [osd2|superblock|reserved_gdt|fileslack|obso_faddr]")
