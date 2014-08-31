#TTWEHost by Rijnard van Tonder 2014

import time
import os
import stat

import sys
import binascii
import array
import time
import warnings

from GoodFETMAXUSB import GoodFETMAXUSBHost

import signal

global client

def signal_handler(signal, frame):
  print('Exiting host...')
  client.usb_disconnect()
  sys.exit(0)


class HostRelayDevice:
  OUT_EP = 0x1
  IN_EP = 0x2
  IN2_EP = 0x3
  
  verbose = True

  read_ep0_snd = open("/tmp/ep0_snd", "r")
  write_ep0_rcv = open("/tmp/ep0_rcv", "w")

  rcv_ep1 = open("/tmp/ep1", "r")  # reads host (client mode) EP3OUT and forwards to device
  snd_ep3 = open("/tmp/ep3", "w")  # writes device data response to EP1IN and forwards to host (client mode)

  configured = False

  rcv = ""
  snd = "\n"

  rcv_ep1_data = ""
  snd_ep3_data = "\n"

  def before_handle(self):

    self.rcv = "" # initialize
    self.rcv = self.read_ep0_snd.readline()
    if len(self.rcv) > 1:
      pass

    self.rcv_ep1_data = ""
    self.rcv_ep1_data = self.rcv_ep1.readline()
    if len(self.rcv_ep1_data) > 1:
      pass

    self.write_ep0_rcv.write(self.snd)
    self.write_ep0_rcv.flush()
    self.snd = "\n"
    if len(self.snd) > 1:
      print("Sending %s on ep0" % self.snd)

    self.snd_ep3.write(self.snd_ep3_data)
    self.snd_ep3.flush()
    self.snd_ep3_data = "\n"
    if len(self.snd_ep3_data) > 1:
      print("Sending %s on ep3" % self.snd_ep3_data)

  def after_handle(self):
    pass

  def handle_snd_buffer_available(self):
    # EP0 HANDLER
    if len(self.rcv) > 3: # parse
      rcv = eval(self.rcv) # TODO serialize properly

      if rcv[1] == 0x09: # if this is set configuration
        client.set_configuration(rcv)
        return
      elif rcv[1] == 0x05:
        print('A set_address request!')
        client.reset_bus()
        client.set_address(rcv)
        return
      elif rcv[1] == 0x0b:
        print('A set_interface request!')
        status = client.ctl_write_nd(rcv)
        print('ctl_write_nd status is %d' % status)
        return
      # TODO add clear_feature request

      print('Sending %s' % rcv)
      status = client.ctl_read(rcv) # ctl_read reads a request from the device
      print('Done checking, status: %s' % status)

      if status:
        print('Something went wrong: %s' % status)

      if rcv[0] == 161 and rcv[1] == 254:
        print('CONFIGURED!')

    if len(self.rcv_ep1_data) > 3: # The device is using ep2, we are getting it from ep according to map
      rcv = eval(self.rcv_ep1_data) # TODO serialize properly

      if self.verbose:
        print('writing OUT data %s to EP%d' % (rcv,self.OUT_EP))
      client.OUT_Transfer(self.OUT_EP, rcv) # read_data in response to this

  def read_data_into_rcv_buffer(self):
    # after issuing OUT_Transfer, call IN_Transfer.
    client.read_data(self.IN_EP)
    client.read_data(self.IN2_EP)

  def handle_rcv_data_available(self, data, endpoint):
    if self.verbose:
      print('Got data: %s, EP%d' % (data, endpoint))
    if endpoint == 0:
      self.snd = str(data)+'\n'
      self.write_ep0_rcv.write(self.snd)
      self.write_ep0_rcv.flush()
      self.snd = '\n'
    elif endpoint == self.IN_EP: # the device is using EP1, we are sending it out on EP3 according to map
      self.snd_ep3_data = str(data)+'\n'
      self.snd_ep3.write(self.snd_ep3_data)
      self.snd_ep3.flush()
      self.snd_ep3_data = '\n'

if __name__ == '__main__':
  #Initialize FET and set baud rate
  client=GoodFETMAXUSBHost();
  client.serInit()

  client.MAXUSBsetup();

  print('host init')
  client.hostinit(HostRelayDevice()); # hub detects device
  client.usbverbose=False;

  print('device detect')
  client.detect_device(); # detect the device-low or full speed
  time.sleep(0.2); 

  client.soft_enumerate() # reset bus, set address 0 #5

  client.reset_bus()

  print('done enumerating, deferring to irqs')
  client.service_irqs()
  client.usb_disconnect()
