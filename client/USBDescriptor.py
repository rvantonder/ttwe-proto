from util import bytes_as_hex

class USBRequest:
  descriptor_type_lookup = {0x00 : "default",
                          0x01 : "device",
                          0x02 : "configuration",
                          0x03 : "string",
                          0x04 : "interface",
                          0x05 : "endpoint",
                          0x06 : "device_qualifier",
                          0x07 : "other_speed_configuration",
                          0x08 : "interface_power",
                          0x09 : "on_the_go",
                          0x0a : "debug",
                          0x0b : "interface_association",
                          0x21 : "hid",
                          0x22 : "report_descriptor",
                          0x23 : "physical_descriptor",
                          -1   : "unknown"}

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
                    0x0c : "synch_frame",
                    0xfe : "custom"}

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
                    0x0c : "0",
                    0xfe : "custom?"}

  def __init__(self, request):
    self.r = request

    self.request_type   = self.r[0] # P 139
    self.request        = self.r[1] # request        : 0x00: get_status, 0x01: clear_feature, 0x03: set_feature, 0x05: set_address, 0x06: getdescriptor
    self.value          = (self.r[3] << 8) | self.r[2] # request_lookup, if it's simple. but might ask for strings
    self.index          = (self.r[5] << 8) | self.r[4]
    self.length         = (self.r[7] << 8) | self.r[6]

  def __repr__(self):
    return self.verbose()

  def verbose(self, handle=None):
    hashString = str(hex(hash(str(self.r))))
    s = "\nHASH: [%s]" % hashString[int(len(hashString)/2):]

    s +=\
"""
  RAW: %s
  bmRequestType (Byte 0):
  |--DIRECTION: %s (%s) (bit 7)
  |--TYPE:      %s (%s) (bit 6, 5)
  `--RECIPIENT: %s (%s) (bit 4, 3, 2, 1, 0)
  bRequest      (Byte 1):
  `--REQUEST NUMBER: 0x%02x <<%s>>
  wValue        (Byte 3, 2)
  `--%s 
  wIndex        (Byte 5, 4)
  `--%s
  wLength       (Byte 7, 6)
  `--LENGTH: 0x%04x (%s)
""" % (bytes_as_hex(self.r), 
       bin(self.get_direction()), "to device" if self.get_direction() == 0 else "to host", # direction
       bin(self.get_type()), "standard" if self.get_type() == 0 else "class" if self.get_type() == 1 else "vendor specific" if self.get_type() == 2 else "unknown!",
       bin(self.get_recipient()), "device" if self.get_recipient() == 0 else "interface" if self.get_recipient() == 1 else "endpoint" if self.get_recipient() == 2 else "other element" if self.get_recipient == 3 else "unknown!",
       self.request, self.request_lookup[self.request],
       self.value_string(),
       self.endpoint_string() if self.get_recipient() == 2 else self.interface_string() if self.get_recipient() == 1 else "DATA: 0x%02x" % self.index,
       self.length, "not a data stage" if self.length == 0 else "exact number of bytes host wants to transfer" if self.get_direction() == 0 else "maximum bytes device may send")

    return s

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
    # (x is unknown, y is the byte we are interested in)
    in_or_out = (self.index >> 7) & 0x01
    s =\
"""\
RAW: 0x%02x
      |--ENDPOINT INDEX NUMBER: %s (bit 3, 2, 1, 0)
      `--ENDPOINT TYPE: %s\
""" % (self.index,
       bin(self.index & 0x0f), # clear all but last 4 bits
       "Control or OUT" if in_or_out == 0 else "IN")

    return s

  def interface_string(self):
    s =\
"""\
RAW: 0x%02x
      |--DATA: 0x%x (bits 8-15)
      `--INTERFACE INDEX NUMBER: 0x%x (bits 0-7)\
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
      `--INDEX: 0x%02x\
""" % ((self.value >> 8) & 0xff, self.descriptor_type_lookup[(self.value >> 8) & 0xff], self.value & 0xff)
    else:
      wvalue_string =\
"""\
   |--<<%s>>""" % self.wvalue_lookup[self.request]

    ret =\
"""\
RAW: 0x%04x #specific to REQUEST # FIX ENDIANESS
%s\
""" % (self.value, wvalue_string)

    return ret
        
