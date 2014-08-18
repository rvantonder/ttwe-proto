#!/usr/bin/env python
# GoodFET Client Library for Maxim USB Chips.
# 
# (C) 2012 Travis Goodspeed <travis at radiantmachines.com>
#
# This code is being rewritten and refactored.  You've been warned!


import sys, time, string, struct, glob, os;
import warnings

from GoodFET import GoodFET;

warnings.warn(
"""This library will soon be deprecated in favor of the USB*.py libraries."""
)

#Handy registers.
rEP0FIFO=0             # endpoint 0 fifo
rEP1OUTFIFO=1          # endpoint 1 OUT fifo
rEP2INFIFO=2           # endpoint 2 IN fifo
rEP3INFIFO=3           # endpoint 3 IN fifo
rSUDFIFO=4             # what is SUD???
rEP0BC=5               # endpoint 0 byte counter
rEP1OUTBC=6            # endpoint 1 out byte counder
rEP2INBC=7
rEP3INBC=8
rEPSTALLS=9            # ?
rCLRTOGS=10
rEPIRQ=11
rEPIEN=12
rUSBIRQ=13
rUSBIEN=14
rUSBCTL=15
rCPUCTL=16
rPINCTL=17
rREVISION=18
rFNADDR=19
rIOPINS=20
rIOPINS1=20  #Same as rIOPINS
rIOPINS2=21
rHIRQ=25
rHIEN=26
rMODE=27
rPERADDR=28
rHCTL=29
rHXFR=30
rHRSL=31

#Host mode registers.
rRCVFIFO =1       # receive fifo
rSNDFIFO =2       # send fifo
rRCVBC   =6       # receive byte counter
rSNDBC   =7       # send byte counter
rHIRQ    =25      # irq?


# R11 EPIRQ register bits
bmSUDAVIRQ =0x20
bmIN3BAVIRQ =0x10
bmIN2BAVIRQ =0x08
bmOUT1DAVIRQ= 0x04
bmOUT0DAVIRQ= 0x02
bmIN0BAVIRQ =0x01

# R12 EPIEN register bits
bmSUDAVIE   =0x20
bmIN3BAVIE  =0x10
bmIN2BAVIE  =0x08
bmOUT1DAVIE =0x04
bmOUT0DAVIE =0x02
bmIN0BAVIE  =0x01

# ************************
# Standard USB Requests
SR_GET_STATUS		=0x00	# Get Status
SR_CLEAR_FEATURE	=0x01	# Clear Feature
SR_RESERVED		=0x02	# Reserved
SR_SET_FEATURE		=0x03	# Set Feature
SR_SET_ADDRESS		=0x05	# Set Address
SR_GET_DESCRIPTOR	=0x06	# Get Descriptor
SR_SET_DESCRIPTOR	=0x07	# Set Descriptor
SR_GET_CONFIGURATION	=0x08	# Get Configuration
SR_SET_CONFIGURATION	=0x09	# Set Configuration
SR_GET_INTERFACE	=0x0a	# Get Interface
SR_SET_INTERFACE	=0x0b	# Set Interface

# Get Descriptor codes	
GD_DEVICE		=0x01	# Get device descriptor: Device
GD_CONFIGURATION	=0x02	# Get device descriptor: Configuration
GD_STRING		=0x03	# Get device descriptor: String
GD_HID	            	=0x21	# Get descriptor: HID
GD_REPORT	        =0x22	# Get descriptor: Report

# SETUP packet header offsets
bmRequestType           =0
bRequest       	        =1
wValueL			=2
wValueH			=3
wIndexL			=4
wIndexH			=5
wLengthL		=6
wLengthH		=7

# HID bRequest values
GET_REPORT		=1
GET_IDLE		=2
GET_PROTOCOL            =3
SET_REPORT		=9
SET_IDLE		=0x0A
SET_PROTOCOL            =0x0B
INPUT_REPORT            =1

# PINCTL bits
bmEP3INAK   =0x80
bmEP2INAK   =0x40
bmEP1INAK   =0x20
bmFDUPSPI   =0x10
bmINTLEVEL  =0x08
bmPOSINT    =0x04
bmGPXB      =0x02
bmGPXA      =0x01

# rUSBCTL bits
bmHOSCSTEN  =0x80
bmVBGATE    =0x40
bmCHIPRES   =0x20
bmPWRDOWN   =0x10
bmCONNECT   =0x08
bmSIGRWU    =0x04

