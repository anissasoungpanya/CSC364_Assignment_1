import socket
import sys
import time
import os
import glob

os.makedirs("./output", exist_ok=True)
# Helper Functions

# The purpose of this function is to set up a socket connection.
def create_socket(host, port):
    # 1. Create a socket.
    soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    soc.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # 2. Try connecting the socket to the host and port.
    try:
        soc.connect((host, port))
    except:
        print("Connection Error to", port)
        sys.exit()
    # 3. Return the connected socket.
    return soc


# The purpose of this function is to read in a CSV file.
def read_csv(path):
    table_list = []
    with open(path, "r") as table_file:
        for line in table_file:
            line = line.strip()
            if not line:
                continue
            parts = [p.strip() for p in line.split(",")]
            table_list.append(parts)
    return table_list


# The purpose of this function is to find the default port
# when no match is found in the forwarding table for a packet's destination IP.
def find_default_gateway(table):
    # 1. Traverse the table, row by row,
    for row in table:
        # 2. and if the network destination of that row matches 0.0.0.0,
        if row[0] == "0.0.0.0":
            # 3. then return the interface of that row.
            return row[3]
    return None


# The purpose of this function is to generate a forwarding table that includes the IP range for a given interface.
# In other words, this table will help the router answer the question:
# Given this packet's destination IP, which interface (i.e., port) should I send it out on?
def generate_forwarding_table_with_range(table):
    # 1. Create an empty list to store the new forwarding table.
    new_table = []
    # 2. Traverse the old forwarding table, row by row,
    for row in table:
        network_dst = row[0]
        netmask = row[1]
        interface = row[3]
        # 3. and process each network destination other than 0.0.0.0
        # (0.0.0.0 is only useful for finding the default port).
        if network_dst == "0.0.0.0":
            continue
        # 4. Store the network destination and netmask.
        # 5. Convert both strings into their binary representations.
        network_dst_bin = ip_to_bin(network_dst)   
        netmask_bin = ip_to_bin(netmask)   
        # 6. Find the IP range.
        network_dst_int = int(network_dst_bin, 2)
        netmask_int = int(netmask_bin, 2)
        min_ip, max_ip = find_ip_range(network_dst_int, netmask_int)
        prefixlen = bin(netmask_int).count("1")
            ## ip_range = ...
            # 7. Build the new row.
        new_row = {
            "min": min_ip,
            "max": max_ip,
            "interface": interface,
            "prefixlen": prefixlen,
            "net": network_dst,
            "mask": netmask,
        }
            # 8. Append the new row to new_table.
            ## new_table.append(new_row)
        new_table.append(new_row)
    # 9. Return new_table.
    return new_table


# The purpose of this function is to convert a string IP to its binary representation.
def ip_to_bin(ip):
    # 1. Split the IP into octets.
    ip_octets = ip.split(".")
    # 2. Create an empty string to store each binary octet.
    ip_bin_string = ""
    # 3. Traverse the IP, octet by octet,
    for octet in ip.split("."):
        # 4. and convert the octet to an int,
        # 5. convert the decimal int to binary,
        # 6. convert the binary to string and remove the "0b" at the beginning of the string,
        # 7. while the sting representation of the binary is not 8 chars long,
        # then add 0s to the beginning of the string until it is 8 chars long
        # (needs to be an octet because we're working with IP addresses).
        # 8. Finally, append the octet to ip_bin_string.
        ip_bin_string += bin(int(octet))[2:].zfill(8)
    # 9. Once the entire string version of the binary IP is created, convert it into an actual binary int.
    # 10. Return the binary representation of this int.
    return bin(int(ip_bin_string, 2))


# The purpose of this function is to find the range of IPs inside a given a destination IP address/subnet mask pair.
def find_ip_range(network_dst, netmask):
    # 1. Perform a bitwise AND on the network destination and netmask
    # to get the minimum IP address in the range.
    bitwise_and = network_dst & netmask
    # 2. Perform a bitwise NOT on the netmask
    # to get the number of total IPs in this range.
    # Because the built-in bitwise NOT or compliment operator (~) works with signed ints,
    # we need to create our own bitwise NOT operator for our unsigned int (a netmask).
    compliment = bit_not(netmask, 32)
    min_ip = bitwise_and
    # 3. Add the total number of IPs to the minimum IP
    # to get the maximum IP address in the range.
    max_ip = min_ip + compliment
    # 4. Return a list containing the minimum and maximum IP in the range.
    return [min_ip, max_ip]


