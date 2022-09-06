import datetime
import socket

import pynmea2
import serial

source = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
source.bind(('', 49002))

dest = serial.Serial('/dev/tty.usbserial-0001', 4800)


class AHRS2NMEA:
  """
  Convert AHRS xplane messages to nmea
  """

  def run(self, source, dest):
    try:
      while True:
        message, address = source.recvfrom(1024)
        data = message.decode("ascii").split(",")
        print(data)

        if data[0] == "XGPS1":
          gga = self.build_gga(data)
          rpc = self.build_rmc(data)
          dest.write(f"{gga}\r\n{rpc}\r\n".encode("ascii"))
    finally:
      source.close()
      dest.close()

  def deg_to_dms(self, deg):
    """Convert from decimal degrees to degrees, minutes.seconds."""
    dd = int(deg)
    mm = 60 * (abs(deg) - dd)

    return str(dd).zfill(2) + ('%.4f' % mm).zfill(7)

  def get_lat_dir(self, deg):
    if deg > 0:
      return 'N'
    else:
      return 'S'

  def get_long_dir(self, deg):
    if deg > 0:
      return 'E'
    else:
      return 'W'

  def build_gga(self, data):
    ts = datetime.datetime.utcnow().strftime("%H%M%S")
    # lat
    lat = self.deg_to_dms(float(data[2]))
    lat_dir = self.deg_to_dms(float(data[2]))
    # long
    long = self.deg_to_dms(float(data[1]))
    long_dir = self.deg_to_dms(float(data[1]))
    # altimiter
    alt = float(data[3])
    gps_qual = "1"
    num_sats = "08"
    nmea = pynmea2.GGA(
        'GP',
        'GGA',
        (ts, str(lat), lat_dir, str(long), long_dir, gps_qual, num_sats, '2.6', str(alt), 'M', '0', 'M', '', '0000')
    )
    return str(nmea)

  def build_rmc(self, data):
    """
    RMC - NMEA has its own version of essential gps pvt (position, velocity, time) data.
     It is called RMC, The Recommended Minimum, which will look similar to:
     $GPRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*6A

    Where:
         RMC          Recommended Minimum sentence C
         123519       Fix taken at 12:35:19 UTC
         A            Status A=active or V=Void.
         4807.038,N   Latitude 48 deg 07.038' N
         01131.000,E  Longitude 11 deg 31.000' E
         022.4        Speed over the ground in knots
         084.4        Track angle in degrees True
         230394       Date - 23rd of March 1994
         003.1,W      Magnetic Variation
         *6A          The checksum data, always begins with *

    :param data:
    :return:
    """
    ts = datetime.datetime.utcnow().strftime("%H%M%S")
    date = datetime.datetime.utcnow().strftime("%d%m%y")

    long = self.deg_to_dms(float(data[1]))
    lat = self.deg_to_dms(float(data[2]))
    alt = float(data[3])
    hdg = float(data[4])
    spd = float(data[5]) * 1.945  # knots to m/s

    lat_dir = "N"
    long_dir = "E"
    nmea = pynmea2.RMC(
        'GP',
        'RMC',
        (ts, 'A', str(lat), lat_dir, str(long), long_dir, str(spd), str(hdg), date, "003.1", "W")
    )
    return str(nmea)


if __name__ == '__main__':
  runner = AHRS2NMEA()
  runner.run(source, dest)