# USBIRQ bits
bmURESDNIRQ =0x80
bmVBUSIRQ   =0x40
bmNOVBUSIRQ =0x20
bmSUSPIRQ   =0x10
bmURESIRQ   =0x08
bmBUSACTIRQ =0x04
bmRWUDNIRQ  =0x02
bmOSCOKIRQ  =0x01

# MODE bits
bmHOST          =0x01
bmLOWSPEED      =0x02
bmHUBPRE        =0x04
bmSOFKAENAB     =0x08
bmSEPIRQ        =0x10
bmDELAYISO      =0x20
bmDMPULLDN      =0x40
bmDPPULLDN      =0x80

# PERADDR/HCTL bits
bmBUSRST        =0x01
bmFRMRST        =0x02
bmSAMPLEBUS     =0x04
bmSIGRSM        =0x08
bmRCVTOG0       =0x10
bmRCVTOG1       =0x20
bmSNDTOG0       =0x40
bmSNDTOG1       =0x80

# rHXFR bits
# Host XFR token values for writing the HXFR register (R30).
# OR this bit field with the endpoint number in bits 3:0
tokSETUP  =0x10  # HS=0, ISO=0, OUTNIN=0, SETUP=1
tokIN     =0x00  # HS=0, ISO=0, OUTNIN=0, SETUP=0
tokOUT    =0x20  # HS=0, ISO=0, OUTNIN=1, SETUP=0
tokINHS   =0x80  # HS=1, ISO=0, OUTNIN=0, SETUP=0
tokOUTHS  =0xA0  # HS=1, ISO=0, OUTNIN=1, SETUP=0 
tokISOIN  =0x40  # HS=0, ISO=1, OUTNIN=0, SETUP=0
tokISOOUT =0x60  # HS=0, ISO=1, OUTNIN=1, SETUP=0

# rRSL bits
bmRCVTOGRD   =0x10
bmSNDTOGRD   =0x20
bmKSTATUS    =0x40
bmJSTATUS    =0x80
# Host error result codes, the 4 LSB's in the HRSL register.
hrSUCCESS   =0x00
hrBUSY      =0x01
hrBADREQ    =0x02
hrUNDEF     =0x03
hrNAK       =0x04
hrSTALL     =0x05
hrTOGERR    =0x06
hrWRONGPID  =0x07
hrBADBC     =0x08
hrPIDERR    =0x09
hrPKTERR    =0x0A
hrCRCERR    =0x0B
hrKERR      =0x0C
hrJERR      =0x0D
hrTIMEOUT   =0x0E
hrBABBLE    =0x0F

# HIRQ bits
bmBUSEVENTIRQ   =0x01   # indicates BUS Reset Done or BUS Resume     
bmRWUIRQ        =0x02
bmRCVDAVIRQ     =0x04
bmSNDBAVIRQ     =0x08
bmSUSDNIRQ      =0x10
bmCONDETIRQ     =0x20
bmFRAMEIRQ      =0x40
bmHXFRDNIRQ     =0x80

# HIEN bits
bmBUSEVENTIE   =0x01
bmRWUIE        =0x02
bmRCVDAVIE     =0x04
bmSNDBAVIE     =0x08
bmSUSDNIE      =0x10
bmCONDETIE     =0x20
bmFRAMEIE      =0x40
bmHXFRDNIE     =0x80

reg_endpoint_irq = 0x19 # this is actually for the host, = hIRQ = 25
rcv_data_avail =   0x04 # for host, RCVDAVIRQ
snd_buffer_avail =   0x08 # for host, SNDBAVIRQ

