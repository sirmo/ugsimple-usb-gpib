#!/usr/bin/env python3

# Copyright (C) 2015 by Jacob Alexander
#
# This file is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This file is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this file.  If not, see <http://www.gnu.org/licenses/>.

### Imports ###

import binascii
import time
import usb.core

from array import array



### Classes ###

class UGSimpleGPIB:
	def __init__( self, device_index=0, debug_mode=False, timeout=30000 ):
		# Enumeration index of the USB device
		# This matters if there is more than one GPIB to USB adapter plugged in
		self.device_index = device_index
		self.debug_mode = debug_mode
		self.timeout = timeout

		# Initialize usb read buffer
		self.usb_read_buf = array('B', [])

		# Search for devices
		self.find_usb_devices()

		# Choose which USB device to use (if there are multiple)
		# TODO Select by device id
		self.device = None
		for index, dev in enumerate( self.devices ):
			# Only configure the indexed device
			if index == device_index:
				self.device = dev
				break

		if self.debug_mode:
			print ( self.device )

		# No device found
		if self.device is None:
			raise ValueError('Device not found')

		# Find the configuration
		self.cfg = self.device.get_active_configuration()

		if self.debug_mode:
			print ( self.cfg )

		# Find the first interface
		self.interface = self.cfg[ (0,0) ]

		if self.debug_mode:
			print ( self.interface )

		# Get read and write endpoints
		self.read_ep = usb.util.find_descriptor(
			self.interface,
			# Match the first IN endpoint
			custom_match = \
				lambda e: \
					usb.util.endpoint_direction( e.bEndpointAddress ) == usb.util.ENDPOINT_IN
		)
		self.write_ep = usb.util.find_descriptor(
			self.interface,
			# Match the first OUT endpoint
			custom_match = \
				lambda e: \
					usb.util.endpoint_direction( e.bEndpointAddress ) == usb.util.ENDPOINT_OUT
		)

		# Make sure that the read_ep has been flushed
		try:
			self.read_ep.read( 64, timeout=1 )
		except:
			pass

		if self.debug_mode:
			print ( self.read_ep )
			print ( self.write_ep )

        def reinit_buffer(self):
                #print('FLUSHING: {}'.format(self.usb_read_buf))
                # Initialize usb read buffer
                self.usb_read_buf = array('B', [])
                try:
                    self.read_ep.read( 64, timeout=500)
                except:
                    pass

        def _device_matcher( self, device ):
		import usb.util
		# Make sure that a Vendor Specific Interface is found in the configuration
		# bInterfaceClass    0xff
		# bInterfaceSubClass 0xff
		# bInterfaceProtocol 0xff
		for cfg in device:
			if ( usb.util.find_descriptor( cfg, bInterfaceClass=0xff ) is not None
				and usb.util.find_descriptor( cfg, bInterfaceSubClass=0xff ) is not None
				and usb.util.find_descriptor( cfg, bInterfaceProtocol=0xff ) is not None ):
				return True

	def find_usb_devices( self ):
		# Search for all USB Devices
		# 0x04d8 is the Microchip USB manufacturer ID
		# 0x000c is the specific product id assigned
		self.devices = usb.core.find(
			idVendor=0x04d8,
			idProduct=0x000c,
			custom_match=self._device_matcher,
			find_all=True,
		)

		# No devices found
		if self.devices is None:
			raise ValueError('Cannot find any devices')

		return self.devices

	# Write data to the USB endpoint
	# data - List of bytes to write
	def usb_write( self, data ):
		assert self.write_ep.write( data, self.timeout ) == len( data )
                if self.debug_mode:
		    print (self.write_ep)

	# Read byte(s) from USB endpoint
	# datalen - Number of bytes to read
	# Returns a byte array
	def usb_read( self, datalen=1 ):
		# Read USB in 64 byte chunks, store bytes until empty, then read again
		while len( self.usb_read_buf ) < 1 or len( self.usb_read_buf ) < datalen:
			self.usb_read_buf += self.read_ep.read( 64, self.timeout )

		if self.debug_mode:
			print ( self.usb_read_buf, len( self.usb_read_buf ) )

		# Retrieve the requested number of bytes, then remove the items
		data = self.usb_read_buf[0:datalen]
		del self.usb_read_buf[0:datalen]
		return data


        # This method does the same thing as usb_read() except it doesn't
        # concern itself with the buffer arithmetic. It purely just returns whatever the
        # instrument spits out
        def usb_read_all(self):
                buf = array('B', [])
                # Read USB in 64 byte chunks, store bytes until empty, then read again
                while len( buf ) < 1: 
                        buf += self.read_ep.read( 64, self.timeout )

                if self.debug_mode:
                        print ( buf, len( buf ) )

                data = buf
                return data


	# Write UGSimple command
	# address - internal command address
	# data    - List of byte width data
	def device_write( self, address, data=[] ):
		# Prepare data for writing
		byteData = [ address, len( data ) + 2 ]
		for byte in data:
			byteData.append( byte )

		if self.debug_mode:
			print ( "WRITE:", byteData )

		# Write command over usb
		self.usb_write( byteData )

	# Read UGSimple command
	def device_read( self, address ):
		# Read USB a single byte to see if a valid command has been received
		read = self.usb_read(1)
                command = read[0]
                print ("READ:", read, " ADDRESS:", address)
		if command != address:
			print ("device_read ERROR: '0x{0:2x}' does not match expected command '0x{0:2x}'".format( command, address ) )
                        print (self.usb_read())
		        return None

		if self.debug_mode:
			print ( "READ CMD:", command )

		# Valid command, read next byte to determine length of command
		length = self.usb_read(1)[0]
                        
		if self.debug_mode:
			print ( "READ LEN:", length )

		# Read the rest of the byteData, the command and length are part of the length (hence -2)
		byteData = self.usb_read( length - 2 )

		if self.debug_mode:
			print ( "READ DATA:", byteData )

		return byteData

	# Get the manufacturer id
	# Returns manufacturer id string
	def manufacturer_id( self ):
		# Request manufacturer id
		self.device_write( 0xFE )

		# Read manufacturer id
		byteData = self.device_read( 0xFE )

		if self.debug_mode:
			print ( "MANUFACTURER ID:", byteData )

		# Flush read, bug in manufacturer_id command that sends an extra 0xAF in Firmware 1.0
		self.usb_read_buf = array('B', [])

		return ''.join( [ chr( x ) for x in byteData ] )

	# Get the series number
	# Returns the series number
	# MMFFFFFF - e.g. 011e7f7f (Model 0x01, Function 0x1e7f7f)
	# MM       - Model number
	# FFFFFF   - Function number
	def series_number( self ):
		# Request series number
		self.device_write( 0x0E )

		# Read series number
		byteData = self.device_read( 0x0E )

		if self.debug_mode:
			print ( "SERIAL NUM:", byteData )

		return ''.join( [ "{0:02x}".format( x ) for x in byteData ] )

	# Get the firmware version
	# Returns "<major>.<minor>"
	def firmware_version( self ):
		# Request firmware version
		self.device_write( 0x00 )

		# Read firmware version
		byteData = self.device_read( 0x00 )

		if self.debug_mode:
			print ( "FIRWMARE VER:", byteData )

		return "{0}.{1}".format( byteData[0], byteData[1] )

	# Query Devices connected to UGSimple
	def query_devices( self ):
		# Device query command
		self.device_write( 0x34 )

		# Read list of devices
		byteData = self.device_read( 0x34 )

		# XXX Not sure what the last byte is for
		# One device  0x1E
		# Two devices 0x7F
		# Stripping for now
		byteData = byteData[:-1]

		if self.debug_mode:
			print ( "DEVICES:", byteData )

		return byteData

	# Write to GPIB Address
	# address - GPIB Address
	# data    - Data to write to address
	def write( self, address, data="" ):
		# Prepare data with appended linefeed (LF)
		dataOut = bytearray( [ address ] ) + bytearray( data, 'ascii' ) + bytearray( [ 0xA ] )

		if self.debug_mode:
			print ( "WRITE CMD:", dataOut )

		# Send write command (no return)
		self.device_write( 0x32, dataOut )

	# Read from GPIB Address
	# address - GPIB Address
	# Returns a byte array
	def read( self, address, delay=0 ):
                # (muxr) this method is problematic
                # the way it flushes the buffer and depends on buffer length arithmetic
                # can cause it to desync depending on the underlying USB subsystem
                # I have instead written a new method which doesn't rely on a living
                # buffer, and instead just reads everything from the buffer. 
                # See _ask_retry() and _ask_quorum() methods

		# Prepare read request command
		dataOut = bytearray( [ address ] )

		if self.debug_mode:
			print ( "READ REQ:", dataOut )

		# Request read
		self.device_write( 0x33, dataOut )

		# Delay if necessary
		time.sleep( delay )

		# Flush read buffer
		self.usb_read()

		# Read data sent from GPIB device
                byteData = None
                while byteData == None:
		    byteData = self.device_read( 0x33 )


                # Flush read buffer
                #self.usb_read()


		# Strip final linefeed
                try:
		    byteData = byteData[:-1]
                except TypeError:
                    byteData = ''

		# Convert to an ascii byte array
		#byteData = bytearray( byteData, 'ascii' )
		byteData = binascii.b2a_qp( byteData )

		if self.debug_mode:
			print ( "READ REPLY:", byteData )

		return byteData



        def _ask(self, address, data):
                self.write(address, data)

                data_out = bytearray([address])
                self.device_write(0x33, data_out)

                ret = self.usb_read_all()
                # usb_read_all will return everything
                # the first two bytes contain the address
                # and length.. we will strip these as we
                # don't need them
                ret = binascii.b2a_qp(ret[2:])
                return ret


        # For instruments which return a delimiter.. the delimiter can be used
        # to check if the returned result is valid. 
        # retry can be used and be based on the expected delimiter
        #    address: interface address
        #    data: command to execute
        #    delimiter: which delimiter to expect
        #    max_retries: how many retries to make
        def _ask_retry(self, address, cmd, delimiter='\r\n', max_retries=10, num_reads=10):
                for i in range(max_retries):
                        res = self._ask(address, cmd)
                        if res.endswith(delimiter):
                                return res[:-2]
                        else:
                                print('unexpected result: {}={}'.format(i, res))

        # With devices which don't have a known delimiter it is possible to attempt
        # a number of retries and return the most common result.
        # this works well for queries which result in finite result, things like backing up
        # NVRAM, but obviously not measurements since those fluctuate.
        # This method is also quite slow.
        #    address: interface address
        #    cmd: command to execute
        #    num_reads: number of separate reads to make
        def _ask_quorum(self, address, cmd, delimiter='\r\n', max_retries=10, num_reads=10):
                reads = {}
                for i in range(num_reads):
                    res = self._ask(address, cmd)
                    # tally how many results are the same
                    if res in reads:
                        reads[res] = reads[res] + 1
                    else:
                        reads[res] = 1

                for k, v in reads.items():
                    # only accept the majority result
                    if v > (num_reads/2):
                        if v <> num_reads:
                            print('{} result was off: {}'.format(num_reads - v, reads))
                        return k
                print('ERROR: no quorum reached {}'.format(reads))


        # Instead of using separate write() and read() you can do both at the same time with ask()
        # this method is also less problematic than the read() method which I have found to have some
        # issues with certain instruments
        #    address: interface address
        #    cmd: command to be sent to the device
        #    methos: retry or quorum 
        def ask(self, address, cmd, method='retry', delimiter='\r\n', max_retries=10, num_reads=10):
                method_to_call = getattr(self,'_ask_' + method)
                return method_to_call(address, cmd, delimiter, max_retries, num_reads)
                 
