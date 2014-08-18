# USBDevice.py
#
# Contains class definitions for USBDevice and USBDeviceRequest.

import sys
import inspect

from USB import *
from USBClass import *
from util import bytes_as_hex, verbose
from USBDescriptor import *


# p115
descriptor_type_lookup = {0x00 : "NONE",    # when we send a get_descriptor, we want to know one of these things
                          0x01 : "device",
                          0x02 : "configuration",
                          0x03 : "string",
                          0x04 : "interface",
                          0x05 : "endpoint",
                          0x06 : "device_qualifier",
                          0x07 : "other_speed_configuration",
                          0x08 : "interface_power",
                          0x09 : "OTG",
                          0x0a : "debug",
                          0x0b : "interface_association",
                          0x22 : "report descriptor",
                          0x23 : "physical descriptor",
                          -1   : "unknown"}

# p148
request_lookup = {0x00 : "get_status",     # when we send a descriptor request, it's one of these
                  0x01 : "clear_feature",
                  # TODO what is 2?? interesting
                  0x03 : "set_feature",
                  0x05 : "set_address",
                  # TODO what is 4?? interesting
                  0x06 : "get_descriptor",
                  0x07 : "set_descriptor",
                  0x08 : "get_configuration",
                  0x09 : "set_configuration",
                  0x0a : "get_interface",
                  0x0b : "set_interface",
                  0x0c : "synch_frame"}
# p148
wvalue_lookup = { 0x00 : "0",              # this is usually for a string that we want
                  0x01 : "feature",
                  0x03 : "feature",
                  0x05 : "device address",
                  0x06 : "descriptor type and index",
                  0x07 : "descriptor type and index",
                  0x08 : "0",
                  0x09 : "configuration",
                  0x0a : "0",
                  0x0b : "interface",
                  0x0c : "0"}

