# geekworm2domoticz
Extract data from Geekworm UPS X708 and send to Domoticz

Open
sudo nano /etc/crontab

add the following line, this will retrieve the information every minute.
"*  *    * * *   root    /home/pi/request.py"