class USBDescriptor:
  descriptor_type_lookup = {0x00 : "default",
                          0x01 : "device",
                          0x02 : "configuration",
                          0x03 : "string",
                          0x04 : "interface",
                          0x05 : "endpoint",
                          0x06 : "device_qualifier",
                          0x07 : "other_speed_configuration",
                          0x08 : "interface_power",
                          0x09 : "on_the_go",
                          0x0a : "debug",
                          0x0b : "interface_association",
#                         0x0f : "bos"
                          0x21 : "hid",
                          0x22 : "report_descriptor",
                          0x23 : "physical_descriptor",
                          -1   : "unknown"}

  def __init__(self, descriptor):
    self.d = descriptor

  def __repr__(self):
    return self.verbose()

  def verbose(self, handle=None): # handle is a specific case to handle report_descriptor since we don't have any indication of what it is when it's TX except for context
    hashString = str(hex(hash(str(self.d))))
    s = "\nHASH: [%s]" % hashString[int(len(hashString)/2):]
    if handle:
      s += getattr(self, handle)()
    else:
      while len(self.d) > 0:
        try:
          s += getattr(self, self.descriptor_type_lookup[self.d[1]])()
        except KeyError:
          s += self.default()
    
    return s

  def default(self):
    s = "No verbose output available"
    return s

  def device(self):
    s =\
"""
  RAW: %s
  bLength: 0x%02x
  bDescriptorType: 0x%02x (Device)
  bcdUSB: 0x%04x (USB specification release number, BCD)
  bDeviceClass: 0x%02x (Class code. 0x01 to 0xfe are USB defined classes. 0x00 if class specified in interface descriptor. 0xff is vendor specific)
  `--%s
  bDeviceSubclass: 0x%02x (Subclass code)
  bDeviceProtocol: 0x%02x (Protocol code)
  bMaxPacketSize0: 0x%02x (Maximum packet size for endpoint 0)
  idVendor: 0x%04x (Vendor ID)
  idProduct: 0x%04x (Product ID)
  bcdDevice: 0x%04x (Device release number, BCD)
  iManufacturer: 0x%02x (Index of string descriptor for the manufacturer)
  iProduct: 0x%02x (Index of string for the product)
  iSerialNumber: 0x%02x (Index of string descriptor containing the serial number)
  bNumConfigurations: 0x%02x (Number of possible configurations)
""" % (bytes_as_hex(self.d), 
       self.d[0], 
       self.d[1],
       (self.d[3] << 8| self.d[2]),
       self.d[4], 
       self.device_class(self.d[5]),
       self.d[5], 
       self.d[6], 
       self.d[7],
       (self.d[9] << 8| self.d[8]), 
       (self.d[11] << 8| self.d[10]),
       (self.d[13] << 8| self.d[12]), 
       self.d[14], 
       self.d[15],
       self.d[16], 
       self.d[17])
    
    self.d = bytearray(self.d[18:])
    return s

  def device_class(self, field):
    lookup = {\
      0x00: "The interface descriptor names the class",
      0x02: "Communications",
      0x03: "Human Interface Device",
      0x04: "Magical Unicorns",
      0x05: "Physical",
      0x06: "Image",
      0x07: "Printer",
      0x08: "Mass storage",
      0x09: "Hub",
      0x0a: "(Communication Device Class) Data Interface",
      0x0b: "Smart card",
      0x0c: "Magical unicorns",
      0x0d: "Content Security",
      0xdc: "Diagnostic device (can also be declared at interface level) -- bDeviceSubClass = 1 for Reprogrammable Diagnostic Device with bDeviceProtocol = 1 for USB2 Compliance Device",
      0xe0: "Wireless Controller (can also be declared at interface level) -- bDeviceSubClass = 1 for RF Controller with bDeviceProtocol = 1 for Bluetooth Programming Interface",
      0xef: "Miscellaneous Device -- bDeviceSubClass = 2 for Common Class with bDeviceProtocol = 1 for Interface Association Descriptor",
      0xff: "Vendor-specific (can also be declared at interface level)"}

    try:
      s = lookup[field]
    except KeyError:
      s = "No idea"

    return s

  def configuration(self):
    s =\
