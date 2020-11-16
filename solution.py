from socket import *
import os
import sys
import struct
import time
import select
import binascii
# Should use stdev

ICMP_ECHO_REQUEST = 8

def sequence(max):
  x = 0
  while True:
    yield x
    x += 1
    if x > max:
      x = 0

seq = sequence(0xffff)

def checksum(string):
    csum = 0
    countTo = (len(string) // 2) * 2
    count = 0

    while count < countTo:
        thisVal = (string[count + 1]) * 256 + (string[count])
        csum += thisVal
        csum &= 0xffffffff
        count += 2

    if countTo < len(string):
        csum += (string[len(string) - 1])
        csum &= 0xffffffff

    csum = (csum >> 16) + (csum & 0xffff)
    csum = csum + (csum >> 16)
    answer = ~csum
    answer = answer & 0xffff
    answer = answer >> 8 | (answer << 8 & 0xff00)
    return answer

def compute_zeroed_checksum(type, code, ID, seqNum, data):
    myChecksum = 0

    # Make a dummy header with a 0 checksum
    # struct -- Interpret strings as packed binary data
    header = struct.pack("bbHHh", type, code, myChecksum, ID, seqNum)
    # Calculate the checksum on the data and the dummy header.
    myChecksum = checksum(header + data)

    # Get the right checksum, and put in the header

    if sys.platform == 'darwin':
        # Convert 16-bit integers from host to network  byte order
        myChecksum = htons(myChecksum) & 0xffff
    else:
        myChecksum = htons(myChecksum)

    return myChecksum

def validate_icmp(ID, seqNum, icmp_data):
  #validate checksum
  icmp_type = icmp_data[0]
  icmp_code = icmp_data[1]
  icmp_checksum = icmp_data[2]
  icmp_id = icmp_data[3]
  icmp_seq = icmp_data[4]
  icmp_payload = icmp_data[5]

  #zero out checksum in header
  zeroed_checksum = compute_zeroed_checksum(icmp_type, icmp_code, icmp_id, icmp_seq, struct.pack("d", icmp_payload))

  return zeroed_checksum == icmp_checksum and ID == icmp_id and icmp_seq == seqNum and icmp_type == 0 and icmp_code == 0

def receiveOnePing(mySocket, ID, timeout, destAddr, seqNum):
    timeLeft = timeout

    while 1:
        startedSelect = time.time()
        whatReady = select.select([mySocket], [], [], timeLeft)
        howLongInSelect = (time.time() - startedSelect)
        if whatReady[0] == []:  # Timeout
            return "Request timed out."

        timeReceived = time.time()
        recPacket, addr = mySocket.recvfrom(1024)

        # Fill in start
        if destAddr == addr[0]:
          icmp_data = struct.unpack('bbHHhd', recPacket[20:])

          if validate_icmp(ID, seqNum, icmp_data):
            delay = (timeReceived-icmp_data[5])*1000
            print(f'Reply from {addr[0]}: bytes={len(recPacket)} time={delay}ms TTL={recPacket[8]}')

        # Fetch the ICMP header from the IP packet

        # Fill in end
        timeLeft = timeLeft - howLongInSelect
        if timeLeft <= 0:
            return "Request timed out."


def sendOnePing(mySocket, destAddr, ID):
    # Header is type (8), code (8), checksum (16), id (16), sequence (16)

    seq_num = next(seq)
    seq_num = seq_num & 0xffff
    send_time = time.time()
    data = struct.pack("d", send_time)

    myChecksum = compute_zeroed_checksum(ICMP_ECHO_REQUEST, 0, ID, seq_num, data)

    header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, myChecksum, ID, seq_num)
    packet = header + data

    mySocket.sendto(packet, (destAddr, 1))  # AF_INET address must be tuple, not str
    return seq_num

    # Both LISTS and TUPLES consist of a number of objects
    # which can be referenced by their position number within the object.

def doOnePing(destAddr, timeout):
    icmp = getprotobyname("icmp")


    # SOCK_RAW is a powerful socket type. For more details:   http://sockraw.org/papers/sock_raw
    mySocket = socket(AF_INET, SOCK_RAW, icmp)

    myID = os.getpid() & 0xFFFF  # Return the current process i
    seq_num = sendOnePing(mySocket, destAddr, myID)
    delay = receiveOnePing(mySocket, myID, timeout, destAddr, seq_num)
    mySocket.close()
    return delay


def ping(host, timeout=1):
    # timeout=1 means: If one second goes by without a reply from the server,  	# the client assumes that either the client's ping or the server's pong is lost
    dest = gethostbyname(host)
    print("Pinging " + dest + " using Python:")
    print("")
    # Calculate vars values and return them
    #  vars = [str(round(packet_min, 2)), str(round(packet_avg, 2)), str(round(packet_max, 2)),str(round(stdev(stdev_var), 2))]
    # Send ping requests to a server separated by approximately one second
    for i in range(0,4):
        delay = doOnePing(dest, timeout)
        print(delay)
        time.sleep(1)  # one second

    return vars

if __name__ == '__main__':
    ping("google.co.il")