class GoodFETMAXUSB(GoodFET):
    MAXUSBAPP=0x40;
    usbverbose=False;

    def service_irqs_deprecated(self):
        """Handle USB interrupt events."""
        epirq=self.rreg(rEPIRQ); # are these enabled by default? lucky
        usbirq=self.rreg(rUSBIRQ);
        
        
        #Are we being asked for setup data?
        if(epirq&bmSUDAVIRQ): #Setup Data Requested
            self.wreg(rEPIRQ,bmSUDAVIRQ); #Clear the bit
            self.do_SETUP();
        if(epirq&bmOUT1DAVIRQ): #OUT1-OUT packet
            self.do_OUT1();
            self.wreg(rEPIRQ,bmOUT1DAVIRQ); #Clear the bit *AFTER* servicing.
        if(epirq&bmIN3BAVIRQ): #IN3-IN packet
            self.do_IN3();
            #self.wreg(rEPIRQ,bmIN3BAVIRQ); #Clear the bit
        if(epirq&bmIN2BAVIRQ): #IN2 packet
            self.do_IN2();
            #self.wreg(rEPIRQ,bmIN2BAVIRQ); #Clear the bit
        #else:
        #    print "No idea how to service this IRQ: %02x" % epirq;
    def do_IN2(self):
        """Overload this."""
    def do_IN3(self):
        """Overload this."""
    def do_OUT1(self):
        """Overload this."""
        if self.usbverbose: print("Ignoring an OUT1 interrupt.")
    def setup2str(self,SUD):
        """Converts the header of a setup packet to a string."""
        return "bmRequestType=0x%02x, bRequest=0x%02x, wValue=0x%04x, wIndex=0x%04x, wLength=0x%04x" % (
                ord(SUD[0]), ord(SUD[1]),
                ord(SUD[2])+(ord(SUD[3])<<8),
                ord(SUD[4])+(ord(SUD[5])<<8),
                ord(SUD[6])+(ord(SUD[7])<<8)
                );
    
    def MAXUSBsetup(self):
        """Move the FET into the MAXUSB application."""
        self.writecmd(self.MAXUSBAPP,0x10,0,self.data); #MAXUSB/SETUP
        self.writecmd(self.MAXUSBAPP,0x10,0,self.data); #MAXUSB/SETUP
        self.writecmd(self.MAXUSBAPP,0x10,0,self.data); #MAXUSB/SETUP
        print("Connected to MAX342x Rev. %x" % (self.rreg(rREVISION)))
        self.wreg(rPINCTL,0x18); #Set duplex and negative INT level.

    def read_raw(self):
      print('attempting to read raw...')
      return self.readcmd()

    def write_raw(self, data):
      self.writecmd(self.MAXUSBAPP,0x00,len(data),data);
        
    def MAXUSBtrans8(self,byte):
        """Read and write 8 bits by MAXUSB."""
        data=self.MAXUSBtrans([byte]);
        return ord(data[0]);
    
    def MAXUSBtrans(self,data):
        """Exchange data by MAXUSB."""
        self.data=data;
        self.writecmd(self.MAXUSBAPP,0x00,len(data),data);
        return self.data;

    def rreg(self,reg):
        """Peek 8 bits from a register."""
        data=[reg<<3,0];
        self.writecmd(self.MAXUSBAPP,0x00,len(data),data);
        return ord(self.data[1]);
    def rregAS(self,reg):
        """Peek 8 bits from a register, setting AS."""
        data=[(reg<<3)|1,0];
        self.writecmd(self.MAXUSBAPP,0x00,len(data),data);
        return ord(self.data[1]);
    def wreg(self,reg,value):
        """Poke 8 bits into a register."""
        #print 'reg is always %d' % reg
        data=[(reg<<3)|2,value];
        self.writecmd(self.MAXUSBAPP,0x00,len(data),data);        
        return value;
    def wregAS(self,reg,value):
        """Poke 8 bits into a register, setting AS."""
        data=[(reg<<3)|3,value];
        self.writecmd(self.MAXUSBAPP,0x00,len(data),data);        
        return value;
    def readbytes(self,reg,length):
        """Peek some bytes from a register."""
        data=[(reg<<3)]+range(0,length);
        self.writecmd(self.MAXUSBAPP,0x00,len(data),data);
        toret=self.data[1:len(self.data)];
        ashex="";
        for foo in toret:
            ashex=ashex+(" %02x"%ord(foo));
        if self.usbverbose: print("GET   %02x==%s" % (reg,ashex))
        return toret;
    def readbytesAS(self,reg,length):
        """Peek some bytes from a register, acking prior transfer."""
        data=[(reg<<3)|1]+range(0,length);
        self.writecmd(self.MAXUSBAPP,0x00,len(data),data);
        toret=self.data[1:len(self.data)];
        ashex="";
        for foo in toret:
            ashex=ashex+(" %02x"%ord(foo));
        if self.usbverbose: print("GETAS %02x==%s" % (reg,ashex))
        return toret;
    def fifo_ep3in_tx(self,data):
        """Sends the data out of EP3 in 64-byte chunks."""
        #Wait for the buffer to be free before starting.
        while not(self.rreg(rEPIRQ)&bmIN3BAVIRQ): pass;
        
        count=len(data);
        pos=0;
        while count>0:
            #Send 64-byte chunks or the remainder.
            c=min(count,64);
            self.writebytes(rEP3INFIFO,
                            data[pos:pos+c]);
            self.wregAS(rEP3INBC,c);
            count=count-c;
            pos=pos+c;
            
            #Wait for the buffer to be free before continuing.
            while not(self.rreg(rEPIRQ)&bmIN3BAVIRQ): pass;
            
        return;
        
    def ctl_write_nd(self,request):
        """Control Write with no data stage.  Assumes PERADDR is set
        and the SUDFIFO contains the 8 setup bytes.  Returns with
        result code = HRSLT[3:0] (HRSL register).  If there is an
        error, the 4LSBits of the returned value indicate the stage 1
        or 2."""

        # 1. Send the SETUP token and 8 setup bytes. 
        # Should ACK immediately.
        #print "Writing bytes to SUDFIFO: %s" % request
        self.writebytes(rSUDFIFO,request); # something bricks
        #print "Sending packet with tokSETUP to EP0..."
        resultcode=self.send_packet(tokSETUP,0); #SETUP packet to EP0.
        print('Performed ctl_write_nd with %s, result: %s' % (request, resultcode))
        #print "result code of SETUP packet: %d" % resultcode
        if resultcode: return resultcode;

        # 2. No data stage, so the last operation is to send an IN
        # token to the peripheral as the STATUS (handhsake) stage of
        # this control transfer.  We should get NAK or the DATA1 PID.
        # When we get back to the DATA1 PID the 3421 automatically
        # sends the closing NAK.
        resultcode=self.send_packet(tokINHS,0); #Function takes care of retries.
        print('Performed ctl_write_nd part 2 with %s, result: %s' % (request, resultcode))
        #print "result code of status after: %d" % resultcode
        if resultcode: return resultcode;
        
        return 0;
        
        
    def ctl_read(self,request):
        """Control read transfer, used in Host mode."""
        resultcode=0;
        bytes_to_read=request[6]+256*request[7];

        self.writebytes(rSUDFIFO,request);     #Load the FIFO

        resultcode=self.send_packet(tokSETUP,0); #SETUP packet to EP0
        if resultcode:
            print("Failed to get ACK on SETUP request in ctl_read().")
            return resultcode;

        if bytes_to_read == 0:
          print("No Data stage for this setup transaction! (probably a get_interface)")

        if bytes_to_read > 0:
          self.wreg(rHCTL,bmRCVTOG1); #  TODO for some reason this needs to be set for every SETUP transfer :/   #FIRST data packet in CTL transfer uses DATA1 toggle.
          #resultcode=self.IN_Transfer(0,bytes_to_read);
          resultcode=self.IN_Transfer(0)
          if resultcode:
            print("Failed on IN Transfer in ctl_read(): %d" % resultcode)
            return resultcode;
        
        self.IN_nak_count=self.nak_count;
        
        #The OUT status stage.
        resultcode=self.send_packet(tokOUTHS,0);
        if resultcode:
            print("Failed on OUT Status stage in ctl_read()")
            return resultcode;

        print("Successful complete control read")
        
        return 0; #Success

    def service_irqs(self):
      while True:
        self.callback.before_handle()

        irq = self.read_register(reg_endpoint_irq)

        if irq & snd_buffer_avail: # first read if we want to send something
          self.callback.handle_snd_buffer_available() # DONE remember handling EP0 versus EP2OUT 

        self.callback.read_data_into_rcv_buffer() # NO IRQ CHECKS?

        self.callback.after_handle() # DONE

    def read_register(self, reg_num, ack=False): # TODO ack?
      return self.rreg(reg_num) # wrapper for now

    def read_data(self,endpoint):
      self.IN_Transfer(endpoint)

    def IN_Transfer(self, endpoint):
      '''
      Constructs data until there's nothing more to receive
      '''
      data = []

      while 1: # check on resultcode
        resultcode = self.send_packet(tokIN, endpoint)

        if resultcode:
          break

        if self.rreg(rHIRQ) & bmRCVDAVIRQ: #if data is available
          bytes_to_transfer = self.rreg(rRCVBC)

          for i in xrange(0, bytes_to_transfer):
            c = self.rreg(rRCVFIFO)
            data.append(c)

          self.wreg(rHIRQ,bmRCVDAVIRQ) # clear IRQ

        if len(data) == 512: # 512 block size
          self.callback.handle_rcv_data_available(data, endpoint)
          data = []

        # want it to break for scsi, why would i not want it to break?
        if bytes_to_transfer < 64: 
          print('bytes to transfer less than 64, breaking')
          break

        if bytes_to_transfer == 0:
          break

      if len(data) > 0:
        self.callback.handle_rcv_data_available(data, endpoint)

    # endpoint will be the requested one, in this case 2 by kingston
    def OUT_Transfer(self,endpoint,data): 
      # check length, etc
      count = len(data)
      pos = 0
      while count > 0:
        while not (self.rreg(rHIRQ) & bmSNDBAVIRQ):
          print("waiting for SND buffer")
        # wait for SND irq to be ready
          pass

        c = min(count, 64)
        self.writebytes(rSNDFIFO,data[pos:pos+c]);     #Load the FIFO
        self.writebytes(rSNDBC, [c])
        count = count - c

        print("Hitting tokOUT to endpoint %d" % endpoint)
        resultcode = self.send_packet(tokOUT,endpoint) # will take care of NAKs and retries
        if resultcode: print("Error in OUT transfer: %d" % resultcode)

    RETRY_LIMIT=1; #normally 3
    NAK_LIMIT=1; #normally 300
    def send_packet(self,token,endpoint):
        #print "In send_packet"
        """Send a packet to an endpoint as the Host, taking care of NAKs.
        Don't use this for device code."""
        self.retry_count=0;
        self.nak_count=0;
        
        #Repeat until NAK_LIMIT or RETRY_LIMIT is reached.
        while self.nak_count<self.NAK_LIMIT and self.retry_count<self.RETRY_LIMIT:
            # launch bits by setting hxfr
            self.wreg(rHXFR,(token|endpoint)); #launch the transfer
            # wait for completion interrupt
            while not (self.rreg(rHIRQ) & bmHXFRDNIRQ):
                # wait for the completion IRQ
                pass;
            #clear irq
            self.wreg(rHIRQ,bmHXFRDNIRQ);           #Clear IRQ
            # check result, HRSLT bits
            resultcode = (self.rreg(rHRSL) & 0x0F); # get the result

            if (resultcode==hrNAK):
                self.nak_count=self.nak_count+1;
            elif (resultcode==hrTIMEOUT):
                self.retry_count=self.retry_count+1;
            else:
                #Success!
                return resultcode;
        return resultcode;
            
    def writebytes(self,reg,tosend):
        """Poke some bytes into a register."""
        data="";
        if type(tosend)==str:
            data=chr((reg<<3)|3)+tosend;
            if self.usbverbose: print("PUT %02x:=%s (0x%02x bytes)" % (reg,tosend,len(data)))
        else:
            data=[(reg<<3)|3]+tosend;
            ashex="";
            for foo in tosend:
                ashex=ashex+(" %02x"%foo);
            if self.usbverbose: print("PUT %02x:=%s (0x%02x bytes)" % (reg,ashex,len(data)))
        self.writecmd(self.MAXUSBAPP,0x00,len(data),data);
    def usb_connect(self):
        """Connect the USB port."""
        
        #disconnect D+ pullup if host turns off VBUS
        self.wreg(rUSBCTL,bmVBGATE|bmCONNECT);
    def usb_disconnect(self):
        """Disconnect the USB port."""
        self.wreg(rUSBCTL,bmVBGATE);
    def STALL_EP0(self,SUD=None):
        """Stall for an unknown SETUP event."""
        if SUD==None:
            print("Stalling EP0.")
        else:
            print("Stalling EPO for %s" % self.setup2str(SUD))
        self.wreg(rEPSTALLS,0x23); #All three stall bits.
    def SETBIT(self,reg,val):
        """Set a bit in a register."""
        self.wreg(reg,self.rreg(reg)|val);
    def vbus_on(self):
        """Turn on the target device."""
        self.wreg(rIOPINS2,(self.rreg(rIOPINS2)|0x08));
    def vbus_off(self):
        """Turn off the target device's power."""
        self.wreg(rIOPINS2,0x00);
    def reset_host(self):
        """Resets the chip into host mode."""
        self.wreg(rUSBCTL,bmCHIPRES); #Stop the oscillator.
        self.wreg(rUSBCTL,0x00);      #restart it.
        
        #FIXME: Why does the OSC line never settle?
        #Code works without it.
        
        #print "Waiting for PLL to sabilize.";
        #while self.rreg(rUSBIRQ)&bmOSCOKIRQ:
        #    #Hang until the PLL stabilizes.
        #    pass;
        #print "Stable.";

