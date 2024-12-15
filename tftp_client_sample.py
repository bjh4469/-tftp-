#!/usr/bin/python3
'''
$ tftp ip_address [-p port_mumber] <get|put> filename
'''
import os
import sys
import socket
import argparse
# import validators
from struct import pack

DEFAULT_PORT = 69
BLOCK_SIZE = 512
DEFAULT_TRANSFER_MODE = 'octet'

OPCODE = {'RRQ': 1, 'WRQ': 2, 'DATA': 3, 'ACK': 4, 'ERROR': 5}
MODE = {'netascii': 1, 'octet': 2, 'mail': 3}

ERROR_CODE = {
    0: "Not defined, see error message (if any).",
    1: "File not found.",
    2: "Access violation.",
    3: "Disk full or allocation exceeded.",
    4: "Illegal TFTP operation.",
    5: "Unknown transfer ID.",
    6: "File already exists.",
    7: "No such user."
}


def send_wrq(filename, mode):
    format = f'>h{len(filename)}sB{len(mode)}sB'
    wrq_message = pack(format, OPCODE['WRQ'], bytes(filename, 'utf-8'), 0, bytes(mode, 'utf-8'), 0)
    sock.sendto(wrq_message, server_address)
    # print(wrq_message)


def send_rrq(filename, mode):
    format = f'>h{len(filename)}sB{len(mode)}sB'
    rrq_message = pack(format, OPCODE['RRQ'], bytes(filename, 'utf-8'), 0, bytes(mode, 'utf-8'), 0)
    sock.sendto(rrq_message, server_address)
    #print(rrq_message)


def send_ack(seq_num, server):
    format = f'>hh'
    ack_message = pack(format, OPCODE['ACK'], seq_num)
    sock.sendto(ack_message, server)
    print(seq_num)
    print(ack_message)

def send_data(block_num, data_block, server):
    """Send DATA packet to server."""
    format = f'>hh{len(data_block)}s'
    data_message = pack(format, OPCODE['DATA'], block_num, data_block)
    sock.sendto(data_message, server)

def put_file(filename, mode):
    """Handle file upload (PUT) to server."""
    # Send WRQ to server
    send_wrq(filename, mode)

    # Open the file to be uploaded
    try:
        file = open(filename, 'rb')
    except FileNotFoundError:
        print("File not found.")
        sys.exit(1)

    block_num = 0

    while True:
        # Read the next block of data
        file_block = file.read(BLOCK_SIZE)
        block_num += 1

        # Send the data block to server
        send_data(block_num, file_block, server_address)

        # Wait for ACK from server
        try:
            data, server_new_socket = sock.recvfrom(516)
            opcode = int.from_bytes(data[:2], 'big')

            if opcode == OPCODE['ACK']:
                ack_block_num = int.from_bytes(data[2:4], 'big')
                if ack_block_num == block_num:
                    print(f"ACK received for block {block_num}")
                else:
                    print(f"Unexpected ACK block number: {ack_block_num}")
            elif opcode == OPCODE['ERROR']:
                error_code = int.from_bytes(data[2:4], byteorder='big')
                print(f"Error from server: {ERROR_CODE[error_code]}")
                file.close()
                sys.exit(1)
        except socket.timeout:
            print(f"Timeout waiting for ACK for block {block_num}")
            file.close()
            sys.exit(1)

        # If the last block was less than BLOCK_SIZE, transfer is complete
        if len(file_block) < BLOCK_SIZE:
            print("File upload completed.")
            break

    file.close()


# parse command line arguments
parser = argparse.ArgumentParser(description='TFTP client program')
parser.add_argument(dest="host", help="Server IP address", type=str)
parser.add_argument(dest="operation", help="get or put a file", type=str)
parser.add_argument(dest="filename", help="name of file to transfer", type=str)
parser.add_argument("-p", "--port", dest="port", type=int)
args = parser.parse_args()

# if validators.domain(args.host):
#     server_ip = gethostbyname(args.host)
# else
#     server_ip = args.host
#
# if args.port == None:
#     server_port = DEFAULT_PORT


# Create a UDP socket
server_ip = args.host
server_port = DEFAULT_PORT
server_address = (server_ip, server_port)
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

mode = DEFAULT_TRANSFER_MODE
operation = args.operation
filename = args.filename

# Send RRQ_message
send_rrq(filename, mode)

# Open a file to save data from server
file = open(filename, 'wb')
expected_block_number = 1

# Determine operation and call respective function
if operation == "get":
    send_rrq(filename, mode)
    file = open(filename, 'wb')
    expected_block_number = 1

    while True:
        # receive data from server
        data, server_new_socket = sock.recvfrom(516)
        opcode = int.from_bytes(data[:2], 'big')

        if opcode == OPCODE['DATA']:
            block_number = int.from_bytes(data[2:4], 'big')
            if block_number == expected_block_number:
                send_ack(block_number, server_new_socket)
                file_block = data[4:]
                file.write(file_block)
                expected_block_number += 1
                print(file_block.decode())
            else:
                send_ack(block_number, server_new_socket)

        elif opcode == OPCODE['ERROR']:
            error_code = int.from_bytes(data[2:4], byteorder='big')
            print(ERROR_CODE[error_code])
            file.close()
            os.remove(filename)
            break

        if len(file_block) < BLOCK_SIZE:
            file.close()
            print("File transfer completed.")
            break

elif operation == "put":
    put_file(filename, mode)


else:
    print("Invalid operation. Use 'get' or 'put'.")
    sys.exit(1)