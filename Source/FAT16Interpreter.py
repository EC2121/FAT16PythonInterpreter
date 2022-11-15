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
        self.disk_name = 'nope'

    def read_disk_image(self, path):
        disk_image = open(path, 'rb')
        full_disk = disk_image.read(os.stat(path).st_size)
        self.initialize_variables(full_disk)
        self.read_root_dir(full_disk)
        disk_image.close()

    def match_file_type(self, file_type, curr_cluster, curr_offset):
        entry_name = curr_cluster[curr_offset: 11 + curr_offset].decode('utf-8')
        match file_type:
            case '0x0':
                return  # null
            case '0x8':  # disk name
                self.disk_name = entry_name
                print('disk name: ' + entry_name)
            case '0x10':  # folder
                print(' folder ' + entry_name.rstrip() + ':')
                # get the cluster index of the folder and read the FAT
                cluster_offset = curr_offset + 26
                cluster_index = struct.unpack('<H', curr_cluster[cluster_offset: cluster_offset + 2])[0]
                self.read_file_allocation_table(cluster_index, True)
            case '0x20':  # file
                cluster_offset = curr_offset + 26
                cluster_index = struct.unpack('<H', curr_cluster[cluster_offset: cluster_offset + 2])[
                    0]  # get cluster index
                file_name_offset = curr_offset
                file_ext_offset = 8 + curr_offset
                file_name = curr_cluster[file_name_offset: 8 + file_name_offset].decode(
                    'utf-8').rstrip()  # get file name
                file_ext = curr_cluster[file_ext_offset: file_ext_offset + 3].decode("utf-8")  # get file ext
                print('     ' + file_name + '.' + file_ext + ':')
                self.read_file_allocation_table(cluster_index,
                                                False)  # read the FAT this time is_folder is false

    def read_root_dir(self, full_disk):
        # Entire root directory
        root_directory = full_disk[self.root_directory_start_index: self.clusters_start_index]
        # cycle all the directory entries
        for i in range(self.dir_entries):
            # read the file type and name
            curr_offset = i * self.dir_entry_size
            file_type = hex(root_directory[11 + curr_offset])
            self.match_file_type(file_type, root_directory, curr_offset)

    def read_file_allocation_table(self, starting_cluster_index, is_folder):
        # read the FAT at the given index
        curr_node_index = starting_cluster_index
        next_node_index = self.find_next_node_index(curr_node_index)
        if hex(next_node_index) == '0xfff7':  # case bad cluster
            raise self.BadClusterException()
        elif curr_node_index not in self.linked_list.keys():
            self.create_linked_list(curr_node_index)
        self.read_cluster(curr_node_index, is_folder)

    def read_cluster(self, curr_node_index, is_folder):
        while curr_node_index != '0xffff':
            starting_index = self.clusters_start_index + (self.sector_size * (curr_node_index - 2))
            if is_folder:
                starting_index += self.dir_entry_size * 2  # we know it is a folder so we can skip the first 64 bytes
                curr_cluster = self.full_disk[
                               starting_index: starting_index + self.sector_size - 64]  # we get the curr cluster( minus the first 64)
                for i in range(len(curr_cluster) // self.dir_entry_size):  # read every entry
                    curr_offset = i * self.dir_entry_size
                    file_type = curr_cluster[11 + curr_offset]  # get file type
                    self.match_file_type(hex(file_type), curr_cluster, curr_offset)
            else:  # it's a file and we can read it
                curr_cluster = self.full_disk[starting_index: starting_index + self.sector_size]
                print("         " + curr_cluster[0: curr_cluster.index(10)].decode("utf-8"))
            curr_node_index = self.linked_list[curr_node_index]

    def create_linked_list(self, curr_node_index):
        next_node_index = self.find_next_node_index(curr_node_index)  # read the FAT at curr index
        if hex(next_node_index) == '0xffff':
            self.linked_list[curr_node_index] = hex(next_node_index)
        else:
            while hex(next_node_index) <= '0xfff8':  # until we find the end of the file we keep reading
                self.linked_list[hex(curr_node_index)] = hex(next_node_index)
                curr_node_index = next_node_index
                next_node_index = self.find_next_node_index(curr_node_index)

    def find_next_node_index(self, curr_node_index):
        offset = (self.FAT_sector_start_index + (curr_node_index * 2))
        next_node_index = struct.unpack('<H', self.full_disk[offset: offset + 2])[0]
        return next_node_index

    def initialize_variables(self, full_disk):
        self.full_disk = full_disk
        self.reserved_sectors = struct.unpack('<H', full_disk[14:14 + 2])[0]
        self.sector_size = struct.unpack('<H', full_disk[11:11 + 2])[0]
        self.FAT_size = struct.unpack('<H', full_disk[22:22 + 2])[0]
        self.FAT_copies = struct.unpack('<b', full_disk[16:16 + 1])[0]
        self.dir_entries = struct.unpack('<H', full_disk[17:17 + 2])[0]
        self.FAT_sector_start_index = self.reserved_sectors * self.sector_size
        self.root_directory_start_index = self.FAT_sector_start_index + \
                                          (self.FAT_copies * self.FAT_size * self.sector_size)
        self.clusters_start_index = self.root_directory_start_index + (self.dir_entries * self.dir_entry_size)


fat16Int = Fat16Interpreter()
fat16Int.read_disk_image('disk_image_test/test.img')
print(fat16Int.linked_list)
