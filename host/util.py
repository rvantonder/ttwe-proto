# util.py
#
# Random helpful functions.

def bytes_as_hex(b, delim=" "):
    return delim.join(["%02x" % x for x in b])

# Describes what the hell is going over the serial

# p115
descriptor_type_lookup = {0x00 : "NONE",
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

# returns a verbose description of request
def verbose(response):
  d = response[1] #kdescriptor type
  s = "HASH: %d",hash(d)

  if d == 0x01: # device
    s = device(response)
  elif d == 0x02: # configuration
    s = configuration(response)
    if len(response) > 9: # There are subordinate descriptors
      print("sending on",bytes_as_hex(response[9:]))
      s += verbose(bytearray(response[9:]))
# elif d == 0x03: # string
#   s = string(response)
  elif d == 0x04: # interface
    s = interface(response)
    if len(response) > 9:
      print("second sending on",bytes_as_hex(response[9:]))
      s += verbose(bytearray(response[9:])) # subordinate descriptor
  elif d == 0x06: # device_qualifier
    s = device_qualifier(response)
  elif d == 0x07:
    s = other_speed_configuration(response)
  elif d == 0x08:
    pass
  elif d == 0x09:
    pass
  elif d == 0x0a:
    pass
  elif d == 0x0b:
    s = interface_association(response)
  elif d == 0x21: # hid descriptor
    s = hid_descriptor(response) 
#    if len(response) > 
  else:
    s = "No verbose output available"

  return s

def default(response):
  s =\
"""
  RAW: %s
""" % (bytes_as_hex(response))

def device(response):
    s =\
"""
  RAW: %s
  bLength: 0x%02x
  bDescriptorType: 0x%02x (Device)
  bcdUSB: 0x%04x (USB specification release number, BCD)
  bDeviceClass: 0x%02x (Class code. 0x01 to 0xfe are USB defined classes. 0x00 if class specified in interface descriptor. 0xff is vendor specific)
  |--%s
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
""" % (bytes_as_hex(response), 
       response[0], 
       response[1],
       (response[2] << 8| response[3]),
       response[4], 
       device_class(response[5]),
       response[5], 
       response[6], 
       response[7],
       (response[8] << 8| response[9]), 
       (response[10] << 8| response[11]),
       (response[12] << 8| response[13]), 
       response[14], 
       response[15],
       response[16], 
       response[17])

    return s

def device_class(field):
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

def configuration(response):
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
  |--%s
  bMaxPower: 0x%02x (Bus power required, expressed as (maximum milliamperes/2)
""" % (bytes_as_hex(response),
       response[0],
       response[1],
       (response[2] << 8| response[3]),
       response[4],
       response[5],
       response[6],
       response[7],
       config_attributes(response[7]),
       response[8])

    return s

def config_attributes(field):
  s = ""
  if field >> 6 & 0x01:
    s += "self-powered"
  else:
    s += "bus-powered"
  
  if field >> 5 & 0x01:
    s += ", supports wakeup (a usb device must enter suspend state if there has been no bus activity for 3 ms)"

  return s

def interface(response):
     s =\
"""
  RAW: %s
  bLength: 0x%02x
  bDescriptorType: 0x%02x (Interface)
  bInterfaceNumber: 0x%02x (Number identifying this interface)
  bAlternateSetting: 0x%02x (Value used to select an alternate setting)
  bNumEndpoints: 0x%02x (Number of endpoints supported, not counting EP0)
  bInterfaceClass: 0x%02x (Class code. 0x01 to 0xfe are reserved for USB-defined classes. 0xff is vender specific. 0x00 is reserved)
  |--%s
  bInterfaceSubclass: 0x%02x (Subclass code. Diagnostic-device, wireless-controller, and application specific class have defined subclasses)
  bInterfaceProtocol: 0x%02x (Protocol code. If between 0x01 and 0xfe, must be zero or a code defined by USB spec)
  iInterface: 0x%02x (Index of string descriptor for the interface)
""" % (bytes_as_hex(response),
       response[0],
       response[1],
       response[2],
       response[3],
       response[4],
       response[5],
       device_class(response[5]), # interface_class and device class are same
       response[6],
       response[7],
       response[8])

     return s  

def endpoint(response):
     s =\
"""
  RAW: %s
  bLength: 0x%02x
  bDescriptorType: 0x%02x (Endpoint)
  bEndpointAddress: 0x%02x (Endpoint number and direction. NOTE: bits 4, 5, 6 are unused and must be 0)
  |--%s
  |--%s
  bmAttributtes: 0x%02x (Transfer type supported. NOTE: for all endpoints, bits 6 and 7 must be 9)
  |--%s (Bits 1, 0. Control assumed for EP0)
  |--%s (Bits 3, 2. In USB 1.1 bits 2 to 7 were reserved. USB 2.0 uses bits 2 to 5 for full and high speed isochronous endpoints)
  |--%s (Bits 5, 4.)
  wMaxPacketSize: 0x%04x (Maximum packet size supported. NOTE: bits 13 to 15 are reserved and must be 0)
  |--%s (Bits 12, 11. USB 2.0 only - number of additional transactions per microframe a high-speed endpoint supports)
  bInterval: 0x%02x (Maximum latency/polling interval/NAK rate)
""" % (bytes_as_hex(response),
       response[0],
       response[1],
       response[2],
       endpoint_number(response[2]),
       endpoint_direction(response[2]),
       response[3],
       endpoint_transfer_support(response[3]),
       endpoint_sync_type(response[3]),
       endpoint_usage_type(response[3]),
       (response[4] << 8| response[5]),
       #endpoint_packet_size(response[4]),
       endpoint_packet_additional(response[4]),
       response[6])

     return s

def endpoint_number(field):
  s = "Endpoint number: %s (bits 3, 2, 1, 0)" % bin(field & 0x0f)
  return s

def endpoint_direction(field):
  s = "Direction: %s (bit 7) - Ignored for Control transfers" % bin(field & 0x10)

def endpoint_transfer_support(field):
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

def endpoint_sync_type(field):
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

def endpoint_usage_type(field):
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

def endpoint_packet_additional(field):
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

def device_qualifier(response):
    s =\
"""
  RAW: %s
  bLength: 0x%02x
  bDescriptorType: 0x%02x (Device Qualifer)
  bcdUSB: 0x%04x (USB specification release number, BCD. NOTE: Must be at least 0x0200)
  bDeviceClass: 0x%02x (Class code)
  |--%s
  bDeviceSubclass: 0x%02x (Subclass code)
  bDeviceProtocol: 0x%02x (Protocol code)
  bMaxPacketSize0: 0x%02x (Maximum packet size for endpoint 0)
  bNumConfigurations: 0x%02x (Number of possible configurations)
  Reserved: 0x%02x (For future use)
""" % (bytes_as_hex(response), 
       response[0], 
       response[1],
       (response[2] << 8| response[3]),
       response[4], 
       device_class(response[5]),
       response[5], 
       response[6], 
       response[7],
       response[8],
       response[9])

    return s

def other_speed_configuration(response):
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
  |--%s
  bMaxPower: 0x%02x (Bus power required, expressed as (maximum milliamperes/2)
""" % (bytes_as_hex(response),
       response[0],
       response[1],
       (response[2] << 8| response[3]),
       response[4],
       response[5],
       response[6],
       config_attributes(response[6]),
       response[7])

    return s
  
def interface_association(response):
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
""" % (bytes_as_hex(response),
       response[0],
       response[1],
       (response[2] << 8| response[3]),
       response[4],
       response[5],
       response[6],
       response[7])

    return s