"""
  RAW: %s
  bLength: 0x%02x
  bDescriptorType: 0x%02x (Configuration)
  wTotalLength: 0x%04x (Number of bytes in the configuration descriptor and all of its subordinate descriptors)
  bNumInterfaces: 0x%02x (Number of interfaces in the configuration. NOTE: Must be at least 1)
  bConfigurationValue: 0x%02x (Identifier for set_configruation and get_configuration requests. NOTE: must be 1 or higher. A set_configuration request with a value of 0 causes the device to enter "Not Configured" state)
  iConfiguration: 0x%02x (Index of string descriptor for the configuration. 0 if no string descriptor)
  bmAttributes: 0x%02x (Self/bus power and remote wakeup settings). Other bits in the field are unused. NOTE: Bits 0 to 4  must be 0. Bit 7 must be 1. In USB 1.1, setting bit 6 to 0 is enough to indicate bus powered, but bit 7 required for USB 1.0)
  `--%s
  bMaxPower: 0x%02x (Bus power required, expressed as (maximum milliamperes/2)
""" % (bytes_as_hex(self.d),
       self.d[0],
       self.d[1],
       (self.d[3] << 8| self.d[2]),
       self.d[4],
       self.d[5],
       self.d[6],
       self.d[7],
       self.config_attributes(self.d[7]),
       self.d[8])

    self.d = bytearray(self.d[9:])
    return s

  def config_attributes(self, field):
    s = ""
    if field >> 6 & 0x01:
      s += "self-powered"
    else:
      s += "bus-powered"
    
    if field >> 5 & 0x01:
      s += ", supports wakeup (a usb device must enter suspend state if there has been no bus activity for 3 ms)"

    return s

  def string(self):
    s =\
"""
  RAW: %s
  bLength: 0x%02x
  bDescriptorType: 0x%02x (String)
  bString or wLangID: %s (Depends on string index requested. wLangID for English is 0x0009, subcode for US is 0x0004)
""" % (bytes_as_hex(self.d),
       self.d[0],
       self.d[1],
       (''.join(map(chr, self.d[2::2]))))

    length = self.d[0]
    self.d = bytearray(self.d[length:]) # trim it
    return s

  def interface(self):
     s =\
"""
  RAW: %s
  bLength: 0x%02x
  bDescriptorType: 0x%02x (Interface)
  bInterfaceNumber: 0x%02x (Number identifying this interface)
  bAlternateSetting: 0x%02x (Value used to select an alternate setting)
  bNumEndpoints: 0x%02x (Number of endpoints supported, not counting EP0)
  bInterfaceClass: 0x%02x (Class code. 0x01 to 0xfe are reserved for USB-defined classes. 0xff is vender specific. 0x00 is reserved)
  `--%s
  bInterfaceSubclass: 0x%02x (Subclass code. Diagnostic-device, wireless-controller, and application specific class have defined subclasses)
  bInterfaceProtocol: 0x%02x (Protocol code. If between 0x01 and 0xfe, must be zero or a code defined by USB spec)
  iInterface: 0x%02x (Index of string descriptor for the interface)
""" % (bytes_as_hex(self.d),
       self.d[0],
       self.d[1],
       self.d[2],
       self.d[3],
       self.d[4],
       self.d[5],
       self.device_class(self.d[5]), # interface_class and device class are same
       self.d[6],
       self.d[7],
       self.d[8])

     self.d = bytearray(self.d[9:])
     return s  

  def endpoint(self):
     s =\
"""
  RAW: %s
  bLength: 0x%02x
  bDescriptorType: 0x%02x (Endpoint)
  bEndpointAddress: 0x%02x (Endpoint number and direction. NOTE: bits 4, 5, 6 are unused and must be 0)
  |--%s
  `--%s
  bmAttributtes: 0x%02x (Transfer type supported. NOTE: for all endpoints, bits 6 and 7 must be 9)
  |--%s (Bits 1, 0. Control assumed for EP0)
  |--%s (Bits 3, 2. In USB 1.1 bits 2 to 7 were reserved. USB 2.0 uses bits 2 to 5 for full and high speed isochronous endpoints)
  `--%s (Bits 5, 4.)
  wMaxPacketSize: 0x%04x (Maximum packet size supported. NOTE: bits 13 to 15 are reserved and must be 0)
  `--%s (Bits 12, 11. USB 2.0 only - number of additional transactions per microframe a high-speed endpoint supports)
  bInterval: 0x%02x (Maximum latency/polling interval/NAK rate)
""" % (bytes_as_hex(self.d),
       self.d[0],
       self.d[1],
       self.d[2],
       self.endpoint_number(self.d[2]),
       self.endpoint_direction(self.d[2]),
       self.d[3],
       self.endpoint_transfer_support(self.d[3]),
       self.endpoint_sync_type(self.d[3]),
       self.endpoint_usage_type(self.d[3]),
       (self.d[5] << 8| self.d[4]),
       #endpoint_packet_size(self.d[4]),
       self.endpoint_packet_additional(self.d[5]),
       self.d[6])

     self.d = bytearray(self.d[7:])
     return s

  def endpoint_number(self, field):
    s = "Endpoint number: %s (bits 3, 2, 1, 0)" % bin(field & 0x0f)
    return s

  def endpoint_direction(self, field):
    s = "Direction: %s %s (bit 7) - Ignored for Control transfers" % (bin(field & 0x80), "(OUT)" if (field & 0x80) == 0 else "IN")
    return s

  def endpoint_transfer_support(self, field):
    t = field & 0x03 # last two bits
    s = "Transfer type: "
    if t == 0:
      s += "Control"
    elif t == 1:
      s += "Isochronous"
    elif t == 2:
      s += "Bulk"
    elif t == 3:
      s += "Intterupt"

    return s

  def endpoint_sync_type(self, field):
    t = (field >> 2) & 0x3 # bits 3 and 2
    s = "Sync type: "
    if t == 0:
      s += "No sync"
    elif t == 1:
      s += "Async"
    elif t == 2:
      s += "Adaptive"
    elif t == 3:
      s += "Synchronous"

    return s

  def endpoint_usage_type(self, field):
    t = (field >> 4) & 0x3 # bits 5, 4
    s = "Usage type: "
    if t == 0:
      s += "Data"
    elif t == 1:
      s += "Feedback endpoint"
    elif t == 2:
      s += "Implicit feedback data endpoint"
    elif t == 3:
      s += "Reserved"

    return s