class USBDevice:
    name = "generic device"

    def __init__(self, maxusb_app, device_class, device_subclass,
            protocol_rel_num, max_packet_size_ep0, vendor_id, product_id,
            device_rev, manufacturer_string, product_string,
            serial_number_string, configurations=[], descriptors={},
            verbose=0, override_device_descriptor=None):

        if override_device_descriptor:
          self.override_device_descriptor = override_device_descriptor
          print("OVERRIDE set to",self.override_device_descriptor)
        else:
          self.override_device_descriptor = None

        self.maxusb_app = maxusb_app
        self.verbose = verbose

        self.strings = [ ]

        self.usb_spec_version           = 0x0001
        self.device_class               = device_class
        self.device_subclass            = device_subclass
        self.protocol_rel_num           = protocol_rel_num
        self.max_packet_size_ep0        = max_packet_size_ep0
        self.vendor_id                  = vendor_id
        self.product_id                 = product_id
        self.device_rev                 = device_rev
        self.manufacturer_string_id     = self.get_string_id(manufacturer_string)
        self.product_string_id          = self.get_string_id(product_string)
        self.serial_number_string_id    = self.get_string_id(serial_number_string)

        # maps from USB.desc_type_* to bytearray OR callable
        self.descriptors = descriptors
        self.descriptors[USB.desc_type_device] = self.get_descriptor
        self.descriptors[USB.desc_type_configuration] = self.handle_get_configuration_descriptor_request
        self.descriptors[USB.desc_type_string] = self.handle_get_string_descriptor_request

        self.config_num = -1
        self.configuration = None
        self.configurations = configurations

        for c in self.configurations:
            csi = self.get_string_id(c.configuration_string)
            c.set_configuration_string_index(csi)
            c.set_device(self)

        self.state = USB.state_detached
        self.ready = False

        self.address = 0

        self.setup_request_handlers()

    def get_string_id(self, s):
        try:
            i = self.strings.index(s)
        except ValueError:
            # string descriptors start at index 1
            self.strings.append(s)
            i = len(self.strings)

        return i

    def setup_request_handlers(self):
        # see table 9-4 of USB 2.0 spec, page 279
        self.request_handlers = {
             0 : self.handle_get_status_request,
             1 : self.handle_clear_feature_request,
             3 : self.handle_set_feature_request,
             5 : self.handle_set_address_request,
             6 : self.handle_get_descriptor_request,
             7 : self.handle_set_descriptor_request,
             8 : self.handle_get_configuration_request,
             9 : self.handle_set_configuration_request,
            10 : self.handle_get_interface_request,
            11 : self.handle_set_interface_request,
            12 : self.handle_synch_frame_request
        }

    def connect(self):
        self.maxusb_app.connect(self)

        # skipping USB.state_attached may not be strictly correct (9.1.1.{1,2})
        self.state = USB.state_powered

    def disconnect(self):
        self.maxusb_app.disconnect()

        self.state = USB.state_detached

    def run(self):
        self.maxusb_app.service_irqs()

    def ack_status_stage(self):
        self.maxusb_app.ack_status_stage()

    def get_descriptor(self, n): # device descriptor
        d = bytearray([
            18,         # length of descriptor in bytes
            1,          # descriptor type 1 == device
            (self.usb_spec_version >> 8) & 0xff,
            self.usb_spec_version & 0xff,
            self.device_class,
            self.device_subclass,
            self.protocol_rel_num,
            self.max_packet_size_ep0,
            self.vendor_id & 0xff,
            (self.vendor_id >> 8) & 0xff,
            self.product_id & 0xff,
            (self.product_id >> 8) & 0xff,
            self.device_rev & 0xff,
            (self.device_rev >> 8) & 0xff,
            self.manufacturer_string_id,
            self.product_string_id,
            self.serial_number_string_id,
            len(self.configurations)
        ])

        if self.override_device_descriptor:
          print("returning OVERRIDE: ",self.override_device_descriptor)
          return self.override_device_descriptor
        else:
          return d

    # IRQ handlers
    #####################################################

    def handle_request(self, req):
        if self.verbose > 3:
          try:
            print(self.name, "received request: ", req)
          except:
            pass

        # figure out the intended recipient
        recipient_type = req.get_recipient()
        recipient = None
        index = req.get_index()
        if recipient_type == USB.request_recipient_device:
            recipient = self
        elif recipient_type == USB.request_recipient_interface:
            if index < len(self.configuration.interfaces):
                recipient = self.configuration.interfaces[index]
        elif recipient_type == USB.request_recipient_endpoint:
            recipient = self.endpoints.get(index, None)

        if not recipient:
            print(self.name, "invalid recipient, stalling")
            self.maxusb_app.stall_ep0()
            return

        # and then the type
        req_type = req.get_type()
        handler_entity = None
        if req_type == USB.request_type_standard:
            handler_entity = recipient
        elif req_type == USB.request_type_class:
            handler_entity = recipient.device_class
        elif req_type == USB.request_type_vendor:
            handler_entity = recipient.device_vendor

        if not handler_entity:
            print(self.name, "invalid handler entity, stalling")
            self.maxusb_app.stall_ep0()
            return

        handler = handler_entity.request_handlers.get(req.request, None)

        if not handler:
            print(self.name, "invalid handler, stalling")
            self.maxusb_app.stall_ep0()
            return

        handler(req)

    def handle_data_available(self, ep_num, data):
        if self.state == USB.state_configured and ep_num in self.endpoints:
            endpoint = self.endpoints[ep_num]
            if callable(endpoint.handler):
                endpoint.handler(data)

    def handle_buffer_available(self, ep_num):
        if self.state == USB.state_configured and ep_num in self.endpoints:
            endpoint = self.endpoints[ep_num]
            if callable(endpoint.handler):
                endpoint.handler()

    # standard request handlers
    #####################################################

    # USB 2.0 specification, section 9.4.5 (p 282 of pdf)
    def handle_get_status_request(self, req):
        print(self.name, sys._getframe().f_code.co_name, "received GET_STATUS request")

        # self-powered and remote-wakeup (USB 2.0 Spec section 9.4.5)
        response = b'\x03\x00'
        self.maxusb_app.send_on_endpoint(0, response)

    # USB 2.0 specification, section 9.4.1 (p 280 of pdf)
    def handle_clear_feature_request(self, req):
        print(self.name, sys._getframe().f_code.co_name, "received CLEAR_FEATURE request with type 0x%02x and value 0x%02x" \
                % (req.request_type, req.value))

    # USB 2.0 specification, section 9.4.9 (p 286 of pdf)
    def handle_set_feature_request(self, req):
        print(self.name, sys._getframe().f_code.co_name, "received SET_FEATURE request")

    # USB 2.0 specification, section 9.4.6 (p 284 of pdf)
    def handle_set_address_request(self, req):
        self.address = req.value
        self.state = USB.state_address
        self.ack_status_stage()

        if self.verbose > 2:
            print(self.name, sys._getframe().f_code.co_name, "received SET_ADDRESS request for address",
                    self.address)

    # USB 2.0 specification, section 9.4.3 (p 281 of pdf)
    def handle_get_descriptor_request(self, req):
        dtype  = (req.value >> 8) & 0xff
        dindex = req.value & 0xff
        lang   = req.index
        n      = req.length

        response = None

        response = self.descriptors.get(dtype, None)  # XXX inject response here, override descriptor, descriptor fetched is self.get_descriptor(). override.

        if callable(response):
            response = response(dindex) # this is madness

        if response:
            n = min(n, len(response))
            self.maxusb_app.verbose += 1

            self.maxusb_app.send_on_endpoint(0, response[:n]) # sends it
            self.maxusb_app.verbose -= 1

            if self.verbose > 5:
                print(self.name, "wrote", response[:n])
                print(self.name, "sent", n, "bytes in response")

            #qw = USBDescriptor(response[:n])
            #print(qw.verbose())
        else:
            self.maxusb_app.stall_ep0()

    def handle_get_configuration_descriptor_request(self, num):
        return self.configurations[num].get_descriptor()

    def handle_get_string_descriptor_request(self, num):
        if num == 0:
            # HACK: hard-coding baaaaad
            d = bytes([
                    4,      # length of descriptor in bytes
                    3,      # descriptor type 3 == string
                    9,      # language code 0, byte 0
                    4       # language code 0, byte 1
            ])
        else:
            # string descriptors start at 1
            try:
              s = self.strings[num-1].encode('utf-16')
            except AttributeError:
              print("Some problem encoding",self.strings[num-1])

            # Linux doesn't like the leading 2-byte Byte Order Mark (BOM);
            # FreeBSD is okay without it
            s = s[2:]

            d = bytearray([
                    len(s) + 2,     # length of descriptor in bytes
                    3               # descriptor type 3 == string
            ])
            d += s

        return d

    # USB 2.0 specification, section 9.4.8 (p 285 of pdf)
    def handle_set_descriptor_request(self, req):
        print(self.name, sys._getframe().f_code.co_name, "received SET_DESCRIPTOR request")

    # USB 2.0 specification, section 9.4.2 (p 281 of pdf)
    def handle_get_configuration_request(self, req):
        print(self.name, sys._getframe().f_code.co_name, "received GET_CONFIGURATION request with data 0x%02x" \
                % req.value)

    # USB 2.0 specification, section 9.4.7 (p 285 of pdf)
    def handle_set_configuration_request(self, req):
        print(self.name, sys._getframe().f_code.co_name, "received SET_CONFIGURATION request")

        # configs are one-based
        self.config_num = req.value - 1
        self.configuration = self.configurations[self.config_num]
        self.state = USB.state_configured

        # collate endpoint numbers
        self.endpoints = { }
        for i in self.configuration.interfaces:
            for e in i.endpoints:
                self.endpoints[e.number] = e

        # HACK: blindly acknowledge request
        self.ack_status_stage()

    # USB 2.0 specification, section 9.4.4 (p 282 of pdf)
    def handle_get_interface_request(self, req):
        print(self.name, sys._getframe().f_code.co_name, "received GET_INTERFACE request")

        if req.index == 0:
            # HACK: currently only support one interface
            self.maxusb_app.send_on_endpoint(0, b'\x00')
        else:
            self.maxusb_app.stall_ep0()

    # USB 2.0 specification, section 9.4.10 (p 288 of pdf)
    def handle_set_interface_request(self, req):
        print(self.name, sys._getframe().f_code.co_name, "received SET_INTERFACE request")

    # USB 2.0 specification, section 9.4.11 (p 288 of pdf)
    def handle_synch_frame_request(self, req):
        print(self.name, sys._getframe().f_code.co_name, "received SYNCH_FRAME request")


