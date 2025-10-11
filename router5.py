import socket
import sys
import traceback
import os
from threading import Thread

# Helper Functions

# The purpose of this function is to set up a socket connection.
def create_socket(host, port):
    # 1. Create a socket.
    soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    soc.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # 2. Try connecting the socket to the host and port.y
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
            if not line or line.startswith("#"):
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
            ## network_dst_string = ...
            ## netmask_string = ...
            # 5. Convert both strings into their binary representations.
        network_dst_bin = ip_to_bin(network_dst)   
        netmask_bin = ip_to_bin(netmask)   
            # 6. Find the IP range.
        network_dst_int = int(network_dst_bin, 2)
        netmask_int = int(netmask_bin, 2)
        min_ip, max_ip = find_ip_range(network_dst_int, netmask_int)
        prefixlen = bin(netmask_int).count("1")
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
        new_table.append(new_row)
    # 9. Return new_table.
    return new_table


# The purpose of this function is to convert a string IP to its binary representation.
def ip_to_bin(ip):
    # 1. Split the IP into octets.
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


# The purpose of this function is to perform a bitwise NOT on an unsigned integer.
def bit_not(n, numbits=32):
    return (1 << numbits) - 1 - n


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


# The purpose of this function is to receive and process an incoming packet.
def receive_packet(connection, max_buffer_size):
    # 1. Receive the packet from the socket.
    received_packet = connection.recv(max_buffer_size)
    # 2. If the packet size is larger than the max_buffer_size, print a debugging message
    packet_size = sys.getsizeof(received_packet)
    if packet_size > max_buffer_size:
        print("The packet size is greater than expected", packet_size)
    # 3. Decode the packet and strip any trailing whitespace.
    decoded_packet = received_packet.decode("utf-8").strip()
    # 3. Append the packet to received_by_router_5.txt.
    print("received packet", decoded_packet)
    write_to_file("./output/received_by_router_5.txt", decoded_packet)
    # 4. Split the packet by the delimiter.
    packet = decoded_packet.split(",") if decoded_packet else []
    # 5. Return the list representation of the packet.
    return packet


# The purpose of this function is to write packets/payload to file.
def write_to_file(path, packet_to_write, send_to_router=None):
    # 1. Open the output file for appending.
    try:
        out_file = open(path, "a")
    except FileNotFoundError:
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


# The purpose of this function is to
# (a) create a server socket,
# (b) listen on a specific port,
# (c) receive and process incoming packets
def start_server():
    #1. Create a socket
    host = "127.0.0.1"
    port = 8005
    soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    soc.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    print("Socket created")
    # 2. Try binding the socket to the appropriate host and receiving port (based on the network topology diagram).
    try:
        soc.bind((host, port))
    except:
        print("Bind failed. Error : " + str(sys.exc_info()))
        sys.exit()
    # 3. Set the socket to listen.
    soc.listen(16)
    print("Socket now listening")

    # 4. Read in and store the forwarding table.
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    router5_table_path = os.path.join(BASE_DIR, "input", "router_5_table.csv")

    try:
        forwarding_table = read_csv(router5_table_path)
    except FileNotFoundError:
        print(f"[Router 5] Missing forwarding table at: {router5_table_path}")
        sys.exit(1)

    # 5. Store the default gateway port.
    default_gateway_port = find_default_gateway(forwarding_table)
    # 6. Generate a new forwarding table that includes the IP ranges for matching against destination IPS.
    forwarding_table_with_range = generate_forwarding_table_with_range(forwarding_table)

    # 7. Continuously process incoming packets.
    while True:
        # 8. Accept the connection.
        connection, address = soc.accept()
        ip, rport = address[0], str(address[1])
        print("Connected with " + ip + ":" + str(port))
        # 9. Start a new thread for receiving and processing the incoming packets.
        try:
            Thread(
                target=processing_thread,
                args=(connection, ip, rport, forwarding_table_with_range, default_gateway_port),
                daemon=True,
            ).start()
        except:
            print("Thread did not start.")
            traceback.print_exc()



# The purpose of this function is to receive and process incoming packets.
def processing_thread(connection, ip, port, forwarding_table_with_range, default_gateway_port, max_buffer_size=5120):
    discarded_path = "./output/discarded_by_router_5.txt"
    out_path = "./output/out_router_5.txt"

    # 2. Continuously process incoming packets
    while True:
        # 3. Receive the incoming packet, process it, and store its list representation
        packet = receive_packet(connection, max_buffer_size)

        # 4. If the packet is empty (Router has finished sending all packets), break out of the processing loop
        if not packet:
            break

        # 5. Store the source IP, destination IP, payload, and TTL.
        sourceIP = packet[0]
        destinationIP = packet[1]
        payload = packet[2]
        ttl = int(packet[3])

        # 6. Decrement the TTL by 1 and construct a new packet with the new TTL.
        new_ttl = ttl - 1
        new_packet = f"{sourceIP},{destinationIP},{payload},{new_ttl}"

        if new_ttl <= 0:
            print("DISCARD (TTL<=0):", new_packet)
            write_to_file(discarded_path, new_packet)
            continue

        # 7. Convert the destination IP into an integer for comparison purposes.
        destinationIP_bin = ip_to_bin(destinationIP)
        destinationIP_int = int(destinationIP_bin, 2)

        # 8. Find the appropriate sending port to forward this new packet to.
        matching_IP = []
        for entry in forwarding_table_with_range:
            if entry["min"] <= destinationIP_int <= entry["max"]:
                matching_IP.append(entry)

        send_interface = None
        if matching_IP:
            matching_IP.sort(key=lambda e: e["prefixlen"], reverse=True)
            send_interface = matching_IP[0]["interface"]

        # 9. If no port is found, then set the sending port to the default port.
        if not send_interface:
            send_interface = default_gateway_port

        # 11. Either
        # (a) append the payload to out_router_5.txt without forwarding because this router is the last hop, or
        # (b) append the new packet to discarded_by_router_5.txt and do not forward the new packet

        if send_interface == "127.0.0.1":
            print("OUT:", payload)
            write_to_file(out_path, payload)
        else:
            print("DISCARD:", new_packet)
            write_to_file(discarded_path, new_packet)
    try:
        connection.close()
    except Exception:
        pass

# Main Program

# 1. Start the server.
start_server()