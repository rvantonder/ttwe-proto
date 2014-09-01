#TTWEClient by Rijnard van Tonder 2014

import os
import stat
import time
import sys
import signal
import random
import subprocess
import argparse

from Facedancer import *
from MAXUSBApp import *

global u

def signal_handler(signal, frame):
  print("Exiting...")
  u.disconnect()
  sys.exit(0)

class TTWEClientDevice:

  verbose = True

  name = "TTWEClient Device"

  write_ep0_snd = open("/tmp/ep0_snd", "w")
  read_ep0_rcv = open("/tmp/ep0_rcv", "r")

  snd_ep1 = open("/tmp/ep1", "w") # writes host data to EP1OUT and forwards to host mode
  rcv_ep3 = open("/tmp/ep3", "r")  # reads device data from EP3IN and forwards to device mode (issues ask IN from device)

  file_log = open("usbcomms.log", "w")

  configured = False

  rcv = ""
  snd = "\n"

  rcv_ep3_data = ""
  snd_ep1_data = "\n"

  start = True

  fuzz_ep0 = False 
  fuzz_ep1 = False

  def __init__(self, verbose, fuzz):
    self.verbose = verbose
    if fuzz == 0:
      self.fuzz_ep0 = True
    elif fuzz == 1:
      self.fuzz_ep1 = True

  def flip_bits(self, l):
    l = eval(l[:-1])
    index = random.choice(range(0,len(l)))
    byte_to_mutate = l[index] 
    mask = random.choice(range(0,256))

    msg = 'index: %d    |    byte to mutate: %d   |   mask: %d    |    result %d' % (index, byte_to_mutate, mask, byte_to_mutate ^ mask)
    print(msg)
    self.file_log.write("bit flip: %s\n" % msg)

    l[index] = mask ^ byte_to_mutate
    return str(l)+'\n'

  def before_handle(self):

    if not self.start: # to get past the readline() block
      self.rcv = "" # initialize every time
      self.rcv = self.read_ep0_rcv.readline() # '\n' if no data
      if len(self.rcv) > 1:
        if self.fuzz_ep0:
          if random.random()*2 < 1: # flip with 50/50 probability during enumeration (EP0)
            self.rcv = self.flip_bits(self.rcv)

        self.file_log.write(">>[0] %s" % self.rcv)
        self.file_log.flush()

      self.rcv_ep3_data = ""
      self.rcv_ep3_data = self.rcv_ep3.readline()
      if len(self.rcv_ep3_data) > 1:
        if self.fuzz_ep1:
          if random.random()*50 < 1: # 1/50 chance to flip during EP1 data transfer
            self.rcv_ep3_data = self.flip_bits(self.rcv_ep3_data)

        self.file_log.write(">>[3] %s" % self.rcv_ep3_data)
        self.file_log.flush()

    if len(self.snd) > 1:
      self.file_log.write("<<[0] %s" % self.snd)
      self.file_log.flush()
      if self.verbose:
        print("Sending %s to ep0 of PERIPH" % self.snd)

    if len(self.snd_ep1_data) > 1:
      self.file_log.write("<<[1] %s" % self.snd_ep1_data)
      self.file_log.flush()
      if self.verbose:
        print("Sending %s to ep1 of PERIPH" % self.snd_ep1_data)

    self.write_ep0_snd.write(self.snd) # send '\n' if no data
    self.write_ep0_snd.flush()
    self.snd = "\n" # after sending a payload 'x' or empty ('\n'), reset

    self.snd_ep1.write(self.snd_ep1_data)
    self.snd_ep1.flush()
    self.snd_ep1_data = "\n"

    self.start = False

  def after_handle(self):
    pass

  def handle_request(self, req):
    '''
    This is only for requests, get EP0 data from host
    '''

    req = list(req.raw_bytes)
    if self.verbose:
      print('Request from HOST: %s' % req)

    if req[1] == 9: # if it is set_configuration
      if self.verbose:
        print('set_configuration acked') # blindly acks to the host
      u.ack_status_stage()
      self.rcv = "" # don't let it send a reply
    if req[1] == 5: # ack set_address
      if self.verbose:
        print('set_address acked')
      u.ack_status_stage()
      self.rcv = "" # don't let it send a reply
    if req[1] == 1: # ack clear_feature
      print('clear_feature acked')
      u.ack_status_stage()
      self.rcv = ""
    if req[1] == 0x0b:
      print('set_interface acked')
      u.ack_status_stage()
      self.rcv = ""
    if req[1] == 3: #
      print('acking set feature. Is this a USB HUB?')
      u.ack_status_stage()
      self.rcv = ""

    self.snd = str(req)+'\n' # prepare for sending over pipe

  def handle_data_available(self, ep_num, data):
    '''
    The authentic host has data for us.
    This is for the data stage, e.g. get EP1OUT data from host
    '''
    if self.verbose:
      print("Data from Authentic host on EP%d: %s" % (ep_num,list(data)))
    self.snd_ep1_data = str(list(data))+'\n' # send over ep1out pipe

  def handle_buffer_available(self, ep_num): # I'm using EP3IN, remember that
    '''
    This is for sending data to the authentic host, e.g. EP0 or EP3IN
    '''
    if ep_num == 0x03: # only for ep3
      if len(self.rcv) > 3:
        rcv = eval(self.rcv) # TODO  seralize properly

        # configured, or lun
        if not self.configured or (len(rcv) == 1 and rcv[0] == 0): # send on ep 0
          if len(rcv) != 1: # if it is, its the lun, for mass storage devices
            if rcv[1] == 2: # hijack interface
             
              if self.verbose:  
                print('Hijacking endpoint descriptor, mapping to maxusb: %s' % rcv)
              rcv = self.hijack_ep(rcv) # will be sent on endpoint 0

          if self.verbose:
            print('Reply from PERIPH is %s\nString:%s' % (rcv, ''.join(map(chr, rcv))))

          u.send_on_endpoint(0x0, bytes(rcv)) 

      if len(self.rcv_ep3_data) > 3:
        if self.verbose:
          print('Got resp: %s' % self.rcv_ep3_data)
        rcv = self.rcv_ep3_data.split(', ') # use local variable to simplify
        rcv[-1] = rcv[-1][:-2] # get rid of ']\n'
        rcv[0] = rcv[0][1:] # get rid of [
        rcv = list(map(int, rcv))

        u.send_on_endpoint(0x2, bytes(rcv)) # endpoint 3 # FIXME hardcoding

  def hijack_ep(self, rcv):
    '''
    Take the descriptor, and modify the endpoints
    '''

    rest = rcv[rcv[0]:] # start at interface
    if len(rest) > 0: #there's more
      rest = rest[rest[0]:] # trim interface, start at endpoint a
      endpoint_a = rest[:rest[0]] # save endpoint a
      rest = rest[rest[0]:] # set start to endpoint b

      offset_a = 0x9 + 0x9 + 0x3 - 1
     
      endpoint_a_address = endpoint_a[2]
      desired_a = endpoint_a_address & 0x0f

      if self.verbose:
        print('---PERIPHERAL--||||---FACEDANCER---')

      if endpoint_a_address & 0x80: # IN
        if self.verbose:
          print('MAP:   EP%dIN  <====>  EP%dIN' % (desired_a, 2))
        rcv[offset_a] = 0x80 | 0x02 
      else:
        if self.verbose:
          print('MAP:   EP%dOUT <====>  EP%dOUT' % (desired_a, 1))
        rcv[offset_a] = 0x00 | 0x01 

      # 2ND ENDPOINT IF DETECTED:
      if len(rest) > 0:
        endpoint_b = rest[:rest[0]] # if there's still left, get it
        rest = rest[rest[0]:] # set start to endpoint index

        offset_b = 0x9 + 0x9 + 0x7 + 0x3 - 1

        endpoint_b_address = endpoint_b[2]
        desired_b = endpoint_b_address & 0x0f

        if endpoint_b_address & 0x80: # IN
          if self.verbose:
            print('MAP:   EP%dIN  <====>  EP%dIN' % (desired_b, 2))
          rcv[offset_b] = 0x80 | 0x02 
        else:
          if self.verbose:
            print('MAP:   EP%dOUT <====>  EP%dOUT' % (desired_b, 1))
          rcv[offset_b] = 0x00 | 0x01 


      # 3RD ENDPOINT, IF DETECTED:
      if len(rest) > 0:
        endpoint_c = rest
        offset_c = 0x9 + 0x9 + 0x7 + 0x7 + 0x3 - 1
        endpoint_c_address = endpoint_c[2]
        desired_c = endpoint_c_address & 0x0f

        rest = rest[rest[0]:]
        if len(rest) > 0:
          print('THREE endpoints and theres STILL more: %s' % rest)

        if endpoint_c_address & 0x80: #IN, we can handle a third endpoint
          if self.verbose:
            print('MAP:   EP%dIN  <====>  EP%dIN' % (desired_c, 3))
          rcv[offset_c] = 0x80 | 0x03
        else:
          print('ERROR: 3RD ENDPOINT CANNOT BE HANDLED, NOT AN "IN" ENDPOINT')

      if self.verbose:
        print("MODIFIED endpoint descriptors: %s" % rcv)

    return rcv

if __name__ == '__main__':

  signal.signal(signal.SIGINT, signal_handler)

  parser = argparse.ArgumentParser()
  parser.add_argument("-v", "--verbose", action="store_true",
      help="turn on verbose output of USB communication")
  parser.add_argument("--fuzz", type=int, default=-1, help="endpoint to be fuzzed (0 for device enumeration phase)")

  args = parser.parse_args()

  sp = GoodFETSerialPort()
  fd = Facedancer(sp, verbose=1)
  u = MAXUSBApp(fd, verbose=1)

  print("Attempting connection")
  u.connect(TTWEClientDevice(args.verbose, args.fuzz))
  print("Done connecting")
  u.service_irqs()
  print ("Running")
  u.disconnect()