class USBDeviceRequest:
    def __init__(self, raw_bytes):
        """Expects raw 8-byte setup data request packet"""

        self.raw_bytes = raw_bytes
        self.request_type   = raw_bytes[0] # P 139
        self.request        = raw_bytes[1] # request        : 0x00: get_status, 0x01: clear_feature, 0x03: set_feature, 0x05: set_address, 0x06: getdescriptor
        self.value          = (raw_bytes[3] << 8) | raw_bytes[2] # request_lookup, if it's simple. but might ask for strings
        self.index          = (raw_bytes[5] << 8) | raw_bytes[4]
        self.length         = (raw_bytes[7] << 8) | raw_bytes[6]

    def __str__(self):
        s = "dir=0x%02x, type=0x%02x, rec=0x%02x, r=0x%02x, v=0x%02x, i=0x%02x, l=0x%02x" \
                % (self.get_direction(), self.get_type(), self.get_recipient(),
                   self.request, self.value, self.index, self.length)
        hashString = str(hex(hash(str(self.raw_bytes))))
        s =\
"""

   HASH: %s
   RAW: %s
   bmRequestType (Byte 0):
   |--DIRECTION: %s (%s) (bit 7)
   |--TYPE:      %s (%s) (bit 6, 5)
   |--RECIPIENT: %s (%s) (bit 4, 3, 2, 1, 0)
   bRequest      (Byte 1):
   |--REQUEST NUMBER: 0x%02x <<%s>>
   wValue        (Byte 3, 2)
   |--%s 
   wIndex        (Byte 5, 4)
   |--%s
   wLength       (Byte 7, 6)
   |--LENGTH: 0x%04x (%s)
""" % (hashString[int(len(hashString)/2):],
       bytes_as_hex(self.raw_bytes), # raw 
       bin(self.get_direction()), "to device" if self.get_direction() == 0 else "to host", # direction
       bin(self.get_type()), "standard" if self.get_type() == 0 else "class" if self.get_type() == 1 else "vendor specific" if self.get_type() == 2 else "unknown!",
       bin(self.get_recipient()), "device" if self.get_recipient() == 0 else "interface" if self.get_recipient() == 1 else "endpoint" if self.get_recipient() == 2 else "other element" if self.get_recipient == 3 else "unknown!",
       self.request, request_lookup[self.request],
       self.value_string(),
       self.endpoint_string() if self.get_recipient() == 2 else self.interface_string() if self.get_recipient() == 1 else "DATA: 0x%02x" % self.index,
       self.length, "not a data stage" if self.length == 0 else "exact number of bytes host wants to transfer" if self.get_direction() == 0 else "maximum bytes device may send")

        return s

    def raw(self):
        """returns request as bytes"""
        b = bytes([ self.request_type, self.request,
                    self.value  & 0xff, (self.value  >> 8) & 0xff,
                    self.index  & 0xff, (self.index  >> 8) & 0xff,
                    self.length & 0xff, (self.length >> 8) & 0xff
                  ])
        return b

    def get_direction(self):
        return (self.request_type >> 7) & 0x01

    def get_type(self):
        return (self.request_type >> 5) & 0x03

    def get_recipient(self):
        return self.request_type & 0x1f

    # meaning of bits in wIndex changes whether we're talking about an
    # interface or an endpoint (see USB 2.0 spec section 9.3.4)
    def get_index(self):
        rec = self.get_recipient()
        if rec == 1:                # interface
            return self.index
        elif rec == 2:              # endpoint
            return self.index & 0x0f
    
    def endpoint_string(self):
      # xxxxxxxx7YYYYYY0 (x is unknown, y is the byte we are interested in)
      in_or_out = (self.index >> 7) & 0x01
      s =\
