# !Note! This program is a small PoC developed for a forensics course at the university of BTH.

### This program is heavily inspired by the fishy framework and utilizes some of their functionality to achieve this PoCs goal. https://www.github.com/dasec/fishy


# EXT4\_DATAFINDER
EXT4\_DATAFINDER is a tool that searches through common "hidden" areas of an ext4 filesystem and extracts information that is found in these areas. The PoC currently supports extracting data from the fields **osd2**, **file slack**, **superblock slack**, **obso_faddr** and **reserved GDT blocks**. This tool does in no way decrypt the data that exists in those placed. It only extracts the contents for further evaluation.

The PoC have been tested in environments that consists of 1 block group and it is possible that file slack detection might break when more than 1 block group exists on the disk.

## Requirements
* An ext4 file system disk
* Python3

## Installation
```bash
$ git clone https://github.com/Liimpo/ext4_datafinder
$ cd <path_to_folder>
```
(**optional**) Create a python virtual environment
```bash
$ pip3 install -r requirements.txt
```
## Usage
To execute the tool one simply needs to supply a disk dump followed by the area one wants to search.
### Example (Extract data in the osd2 field)
```bash
$ python3 ext4_datafinder.py ../ext4-diskdump.dd osd2
```

### Options
The current available options are:
"path-to-diskdump" followed by either [fileslack|superblock|reserved\_gdt|osd2|obso\_faddr]
The -h option also exists for further information about the script
