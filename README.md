### Overview

This is a prototype rendition of the TTWE framework. It is not considered mature,
as many changes need to be made to improve maintainability and usability. You have been warned.

It is provided as an early taster for the very curious, until the aforementioned changes
make it suitable for mass consumption.

For a full description, please refer to the WOOT paper: https://www.usenix.org/system/files/conference/woot14/woot14-vantonder.pdf

### Running it

Create the necessary pipes for the driver communication. For instance:

	$ sudo ./create_pipes.sh

You need Python 2.7 for the host emulation driver, and Python 3 for the client emulation driver. Future
changes will use only Python 3. 

Plug the **HOST** emluating Facedancer in first, which will register as ttyUSB0.

	$ sudo python TTWEHost.py [-h] [-v] [--OUT OUT] [--IN IN] [--IN2 IN2]

  ``` 
  optional arguments:
    -h, --help     show this help message and exit
    -v, --verbose  turn on verbose output of USB communication
    --OUT OUT      peripheral OUT Endpoint number
    --IN IN        peripheral IN Endpoint number
    --IN2 IN2      peripheral IN2 Endpoint number
  ```

	$ sudo python3 TTWEClient.py [-h] [-v] [--fuzz FUZZ]

  ```
  optional arguments:
    -h, --help     show this help message and exit
    -v, --verbose  turn on verbose output of USB communication
    --fuzz FUZZ    endpoint to be fuzzed (0 for device enumeration phase)
  ```

### Notes

The client and host drivers are built on top of the GoodFET software for 
the Facedancer. A series of callbacks in the ```service_irqs``` functions of GoodFETMAXUSB.py and
MAXUSBApp.py refer to the functions in TTWEHost.py and TTWEClient.py repsectively. 

You may need to change the HostRelayDevice endpoint numbers to correspond with those specified in the 
endpoint descriptor of the original peripheral if you want to fiddle with bulk or interrupt transfers.
This can be done with the `--OUT`, `--IN`, and `--IN2` options. The Facedancer supports up to one OUT
endpoint and two IN endpoints, which should suffice for most USB peripherals.

Communication output is placed in `usbcomms.log`

Here is a diagram of the concept:

![logo](https://raw.github.com/rvantonder/ttwe-proto/master/ttwe-mitm.png)



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
