### Overview

This is a prototype rendition of the TTWE framework. It is not considered mature,
as many changes need to be made to improve maintainability and usability. You have been warned.

It is provided as an early taster for the very curious, until the aforementioned changes
make it suitable for mass consumption.

### Running it

Create the necessary pipes for the driver communiction. For instance:

	$ sudo ./create_pipes.sh

You need Python 2.7 for the host emulation driver, and Python 3 for the client emulation driver. Future
changes will use only Python 3. The client and host drivers are built on top of the GoodFET software for 
the Facedancer.

	$ sudo python3 TTWEClient.py (True|False) # flag elects to fuzz the host during enumeration phase
	$ sudo python TTWEHost.py

### Notes

You may need to change the HostRelayDevice endpoint numbers to correspond with those specified in the 
endpoint descriptor of the original peripheral if you want to fiddle with bulk or interrupt transfers.

E.g.:

  OUT_EP = 0x1
  
  IN_EP = 0x2
  
  IN2_EP = 0x3
  
Communication output is placed in `usbcomms.log`

### License

Copyright (c) 2014 Rijnard van Tonder, @rvtond

MIT License

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
"Software"), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.