class GoodFETMAXUSBHost(GoodFETMAXUSB):
    """This is a class for implemented a minimal USB host.
    It's intended for fuzzing, rather than for daily use."""
    def hostinit(self, callback):
        self.first_time = True
        self.callback = callback
        """Initialize the MAX3421 as a USB Host."""
        self.usb_connect();
        print("Enabling host mode.")
        self.wreg(rPINCTL,(bmFDUPSPI|bmPOSINT));
        print("Resetting host.")
        self.reset_host();
        self.vbus_off();
        time.sleep(0.2);
        print("Powering host.")
        self.vbus_on();
        
    def detect_device(self):
        """Waits for a device to be inserted and then returns."""
        busstate=0;
        
        #Activate host mode and turn on 15K pulldown resistors on D+ and D-.
        self.wreg(rMODE,(bmDPPULLDN|bmDMPULLDN|bmHOST));
        #Clear connection detect IRQ.
        self.wreg(rHIRQ,bmCONDETIRQ);
        
        print("Waiting for a device connection.")
        while busstate==0:
            self.wreg(rHCTL,bmSAMPLEBUS); #Update JSTATUS and KSTATUS bits.
            busstate=self.rreg(rHRSL) & (bmJSTATUS|bmKSTATUS);
            
        if busstate==bmJSTATUS:
            print("Detected Full-Speed Device.")
            self.wreg(rMODE,(bmDPPULLDN|bmDMPULLDN|bmHOST|bmSOFKAENAB));
        elif busstate==bmKSTATUS:
            print("[!!!] Detected LOW-SPEED Device.")
            self.wreg(rMODE,(bmDPPULLDN|bmDMPULLDN|bmHOST|bmLOWSPEED|bmSOFKAENAB));
        else:
            print("Not sure whether this is Full-Speed or Low-Speed.  Please investigate.")
    def wait_for_disconnect(self):
        """Wait for a device to be disconnected."""
        print("Waiting for a device disconnect.")
        
        self.wreg(rHIRQ,bmCONDETIRQ); #Clear disconnect IRQ
        while not (self.rreg(rHIRQ) & bmCONDETIRQ):
            #Wait for IRQ to change.
            pass;
        
        #Turn off markers.
        self.wreg(rMODE,bmDPPULLDN|bmDMPULLDN|bmHOST);
        print("Device disconnected.")
        self.wreg(rIOPINS2,(self.rreg(rIOPINS2) & ~0x04)); #HL1_OFF
        self.wreg(rIOPINS1,(self.rreg(rIOPINS1) & ~0x02)); #HL4_OFF

    def set_configuration(self, req):
      conf = req[2]
      HR = self.ctl_write_nd(req)

    def set_address(self, req):
      addr = req[2]

      print("Setting address to %d" % addr)
      if not self.first_time:
        print("CTRL WRITE ND FOR SET ADDRESS HIT")
        HR = self.ctl_write_nd(req)   # CTL-Write, no data stage
        print("Error in ctl_write_nd? : %d" % HR)

        time.sleep(0.002);           # Device gets 2 msec recovery time
        self.wreg(rPERADDR,addr)       # now all transfers go to addr 7
        self.first_time = False

      print("All transfers now go to %d" % addr)

    def reset_bus(self):
        print("Bus will now reset")
        self.wreg(rHCTL,bmBUSRST);
        while self.rreg(rHCTL) & bmBUSRST:
            #Wait for reset to complete.
            pass;
        
        time.sleep(0.2);
        print("Bus done resetting")

    def soft_enumerate(self):
        """Emulate enumerate softly"""

        self.reset_bus()

        self.wreg(rPERADDR,0); #First request to address 0.
        self.maxPacketSize=8
