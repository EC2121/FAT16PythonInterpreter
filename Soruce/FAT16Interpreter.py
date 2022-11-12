import os
import struct


class Fat16Interpreter:
    class BadClusterException(Exception):
        pass

    def __init__(self):
        self.full_disk = []
        self.linked_list = {}
        self.reserved_sectors = 0
        self.sector_size = 0
        self.FAT_sector_start_index = 0
        self.FAT_size = 0
        self.FAT_copies = 0
        self.root_directory_start_index = 0
        self.dir_entries = 0
        self.dir_entry_size = 32
        self.clusters_start_index = 0
        self.disk_name = "nope"

    def read_disk_image(self, path):
        disk_image = open(path, "rb")
        full_disk = disk_image.read(os.stat(path).st_size)
        self.initialize_variables(full_disk)
        self.read_root_dir(full_disk)
        disk_image.close()

    def read_root_dir(self, full_disk):
        root_directory = full_disk[self.root_directory_start_index: self.clusters_start_index]
        for i in range(self.dir_entries):
            file_type = hex(root_directory[11 + i * self.dir_entry_size])
            entry_name = root_directory[i * self.dir_entry_size: 11 + (i * self.dir_entry_size)].decode("utf-8")
            match file_type:
                case '0x0':
                    continue
                case '0x8':
                    self.disk_name = entry_name
                    print('disk name: ' + entry_name)
                case '0x10':
                    print(' folder ' + entry_name.rstrip() + ':')
                    cluster_offset = (i * self.dir_entry_size) + 26
                    cluster_index = struct.unpack("<H", root_directory[cluster_offset: cluster_offset + 2])[0]
                    self.read_file_allocation_table(cluster_index, True)

    def read_file_allocation_table(self, starting_cluster_index, is_folder):
        curr_node_index = starting_cluster_index
        next_node_index = self.find_next_node_index(curr_node_index)
        if hex(next_node_index) == "0xfff7":
            raise self.BadClusterException()
        elif hex(next_node_index) == "0xffff":
            self.read_cluster(curr_node_index, is_folder)
            return
        else:
            self.create_linked_list(curr_node_index)

    def read_cluster(self, curr_node_index, is_folder):
        starting_index = self.clusters_start_index + (512 * (curr_node_index - 2))
        if is_folder:
            starting_index += self.dir_entry_size * 2
            curr_cluster = self.full_disk[starting_index: starting_index + self.sector_size - 64]
            for i in range(len(curr_cluster) // self.dir_entry_size):
                file_type = curr_cluster[11 + i * self.dir_entry_size]
                cluster_offset = (i * self.dir_entry_size) + 26
                cluster_index = struct.unpack("<H", curr_cluster[cluster_offset: cluster_offset + 2])[0]
                match hex(file_type):
                    case '0x0':
                        continue
                    case '0x20':
                        file_name_offset = i * self.dir_entry_size
                        file_ext_offset = 8 + i * self.dir_entry_size
                        file_name = curr_cluster[file_name_offset: 8 + file_name_offset].decode("utf-8").rstrip()
                        file_ext = curr_cluster[file_ext_offset: file_ext_offset + 3].decode("utf-8")
                        print('     ' + file_name + '.' + file_ext + ':')
                        self.read_file_allocation_table(cluster_index, False)
        else:
            curr_cluster = self.full_disk[starting_index: starting_index + 512]
            print("         " + curr_cluster[0: curr_cluster.index(10)].decode("utf-8"))

    def create_linked_list(self, curr_node_index):
        next_node_index = self.find_next_node_index(curr_node_index)
        while hex(next_node_index) <= "0xfff8":
            self.linked_list[curr_node_index] = next_node_index
            curr_node_index = next_node_index
            next_node_index = self.find_next_node_index(curr_node_index)

    def find_next_node_index(self, curr_node_index):
        offset = (self.FAT_sector_start_index + (curr_node_index * 2))
        next_node_index = struct.unpack("<H", self.full_disk[offset: offset + 2])[0]
        return next_node_index

    def initialize_variables(self, full_disk):
        self.full_disk = full_disk
        self.reserved_sectors = struct.unpack("<H", full_disk[14:14 + 2])[0]
        self.sector_size = struct.unpack("<H", full_disk[11:11 + 2])[0]
        self.FAT_size = struct.unpack("<H", full_disk[22:22 + 2])[0]
        self.FAT_copies = struct.unpack("<b", full_disk[16:16 + 1])[0]
        self.dir_entries = struct.unpack("<H", full_disk[17:17 + 2])[0]
        self.FAT_sector_start_index = self.reserved_sectors * self.sector_size
        self.root_directory_start_index = self.FAT_sector_start_index + \
                                          (self.FAT_copies * self.FAT_size * self.sector_size)
        self.clusters_start_index = self.root_directory_start_index + (self.dir_entries * self.dir_entry_size)


fat16Int = Fat16Interpreter()
fat16Int.read_disk_image("test.img")