#def endpoint_packet_size(field):
#  s = "Size: %d" % 

  def endpoint_packet_additional(self, field):
    t = (field >> 2) & 0x3 # high byte, offset 2
    s = "Additional transactions supported: "
    if t == 0:
      s += "None"
    elif t == 1:
      s += "1 additional"
    elif t == 2:
      s += "2 additional"
    elif t == 3:
      s += "reserved"

    return s

  def device_qualifier(self):
    s =\
"""
  RAW: %s
  bLength: 0x%02x
  bDescriptorType: 0x%02x (Device Qualifer)
  bcdUSB: 0x%04x (USB specification release number, BCD. NOTE: Must be at least 0x0200)
  bDeviceClass: 0x%02x (Class code)
  `--%s
  bDeviceSubclass: 0x%02x (Subclass code)
  bDeviceProtocol: 0x%02x (Protocol code)
  bMaxPacketSize0: 0x%02x (Maximum packet size for endpoint 0)
  bNumConfigurations: 0x%02x (Number of possible configurations)
  Reserved: 0x%02x (For future use)
""" % (bytes_as_hex(self.d), 
       self.d[0], 
       self.d[1],
       (self.d[3] << 8| self.d[2]),
       self.d[4], 
       self.device_class(self.d[5]),
       self.d[5], 
       self.d[6], 
       self.d[7],
       self.d[8],
       self.d[9])

    self.d = bytearray(self.d[10:])
    return s

  def other_speed_configuration(self):
    s =\
"""
  RAW: %s
  bLength: 0x%02x
  bDescriptorType: 0x%02x (Other Speed Configuration)
  wTotalLength: 0x%04x (Number of bytes in the configuration descriptor and all of its subordinate descriptors)
  bNumInterfaces: 0x%02x (Number of interfaces in the configuration. NOTE: Must be at least 1)
  bConfigurationValue: 0x%02x (Identifier for set_configruation and get_configuration requests. NOTE: must be 1 or higher. A set_configuration request with a value of 0 causes the device to enter "Not Configured" state)
  iConfiguration: 0x%02x (Index of string descriptor for the configuration. 0 if no string descriptor)
  bmAttributes: 0x%02x (Self/bus power and remote wakeup settings). Other bits in the field are unused. NOTE: Bits 0 to 4  must be 0. Bit 7 must be 1. In USB 1.1, setting bit 6 to 0 is enough to indicate bus powered, but bit 7 required for USB 1.0)
  `--%s
  bMaxPower: 0x%02x (Bus power required, expressed as (maximum milliamperes/2)
""" % (bytes_as_hex(self.d),
       self.d[0],
       self.d[1],
       (self.d[3] << 8| self.d[2]),
       self.d[4],
       self.d[5],
       self.d[6],
       self.config_attributes(self.d[6]),
       self.d[7])

    self.d = bytearray(self.d[8:])
    return s

  def interface_power(self):
    return "interface_power not implemented"

  def on_the_go(self):
    return "on_the_go not implemented"

  def debug(self):
    return "debug not implemented"
  
  def interface_association(self):
    s =\