# The purpose of this function is to perform a bitwise NOT on an unsigned integer.
def bit_not(n, numbits=32):
    return (1 << numbits) - 1 - n


# The purpose of this function is to write packets/payload to file.
def write_to_file(path, packet_to_write, send_to_router=None):
    # 1. Open the output file for appending.
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    out_file = open(path, "a")
    # 2. If this router is not sending, then just append the packet to the output file.
    if send_to_router is None:
        out_file.write(packet_to_write + "\n")
    # 3. Else if this router is sending, then append the intended recipient, along with the packet, to the output file.
    else:
        out_file.write(packet_to_write + " " + "to Router " + send_to_router + "\n")
    # 4. Close the output file.
    out_file.close()


# Main Program

# 0. Remove any output files in the output directory
# (this just prevents you from having to manually delete the output files before each run).
files = glob.glob('./output/*')
for f in files:
    os.remove(f)

# 1. Connect to the appropriate sending ports (based on the network topology diagram).
sock_to_r2 = create_socket("127.0.0.1", 8002)
sock_to_r4 = create_socket("127.0.0.1", 8004)

port_to_sock = {
    "8002": sock_to_r2,
    "8004": sock_to_r4,
}
port_to_router = {
    "8002": "2",
    "8004": "4",
}
# 2. Read in and store the forwarding table.
forwarding_table = read_csv("./input/router_1_table.csv")
# 3. Store the default gateway port.
default_gateway_port = find_default_gateway(forwarding_table)
# 4. Generate a new forwarding table that includes the IP ranges for matching against destination IPS.
forwarding_table_with_range = generate_forwarding_table_with_range(forwarding_table)

# 5. Read in and store the packets.
packets_table = read_csv("./input/packets.csv")

sent_path = "./output/sent_by_router_1.txt"
discarded_path = "./output/discarded_by_router_1.txt"
out_path = "./output/out_router_1.txt"

# 6. For each packet,
for row in packets_table:
    # 7. Store the source IP, destination IP, payload, and TTL.
    sourceIP = row[0]
    destinationIP = row[1]
    payload = row[2]
    ttl = int(row[3])

    # 8. Decrement the TTL by 1 and construct a new packet with the new TTL.
    new_ttl = ttl - 1
    new_packet = f"{sourceIP},{destinationIP},{payload},{new_ttl}"

    # 9. Convert the destination IP into an integer for comparison purposes.
    destinationIP_bin = ip_to_bin(destinationIP)
    destinationIP_int = int(destinationIP_bin, 2)

    # 9. Find the appropriate sending port to forward this new packet to.
    matching_IP = []
    for entry in forwarding_table_with_range:
        if entry["min"] <= destinationIP_int <= entry["max"]:
            matching_IP.append(entry)
    send_interface = None
    if matching_IP:
        matching_IP.sort(key=lambda e: e["prefixlen"], reverse=True)
        send_interface = matching_IP[0]["interface"]

    # 10. If no port is found, then set the sending port to the default port.
    if not send_interface:
        send_interface = default_gateway_port
    

    # 11. Either
    # (a) send the new packet to the appropriate port (and append it to sent_by_router_1.txt),
    # (b) append the payload to out_router_1.txt without forwarding because this router is the last hop, or
    # (c) append the new packet to discarded_by_router_1.txt and do not forward the new packet
    if send_interface == "8002":       
        print("sending packet", new_packet, "to Router 2")
        write_to_file(sent_path, new_packet, "2")
        sock_to_r2.sendall((new_packet + "\n").encode("utf-8"))
    elif send_interface == "8004":     
        print("sending packet", new_packet, "to Router 4")
        write_to_file(sent_path, new_packet, "4")
        sock_to_r4.sendall((new_packet + "\n").encode("utf-8"))
    elif send_interface == "127.0.0.1":
        print("OUT:", payload)
        write_to_file(out_path, payload)
    else:
        print("DISCARD:", new_packet)
        write_to_file(discarded_path, new_packet)

    # Sleep for some time before sending the next packet (for debugging purposes)
    time.sleep(1)