"""\
RAW: 0x%02x
      |--ENDPOINT INDEX NUMBER: %s (bit 3, 2, 1, 0)
      |--ENDPOINT TYPE: %s\
""" % (self.index,
       bin(self.index & 0x0f), # clear all but last 4 bits
       "Control or OUT" if in_or_out == 0 else "IN")

      return s

    def interface_string(self):
      s =\
"""\
RAW: 0x%02x
      |--DATA: 0x%x (bits 8-15)
      |--INTERFACE INDEX NUMBER: 0x%x (bits 0-7)\
""" % (self.index,
      (self.index >> 8) & 0xff, # get the second byte
      self.index & 0xff) # clear all but last 8 bits

      return s

    def value_string(self): # try except for unknown descriptors
      wvalue_string = ""
      if self.request == 0x06 or self.request == 0x07:
        wvalue_string =\
"""\
      |--DESCRIPTOR TYPE: 0x%02x <<%s>> (bDescriptorType)
      |--INDEX: 0x%02x\
""" % ((self.value >> 8) & 0xff, descriptor_type_lookup[(self.value >> 8) & 0xff], self.value & 0xff)
      else:
        wvalue_string =\
"""\
   |--<<%s>>""" % wvalue_lookup[self.request]

      ret =\
"""\
RAW: 0x%04x #specific to REQUEST # FIX ENDIANESS
%s\
""" % (self.value, wvalue_string)

      return ret                                         