"""
  RAW: %s
  bLength: 0x%02x
  bDescriptorType: 0x%02x (Interface Association)
  bFirstInterface 0x%02x (Number identifying the first interface associated with the function)
  bInterfaceCount 0x%02x (Number of contiguous interfaces associated with the function)
  bFunctionClass 0x%02 (Class code)
  bFunctionSubClass 0x%02 (Sublcass code)
  bFunctionProtocol 0x%02 (Protocol code)
  iFunction 0x%02 (Index string descriptor for the function. 0 if no string descriptor)
""" % (bytes_as_hex(self.d),
       self.d[0],
       self.d[1],
       (self.d[3] << 8| self.d[2]),
       self.d[4],
       self.d[5],
       self.d[6],
       self.d[7])

    self.d = bytearray(self.d[8:])
    return s

  # p345
  def hid(self):
    s =\
"""
  RAW: %s
  bLength: 0x%02x
  bDescriptorType: 0x%02x (HID)
  bcdHID: 0x%04x (HID specification release number, BCD)
  bCountryCode: 0x%02x (Numeric expression identifying the country for localized hardware, BCD)
  bNumDescriptors: 0x%02x (Number of subordinate report and physical descriptors)
  bDescriptorType: 0x%02x (The type of a class-specific descriptor that follows. A report descriptor (required) is 0x22)
  wDescriptorLength: 0x%04x (Total length of the descriptor identified above)
  bDescriptorType: 0x%02x (Optional. The type of a class-specific descriptor that follows. A physical descriptor is type 0x23)
  wDescriptorLength: 0X%04X (Total length of the descriptor identified above. Present only if bDescriptorType is present immediately above. NOTE: May be followed by additional wDescriptorType and DescriptorLength fields)
""" % (bytes_as_hex(self.d),
       self.d[0],
       self.d[1],
       (self.d[3] << 8| self.d[2]),
       self.d[4],
       self.d[5],
       self.d[6],
       (self.d[8] << 8| self.d[7]),
       self.d[9],
       (self.d[11]| self.d[10]))

    length = self.d[0]
    self.d = bytearray(self.d[length:]) # trim it
    return s

# def bos(self):
#   pass

  # p350
  def report_descriptor(self):
    s =\
"""
  RAW: %s
  0x%02x 0x%02x Usage page (generic desktop)
  0x%02x 0x%02x Usage (keyboard)
  0x%02x 0x%02x Collection (Application)
  0x%02x 0x%02x Usage Page 7 (keyboard/keypad)
  0x%02x 0x%02x Usage min = 224
  0x%02x 0x%02x Usage max = 231
  0x%02x 0x%02x Logical min = 0
  0x%02x 0x%02x Logical max = 1
  0x%02x 0x%02x Report size = 1
  0x%02x 0x%02x Report count = 8
  0x%02x 0x%02x Input (Data, Variable, Absolute)
  0x%02x 0x%02x Report Count = 1
  0x%02x 0x%02x Report size = 8
  0x%02x 0x%02x Input (Constant)
  0x%02x 0x%02x Usage min = 0
  0x%02x 0x%02x Usage max = 101
  0x%02x 0x%02x Logical min = 0
  0x%02x 0x%02x Logical max = 101
  0x%02x 0x%02x Report size = 8
  0x%02x 0x%02x Report Count = 1
  0x%02x 0x%02x Input (Data, Variable, Array)
  0x%02x        End Collection
""" % (bytes_as_hex(self.d),
       self.d[0], self.d[1],
       self.d[2], self.d[3],
       self.d[4], self.d[5],
       self.d[6], self.d[7],
       self.d[8], self.d[9],
       self.d[10], self.d[11],
       self.d[12], self.d[13],
       self.d[14], self.d[15],
       self.d[16], self.d[17],
       self.d[18], self.d[19],
       self.d[20], self.d[21],
       self.d[22], self.d[23],
       self.d[24], self.d[25],
       self.d[26], self.d[27],
       self.d[28], self.d[29],
       self.d[30], self.d[31],
       self.d[32], self.d[33],
       self.d[34], self.d[35],
       self.d[36], self.d[37],
       self.d[38], self.d[39],
       self.d[40], self.d[41],
       self.d[42])

    length = self.d[0]
    self.d = bytearray(self.d[length:]) # trim it
    if len(self.d) > 0:
      print("There's still some left...")
    return s
